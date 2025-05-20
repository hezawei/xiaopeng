# pip install autogen-ext[http-tool]

import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.http import HttpTool

# Define a JSON schema for a base64 decode tool
base64_schema = {
    "type": "object",
    "properties": {
        "value": {"type": "string", "description": "The base64 value to decode"},
    },
    "required": ["value"],
}

# Create an HTTP tool for the httpbin API
base64_tool = HttpTool(
    name="base64_decode",
    description="base64 decode a value",
    scheme="https",
    host="httpbin.org",
    port=443,
    path="/base64/{value}",
    method="GET",
    json_schema=base64_schema,
)


async def main():
    # Create an assistant with the base64 tool
    from agent_system.llms import model_client
    assistant = AssistantAgent("base64_assistant", model_client=model_client, tools=[base64_tool])

    # The assistant can now use the base64 tool to decode the string
    response = await assistant.on_messages(
        [TextMessage(content="Can you base64 decode the value 'YWJjZGU=', please?", source="user")],
        CancellationToken(),
    )
    print(response.chat_message.content)


asyncio.run(main())