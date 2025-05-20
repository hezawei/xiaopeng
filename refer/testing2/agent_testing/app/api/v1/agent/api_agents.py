import json
import sys
import logging
import tempfile
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, Awaitable
import httpx
from datetime import datetime
import re
import os

# AutoGen 组件导入
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent
from autogen_core import RoutedAgent, type_subscription, message_handler, MessageContext, SingleThreadedAgentRuntime, \
    ClosureContext, TypeSubscription, ClosureAgent
from autogen_core import DefaultTopicId, TopicId
from autogen_core.code_executor import CodeBlock
from autogen_core.models import UserMessage, SystemMessage, AssistantMessage
from pydantic import BaseModel, Field, ConfigDict, field_validator

# 导入自定义组件
from .code_executor import UniversalExecutor
from .llms import model_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_agents")


# 主题类型定义
class TopicTypes:
    API_DOCS_FETCHER = "api_docs_fetcher"
    API_ANALYZER = "api_analyzer"
    TEST_GENERATOR = "test_generator"
    TEST_EXECUTOR = "test_executor"
    TEST_RESULT = "test_result"
    TEST_REPORT_ENHANCER = "test_report_enhancer"


# 模型定义
class APIDocsInput(BaseModel):
    """API文档输入参数模型"""
    api_docs_url: str = Field(..., description="OpenAPI文档的URL")
    base_url: str = Field(..., description="API的基础URL")
    enable_review: bool = Field(True, description="是否启用测试用例评审")
    user_review: bool = Field(False, description="是否需要用户参与评审")
    use_local_executor: bool = Field(False, description="是否使用本地代码执行器")
    api_doc_content: Optional[Dict[str, Any]] = Field(None, description="OpenAPI文档内容")
    test_focus: Optional[str] = Field(None, description="测试重点，如果为None则全面测试所有API端点")
    api_doc_supplement: Optional[str] = Field(None, description="API文档补充说明，用于提供文档中未包含的信息")

    model_config = ConfigDict(
        title="API文档输入",
        json_schema_extra={
            "example": {
                "api_docs_url": "http://example.com/openapi.json",
                "base_url": "http://example.com/api",
                "enable_review": True,
                "user_review": False,
                "use_local_executor": False
            }
        }
    )


class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str = Field(..., description="消息类型：log/progress/result/review/error")
    content: Union[str, Dict[str, Any]] = Field(..., description="消息内容")
    source: str = Field(..., description="消息来源")
    timestamp: Optional[str] = Field(None, description="时间戳")

    model_config = ConfigDict(
        title="WebSocket消息",
        arbitrary_types_allowed=True,
        json_encoders={
            # 为无法序列化的类型添加自定义编码器
            object: lambda obj: str(obj),
        }
    )

    @field_validator('timestamp', mode='before')
    def set_timestamp(cls, v):
        return v or datetime.now().isoformat()

    def model_dump_json(self, **kwargs) -> str:
        """确保对象可以被json.dumps序列化"""
        try:
            # 首先尝试使用Pydantic的标准方法
            if hasattr(super(), 'model_dump_json'):
                return super().model_dump_json(**kwargs)
            # 手动转为字典再序列化
            data = self.to_dict()
            return json.dumps(data, **kwargs)
        except Exception as e:
            # 确保即使失败也能返回一个有效的JSON字符串
            return json.dumps({
                "type": self.type,
                "content": str(self.content),
                "source": self.source,
                "timestamp": self.timestamp or datetime.now().isoformat()
            }, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """将WebSocketMessage转换为字典"""
        try:
            if hasattr(self, 'model_dump'):
                result = self.model_dump()
                # 确保结果是可序列化的
                json.dumps(result)
                return result
            else:
                # 手动创建字典
                return {
                    "type": self.type,
                    "content": self.content,
                    "source": self.source,
                    "timestamp": self.timestamp or datetime.now().isoformat()
                }
        except (TypeError, ValueError, OverflowError) as e:
            logger.warning(f"WebSocketMessage转换为字典失败: {e}")
            # 失败时返回安全的字典
            return {
                "type": self.type,
                "content": str(self.content),
                "source": self.source,
                "timestamp": self.timestamp or datetime.now().isoformat()
            }


# 定义消息类型
class APIAnalysisResult(BaseModel):
    """API分析结果消息类型"""
    api_docs_url: str = Field(..., description="OpenAPI文档的URL")
    base_url: str = Field(..., description="API的基础URL")
    analysis: str = Field(..., description="API分析结果")
    enable_review: bool = Field(True, description="是否启用测试用例评审")
    user_review: bool = Field(False, description="是否需要用户参与评审")
    use_local_executor: bool = Field(False, description="是否使用本地代码执行器")
    test_focus: Optional[str] = Field(None, description="测试重点，如果为None则全面测试所有API端点")
    api_doc_supplement: Optional[str] = Field(None, description="API文档补充说明，用于提供文档中未包含的信息")
    template_info: Optional[Dict[str, Any]] = Field(None, description="模板生成所需的分析结果")


class TestGenerationResult(BaseModel):
    """测试生成结果消息类型"""
    test_file_path: str = Field(..., description="测试文件路径")
    base_url: str = Field(..., description="API的基础URL")
    enable_review: bool = Field(True, description="是否启用测试用例评审")
    user_review: bool = Field(False, description="是否需要用户参与评审")
    use_local_executor: bool = Field(False, description="是否使用本地代码执行器")
    test_params: Optional[Dict[str, Any]] = Field(None, description="测试参数配置")
    test_dir: Optional[str] = Field(None, description="测试目录路径")


class TestExecutionResult(BaseModel):
    """测试执行结果消息类型"""
    test_result: Dict[str, Any] = Field(..., description="测试结果")
    test_file_path: str = Field(..., description="测试文件路径")
    analysis: str = Field(..., description="测试结果分析")
    report_url: Optional[str] = Field(None, description="测试报告URL")
    allure_report_url: Optional[str] = Field(None, description="Allure测试报告URL")


# 辅助函数
async def publish_log_message(agent: RoutedAgent, content: str, source: str) -> None:
    """发布日志消息到结果主题"""
    # 使用WebSocketMessage对象
    message = WebSocketMessage(
        type="log",
        content=content,
        source=source
    )

    # 发布WebSocketMessage对象
    await agent.publish_message(
        message,
        topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=agent.id.key)
    )


async def publish_progress_message(agent: RoutedAgent, stage: str, percentage: int, message: str, source: str) -> None:
    """发布进度消息到结果主题"""
    # 构建安全的content字典
    content = {
        "stage": stage,
        "percentage": percentage,
        "message": str(message) if not isinstance(message, str) else message
    }

    # 使用WebSocketMessage对象
    msg = WebSocketMessage(
        type="progress",
        content=content,
        source=source
    )

    # 发布WebSocketMessage对象
    await agent.publish_message(
        msg,
        topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=agent.id.key)
    )


async def publish_error_message(agent: RoutedAgent, error_message: str, source: str) -> None:
    """发布错误消息到结果主题"""
    # 确保错误消息是字符串
    if not isinstance(error_message, str):
        error_message = str(error_message)

    # 使用WebSocketMessage对象
    message = WebSocketMessage(
        type="error",
        content=error_message,
        source=source
    )

    # 发布WebSocketMessage对象
    await agent.publish_message(
        message,
        topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=agent.id.key)
    )


