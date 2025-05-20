from fastapi import FastAPI, APIRouter, WebSocket, Depends, HTTPException
import asyncio
import autogen
from .llms import model_client
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
router = APIRouter()



# 模拟 AutoGen 需求分析函数
async def analyze_requirements(requirements: str) -> str:
    """模拟需求分析过程"""

    assistant = autogen.AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message="你是一个高级需求分析师."
    )
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
    )

    # 模拟对话
    user_proxy.initiate_chat(assistant, message=requirements)
    result = ""
    while not user_proxy.chat_messages[assistant][-1]["content"].endswith("END"):
        await asyncio.sleep(1)  # 模拟流式输出延迟
        result += user_proxy.chat_messages[assistant][-1]["content"]
        yield result
    yield result + "END"

# WebSocket 路由
@router.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        requirements = data.get("requirements", "")
        if not requirements:
            await websocket.send_json({"error": "No requirements provided."})
            return

        async for output in analyze_requirements(requirements):
            if output.endswith("END"):
                output = output[:-3]  # 去掉结束标记
            await websocket.send_json({"content": output})
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()

# REST API 路由（可选）
@router.post("/analyze")
async def analyze_post(requirements: str):
    """通过 POST 请求分析需求"""
    if not requirements:
        raise HTTPException(status_code=400, detail={"error": "No requirements provided."})
    result = ""
    # print(result)
    async for output in analyze_requirements(requirements):
        result = output
        # print(result)
    return {"result": result}