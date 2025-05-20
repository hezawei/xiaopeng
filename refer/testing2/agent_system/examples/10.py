import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console

from agent_system.llms import model_client
async def get_document_from_file(page_num: int):
    print(page_num)
    return f"文档内容{page_num}"
requirement_acquisition_agent = AssistantAgent(
    name="requirement_acquisition_agent",
    model_client=model_client,
    tools=[get_document_from_file],
    system_message="调用工具获取文档内容，当前需要获取的文档为10页，需要分别调用10次函数进行数据读取，每次调用需要传入页码",
    model_client_stream=False,
)
asyncio.run(Console(requirement_acquisition_agent.run_stream(task="读取数据")))