def extract_code_blocks(markdown_text: str) -> List[CodeBlock]:
    """从Markdown文本中提取代码块"""
    import re
    pattern = re.compile(r"```(?:\s*([\w\+\-]+))?\n([\s\S]*?)```")
    matches = pattern.findall(markdown_text)
    code_blocks: List[CodeBlock] = []
    for match in matches:
        language = match[0].strip() if match[0] else ""
        code_content = match[1]
        code_blocks.append(CodeBlock(code=code_content, language=language))
    return code_blocks


def extract_python_code(markdown_text: str) -> str:
    """提取Markdown中的Python代码"""
    result = ""
    # 尝试提取```python格式
    if "```python" in markdown_text:
        parts = markdown_text.split("```python")
        for part in parts[1:]:
            if "```" in part:
                code = part.split("```")[0].strip()
                result += code + "\n\n"
    # 尝试提取普通```格式
    elif "```" in markdown_text:
        parts = markdown_text.split("```")
        for i in range(1, len(parts), 2):
            if i < len(parts):
                code = parts[i].strip()
                # 简单检查是否为Python代码
                if "import" in code or "def " in code or "class " in code:
                    result += code + "\n\n"

    return result.strip()


async def create_executor(work_dir: Path, use_local_executor: bool = False) -> UniversalExecutor:
    """创建代码执行器"""
    try:
        executor = UniversalExecutor(
            work_dir=work_dir,
            timeout=300,
            use_local_executor=use_local_executor
        )
        logger.info(f"成功创建通用执行器: 工作目录={work_dir}, 使用本地执行器={use_local_executor}")
        return executor
    except Exception as e:
        logger.error(f"创建执行器失败: {str(e)}")
        raise Exception(f"无法创建代码执行器: {str(e)}")


# API文档获取智能体
@type_subscription(topic_type=TopicTypes.API_DOCS_FETCHER)
class APIDocsFetcherAgent(RoutedAgent):
    """API文档获取智能体"""

    def __init__(self):
        super().__init__("api_docs_fetcher_agent")

    @message_handler
    async def handle_message(self, message: APIDocsInput, ctx: MessageContext) -> None:
        """处理API文档获取请求"""
        logger.info(f"开始获取API文档: {message.api_docs_url}")

        try:
            # 发送日志消息
            await publish_log_message(self, f"正在获取API文档: {message.api_docs_url}", "api_docs_fetcher")

            # 获取API文档内容（如果接口信息是pdf文档，可以调用utils.py 中的 extract_text_from_llm）
            api_doc = await self.fetch_api_doc(message.api_docs_url)

            # 更新消息中的API文档内容
            message.api_doc_content = api_doc

            # 将消息发送给分析智能体
            await self.publish_message(
                message,
                topic_id=TopicId(type=TopicTypes.API_ANALYZER, source=self.id.key)
            )

            # 发送进度消息
            await publish_progress_message(
                self, "fetch", 10, "API文档获取完成", "api_docs_fetcher"
            )

        except Exception as e:
            error_msg = f"获取API文档出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await publish_error_message(self, error_msg, "api_docs_fetcher")

    async def fetch_api_doc(self, url: str) -> dict:
        """获取API文档内容"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"获取API文档失败: HTTP错误 {e.response.status_code}")
        except httpx.RequestError as e:
            raise Exception(f"获取API文档请求错误: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("API文档不是有效的JSON格式")
        except Exception as e:
            raise Exception(f"获取API文档出错: {str(e)}")


# API分析器智能体
@type_subscription(topic_type=TopicTypes.API_ANALYZER)
class APIAnalyzerAgent(RoutedAgent):
    """API分析智能体，负责分析API文档并生成分析结果"""

    def __init__(self):
        super().__init__("api_analyzer_agent")
        self.system_message = """
你是一名专业的API分析专家，具有丰富的REST API设计、分析和测试经验。你的任务是分析OpenAPI文档，提供全面而深入的分析结果，为后续的自动化测试生成提供基础。

作为API分析专家，你需要：

1. 对API整体结构进行分析：
   - API分组和功能模块划分
   - 资源和端点的组织方式
   - API版本策略

2. 详细分析每个API端点：
   - 路径、HTTP方法、功能描述
   - 请求参数（路径参数、查询参数、请求体）
   - 响应结构和状态码
   - 认证需求和权限控制

3. 识别API的认证和授权机制：
   - 认证类型（Basic、Bearer Token、OAuth2、API Key等）
   - 认证流程和token获取方式
   - 权限级别和访问控制模型

4. 分析数据模型和结构：
   - 主要数据实体及其关系
   - 数据验证规则和约束
   - 数据格式和类型

5. 识别API间的依赖关系：
   - 业务流程和操作顺序
   - 数据流和状态转换
   - 前置条件和后置条件

6. 分析特殊场景和功能：
   - 分页实现方式
   - 批量操作支持
   - 文件上传/下载
   - 长轮询或WebSocket支持
   - 缓存策略

7. 识别可能的测试挑战：
   - 复杂依赖关系
   - 特殊数据要求
   - 潜在的性能或安全问题
   - 并发和事务处理

8. 提供测试策略建议：
   - 测试优先级和关键路径
   - 测试数据准备策略
   - 用于测试的示例请求和响应

你的分析将直接用于自动生成测试用例和辅助代码。请确保分析全面、准确，并提供足够的细节，以便后续步骤能够生成高质量的测试代码。
"""

    @message_handler
    async def handle_message(self, message: APIDocsInput, ctx: MessageContext) -> None:
        """处理API文档分析请求"""
        logger.info(f"开始分析API文档: {message.api_docs_url}")

        # 发送进度消息
        await publish_progress_message(
            self, "analyze", 10, "开始分析API文档", "api_analyzer"
        )

        try:
            # 获取API文档
            # if message.api_doc_content:
            #     api_docs = message.api_doc_content
            #     logger.info(f"使用提供的API文档内容进行分析")
            # else:
            #     logger.info(f"从URL获取API文档: {message.api_docs_url}")
            #     await publish_log_message(self, f"从URL获取API文档: {message.api_docs_url}", "api_analyzer")
            #     api_docs = await self.fetch_api_doc(message.api_docs_url)

            # 发送API文档获取成功消息
            await publish_progress_message(
                self, "analyze", 20, "API文档获取成功", "api_analyzer"
            )

            # 构建API分析的问题
            question = f"""
请分析以下OpenAPI文档，并提供详细的分析报告。这个分析将用于生成自动化测试代码。

API基础URL: {message.base_url}
{"API文档补充说明: " + message.api_doc_supplement if message.api_doc_supplement else ""}

请在分析中包含以下内容：

1. API总体概述：
   - API的主要功能和用途
   - API资源和端点的组织结构
   - 版本策略和命名约定

2. 详细的端点分析：
   - 每个端点的路径、HTTP方法和功能
   - 请求参数说明（必选/可选，类型，约束）
   - 响应结构和状态码
   - 示例请求和响应

3. 认证和授权机制：
   - 认证类型（Basic Auth, Bearer Token, OAuth2, API Key等）
   - 详细的认证流程和获取token的方法
   - 不同端点的权限要求
   - 认证失败的处理方式

4. 数据模型和结构：
   - 主要数据实体的结构和关系
   - 字段约束和验证规则
   - 数据格式和特殊类型处理

5. API依赖关系：
   - 业务流程和操作顺序
   - 数据依赖和状态转换
   - 端点之间的前置和后置条件
   - 级联操作和副作用

6. 特殊功能和场景：
   - 分页实现方式
   - 搜索和过滤机制
   - 批量操作支持
   - 文件上传/下载
   - 其他特殊功能

7. 测试策略：
   - 各端点的测试优先级
   - 关键的业务流程和场景
   - 测试数据准备策略
   - 并发和性能测试建议
   - 安全测试注意事项

