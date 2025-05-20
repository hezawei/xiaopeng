import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage
from autogen_core.models import ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-3f0a16cad7ff45f1a0596c13cc489e23",
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
    },
)
async def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f" {city} 晴天, 温度 25°C"
async def main() -> None:
    agent = AssistantAgent("assistant", model_client=model_client, model_client_stream=True)#, tools=[get_weather])
    async for message in agent.run_stream(task="给出一个北京旅行计划"):
        if isinstance(message, ModelClientStreamingChunkEvent):
            print(message.content)
        elif isinstance(message, TextMessage) and message.models_usage is not None:
            print(message.models_usage.completion_tokens)
        elif isinstance(message, TaskResult):
            print(message.messages[-1].content)

asyncio.run(main())