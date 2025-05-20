from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import UserMessage, AssistantMessage, SystemMessage

s_model_context = BufferedChatCompletionContext(buffer_size=5)

user_message = UserMessage(content="你好", source="user")
assistant_message = AssistantMessage(content="你好，我是assistant", source="assistant")
system_messages = [SystemMessage(content="You are a helpful AI assistant.")]
