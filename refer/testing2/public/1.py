import asyncio

from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_agentchat.ui import Console
from llms import model_client

async def example_usage1():
    m1 = MagenticOne(client=model_client)
    task = "编写pytest脚本测试登录的功能，并将测试用例保存到到Python脚本中"
    result = await Console(m1.run_stream(task=task))
    print(result)

async def example_usage2():
    m1 = FileSurfer(model_client=model_client, name="coder")
    task = "请将下列内容保存到到Python脚本中:print('hello')"
    result = await Console(m1.run_stream(task=task))
    print(result)

if __name__ == "__main__":
    asyncio.run(example_usage1())