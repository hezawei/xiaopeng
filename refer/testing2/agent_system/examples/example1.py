import asyncio

from autogen_core.models import UserMessage, SystemMessage
from agent_system.llms import model_client
async def main_1():
    result = await model_client.create([SystemMessage(content="你是一位旅游博主"), UserMessage(content="请介绍一下杭州", source="user")])
    print(result.content)
async def main_2():
    result = model_client.create_stream([UserMessage(content="请介绍一下杭州", source="user")])
    async for msg in result:
        print(msg)
# asyncio.run(main_2())

