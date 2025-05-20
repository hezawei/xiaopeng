import json
import logging
import os
import uuid
from typing import Any

import aiofiles
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage, UserInputRequestedEvent, ToolCallSummaryMessage
from autogen_core import CancellationToken
from fastapi import APIRouter, Query, HTTPException
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.schemas import Success
from .agents import RequirementAnalysisAgent

from fastapi import File, UploadFile
from pathlib import Path


logger = logging.getLogger(__name__)

router = APIRouter()

async def get_history(history_path: str) -> list[dict[str, Any]]:
    """Get chat history from file."""
    if not os.path.exists(history_path):
        return []
    async with aiofiles.open(history_path, "r") as file:
        return json.loads(await file.read())


@router.get("/history")
async def history(user_id: int = Query(..., description="用户ID"),) -> list[dict[str, Any]]:
    try:
        return await get_history(str(user_id)+"_history.json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.websocket("/ws/analyze")
async def analyze_requirements(websocket: WebSocket):
    await websocket.accept()
    requirements_analysis_agent = None
    is_final = False
    # User input function used by the team.
    async def _user_input(prompt: str, cancellation_token: CancellationToken | None) -> str:
        # 等待用户输入（代码阻塞执行）
        data = await websocket.receive_json()
        # 开始新一轮对话
        nonlocal is_final
        is_final = False
        requirements_analysis_agent.files = [file['path'] for file in data['files']]
        message = TextMessage.model_validate(data)
        return message.content

    try:
        while True:
            # Get user message.
            data = await websocket.receive_json()
            request = TextMessage.model_validate(data)
            requirements_analysis_agent = RequirementAnalysisAgent(files=[file['path'] for file in data['files']])
            user_id = str(data.get("user_id"))
            try:
                # Get the team and respond to the message.
                # team = await get_team(_user_input)
                team = await requirements_analysis_agent.create_team(user_input_func=_user_input)
                history = await get_history(user_id + "_history.json")
                stream = team.run_stream(task=request)

                async for message in stream:
                    if is_final or isinstance(message, TaskResult):
                        continue
                    msg = message.model_dump()
                    msg["is_final"] = is_final
                    # 首先给出提示
                    if message.source == "user":
                        await websocket.send_json(message.model_dump())

                        msg["source"] = "需求获取智能体"
                        msg["content"] = "需求获取智能体启动，正在解析需求文件......"

                        await websocket.send_json(msg)

                    elif (message.source == "requirement_acquisition_agent"
                          and isinstance(message,ToolCallSummaryMessage)):
                        # 发送需求获取智能体输出的结果
                        msg["source"] = "需求获取智能体"
                        await websocket.send_json(msg)

                        # 输出下一个即将执行的智能体提示
                        msg["source"] = "需求分析智能体"
                        msg["content"] = "需求分析智能体启动，正在执行需求分析......"
                        await websocket.send_json(msg)
                    elif message.source == "requirement_analysis_agent" and isinstance(message, TextMessage):
                        # 发送需求分析智能体输出的结果
                        msg["source"] = "需求分析智能体"
                        await websocket.send_json(msg)

                        # 输出下一个即将执行的智能体提示
                        msg["source"] = "需求结构化智能体"
                        msg["content"] = "需求结构化智能体启动，正在执行需求结构化输出......"
                        await websocket.send_json(msg)
                    elif message.source == "requirement_output_agent" and isinstance(message, TextMessage):
                        msg["source"] = "需求结构化智能体"
                        await websocket.send_json(msg)

                        msg["source"] = "数据库智能体"
                        msg["content"] = "数据库智能体启动，正在执行数据入库操作......"
                        await websocket.send_json(msg)
                    elif message.source == "requirement_into_db_agent" and isinstance(message, ToolCallSummaryMessage):
                        msg["source"] = "数据库智能体"
                        is_final = True
                        msg["is_final"] = is_final
                        await websocket.send_json(msg)

                    # await websocket.send_json(message.model_dump())
                    if not isinstance(message, UserInputRequestedEvent):
                        # Don't save user input events to history.
                        history.append(message.model_dump())

                # Save team state to file.
                async with aiofiles.open(user_id + "_state.json", "w") as file:
                    state = await team.save_state()
                    await file.write(json.dumps(state))

                # Save chat history to file.
                async with aiofiles.open(user_id + "_history.json", "w") as file:
                    await file.write(json.dumps(history))

            except Exception as e:
                # Send error message to client
                error_message = {
                    "type": "error",
                    "content": f"Error: {str(e)}",
                    "source": "system"
                }
                await websocket.send_json(error_message)
                # Re-enable input after error
                await websocket.send_json({
                    "type": "UserInputRequestedEvent",
                    "content": "An error occurred. Please try again.",
                    "source": "system"
                })

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Unexpected error: {str(e)}",
                "source": "system"
            })
        except:
            pass


@router.post("/upload", summary="上传文件")
async def upload_file(
        user_id: int = Query(..., description="用户ID"),
        file: UploadFile = File(..., description="上传的文件")
):
    """处理文件上传并返回存储路径"""
    # 文件类型验证
    ALLOWED_TYPES = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain"
    ]
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, detail=f"不支持的文件类型: {file.content_type}")

    try:
        upload_dir = Path("uploads") / str(user_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        file_ext = Path(file.filename).suffix
        uuid_name = f"{uuid.uuid4().hex}{file_ext}"
        file_path = upload_dir / uuid_name

        # 流式写入文件并控制大小
        max_size = 10 * 1024 * 1024  # 10MB
        total_size = 0
        async with aiofiles.open(file_path, "wb") as buffer:
            while chunk := await file.read(8192):
                total_size += len(chunk)
                if total_size > max_size:
                    await buffer.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(413, detail="文件大小超过10MB限制")
                await buffer.write(chunk)

        return Success(data={
            "filePath": file_path.as_posix(),
            "fileId": uuid_name,
            "fileName": file.filename
        })
        # return {
        #     "filePath": file_path.as_posix(),
        #     "fileId": uuid_name,
        #     "fileName": file.filename
        # }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(500, detail="文件上传失败") from e