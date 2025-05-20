from typing import Dict

from autogen_core.models import ModelCapabilities, ModelInfo, ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.openai._model_info import _MODEL_INFO, _MODEL_TOKEN_LIMITS

DEEPSEEK_MODELS: Dict[str, ModelInfo]  = {
    "deepseek-chat": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
    },
}
DEEPSEEK_TOKEN_LIMITS: Dict[str, int] = {
    "deepseek-chat": 128000,
}
_MODEL_INFO.update(DEEPSEEK_MODELS)
_MODEL_TOKEN_LIMITS.update(DEEPSEEK_TOKEN_LIMITS)



DEEPSEEK_MODELS_V3: Dict[str, ModelInfo]  = {
    "deepseek-v3": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
    },
}
DEEPSEEK_TOKEN_LIMITS_V3: Dict[str, int] = {
    "deepseek-v3": 128000,
}
_MODEL_INFO.update(DEEPSEEK_MODELS_V3)
_MODEL_TOKEN_LIMITS.update(DEEPSEEK_TOKEN_LIMITS_V3)

model_client = OpenAIChatCompletionClient(
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-d86cc49e3ec0449b9d59635ba7283299",
        )

# model_client = OpenAIChatCompletionClient(
#             model="deepseek-v3",
#             base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
#             api_key="sk-d86cc49e3ec0449b9d59635ba7283299",
#             max_tokens=8192
#         )