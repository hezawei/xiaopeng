from autogen_core.models import ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient
# pip install -U "autogen-agentchat"
# pip install -U "autogen-ext[openai]"

model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-aec84097bc1b4f1fb5398790825bb379",
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
    },
)