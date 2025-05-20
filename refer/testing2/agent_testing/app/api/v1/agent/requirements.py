import json
import logging
import os
import uuid
from typing import Any

import aiofiles
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage, UserInputRequestedEvent, ToolCallSummaryMessage
from autogen_core import CancellationToken, ClosureContext, MessageContext
from fastapi import APIRouter, Query, HTTPException
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.schemas import Success
from .requirement_agents import RequirementFilesMessage, ResponseMessage, start_runtime

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


@router.get("/requirements/history")
async def history(user_id: int = Query(..., description="用户ID"),) -> list[dict[str, Any]]:
    try:
        return await get_history(str(user_id)+"_history.json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.websocket("/ws/analyze")
async def analyze_requirements(websocket: WebSocket):
    await websocket.accept()

    # 将收到的消息发送给前端（浏览器）
    async def collect_result(_agent: ClosureContext, message: ResponseMessage, ctx: MessageContext) -> None:
        msg = message.model_dump()
        print("返回的消息：", msg)
        # 将收到的消息发送给前端（浏览器）
        await websocket.send_json(msg)
    
    async def _user_input(prompt: str, cancellation_token: CancellationToken | None) -> str:
        # 等待用户输入（代码阻塞执行）,下面的代码的效果类似 input
        data = await websocket.receive_json()
        message = TextMessage.model_validate(data)
        return message.content

    try:
        while True:
            data = await websocket.receive_json()
            
            # 创建需求文件消息
            requirement_files = RequirementFilesMessage(
                user_id=str(data.get("userId", "")),
                files=[file['path'] for file in data.get('files', [])],
                content=data.get("content", ""),
                task=data.get("task", "分析需求文档")
            )
            
            try:
                # 启动需求分析运行时
                await start_runtime(
                    requirement_files=requirement_files,
                    collect_result=collect_result,
                    user_input_func=_user_input
                )
            except Exception as e:
                # 发送错误消息给客户端
                error_message = {
                    "type": "error",
                    "content": f"Error: {str(e)}",
                    "source": "system"
                }
                await websocket.send_json(error_message)
                # 错误后重新启用输入
                await websocket.send_json({
                    "type": "UserInputRequestedEvent",
                    "content": "发生错误，请重试。",
                    "source": "system"
                })

    except WebSocketDisconnect:
        logger.info("客户端断开连接")
    except Exception as e:
        logger.error(f"意外错误: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"意外错误: {str(e)}",
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
    # ALLOWED_TYPES = [
    #     "application/pdf",
    #     "application/msword",
    #     "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    #     "text/plain"
    # ]
    # if file.content_type not in ALLOWED_TYPES:
    #     raise HTTPException(400, detail=f"不支持的文件类型: {file.content_type}")

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
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(500, detail="文件上传失败") from e