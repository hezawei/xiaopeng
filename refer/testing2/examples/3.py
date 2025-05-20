from typing import Dict

from llama_index.core import Settings
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.llms.openai import OpenAI
from llama_index.llms.openai.utils import ALL_AVAILABLE_MODELS, CHAT_MODELS
DEEPSEEK_MODELS: Dict[str, int] = {
    "deepseek-chat": 128000,
}
ALL_AVAILABLE_MODELS.update(DEEPSEEK_MODELS)
CHAT_MODELS.update(DEEPSEEK_MODELS)

llm = OpenAI(
    model="deepseek-chat",
    api_key="sk-ccd05ac9657c49dca6102828df9ec255",  # uses OPENAI_API_KEY env var by default
    api_base="https://api.deepseek.com/v1",
)

Settings.llm = llm
chat_engine = SimpleChatEngine.from_defaults()
chat_engine.streaming_chat_repl()