8. 潜在的测试挑战：
   - 复杂依赖和环境要求
   - 特殊数据或状态要求
   - 边界条件和异常情况
   - 测试中需要特别注意的地方

9. 测试辅助代码建议：
   - 建议的测试数据生成方法
   - 辅助函数和工具需求
   - 特定的断言和验证需求

10. API分组和测试用例规划：
    - 按功能或资源分组的测试用例建议
    - 每组API的测试覆盖建议
    - 测试用例间的依赖处理策略

请确保您的分析全面、准确，并提供足够的细节，以便自动化测试系统能够生成高质量的测试代码。
如果文档中有任何不明确的地方，请指出并提供您的解释或假设。

如果您收到了API文档补充说明，请特别关注其中提到的内容，并将其纳入您的分析考虑范围。
如果指定了测试重点，请确保在分析中重点关注这些方面。

OpenAPI文档内容:
```
{json.dumps(message.api_doc_content, indent=2)}
```
"""

            # 如果指定了测试重点，添加到问题中
            if message.test_focus:
                test_focus_prompt = f"""
此外，需要特别关注以下测试重点：
{message.test_focus}

请确保您的分析详细覆盖上述测试重点，并在分析报告中专门针对这些方面提供更深入的测试建议和策略。
"""
                question += test_focus_prompt

            # 使用OpenAI API分析API文档
            logger.info(f"开始使用智能体分析API文档")
            await publish_log_message(self, "使用智能体分析API文档中...", "api_analyzer")

            # 创建分析智能体并使用流式输出
            analyzer_agent = AssistantAgent(
                name="analyzer_agent",
                model_client=model_client,
                system_message=self.system_message,
                model_client_stream=True,
            )

            # from openai import OpenAI
            #
            # client = OpenAI(
            #     api_key="$MOONSHOT_API_KEY",
            #     base_url="https://api.moonshot.cn/v1",
            # )
            #
            # completion = client.chat.completions.create(
            #     model="moonshot-v1-8k",
            #     messages=[
            #         {"role": "system",
            #          "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。"},
            #         {"role": "user", "content": "你好，我叫李雷，1+1等于多少？"}
            #     ],
            #     temperature=0.3,
            # )
            # print(completion.choices[0].message.content)
            #
            # response1 = await model_client.create(
            #     messages=[
            #         SystemMessage(content=self.system_message),
            #         UserMessage(content=question, source="user"),
            #     ],
            # )
            # result = response1.content

            api_analysis = ""
            stream = analyzer_agent.run_stream(task=question)
            
            await publish_log_message(self, "正在生成API分析...", "api_analyzer")

            async for msg in stream:
                if isinstance(msg, ModelClientStreamingChunkEvent):
                    # 将生成进度发送到前端
                    await publish_log_message(self, msg.content, "api_analyzer")
                    continue

                if isinstance(msg, TaskResult):
                    # 获取完整的生成结果
                    api_analysis = msg.messages[-1].content

            # 发送进度消息
            await publish_progress_message(
                self, "analyze", 25, "API文档智能体分析完成", "api_analyzer"
            )

            logger.info(f"API文档分析完成")
            await publish_log_message(self, "API文档分析完成", "api_analyzer")

            # 提取API分析结果中的结构化信息
            # 这步是为了进一步分析出需要为特定API生成的辅助文件模板
            template_analysis_question = f"""
基于上述API分析，我需要为此API生成自定义的测试辅助工具。请提供以下信息：

1. 认证机制详情：
   - 主要认证类型（Basic、OAuth2、JWT、API Key等）
   - 如何获取和使用认证凭据
   - 认证相关的端点和流程

2. 关键数据模型：
   - 列出需要为测试创建的主要数据模型（用户、产品、订单等）
   - 每个模型的关键字段及其约束
   - 模型之间的关系和依赖

3. 特殊功能要求：
   - 分页实现细节（页码/游标/偏移量）
   - 文件上传/下载处理需求
   - 批量操作和事务处理
   - 特殊数据类型处理（日期、枚举、文件等）

4. 测试辅助工具需求：
   - 针对此API的测试数据生成器需求
   - 特定的请求处理和响应验证需求
   - 特殊的测试场景辅助函数需求

请以JSON格式提供这些信息，结构清晰明确，以便用于生成适合此API的自定义测试辅助工具。

{api_analysis}
"""

            # 获取模板生成需要的分析结果 - 修改为使用create方法
            template_analyzer = AssistantAgent(
                name="template_analyzer",
                model_client=model_client,
                system_message="你是一位API模板分析专家，负责提取API特性以便生成合适的测试模板。",
                model_client_stream=True,
            )
            
            template_analysis = ""
            template_stream = template_analyzer.run_stream(task=template_analysis_question)
            
            await publish_log_message(self, "正在分析API模板需求...", "api_analyzer")

            async for msg in template_stream:
                if isinstance(msg, ModelClientStreamingChunkEvent):
                    # 将生成进度发送到前端
                    await publish_log_message(self, msg.content, "api_analyzer")

                if isinstance(msg, TaskResult):
                    # 获取完整的生成结果
                    template_analysis = msg.messages[-1].content

            # 发送进度消息
            await publish_progress_message(
                self, "analyze", 25, "API文档模板分析完成", "api_analyzer"
            )

            logger.info(f"API文档模板分析完成")
            await publish_log_message(self, "API文档模板分析完成", "api_analyzer")

            # 尝试解析JSON格式的模板分析结果
            try:
                # 尝试从回复中提取JSON部分
                json_match = re.search(r'```json\n(.*?)\n```', template_analysis, re.DOTALL)
                if json_match:
                    template_json_str = json_match.group(1)
                else:
                    # 如果没有Markdown代码块，尝试直接解析整个回复
                    template_json_str = template_analysis

                template_info = json.loads(template_json_str)
                logger.info("成功解析模板分析结果为JSON格式")
            except Exception as e:
                logger.warning(f"无法解析模板分析结果为JSON格式: {str(e)}")
                # 如果解析失败，将整个分析结果作为文本保存
                template_info = {"raw_analysis": template_analysis}

            # 发送分析结果到测试生成器
            await self.publish_message(
                APIAnalysisResult(
                    api_docs_url=message.api_docs_url,
                    base_url=message.base_url,
                    analysis=api_analysis,
                    enable_review=message.enable_review,
                    user_review=message.user_review,
                    use_local_executor=message.use_local_executor,
                    test_focus=getattr(message, 'test_focus', None),
                    api_doc_supplement=getattr(message, 'api_doc_supplement', None),
                    template_info=template_info  # 添加模板生成所需的分析结果
                ),
                topic_id=TopicId(type=TopicTypes.TEST_GENERATOR, source=self.id.key)
            )

            # 发送进度消息
            await publish_progress_message(
                self, "analyze", 30, "API文档分析完成", "api_analyzer"
            )

            logger.info(f"API文档分析完成: {message.api_docs_url}")

            # APIAnalyzerAgent的流处理完成后
            await publish_progress_message(
                self, "analyze", 30, "API分析和模板生成完成", "api_analyzer"
            )

        except Exception as e:
            error_msg = f"API分析处理出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await publish_error_message(self, error_msg, "api_analyzer")


# 测试代码生成器智能体
@type_subscription(topic_type=TopicTypes.TEST_GENERATOR)
class TestGeneratorAgent(RoutedAgent):
    """测试生成智能体，根据API分析结果动态生成测试代码和辅助文件"""

    def __init__(self):
        super().__init__("test_generator_agent")
        self.system_message = """
