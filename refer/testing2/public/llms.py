from autogen_ext.models.openai import OpenAIChatCompletionClient
# pip install -U "autogen-agentchat"
# pip install -U "autogen-ext[openai]"

model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-efe87e8de6c8431ab7dcb824823efc7c",
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": "unknown",
    },
)