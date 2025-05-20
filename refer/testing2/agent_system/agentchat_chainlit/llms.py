from autogen_ext.models.openai import OpenAIChatCompletionClient
# pip install -U "autogen-agentchat"
# pip install -U "autogen-ext[openai]"

model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-e5b2a319f9ce4d0fb71c5dc96596a69d",
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": "unknown",
    },
)