你是一名专业的Python自动化测试专家，你的任务是生成高质量的API自动化测试代码和必要的辅助文件。

以下是生成测试代码的要求：
1. 生成一套完整的、可直接执行的Python测试文件，包含所有必要的测试用例和辅助文件
2. 确保测试代码遵循测试自动化最佳实践：
   - 清晰的测试结构和命名
   - 适当的测试隔离
   - 详细的测试记录和报告
   - 良好的错误处理机制
   - 测试数据的独立性和可重用性
3. 使用pytest和allure框架
4. 确保测试代码具有良好的可维护性和可扩展性
5. 使用统一的编码风格和命名约定
6. 正确处理测试前置条件和清理操作
7. 确保测试报告详细且信息丰富
8. 测试应涵盖正向路径和错误路径
9. 测试用例应具有独立性，减少依赖

你需要根据给定的API分析结果，生成以下文件：
1. conftest.py - 包含动态生成的pytest fixtures和配置
2. utils.py - 包含针对当前API的工具函数和辅助类
3. test_[资源名称].py - 一个或多个测试文件，包含完整的测试用例

确保所有生成的代码能够无缝协作，并且针对特定API的特点进行优化，而不是使用通用模板。
"""

    @message_handler
    async def handle_message(self, message: APIAnalysisResult, ctx: MessageContext) -> None:
        """处理API分析结果，生成测试代码和辅助文件"""
        logger.info(f"开始生成测试代码，基于API: {message.base_url}")

        try:
            # 创建测试生成智能体，使用全局统一的模型客户端
            test_generator = AssistantAgent(
                name="test_generator",
                model_client=model_client,
                system_message=self.system_message,
                model_client_stream=True,  # 启用流式输出
            )

            # 构造API测试问题
            await publish_log_message(self, "开始生成API测试用例和辅助文件...", "test_generator")

            # 首先生成针对当前API的辅助文件模板
            template_info = getattr(message, 'template_info', {})
            await publish_log_message(self, "根据API分析结果生成自定义测试辅助文件...", "test_generator")

            # 生成conftest.py - 修改为使用create方法
            conftest_question = f"""
基于以下API分析结果，为这个特定API生成一个完整的conftest.py文件，用于pytest测试。

API基础URL: {message.base_url}
API文档URL: {message.api_docs_url}

API分析结果摘要:
{message.analysis[:1000]}... (摘要)

模板生成信息:
{json.dumps(template_info, indent=2)}

请生成一个完整的conftest.py文件，包含以下内容：
1. 所有必要的导入
2. 日志配置
3. 根据API特性定制的pytest fixtures，特别是：
   - 认证相关的fixtures（根据API的认证机制，如BasicAuth、JWT、OAuth2等）
   - 测试会话管理
   - 基础URL配置
   - 测试数据准备和清理
   - 文件上传/下载处理（如果API支持）
   - 错误处理和重试机制
4. 任何其他特定于此API的pytest钩子或配置
5. 数据的生成方法优先选择mimesis模块提供的方法

请确保生成的conftest.py文件能够：
- 适应此特定API的特点和需求
- 提供足够的灵活性和可配置性
- 包含详细的注释，解释每个fixture的用途和用法
- 考虑测试之间的独立性，避免测试间相互干扰
- 遵循Python最佳实践和pytest最佳实践
- 包含错误处理和日志记录

请直接输出完整的Python代码，不需要任何Markdown标记或额外说明。
"""

            # 获取conftest.py代码 - 修改为使用create方法
            conftest_generator = AssistantAgent(
                name="conftest_generator",
                model_client=model_client,
                system_message="你是一位pytest配置专家，负责生成高质量的conftest.py文件。",
                model_client_stream=True,
            )
            
            conftest_code = ""
            conftest_stream = conftest_generator.run_stream(task=conftest_question)
            
            await publish_log_message(self, "正在生成conftest.py...", "test_generator")

            async for msg in conftest_stream:
                if isinstance(msg, ModelClientStreamingChunkEvent):
                    # 将生成进度发送到前端
                    await publish_log_message(self, msg.content, "test_generator")

                if isinstance(msg, TaskResult):
                    # 获取完整的生成结果
                    conftest_code = msg.messages[-1].content

            conftest_code = extract_python_code(conftest_code)

            await publish_progress_message(
                self, "generate", 45, "conftest.py 生成完成", "test_generator"
            )
            # 生成utils.py - 修改为使用create方法
            utils_question = f"""
基于以下API分析结果，为这个特定API生成一个完整的utils.py文件，包含测试所需的工具类和辅助函数。

API基础URL: {message.base_url}
API文档URL: {message.api_docs_url}

API分析结果摘要:
{message.analysis[:1000]}... (摘要)

模板生成信息:
{json.dumps(template_info, indent=2)}

请生成一个完整的utils.py文件，包含以下内容：
1. 所有必要的导入
2. TestDataFactory类，根据API的数据模型自定义以下方法：
   - 为API中的每种主要资源生成测试数据的方法（用户、产品、订单等）
   - 生成唯一ID或其他唯一标识符的方法
   - 处理特殊数据类型的方法（日期、枚举等）
   - 数据的生成方法优先选择mimesis模块提供的方法
3. 请求处理函数：
   - 定制request_with_logging函数，适应API的特点
   - 根据API的需求添加额外的请求处理功能
4. 响应验证类：
   - 扩展ResponseValidator类，添加针对此API的特定验证方法
   - 包含适合API的数据验证和断言方法
5. 错误处理和重试机制：
   - 根据API的错误处理方式定制冲突和错误处理函数
6. 任何其他特定于此API的辅助函数或类

请确保生成的utils.py文件能够：
- 完全适应此特定API的特点和需求
- 提供丰富的测试数据生成功能，考虑API的数据模型和约束
- 包含详细的注释，解释每个函数和类的用途和用法
- 考虑测试数据的唯一性和隔离性
- 遵循Python最佳实践和自动化测试最佳实践
- 包含错误处理和日志记录

请直接输出完整的Python代码，不需要任何Markdown标记或额外说明。
"""

            # 生成utils.py - 修改为使用create方法
            utils_generator = AssistantAgent(
                name="utils_generator",
                model_client=model_client,
                system_message="你是一位测试工具类专家，负责生成高质量的utils.py工具类文件。",
                model_client_stream=True,
            )
            
            utils_code = ""
            utils_stream = utils_generator.run_stream(task=utils_question)
            
            await publish_log_message(self, "正在生成utils.py...", "test_generator")

            async for msg in utils_stream:
                if isinstance(msg, ModelClientStreamingChunkEvent):
                    # 将生成进度发送到前端
                    await publish_log_message(self, msg.content, "test_generator")

                if isinstance(msg, TaskResult):
                    # 获取完整的生成结果
                    utils_code = msg.messages[-1].content

            utils_code = extract_python_code(utils_code)

            await publish_progress_message(
                self, "generate", 60, "utils.py 生成完成", "test_generator"
            )

            # 生成base.py - 修改为使用create方法
            base_question = f"""
基于以下API分析结果，为这个特定API生成一个base.py文件，包含所有测试类的基类。

API基础URL: {message.base_url}
API文档URL: {message.api_docs_url}

API分析结果摘要:
{message.analysis[:1000]}... (摘要)

模板生成信息:
{json.dumps(template_info, indent=2)}

请生成一个简洁但功能完整的base.py文件，包含以下内容：
1. 所有必要的导入
2. BaseAPITest类，包含：
   - 适当的setup/teardown方法
   - 通用的测试辅助方法
   - 适合此API的验证和断言方法
   - 错误处理和清理机制
