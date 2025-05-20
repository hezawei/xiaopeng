import asyncio
from autogen_core.models import UserMessage, ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(
        model="deepseek-reasoner",
        api_key="sk-e5b2a319f9ce4d0fb71c5dc96596a69d",
        base_url="https://api.deepseek.com/v1",
        model_info={
            "function_calling": False,
            "json_output": False,
            "vision": False,
            "family": ModelFamily.R1,
        }
    )
    create_result = await model_client.create(
        messages=[
            UserMessage(
                content="性能测试思路",
                source="user",
            ),
        ]
    )
    # CreateResult.thought field contains the thinking content.
    print(create_result.thought)
    print(create_result.content)

asyncio.run(main())
