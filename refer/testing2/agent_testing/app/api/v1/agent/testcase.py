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

from fastapi import File, UploadFile
from pathlib import Path
from .testcase_agents import ResponseMessage, RequirementMessage, start_runtime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/generate")
async def generate_testcase(websocket: WebSocket):
    await websocket.accept()

    # 前端发送任何智能体执行的结果
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
            requirement = RequirementMessage.model_validate(data)
            try:
                await start_runtime(requirement=requirement,
                                    collect_result=collect_result,
                                    user_input_func=_user_input)

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