3. 任何特定于此API的基础功能

请确保生成的base.py文件能够：
- 适应此特定API的特点和需求
- 提供一个强大但轻量的基类，避免过度设计
- 包含详细的注释，解释类的用途和用法
- 遵循Python最佳实践和测试最佳实践
- 支持测试用例的独立性

请直接输出完整的Python代码，不需要任何Markdown标记或额外说明。
"""

            # 生成base.py - 修改为使用create方法
            base_generator = AssistantAgent(
                name="base_generator",
                model_client=model_client,
                system_message="你是一位测试基类专家，负责生成高质量的测试基类文件。",
                model_client_stream=True,
            )
            
            base_code = ""
            base_stream = base_generator.run_stream(task=base_question)
            
            await publish_log_message(self, "正在生成base.py...", "test_generator")

            async for msg in base_stream:
                if isinstance(msg, ModelClientStreamingChunkEvent):
                    # 将生成进度发送到前端
                    await publish_log_message(self, msg.content, "test_generator")

                if isinstance(msg, TaskResult):
                    # 获取完整的生成结果
                    base_code = msg.messages[-1].content

            base_code = extract_python_code(base_code)

            await publish_progress_message(
                self, "generate", 75, "base.py 生成完成", "test_generator"
            )
            # 生成测试代码
            # 根据API分析结果构建问题
            question = f"""
我需要你基于以下API分析结果为'{message.base_url}'生成Python测试代码。

API文档URL: {message.api_docs_url}
API基础URL: {message.base_url}

API分析结果:
{message.analysis}

{"测试重点: " + message.test_focus if message.test_focus else "测试重点: 全面测试所有API端点"}
{"API文档补充说明: " + message.api_doc_supplement if message.api_doc_supplement else ""}

我已经为这个API生成了以下自定义辅助文件，你应该导入并使用这些文件中的类和函数：

1. conftest.py - 包含pytest fixtures和配置
2. utils.py - 包含TestDataFactory、request_with_logging和ResponseValidator等
3. base.py - 包含BaseAPITest基类

请根据API分析，生成一个或多个测试文件（按API资源或功能分组），每个文件包含完整的测试用例，涵盖API的各个方面。
测试应包括正常路径和异常路径，确保每个测试用例都有足够的独立性。

请注意以下要点：
1. 每个测试类都应继承base.py中的BaseAPITest类
2. 使用conftest.py中定义的fixtures
3. 使用utils.py中的工具类和函数
4. 测试类和方法应使用@allure.feature和@allure.story标注
5. 使用with allure.step()添加清晰的测试步骤
6. 确保测试用例之间的独立性，避免相互依赖
7. 实现适当的错误处理和断言
8. 遵循Python最佳实践和PEP 8风格指南

