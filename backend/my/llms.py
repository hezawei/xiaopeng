from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelFamily

# 配置模型客户端
model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",  # 切换到支持函数调用的模型
    api_key="sk-cdb5b06b8ebd4a44a546371052d72f96",  # 请替换为你的API密钥
    base_url="https://api.deepseek.com/v1",  # 可以替换为其他API端点
    model_info={
        "function_calling": True,
        "json_output": True,
        "vision": False,
        "family": ModelFamily.R1,
    },
    # 设置较小的最大token数，防止超出模型限制
    max_tokens=1000
)
