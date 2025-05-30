import asyncio

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import TextMentionTermination, TextMessageTermination
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from llms import model_client
# Create the agents.
assistant = AssistantAgent("assistant", model_client=model_client)
#
# async def main():
#     s = await assistant.run(task="编写一首4句古诗")
#     print(s)
user_proxy = UserProxyAgent("user_proxy", input_func=input)  # Use input() to get user input from console.

# Create the termination condition which will end the conversation when the user says "APPROVE".
termination1 = TextMentionTermination("APPROVE")
termination3 = TextMentionTermination("同意")
termination2 = TextMessageTermination("assistant")
# Create the team.
team = RoundRobinGroupChat([assistant, user_proxy], termination_condition=termination1 | termination3)

# Run the conversation and stream to the console.
stream = team.run_stream(task="编写一首4句古诗")
# Use asyncio.run(...) when running in a script.
async def main():
    async for message in stream:
        if isinstance(message, TaskResult):
            # print(message.messages[-1].content)
            continue

        if isinstance(message, TextMessage) and message.source == "assistant":
            print(message.content)
            continue

        if message.source == "user_proxy":
            continue

asyncio.run(main())