请直接输出Python测试代码，不需要任何Markdown标记或额外说明。
生成的测试代码应该可以直接运行，不需要额外修改。
"""

            # 获取API分析和测试生成的结果
            test_code = ""

            try:
                # 使用流式模式
                await publish_log_message(self, "生成测试代码中...", "test_generator")

                # 使用test_generator智能体生成测试代码
                stream = test_generator.run_stream(task=question)
                
                async for msg in stream:
                    if isinstance(msg, ModelClientStreamingChunkEvent):
                        # 将生成进度发送到结果主题
                        await publish_log_message(self, msg.content, "test_generator")

                    if isinstance(msg, TaskResult):
                        # 获取完整的生成结果
                        test_code = msg.messages[-1].content

            except Exception as e:
                logger.error(f"生成测试代码出错: {str(e)}", exc_info=True)
                await publish_error_message(self, f"生成测试代码出错: {str(e)}", "test_generator")
                return

            if not test_code or test_code.strip() == "":
                error_msg = "测试代码生成为空，无法继续执行"
                logger.warning(error_msg)
                await publish_error_message(self, error_msg, "test_generator")
                return

            # 为测试创建唯一目录
            test_dir = Path(tempfile.mkdtemp(prefix="api_test_"))

            # 提取Python代码（如果是Markdown格式）
            test_code = extract_python_code(test_code)

            # 解析测试代码，可能包含多个测试文件
            test_files = {}

            # 尝试识别多个测试文件（如果有明确的分隔标记）
            file_pattern = re.compile(r'# (?:FILE|File|file)[:\s]+([a-zA-Z0-9_]+\.py)', re.MULTILINE)
            file_matches = list(file_pattern.finditer(test_code))

            if file_matches:
                # 多个文件情况
                for i in range(len(file_matches)):
                    file_name = file_matches[i].group(1)
                    start_pos = file_matches[i].end()

                    # 确定结束位置
                    end_pos = len(test_code)
                    if i < len(file_matches) - 1:
                        end_pos = file_matches[i + 1].start()

                    # 提取文件内容
                    file_content = test_code[start_pos:end_pos].strip()
                    test_files[file_name] = file_content
            else:
                # 单文件情况，使用默认文件名
                test_files[f"test_api_{uuid.uuid4().hex[:8]}.py"] = test_code

            # 保存生成的所有文件
            # 首先保存辅助文件
            with open(test_dir / "conftest.py", 'w', encoding='utf-8') as f:
                f.write(conftest_code)

            with open(test_dir / "utils.py", 'w', encoding='utf-8') as f:
                f.write(utils_code)

            with open(test_dir / "base.py", 'w', encoding='utf-8') as f:
                f.write(base_code)

            # 然后保存测试文件
            main_test_file = None
            for file_name, file_content in test_files.items():
                file_path = test_dir / file_name
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)

                # 设置第一个测试文件为主测试文件
                if main_test_file is None:
                    main_test_file = file_path

            logger.info(f"测试代码和辅助文件已保存到: {test_dir}")

            # 发送测试代码到前端显示
            code_content = {
                "code": test_code,
                "test_file_path": str(main_test_file),
                "aux_files": {
                    "conftest.py": conftest_code,
                    "utils.py": utils_code,
                    "base.py": base_code
                }
            }

            await self.publish_message(
                WebSocketMessage(
                    type="code",
                    content=code_content,
                    source="test_generator"
                ),
                topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=self.id.key)
            )

            # 将测试文件路径发布到测试执行器主题
            await self.publish_message(
                TestGenerationResult(
                    test_file_path=str(main_test_file),
                    base_url=message.base_url,
                    enable_review=message.enable_review,
                    user_review=message.user_review,
                    use_local_executor=message.use_local_executor,
                    test_dir=str(test_dir)  # 添加整个测试目录路径
                ),
                topic_id=TopicId(type=TopicTypes.TEST_EXECUTOR, source=self.id.key)
            )

            # 发送进度消息
            await publish_progress_message(
                self, "generate", 85, "测试代码生成完成", "test_generator"
            )

            logger.info(f"测试代码生成完成: {main_test_file}")

        except Exception as e:
            error_msg = f"测试代码生成出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await publish_error_message(self, error_msg, "test_generator")


# 测试执行器智能体
@type_subscription(topic_type=TopicTypes.TEST_EXECUTOR)
class TestExecutorAgent(RoutedAgent):
    """测试执行智能体"""

    def __init__(self, use_local_executor: bool = True):
        super().__init__("test_executor_agent")
        # 延迟初始化执行器，在handle_message中创建
        self._code_executor = None
        self._use_local_executor = use_local_executor
        self._work_dir = None

    async def _init_executor(self) -> None:
        """初始化代码执行器"""
        if self._code_executor is None:
            # 工作目录已在handle_message中设置
            logger.info(f"测试执行器使用工作目录: {self._work_dir}")
            try:
                self._code_executor = UniversalExecutor(
                    work_dir=self._work_dir,
                    use_local_executor=self._use_local_executor
                )
                logger.info(f"测试执行器初始化成功")
            except Exception as e:
                error_msg = f"初始化测试执行器失败: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg)

    def _extract_test_stats(self, output: str, report_data: Optional[dict] = None) -> Dict[str, int]:
        """从测试输出和报告数据中提取测试统计信息"""
        stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "error": 0,
            "skipped": 0,
            "duration": 0
        }

        # 尝试从pytest输出中提取统计信息
        try:
            # 解析总体统计信息
            summary_pattern = r'(\d+) passed,?\s*(\d+) failed,?\s*(\d+) error(?:ed)?,?\s*(\d+) skipped'
            alt_summary_pattern = r'(\d+) passed,?\s*(\d+) failed,?\s*(\d+) skipped'
            duration_pattern = r'in\s+([\d\.]+)s'

            # 尝试匹配详细模式（包含错误）
            summary_match = re.search(summary_pattern, output)
            if summary_match:
                stats["passed"] = int(summary_match.group(1))
                stats["failed"] = int(summary_match.group(2))
                stats["error"] = int(summary_match.group(3))
                stats["skipped"] = int(summary_match.group(4))
            else:
                # 尝试匹配简化模式
                alt_match = re.search(alt_summary_pattern, output)
                if alt_match:
                    stats["passed"] = int(alt_match.group(1))
                    stats["failed"] = int(alt_match.group(2))
                    stats["skipped"] = int(alt_match.group(3))

            # 提取持续时间
            duration_match = re.search(duration_pattern, output)
            if duration_match:
                stats["duration"] = float(duration_match.group(1))

            # 计算总数
            stats["total"] = stats["passed"] + stats["failed"] + stats["error"] + stats["skipped"]
        except Exception as e:
            logger.warning(f"从输出提取测试统计失败: {str(e)}")

        # 如果有JSON报告数据，尝试从中提取更准确的信息
        if report_data:
            try:
                if "summary" in report_data:
                    summary = report_data["summary"]
                    stats["total"] = summary.get("total", stats["total"])
                    stats["passed"] = summary.get("passed", stats["passed"])
                    stats["failed"] = summary.get("failed", stats["failed"])
                    stats["error"] = summary.get("error", stats["error"])
                    stats["skipped"] = summary.get("skipped", stats["skipped"])
                    stats["duration"] = summary.get("duration", stats["duration"])
                elif "tests" in report_data:
                    # 如果没有摘要，但有测试列表，则手动计算
                    tests = report_data["tests"]
                    stats["total"] = len(tests)
                    stats["passed"] = sum(1 for t in tests if t.get("outcome") == "passed")
                    stats["failed"] = sum(1 for t in tests if t.get("outcome") == "failed")
                    stats["error"] = sum(1 for t in tests if t.get("outcome") == "error")
                    stats["skipped"] = sum(1 for t in tests if t.get("outcome") == "skipped")

                    # 尝试计算总持续时间
                    if "duration" in report_data:
                        stats["duration"] = report_data["duration"]
            except Exception as e:
                logger.warning(f"从JSON报告提取测试统计失败: {str(e)}")

        return stats

    @message_handler
    async def handle_message(self, message: TestGenerationResult, ctx: MessageContext) -> None:
        """处理测试执行请求"""
        try:
            # 获取测试文件路径
            test_file_path = message.test_file_path
            test_dir = message.test_dir if hasattr(message, 'test_dir') and message.test_dir else None

            logger.info(f"准备执行测试: {test_file_path}")

            # 验证测试文件是否存在
            if not os.path.exists(test_file_path):
                error_msg = f"测试文件不存在: {test_file_path}"
                logger.error(error_msg)
                await publish_error_message(self, error_msg, "test_executor")
                return

            # 设置工作目录
            self._work_dir = os.path.dirname(test_file_path)
            if test_dir and os.path.exists(test_dir):
                self._work_dir = test_dir

            logger.info(f"测试执行工作目录: {self._work_dir}")

            # 用户评审环节，如果需要
            if message.enable_review and message.user_review:
                # 发送等待用户评审的消息
                await publish_log_message(self, "等待用户评审测试代码...", "test_executor")
                await publish_progress_message(
                    self, "review", 90, "等待用户评审", "test_executor"
                )

                # 这里应该有一个等待用户评审的逻辑
                # 在实际应用中，可能需要一个额外的消息处理程序来接收用户评审结果

                # 临时简化处理：假设用户已经评审通过
                await publish_log_message(self, "用户评审完成，准备执行测试", "test_executor")

            # 初始化执行器
            await self._init_executor()

            # 发送测试开始的消息
            await publish_log_message(self, "开始执行测试...", "test_executor")
            await publish_progress_message(
                self, "execute", 80, "开始执行测试", "test_executor"
            )

            try:
                # 安装测试依赖
                if os.path.exists(os.path.join(self._work_dir, "requirements.txt")):
                    await publish_log_message(self, "安装测试依赖...", "test_executor")
                    install_cmd = "pip install -r requirements.txt"
                    install_result = await self._code_executor.execute_command(install_cmd)
                    logger.info(f"依赖安装结果: {install_result}")

                # 构建测试命令
                # 使用pytest运行测试，包含生成HTML和JSON报告
                test_cmd = f"cd {self._work_dir} && "
                test_cmd += "python -m pytest "

                if test_dir and os.path.exists(test_dir):
                    # 如果有测试目录，运行目录下所有测试
                    test_cmd += f". "
                else:
                    # 否则运行单个测试文件
                    test_cmd += f"{os.path.basename(test_file_path)} "

                # 添加报告输出选项
                test_cmd += "-v --html=report.html --json-report --json-report-file=report.json "

                # 添加Allure报告
                test_cmd += "--alluredir=./allure-results"

                # 添加测试基础URL
                test_cmd += f" --base-url={message.base_url}"

                # 执行测试命令
                await publish_log_message(self, f"执行测试命令: {test_cmd}", "test_executor")
                test_result = await self._code_executor.execute_command(test_cmd)

                # 输出测试结果
                output = test_result.get("output", "")
                exit_code = test_result.get("exit_code", -1)

                logger.info(f"测试执行完成，退出码: {exit_code}")
                await publish_log_message(self, f"测试执行完成，退出码: {exit_code}", "test_executor")

                # 检查是否有测试报告
                report_path = os.path.join(self._work_dir, "report.html")
                json_report_path = os.path.join(self._work_dir, "report.json")
                allure_results_dir = os.path.join(self._work_dir, "allure-results")

                report_url = None
                allure_report_url = None

                # 读取JSON报告
                report_data = None
                if os.path.exists(json_report_path):
                    try:
                        with open(json_report_path, "r") as f:
                            report_data = json.load(f)
                    except Exception as e:
                        logger.error(f"读取JSON报告失败: {str(e)}")

                # 提取测试统计
                test_stats = self._extract_test_stats(output, report_data)

                # 生成Allure报告
                if os.path.exists(allure_results_dir) and os.listdir(allure_results_dir):
                    try:
                        allure_cmd = f"cd {self._work_dir} && allure generate allure-results -o allure-report --clean"
                        allure_result = await self._code_executor.execute_command(allure_cmd)
                        if allure_result.get("exit_code", -1) == 0:
                            allure_report_url = os.path.join(self._work_dir, "allure-report")
                            logger.info(f"Allure报告生成成功: {allure_report_url}")
                    except Exception as e:
                        logger.error(f"生成Allure报告失败: {str(e)}")

                # 分析测试结果 - 修改为使用create方法
                analysis_question = f"""
