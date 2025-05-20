from typing import List, cast

import chainlit as cl
import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient
from llms import model_client

@cl.on_chat_start  # type: ignore
async def start_chat() -> None:
    # Create the assistant agent.
    assistant = AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message="You are a helpful assistant.",
        model_client_stream=True,  # Enable model client streaming.
    )

    # Create the critic agent.
    critic = AssistantAgent(
        name="critic",
        model_client=model_client,
        system_message="你是一位批评者。请提供建设性反馈"
        "如果你的反馈意见被采纳，请回复`APPROVE`",
        model_client_stream=True,  # Enable model client streaming.
    )

    # Termination condition.
    termination = TextMentionTermination("APPROVE", sources=["critic"])

    # Chain the assistant and critic agents using RoundRobinGroupChat.
    group_chat = RoundRobinGroupChat([assistant, critic], termination_condition=termination)

    # Set the assistant agent in the user session.
    cl.user_session.set("prompt_history", "")  # type: ignore
    cl.user_session.set("team", group_chat)  # type: ignore


@cl.set_starters  # type: ignore
async def set_starts() -> List[cl.Starter]:
    return [
        cl.Starter(
            label="诗词写作",
            message="编写一首关于春天的诗",
        ),
        cl.Starter(
            label="故事写作",
            message="写一个关于侦探解开谜团的故事。",
        ),
        cl.Starter(
            label="编写代码",
            message="编写一段 Python代码，要求实现一个简单的文本分类器。",
        ),
    ]


@cl.on_message  # type: ignore
async def chat(message: cl.Message) -> None:
    # Get the team from the user session.
    team = cast(RoundRobinGroupChat, cl.user_session.get("team"))  # type: ignore
    # Streaming response message.
    streaming_response: cl.Message | None = None
    # Stream the messages from the team.
    async for msg in team.run_stream(
        task=[TextMessage(content=message.content, source="user")],
        cancellation_token=CancellationToken(),
    ):
        if isinstance(msg, ModelClientStreamingChunkEvent):
            # Stream the model client response to the user.
            if streaming_response is None:
                # Start a new streaming response.
                streaming_response = cl.Message(content="", author=msg.source)
            await streaming_response.stream_token(msg.content)
        elif streaming_response is not None:
            # Done streaming the model client response.
            # We can skip the current message as it is just the complete message
            # of the streaming response.
            await streaming_response.send()
            # Reset the streaming response so we won't enter this block again
            # until the next streaming response is complete.
            streaming_response = None
        elif isinstance(msg, TaskResult):
            # Send the task termination message.
            final_message = "Task terminated. "
            if msg.stop_reason:
                final_message += msg.stop_reason
            await cl.Message(content=final_message).send()
        else:
            # Skip all other message types.
            pass
