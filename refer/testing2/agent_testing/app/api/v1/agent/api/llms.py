# model_client.py
# LLM模型客户端实现

import os
import logging
from typing import Dict, List, Optional, Any, Union

# 配置日志
logger = logging.getLogger("model_client")

from autogen_core.models import ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os
import logging
# pip install -U "autogen-agentchat"
# pip install -U "autogen-ext[openai]"

# 配置日志
logger = logging.getLogger("model_client")

# 设置超时和重试
TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "120"))
MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))

# 默认API配置
DEFAULT_MODEL = os.environ.get("DEFAULT_LLM_MODEL", "deepseek-chat")
DEFAULT_API_BASE = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")
DEFAULT_API_KEY = os.environ.get("LLM_API_KEY", "sk-aec84097bc1b4f1fb5398790825bb379")
def create_model_client():
    try:
        client = OpenAIChatCompletionClient(
            model=DEFAULT_MODEL,
            base_url=DEFAULT_API_BASE,
            api_key=DEFAULT_API_KEY,
            max_retries=MAX_RETRIES,
            model_info={
                "vision": False,
                "function_calling": True,
                "json_output": True,
                "family": ModelFamily.UNKNOWN,
            },
        )
        logger.info(f"初始化模型客户端成功: {DEFAULT_MODEL}, API Base: {DEFAULT_API_BASE}")
        return client

    except Exception as e:
        logger.error(f"初始化模型客户端失败: {str(e)}")


# 创建全局模型客户端实例
model_client = create_model_client()
