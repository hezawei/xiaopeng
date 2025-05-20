import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken

from llms import model_client
streaming_assistant = AssistantAgent(
    name="assistant",
    model_client=model_client,
    system_message="You are a helpful assistant.",
    # model_client_stream=True,  # Enable streaming tokens.
)
async def main():
    async for message in streaming_assistant.on_messages_stream(  # type: ignore
        [TextMessage(content="写一首七言绝句", source="user")],
        cancellation_token=CancellationToken(),
    ):
        print(message)
async def main2():
    stream = streaming_assistant.run_stream(task="写一首七言绝句")
    async for message in stream:
        print(message)
asyncio.run(main2())
