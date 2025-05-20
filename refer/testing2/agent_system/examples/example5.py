import asyncio
from dataclasses import dataclass

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.ui import Console
from autogen_core import RoutedAgent, MessageContext, message_handler, AgentId
from autogen_ext.models.openai import OpenAIChatCompletionClient
from agent_system.llms import model_client
@dataclass
class MyMessageType:
    content: str

async def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f" {city} 晴天, 温度 25°C"

class MyAssistant(RoutedAgent):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._delegate = AssistantAgent(name,
                                        system_message="借助工具回复用户问题",
                                        model_client=model_client,
                                        tools=[get_weather],
                                        reflect_on_tool_use=True)

    @message_handler
    async def handle_my_message_type(self, message: MyMessageType, ctx: MessageContext) -> None:
        print(f"{self.id.type} received message: {message.content}")
        await Console(self._delegate.run_stream(task="北京今天的天气咋样"))
        # response = await self._delegate.on_messages(
        #     [TextMessage(content=message.content, source="user")], ctx.cancellation_token
        # )
        # print(f"{self.id.type} responded: {response.chat_message.content}")


async def main():
    from autogen_core import SingleThreadedAgentRuntime

    runtime = SingleThreadedAgentRuntime()
    await MyAssistant.register(runtime, "my_assistant", lambda: MyAssistant("my_assistant"))

    runtime.start()  # Start processing messages in the background.
    await runtime.send_message(MyMessageType("Hello, World!"), AgentId("my_assistant", "default"))
    await runtime.stop()  # Stop processing messages in the background.

asyncio.run(main())