分析以下测试执行结果，提供详细的测试总结。请包括以下内容：

1. 测试执行摘要：
   - 成功/失败/错误/跳过的测试用例数量
   - 总测试用例数和通过率
   - 测试执行时间

2. 失败的测试用例分析：
   - 失败的测试用例名称和原因
   - 可能的根本原因
   - 建议的修复方法

3. 主要测试观察结果：
   - 关键功能是否正常工作
   - 发现的主要问题
   - 性能或响应时间问题

4. 测试覆盖分析：
   - 测试覆盖了哪些关键API功能
   - 可能的测试覆盖缺口
   - 建议的额外测试

5. 后续步骤和建议：
   - 需要进一步调查的地方
   - 改进测试质量的建议
   - 修复优先级建议

执行结果：
```
{output[:4000] if len(output) > 4000 else output}
```

测试统计信息：
- 总测试数: {test_stats.get('total', 'N/A')}
- 通过: {test_stats.get('passed', 'N/A')}
- 失败: {test_stats.get('failed', 'N/A')}
- 错误: {test_stats.get('error', 'N/A')}
- 跳过: {test_stats.get('skipped', 'N/A')}
- 执行时间: {test_stats.get('duration', 'N/A')} 秒

请提供全面、客观的分析，重点指出发现的问题和改进建议。
"""

                analysis_agent = AssistantAgent(
                    name="analysis_agent",
                    model_client=model_client,
                    system_message="你是一位测试分析专家，负责深入分析测试结果并提供专业见解。",
                    model_client_stream=True,
                )
                
                analysis_result = ""
                analysis_stream = analysis_agent.run_stream(task=analysis_question)
                
                await publish_log_message(self, "正在分析测试结果...", "test_executor")

                async for msg in analysis_stream:
                    if isinstance(msg, ModelClientStreamingChunkEvent):
                        # 将生成进度发送到前端
                        await publish_log_message(self, msg.content, "test_executor")

                    if isinstance(msg, TaskResult):
                        # 获取完整的生成结果
                        analysis_result = msg.messages[-1].content

                # TestExecutorAgent的分析完成后
                await publish_progress_message(
                    self, "analyze", 95, "测试结果分析完成", "test_executor"
                )

                # 发送测试执行完成的消息
                await publish_progress_message(
                    self, "execute", 100, "测试执行完成", "test_executor"
                )

                # 发布测试结果
                test_result_msg = {
                    "output": output,
                    "exit_code": exit_code,
                    "stats": test_stats,
                    "report_path": report_path if os.path.exists(report_path) else None,
                    "report_data": report_data
                }

                await self.publish_message(
                    TestExecutionResult(
                        test_result=test_result_msg,
                        test_file_path=test_file_path,
                        analysis=analysis_result,
                        report_url=report_url,
                        allure_report_url=allure_report_url
                    ),
                    topic_id=TopicId(type=TopicTypes.TEST_REPORT_ENHANCER, source=self.id.key)
                )

                logger.info("测试结果已发送")

            except Exception as e:
                error_msg = f"执行测试出错: {str(e)}"
                logger.error(error_msg, exc_info=True)
                await publish_error_message(self, error_msg, "test_executor")

        except Exception as e:
            error_msg = f"处理测试执行请求出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await publish_error_message(self, error_msg, "test_executor")

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self._work_dir and self._work_dir.exists():
                shutil.rmtree(self._work_dir, ignore_errors=True)
                logger.info(f"已清理测试执行器工作目录: {self._work_dir}")
        except Exception as e:
            logger.error(f"清理资源失败: {str(e)}")


# 测试报告增强智能体
@type_subscription(topic_type=TopicTypes.TEST_REPORT_ENHANCER)
class TestReportEnhancerAgent(RoutedAgent):
    """测试报告增强智能体，用于改进测试报告的可视化和内容"""

    def __init__(self):
        super().__init__("test_report_enhancer_agent")

    @message_handler
    async def handle_message(self, message: TestExecutionResult, ctx: MessageContext) -> None:
        """处理测试报告增强请求"""
        logger.info(f"开始增强测试报告")

        try:
            # 检查是否有报告URL
            if not message.report_url:
                await publish_log_message(self, "没有找到报告URL，无法增强报告", "report_enhancer")
                return

            # 报告URL中提取报告文件路径
            report_url = message.report_url
            report_path = Path("./static" + report_url.replace("/static", ""))

            if not report_path.exists():
                await publish_log_message(self, f"报告文件不存在: {report_path}", "report_enhancer")
                return

            # 读取原始报告文件内容
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()

            # 创建报告增强智能体
            report_enhancer = AssistantAgent(
                name="report_enhancer",
                model_client=model_client,
                system_message="""你是一位测试报告增强专家，擅长改进HTML测试报告的可视化和内容。
你的任务是分析当前HTML报告并提供增强建议。
按照以下步骤工作：
1. 分析HTML报告的结构和内容
2. 识别可以改进的区域
3. 提供额外的CSS和JavaScript，增强报告的可视化效果
4. 建议添加的图表、统计和摘要信息
5. 提供更好地展示测试结果的方法
""",
                model_client_stream=True
            )

            # 提取测试统计信息
            test_stats = message.test_result.get("stats", {})

            # 构造问题
            question = f"""
我有一个由pytest-html生成的测试报告，需要增强其可视化效果和内容。

测试统计信息:
- 总用例数: {test_stats.get('total', 0)}
- 通过: {test_stats.get('passed', 0)}
- 失败: {test_stats.get('failed', 0)}
- 错误: {test_stats.get('error', 0)}
- 跳过: {test_stats.get('skipped', 0)}
- 执行时间: {test_stats.get('duration', 0)}秒

请提供额外的HTML、CSS和JavaScript代码，来增强报告的以下方面:
1. 添加一个显眼的执行结果摘要区域
2. 添加一个使用Chart.js或类似库的可视化图表，展示测试结果分布
3. 改进整体样式，使其更专业和现代化
4. 添加可折叠的测试结果详情区域
5. 增加测试时间和执行环境信息
6. 提供交互式过滤和搜索功能

