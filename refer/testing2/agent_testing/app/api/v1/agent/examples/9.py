# pip install mcp-server-fetch autogen-ext[mcp]

import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools

from llms import model_client
async def main() -> None:
    # Get the fetch tool from mcp-server-fetch.
    fetch_mcp_server = StdioServerParams(command="cmd", args=["/c", "npx", '-y', '@pydantic/mcp-run-python', 'stdio'])
    tools = await mcp_server_tools(fetch_mcp_server)

    # Create an agent that can use the fetch tool.
    agent = AssistantAgent(name="fetcher", model_client=model_client, tools=tools, reflect_on_tool_use=True)  # type: ignore

    # Let the agent fetch the content of a URL and summarize it.
    result = agent.run_stream(task="运行python脚本：print('hello, world')")
    async for message in result:
        print(message)


asyncio.run(main())