from autogen_ext.models.openai import OpenAIChatCompletionClient
# pip install -U "autogen-agentchat"
# pip install -U "autogen-ext[openai]"

model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-3f0a16cad7ff45f1a0596c13cc489e23",
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": "unknown",
    },
)