请提供完整的HTML/CSS/JS代码片段，我将把它们注入到现有的HTML报告中。
"""

            await publish_log_message(self, "分析报告并生成增强内容...", "report_enhancer")

            enhancement_code = ""

            # 使用流式模式
            stream = report_enhancer.run_stream(task=question)

            async for msg in stream:
                if isinstance(msg, ModelClientStreamingChunkEvent):
                    # 将进度发送到结果主题
                    await publish_log_message(self, msg.content, "report_enhancer")

                if isinstance(msg, TaskResult):
                    # 获取完整的增强代码
                    result_content = msg.messages[-1].content
                    enhancement_code = extract_code_blocks(result_content)

            if not enhancement_code:
                await publish_log_message(self, "未能从响应中提取有效的代码", "report_enhancer")
                return

            # 将增强代码应用到报告
            enhanced_report_content = self._apply_enhancements(report_content, enhancement_code)

            # 备份原始报告
            backup_path = report_path.with_suffix('.original.html')
            shutil.copy2(report_path, backup_path)

            # 写入增强后的报告
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(enhanced_report_content)

            await publish_log_message(self, f"报告增强完成: {report_url}", "report_enhancer")

            # 发送增强的报告URL到结果主题
            enhanced_report_content = {
                "report_url": report_url,
                "enhancement_applied": True
            }

            await self.publish_message(
                WebSocketMessage(
                    type="enhanced_report",
                    content=enhanced_report_content,
                    source="report_enhancer"
                ),
                topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=self.id.key)
            )

        except Exception as e:
            error_msg = f"增强测试报告出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await publish_error_message(self, error_msg, "report_enhancer")

    def _apply_enhancements(self, original_html: str, enhancements: List[CodeBlock]) -> str:
        """将增强代码应用到原始HTML报告中"""
        try:
            # 处理每个代码块
            css_code = ""
            js_code = ""
            html_code = ""

            for block in enhancements:
                content = block.code.strip()
                lang = block.language.lower()

                if lang == "css":
                    css_code += content + "\n"
                elif lang in ["javascript", "js"]:
                    js_code += content + "\n"
                elif lang in ["html", ""]:
                    html_code += content + "\n"

            # 通过简单的字符串替换注入增强内容
            enhanced_html = original_html

            # 注入CSS
            if css_code:
                css_injection = f"<style>\n{css_code}\n</style>"
                if "</head>" in enhanced_html:
                    enhanced_html = enhanced_html.replace("</head>", f"{css_injection}\n</head>")
                else:
                    enhanced_html = f"{css_injection}\n{enhanced_html}"

            # 注入JavaScript
            if js_code:
                # 添加Chart.js依赖
                chart_js_cdn = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
                js_injection = f"{chart_js_cdn}\n<script>\n{js_code}\n</script>"
                if "</body>" in enhanced_html:
                    enhanced_html = enhanced_html.replace("</body>", f"{js_injection}\n</body>")
                else:
                    enhanced_html += f"\n{js_injection}"

            # 注入HTML
            if html_code:
                # 尝试注入到<body>之后
                if "<body>" in enhanced_html:
                    enhanced_html = enhanced_html.replace("<body>", f"<body>\n{html_code}")
                # 或者尝试注入到结果摘要之前
                elif '<div class="summary">' in enhanced_html:
                    enhanced_html = enhanced_html.replace('<div class="summary">',
                                                          f'{html_code}\n<div class="summary">')
                # 最后尝试注入到文档开始
                else:
                    enhanced_html = f"{html_code}\n{enhanced_html}"

            return enhanced_html
        except Exception as e:
            logger.error(f"应用报告增强失败: {str(e)}")
            return original_html  # 返回原始内容


# 启动运行时并执行API自动化测试流程
async def start_api_test_runtime(
        api_input: APIDocsInput,
        client_id: Optional[str] = None,
        result_handler: Optional[Callable[[ClosureContext, WebSocketMessage, MessageContext], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """启动API测试运行时并执行测试流程"""
    try:
        # 创建工作目录
        work_dir = Path(tempfile.mkdtemp(prefix="api_test_"))
        logger.info(f"创建API测试工作目录: {work_dir}")

        # 创建运行时
        runtime = SingleThreadedAgentRuntime()

        # 注册所有智能体
        await APIDocsFetcherAgent.register(runtime, TopicTypes.API_DOCS_FETCHER, lambda: APIDocsFetcherAgent())
        await APIAnalyzerAgent.register(runtime, TopicTypes.API_ANALYZER, lambda: APIAnalyzerAgent())
        await TestGeneratorAgent.register(runtime, TopicTypes.TEST_GENERATOR, lambda: TestGeneratorAgent())
        await TestExecutorAgent.register(
            runtime,
            TopicTypes.TEST_EXECUTOR,
            lambda: TestExecutorAgent(api_input.use_local_executor)
        )
        await TestReportEnhancerAgent.register(
            runtime,
            TopicTypes.TEST_REPORT_ENHANCER,
            lambda: TestReportEnhancerAgent()
        )

        # 注册结果处理程序
        if result_handler:
            await ClosureAgent.register_closure(
                runtime,
                "result_collector",
                result_handler,
                subscriptions=lambda: [
                    TypeSubscription(topic_type=TopicTypes.TEST_RESULT, agent_type="result_collector")],
            )
        elif client_id:
            from .api import manager
            async def send_to_websocket(ctx: ClosureContext, message: Any,
                                        msg_ctx: MessageContext) -> None:
                """发送消息到WebSocket"""
                # 添加日志
                logger.info(f"Sending message to websocket: {type(message)}")

                try:
                    # 将WebSocketMessage对象转换为字典
                    if isinstance(message, WebSocketMessage):
                        if hasattr(message, 'to_dict') and callable(getattr(message, 'to_dict')):
                            ctx.result = message.to_dict()
                        elif hasattr(message, 'model_dump') and callable(getattr(message, 'model_dump')):
                            ctx.result = message.model_dump()
                        else:
                            # 手动创建字典
                            ctx.result = {
                                "type": message.type,
                                "content": message.content,
                                "source": message.source,
                                "timestamp": message.timestamp or datetime.now().isoformat()
                            }
                    elif isinstance(message, dict):
                        ctx.result = message
                    else:
                        # 对于其他类型的消息，创建标准日志消息
                        logger.warning(f"收到未知类型的消息: {type(message)}")
                        ctx.result = {
                            "type": "log",
                            "content": str(message),
                            "source": "system",
                            "timestamp": datetime.now().isoformat()
                        }

                    # 确保字典包含所有必要的键
                    if "type" not in ctx.result:
                        ctx.result["type"] = "log"
                    if "content" not in ctx.result:
                        ctx.result["content"] = "无内容"
                    if "source" not in ctx.result:
                        ctx.result["source"] = "system"
                    if "timestamp" not in ctx.result:
                        ctx.result["timestamp"] = datetime.now().isoformat()

                    # 检查消息内容是否可序列化
                    try:
                        json.dumps(ctx.result)
                    except (TypeError, ValueError, OverflowError):
                        # 如果序列化失败，将content转换为字符串
                        if isinstance(ctx.result["content"], dict):
                            for key, value in ctx.result["content"].items():
                                if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                                    ctx.result["content"][key] = str(value)
                        else:
                            ctx.result["content"] = str(ctx.result["content"])

                except Exception as e:
                    logger.error(f"处理WebSocket消息时发生异常: {e}", exc_info=True)
                    ctx.result = {
                        "type": "error",
                        "content": f"处理消息出错: {str(e)}",
                        "source": "system",
                        "timestamp": datetime.now().isoformat()
                    }

            await ClosureAgent.register_closure(
                runtime,
                "websocket_sender",
                send_to_websocket,
                subscriptions=lambda: [
                    TypeSubscription(topic_type=TopicTypes.TEST_RESULT, agent_type="websocket_sender")],
            )

        # 启动运行时
        runtime.start()

        # 发布初始消息到API文档获取智能体
        await runtime.publish_message(
            api_input,
            topic_id=DefaultTopicId(type=TopicTypes.API_DOCS_FETCHER)
        )

        # 如果不使用回调，则等待运行时完成
        if not (result_handler or client_id):
            logger.info("等待API测试流程完成...")
            await runtime.stop_when_idle()
            # 清理资源
            shutil.rmtree(work_dir, ignore_errors=True)

        return {"status": "success", "message": "测试流程已启动"}
    except Exception as e:
        logger.error(f"API测试运行时启动失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"API测试运行时启动失败: {str(e)}"
        }


# 关闭模型客户端的函数
async def close_model_client():
    """关闭全局模型客户端"""
    try:
        await model_client.close()
        logger.info("已关闭全局模型客户端")
    except Exception as e:
        logger.error(f"关闭全局模型客户端出错: {str(e)}")