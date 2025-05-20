from typing import List, cast, Optional, Dict

import chainlit as cl
import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient
from autogen_core.tools import FunctionTool

from llms import model_client

# pip install duckduckgo-search
@cl.set_starters  # type: ignore
async def set_starts() -> List[cl.Starter]:
    return [
        cl.Starter(
            label="问候",
            message="有什么可以帮助您的？",
        ),
        cl.Starter(
            label="天气",
            message="查询一下杭州的天气情况？",
        ),
    ]


@cl.step(type="tool")
async def web_search(
        query: str,
        region: Optional[str] = "wt-wt",
        max_results: Optional[int] = 10,
) -> List[Dict]:
    """
    Make a query to DuckDuckGo search to receive a full search results.

    Args:
        query (str): The query to be passed to DuckDuckGo.
        region (Optional[str]): The region to be used for the search in [country-language] convention, ex us-en, uk-en, ru-ru, etc...
        max_results (Optional[int]): The maximum number of results to be returned.
    """
    from duckduckgo_search import DDGS

    params = {
        "keywords": query,
        "region": region,
        "max_results": max_results,
    }

    with DDGS() as ddg:
        return list(ddg.text(**params))

@cl.step(type="tool")  # type: ignore
async def get_weather(city: str) -> str:
    """获取某个城市的天气"""
    return f"{city} 的天气是晴天，温度是 25°C。"

# tool_weather = FunctionTool(get_weather, description="获取某个城市的天气")
@cl.on_chat_start  # type: ignore
async def start_chat() -> None:

    # Create the assistant agent with the get_weather tool.
    assistant = AssistantAgent(
        name="assistant",
        tools=[get_weather, web_search],
        model_client=model_client,
        system_message="You are a helpful assistant",
        model_client_stream=True,  # Enable model client streaming.
        reflect_on_tool_use=True,  # 函数返回的结果会再次发给LLM进行加工处理
    )

    # Set the assistant agent in the user session.
    cl.user_session.set("prompt_history", "")  # type: ignore
    cl.user_session.set("agent", assistant)  # type: ignore


@cl.on_message  # type: ignore
async def chat(message: cl.Message) -> None:
    # Get the assistant agent from the user session.
    agent = cast(AssistantAgent, cl.user_session.get("agent"))  # type: ignore
    # Construct the response message.
    response = cl.Message(content="")

    async for msg in agent.on_messages_stream(
        messages=[TextMessage(content=message.content, source="user")],
        cancellation_token=CancellationToken(),
    ):
        if isinstance(msg, ModelClientStreamingChunkEvent):
            # Stream the model client response to the user.
            await response.stream_token(msg.content)
        elif isinstance(msg, Response):
            # Done streaming the model client response. Send the message.
            await response.send()
