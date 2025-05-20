import json
import logging
import sys
import tempfile
import uuid
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, Awaitable
import httpx
from datetime import datetime
import shutil
import asyncio

# AutoGen 组件导入
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage
from autogen_core import RoutedAgent, type_subscription, message_handler, MessageContext, SingleThreadedAgentRuntime, \
    ClosureContext, TypeSubscription, ClosureAgent
from autogen_core import DefaultTopicId, TopicId
from autogen_core.models import UserMessage, SystemMessage, AssistantMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination

# 导入自定义组件
from .code_executor import UniversalExecutor
from .llms import model_client
from .models import (
    APIDocsInput, WebSocketMessage, APIAnalysisResult,
    TestGenerationResult, TestExecutionResult, TopicTypes,
    TestExecutionOutput, TestCaseDesignResult
)
from .utils import (
    publish_log_message, publish_progress_message, publish_error_message,
    extract_code_blocks, extract_python_code, extract_interfaces,
    create_temp_dir, cleanup_dir, parse_test_files, save_code_to_file, save_multiple_files
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_agents")


# 辅助函数
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


class CodeGenerationTeam:
    """代码生成和审查团队"""

    def __init__(self, model_client, agent: RoutedAgent):
        self.model_client = model_client
        self.agent = agent  # 添加 RoutedAgent 成员变量

        # 创建代码生成智能体
        self.code_generator = AssistantAgent(
            name="code_generator",
            model_client=model_client,
            system_message="""你是一位专业的Python测试代码生成专家。你的任务是:
            1. 生成高质量的测试代码和辅助文件
            2. 确保代码遵循Python和测试最佳实践
            3. 生成完整的导入语句和依赖
            4. 提供详细的代码注释
            5. 确保代码的可维护性和可扩展性
            6. 生成符合PEP 8规范的代码
            7. 根据审查者的反馈及时修改代码
            8. 确保最终输出的代码是完整且正确的

            特别强调：每次输出的代码都必须是完整，不能只输出修改后的代码。
            """,
        )

        # 创建代码审查智能体
        self.code_reviewer = AssistantAgent(
            name="code_reviewer",
            model_client=model_client,
            system_message="""你是一位专业的Python代码审查专家。你的任务是:
            1. 严格审查代码的语法正确性
            2. 验证导入语句的完整性
            3. 检查函数和类的定义
            4. 确保代码风格符合PEP 8
            5. 识别潜在的错误和异常
            6. 验证与依赖文件的兼容性
            7. 提供具体的修复建议
            8. 主动指出问题并提供修复方案
            9. 确保代码的完整性和正确性

            审查时请按以下格式提供反馈：
            ISSUE: [问题描述]
            SEVERITY: [严重程度: HIGH/MEDIUM/LOW]
            SUGGESTION: [修复建议]
            FIX: [修复后的代码片段]

            当代码完全正确时，请回复 "APPROVED"。
            """,
        )

        # 创建终止条件 - 当审查者批准代码时终止
        self.termination_condition = TextMentionTermination("APPROVED")

        # 创建团队
        self.team = RoundRobinGroupChat(
            [self.code_generator, self.code_reviewer],
            termination_condition=self.termination_condition, max_turns=3
        )

    async def reset(self):
        await self.team.reset()

    async def generate_and_review_code(
            self,
            code_type: str,
            requirements: str,
            dependencies: List[str] = None
    ) -> Dict[str, Any]:
        """生成并审查代码"""
        try:
            # 构建初始任务
            task = f"""请生成并审查{code_type}代码。
            要求:
            {requirements}

            依赖文件:
            {', '.join(dependencies) if dependencies else '无'}

            代码生成者请先生成代码。
            审查者请进行严格审查，如果发现问题：
            1. 使用ISSUE格式指出问题
            2. 提供具体的修复建议
            3. 给出修复后的代码片段
            4. 等待生成者修改后再次审查

            生成者收到审查反馈后：
            1. 仔细分析问题
            2. 按照建议修改代码
            3. 确保修改后的代码完整且正确
            4. 重新提交代码供审查
            """

            # 初始化结果变量
            code_content = ""
            review_notes = []
            is_valid = True
            total_chunks = 0
            processed_chunks = 0
            current_phase = "generation"  # 可能的值: generation, review, revision

            # 开始流式处理
            code_stream = self.team.run_stream(task=task)
            async for msg in code_stream:
                try:
                    if isinstance(msg, TaskResult):
                        continue
                    if msg.source != "user" and isinstance(msg, TextMessage):
                        # 更新处理进度
                        processed_chunks += 1
                        total_chunks = max(total_chunks, processed_chunks)

                        # 根据消息内容判断当前阶段
                        if "ISSUE:" in msg.content:
                            current_phase = "review"
                        elif "APPROVED" in msg.content:
                            current_phase = "approved"
                        elif "FIX:" in msg.content:
                            current_phase = "revision"

                        # 计算进度百分比
                        base_progress = {
                            "generation": 53,
                            "review": 60,
                            "revision": 70,
                            "approved": 75
                        }.get(current_phase, 53)

                        # 根据内容长度和阶段动态调整进度
                        content_length_factor = min(1.0, len(msg.content) / 1000)
                        phase_progress = base_progress + (content_length_factor * 5)
                        current_progress = min(75, int(phase_progress))

                        # 发送进度消息
                        await publish_progress_message(
                            self.agent,  # 使用 agent 成员变量
                            "generate",
                            current_progress,
                            f"代码{current_phase}阶段 ({current_progress}%)",
                            self.agent.id.key
                        )

                        # 发送内容到前端
                        await publish_log_message(
                            self.agent,  # 使用 agent 成员变量
                            msg.content,
                            self.agent.id.key
                        )

                        # 提取代码内容
                        if msg.source == "code_generator" and "```python" in msg.content:
                            code_blocks = extract_code_blocks(msg.content)
                            if code_blocks:
                                code_content = code_blocks[0]

                        # 提取审查反馈
                        if "ISSUE:" in msg.content:
                            review_notes.append(msg.content)

                except Exception as chunk_error:
                    logger.error(f"处理消息块时出错: {str(chunk_error)}")
                    await publish_error_message(
                        self.agent,  # 使用 agent 成员变量
                        f"处理消息时出错: {str(chunk_error)}",
                        "test_case_generator"
                    )
                    continue

            return {
                "code_content": code_content,
                "review_notes": review_notes,
                "is_valid": is_valid
            }

        except Exception as e:
            error_msg = f"代码生成和审查失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await publish_error_message(self.agent, error_msg, "test_case_designer")
            return {
                "code_content": code_content,
                "review_notes": [error_msg],
                "is_valid": False
            }


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
            await publish_progress_message(self, "fetch", 1, "开始获取API文档", "api_docs_fetcher")

            # 获取API文档内容
            api_doc = await self.fetch_api_doc(message.api_docs_url)
            await publish_progress_message(self, "fetch", 3, "API文档获取中", "api_docs_fetcher")

            # 更新消息中的API文档内容
            message.api_doc_content = api_doc
            await publish_progress_message(self, "fetch", 5, "API文档获取完成，准备分析", "api_docs_fetcher")

            # 将消息发送给分析智能体
            await self.publish_message(
                message,
                topic_id=TopicId(type=TopicTypes.API_ANALYZER, source=self.id.key)
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
   - 资源和接口的组织方式
   - API版本策略

2. 详细分析每个API接口：
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
        await publish_progress_message(self, "analyze", 6, "初始化API文档分析", "api_analyzer")

        try:
            # 构建API分析的问题
            await publish_progress_message(self, "analyze", 8, "构建API分析规则和模型", "api_analyzer")

            # 使用API分析智能体并使用流式输出
            logger.info(f"开始使用智能体分析API文档")
            await publish_log_message(self, "API文档分析中...\n\n", "api_analyzer")
            await publish_progress_message(self, "analyze", 10, "开始解析API文档", "api_analyzer")

            # 构建API分析的问题
            api_analysis_prompt = f"""
            分析以下OpenAPI文档，提供详细、系统化的分析报告，以便生成高质量的自动化测试代码。

            API基础信息:
            - 基础URL: {message.base_url}
            {f"- API文档补充说明: {message.api_doc_supplement}" if message.api_doc_supplement else ""}

            请参考以下结构组织您的分析报告（可以根据接口的功能和特点进行调整）：

            ## 1. API总体概述
            - API的主要功能和用途
            - API资源和接口的组织结构
            - 版本策略和命名约定

            ## 2. 接口详细分析
            针对每个API接口提供以下分析：
            接口名称: [名称]
            路径: [路径]
            HTTP方法: [GET/POST/PUT/DELETE等]
            功能描述: [功能说明]
            请求参数:
            	- 路径参数: [参数名]: [类型] - [是否必须] - [说明] - [约束]
            	- 查询参数: [参数名]: [类型] - [是否必须] - [说明] - [约束]
            	- 请求体参数: [参数名]: [类型] - [是否必须] - [说明] - [约束]
            响应状态码:
            	- [状态码]: [说明]
            响应结构:
            	[响应结构描述]
            	示例请求/响应:
            	[示例]

            ## 3. 认证和授权机制
            - 认证类型: [类型]
            - 认证流程和获取token方法: [方法]
            - 不同接口的权限要求: [要求]
            - 认证失败处理方式: [处理方式]

            ## 4. 数据模型和结构
            对每个主要数据模型提供以下分析:
            模型名称: [名称]
            字段:
            - [字段名]: [类型] - [是否必须] - [说明] - [约束]
            - ...
            关系: [与其他模型的关系]
            验证规则: [验证规则]


            ## 5. API依赖关系分析
            - API操作序列依赖: [依赖说明]
            - 资源依赖关系: [依赖说明]
            - 各资源CRUD操作路径: [路径]
            - 完整生命周期流程: [流程]
            - 认证相关的操作流: [流程]

            ## 6. 特殊功能和场景
            - 分页实现: [实现方式]
            - 搜索和过滤: [机制]
            - 批量操作: [支持情况]
            - 文件处理: [上传/下载机制]
            - 其他特殊功能: [功能说明]

            ## 7. 测试策略建议
            - 接口测试优先级: [优先级]
            - 关键业务流程: [流程]
            - 测试数据准备策略: [策略]
            - 性能测试建议: [建议]
            - 安全测试重点: [重点]

            ## 8. 潜在测试挑战
            - 复杂依赖: [依赖说明]
            - 特殊数据要求: [要求]
            - 边界条件: [条件]
            - 测试注意事项: [注意事项]

            ## 9. 测试辅助代码建议
            - 测试数据生成方法: [方法]
            - 辅助函数需求: [需求]
            - 断言和验证: [验证需求]

            ## 10. API分组和测试用例规划
            - 功能/资源分组: [分组]
            - 测试覆盖建议: [建议]
            - 依赖处理策略: [策略]

            ## 11. 测试数据生成需求
            - 数据类型生成需求: [需求]
            - 模板和规则: [规则]

            如文档有不明确之处，请明确标注并提供合理解释或假设。确保您的分析全面、准确、详细，特别关注API间的依赖关系，以便测试代码能够正确处理这些依赖。

            {f"请特别关注API文档补充说明中提到的内容: {message.api_doc_supplement}" if message.api_doc_supplement else ""}
            {f"请特别关注以下测试重点: {message.test_focus}" if message.test_focus else ""}

            OpenAPI文档内容:
            ```json
            {json.dumps(message.api_doc_content, indent=2)}
            ```
            """

            # 创建分析智能体并使用流式输出
            analyzer_agent = AssistantAgent(
                name="analyzer_agent",
                model_client=model_client,
                system_message=self.system_message,
                model_client_stream=True,
            )

            api_analysis = ""
            stream = analyzer_agent.run_stream(task=api_analysis_prompt)

            await publish_log_message(self, "正在分析API文档...\n\n", "api_analyzer")

            async for msg in stream:
                if isinstance(msg, ModelClientStreamingChunkEvent):
                    # 将生成进度发送到前端
                    await publish_log_message(self, msg.content, "api_analyzer")
                    # 动态更新进度，基于内容生成长度
                    content_length = len(msg.content)
                    # 基于内容长度估算进度，区间为10-25%
                    estimated_progress = 10 + min(15, int(content_length / 150))
                    await publish_progress_message(
                        self,
                        "analyze",
                        estimated_progress,
                        "分析API接口结构",
                        "api_analyzer"
                    )
                    continue

                if isinstance(msg, TaskResult):
                    # 获取完整的生成结果
                    api_analysis = msg.messages[-1].content

            # 发送分析结果到测试用例设计器（不是测试生成器）
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
                ),
                topic_id=TopicId(type=TopicTypes.TEST_CASE_DESIGNER, source=self.id.key)
            )
            await publish_progress_message(self, "analyze", 25, "API文档分析完成，整理结果中", "api_analyzer")

            # 发送进度消息
            await publish_progress_message(
                self, "analyze", 30, "API文档分析报告完成，准备设计测试用例", "api_analyzer"
            )

            logger.info(f"API文档分析完成")
            await publish_log_message(self, "API文档分析完成\n\n", "api_analyzer")

        except Exception as e:
            error_msg = f"API分析处理出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await publish_error_message(self, error_msg, "api_analyzer")


# API测试用例设计智能体
@type_subscription(topic_type=TopicTypes.TEST_CASE_DESIGNER)
class TestCaseDesignerAgent(RoutedAgent):
    """API测试用例设计智能体，负责根据API分析结果设计全面的测试用例"""

    def __init__(self):
        super().__init__("test_case_designer_agent")
        self.system_message = """
你是一位专业的API测试用例设计专家，负责根据API分析结果设计全面、高质量的测试用例。

你的测试用例设计应涵盖以下方面：

1. 功能测试（核心）：
   - 每个接口的正常流程测试（正向场景）
   - 所有必选参数和可选参数的组合
   - 不同HTTP方法的正确使用
   - 资源间依赖关系的处理流程（例如先创建再查询）
   - 完整的CRUD操作链

2. 边界条件测试：
   - 输入参数的边界值（最小值、最大值、临界值）
   - 空值、0值、极大值的处理
   - 字符串长度限制和格式限制
   - 日期范围和时间格式处理

3. 异常流程测试：
   - 无效参数和无效格式的处理
   - 缺失必填参数的情况
   - 错误的认证凭据
   - 无权限访问的资源
   - 重复操作和冲突处理（如创建已存在的资源）

4. 数据验证测试：
   - 响应数据结构符合规范
   - 响应字段的类型、格式和值范围验证
   - 状态码正确性验证
   - 响应头部验证

5. 安全测试：
   - 认证和授权逻辑
   - 敏感数据传输
   - CSRF/XSS防护验证
   - 过度请求限制测试

6. 并发和性能测试（根据需求）：
   - 简单的并发请求测试
   - 基本性能指标验证
   - 大数据量处理能力

每个测试用例应包含：

1. 用例ID和名称：简洁明了的标识
2. 前置条件：测试执行的必要准备工作
3. 测试步骤：详细的操作步骤
4. 输入数据：请求参数、请求体和必要的请求头
5. 预期结果：期望的响应状态码、响应体和其他响应属性
6. 后置处理：测试完成后的清理步骤

特别注意：

- 确保测试用例之间的独立性，每个用例应自包含，不依赖其他用例的执行结果
- 对于有依赖关系的操作（如编辑前需要先创建资源），在同一用例中处理完整流程
- 设计测试数据时考虑数据的唯一性和有效性
- 考虑API的特性和限制，设计针对性的测试用例
- 针对特定业务规则和约束设计专门的验证用例
"""

    @message_handler
    async def handle_message(self, message: APIAnalysisResult, ctx: MessageContext) -> None:
        """处理API分析结果，设计测试用例"""
        logger.info(f"开始设计API测试用例: {message.base_url}")

        try:
            # 发送进度消息
            await publish_progress_message(self, "design", 31, "初始化测试用例设计流程", "test_case_designer")

            # 构建测试用例设计问题
            await publish_progress_message(self, "design", 33, "构建测试用例设计方案", "test_case_designer")
            # 构建测试用例设计问题
            question = f"""
            根据以下API分析结果，设计一套全面的API测试用例，尽量覆盖较多的测试场景，较高的用例覆盖率

            API基础URL: {message.base_url}
            API文档URL: {message.api_docs_url}

            API分析结果:
            {message.analysis}

            {"测试重点: " + message.test_focus if message.test_focus else ""}
            {"API文档补充说明: " + message.api_doc_supplement if message.api_doc_supplement else ""}

            请设计测试用例，包括但不限于以下类型：
            1. 功能测试（正向流程）
            2. 边界条件测试
            3. 异常流程测试
            4. 数据验证测试
            5. 安全测试
            6. 并发和性能测试（如适用）

            ==== 格式要求 ====
            每个测试用例必须使用以下格式，并用特殊分隔符"===TEST_CASE_SEPARATOR==="标记每个用例的开始：

            ===TEST_CASE_SEPARATOR===
            ## 测试用例 ID: TC-XXX

            **名称**: [测试用例名称]

            **类型**: [测试类型，如：功能测试/边界测试/异常测试等]

            **前置条件**:
            - [前置条件1]
            - [前置条件2]

            **测试步骤**:
            1. [步骤1]
            2. [步骤2]
            3. [步骤3]

            **输入数据**:
            ```json
            {{
              "key": "value"
            }}
            ```

            **预期结果**:
            - [预期结果1]
            - [预期结果2]

            **后置处理**:
            - [清理步骤1]
            - [清理步骤2]

            ==== 要求 ====
            测试用例设计应考虑以下特点：
            - 完全独立性：每个测试用例能单独运行，不依赖其他用例
            - 自包含性：每个用例包含所有必要的步骤，从创建依赖资源到清理
            - 资源生命周期管理：测试用例创建的所有资源在测试完成后应被清理
            - 数据有效性：使用符合业务规则的有效测试数据
            - 针对API特性的定制测试

            请按照API的主要功能模块或资源类型组织测试用例，并确保覆盖所有关键场景。
            注意：始终使用"===TEST_CASE_SEPARATOR==="作为每个测试用例的起始标记，这对于测试用例计数和展示非常重要。
            """
            # 创建测试用例设计智能体
            case_designer = AssistantAgent(
                name="case_designer",
                model_client=model_client,
                system_message=self.system_message,
                model_client_stream=True,
            )
            await publish_progress_message(self, "design", 35, "启动智能测试用例设计引擎", "test_case_designer")

            # 生成测试用例设计
            test_cases = ""
            design_stream = case_designer.run_stream(task=question)

            await publish_log_message(self, "开始设计API测试用例...\n\n", "test_case_designer")

            async for msg in design_stream:
                if isinstance(msg, ModelClientStreamingChunkEvent):
                    await publish_log_message(self, msg.content, "test_case_designer")
                    # 动态更新进度，基于内容生成的进度
                    # 设计阶段的进度区间是35-49%
                    content_length = len(msg.content)
                    # 基于内容长度估算进度
                    estimated_progress = 35 + min(14, int(content_length / 100))
                    await publish_progress_message(
                        self, 
                        "design", 
                        estimated_progress,
                        "正在生成测试用例",
                        "test_case_designer"
                    )
                if isinstance(msg, TaskResult):
                    test_cases = msg.messages[-1].content

            await publish_progress_message(self, "design", 50, "测试用例设计完成，进行测试覆盖率分析",
                                           "test_case_designer")

            # 发送进度消息
            await publish_progress_message(
                self, "design", 52, "测试用例设计与分析完成，准备生成测试代码", "test_case_designer"
            )

            # 提取测试用例元数据
            try:
                # 使用分隔符统计测试用例数量
                separator = "===TEST_CASE_SEPARATOR==="
                # 计算分隔符出现的次数作为测试用例数量
                case_count = test_cases.count(separator)

                # 如果没有找到分隔符，尝试使用之前的方法估算
                if case_count == 0:
                    # 按段落分割（连续的两个换行符表示段落）
                    paragraphs = re.split(r'\n\s*\n', test_cases)
                    # 筛选疑似测试用例的段落（含有测试相关关键词的段落）
                    test_keywords = ['测试', '验证', '检查', 'test', 'verify', 'check', 'assert']
                    possible_test_cases = [p for p in paragraphs if any(kw in p.lower() for kw in test_keywords)]
                    case_count = len(possible_test_cases)

                # 分析用例类型覆盖
                coverage_analysis = {
                    "functional": "功能测试" in test_cases,
                    "boundary": "边界" in test_cases or "边界条件" in test_cases,
                    "negative": "异常" in test_cases or "负向" in test_cases,
                    "validation": "验证" in test_cases,
                    "security": "安全" in test_cases,
                    "performance": "性能" in test_cases or "并发" in test_cases
                }

                # 估算用例覆盖率 - 改进覆盖率计算逻辑
                # 基于测试用例数量和覆盖的测试类型数量
                covered_types = sum(1 for value in coverage_analysis.values() if value)
                type_coverage_factor = covered_types / len(coverage_analysis)

                # 根据API分析结果中提到的接口数估算
                endpoint_pattern = r'(接口|endpoint|API|路径|path)[^\d]*(\d+)'
                endpoint_matches = re.findall(endpoint_pattern, message.analysis, re.IGNORECASE)
                endpoint_count = int(endpoint_matches[0][1]) if endpoint_matches else 5

                # 计算每个接口的平均测试用例数
                cases_per_endpoint = case_count / endpoint_count if endpoint_count > 0 else 1

                # 综合考虑用例数量、覆盖类型和每个接口的平均用例数
                api_coverage = min(95, int(50 * type_coverage_factor + 10 * min(cases_per_endpoint, 5)))

                test_case_metadata = {
                    "total_test_cases": case_count,
                    "coverage_types": coverage_analysis,
                    "api_coverage_estimate": f"{api_coverage}%",
                    "endpoints_count": endpoint_count
                }
            except Exception as e:
                logger.warning(f"提取测试用例元数据失败: {str(e)}")
                test_case_metadata = {"warning": "无法提取测试用例统计信息"}

            # 发送测试用例到测试生成器
            await self.publish_message(
                TestCaseDesignResult(
                    api_docs_url=message.api_docs_url,
                    base_url=message.base_url,
                    test_cases=test_cases,
                    api_analysis=message.analysis,
                    enable_review=message.enable_review,
                    user_review=message.user_review,
                    use_local_executor=message.use_local_executor,
                    test_focus=getattr(message, 'test_focus', None),
                    api_doc_supplement=getattr(message, 'api_doc_supplement', None),
                    test_case_metadata=test_case_metadata
                ),
                topic_id=TopicId(type=TopicTypes.TEST_GENERATOR, source=self.id.key)
            )

            # 将测试用例信息发送到前端
            await self.publish_message(
                WebSocketMessage(
                    type="test_cases",
                    content={"test_cases": test_cases, "metadata": test_case_metadata},
                    source="test_case_designer"
                ),
                topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=self.id.key)
            )

            logger.info(f"API测试用例设计完成: {message.base_url}")

        except Exception as e:
            error_msg = f"设计API测试用例出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await publish_error_message(self, error_msg, "test_case_designer")


# 测试代码生成器智能体
@type_subscription(topic_type=TopicTypes.TEST_GENERATOR)
class TestGeneratorAgent(RoutedAgent):
    """测试代码生成智能体"""

    def __init__(self, work_dir: Path):
        super().__init__("test_generator_agent")
        self.code_team = CodeGenerationTeam(model_client, self)
        self._work_dir = work_dir

    @message_handler
    async def handle_message(self, message: TestCaseDesignResult, ctx: MessageContext) -> None:
        """处理测试用例设计结果并生成测试代码"""
        try:
            # 生成并审查合并后的测试脚本
            test_result = await self.code_team.generate_and_review_code(
                code_type="test_script",
                requirements=f"""
                基于以下内容生成一个完整的pytest测试脚本文件(test_script.py)。
                这个文件需要包含所有必要的工具类、配置和测试用例。

                API信息:
                - API文档URL: {message.api_docs_url}
                - API基础URL: {message.base_url}
                - API分析结果: {message.api_analysis}

                测试需求:
                - 测试用例设计: {message.test_cases}
                - {"测试重点: " + message.test_focus if message.test_focus else "测试重点: 全面测试所有API接口"}
                - {"API文档补充说明: " + message.api_doc_supplement if message.api_doc_supplement else ""}

                请在test_script.py中实现以下内容：

                1. 工具类部分:
                   - 导入所有必要的包和模块
                   - DataGenerator类用于生成测试数据（可以借助Faker或者mimesis）
                   - ApiClient类实现API请求工具
                   - 其他必要的数据模型和工具函数

                2. 测试配置部分:
                   - pytest fixtures的定义
                   - 会话级别(session scope)的fixtures
                   - 模块级别(module scope)的fixtures
                   - 功能级别(function scope)的fixtures
                   - 资源管理fixtures
                   - 测试hooks配置

                3. 测试用例部分:
                   - 基于测试用例设计实现具体的测试函数
                   - 确保测试用例完全独立
                   - 实现完整的测试数据生命周期管理
                   - 处理测试资源的创建和清理

                代码要求:
                1. 文件结构清晰，使用注释分隔不同部分
                2. 提供详细的文档注释
                3. 确保代码的可维护性和可扩展性
                4. 遵循Python最佳实践和PEP 8规范
                5. 实现完整的错误处理和日志记录
                6. 确保测试用例之间的独立性
                7. 对于需要登录的操作：
                   - 创建测试账号
                   - 执行登录
                   - 执行测试
                   - 清理账号
                8. 对于有依赖关系的资源：
                   - 按正确顺序创建依赖资源
                   - 执行测试操作
                   - 按相反顺序清理资源

                文件结构示例：
                ```python
                # === 导入部分 ===
                import pytest
                import requests
                # ... 其他导入

                # === 工具类部分 ===
                class DataGenerator:
                    # ... 实现测试数据生成逻辑

                class ApiClient:
                    # ... 实现API请求工具

                # === Fixtures部分 ===
                @pytest.fixture(scope="session")
                def api_client():
                    # ... 实现API客户端fixture

                # === 测试用例部分 ===
                class TestApiEndpoints:
                    # ... 实现测试用例
                ```
                """,
                dependencies=[]
            )

            # 保存合并后的测试脚本
            test_file_path = self._work_dir / "test_script.py"

            # 确保code_content是字符串
            code_content = test_result["code_content"].code if hasattr(test_result["code_content"], 'code') else str(
                test_result["code_content"])

            save_code_to_file(code_content, test_file_path)

            # 发送测试代码到前端显示
            code_content_msg = {
                "code": code_content,
                "test_file_path": str(test_file_path),
                "aux_files": {}
            }

            await self.publish_message(
                WebSocketMessage(
                    type="code",
                    content=code_content_msg,
                    source="test_generator"
                ),
                topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=self.id.key)
            )

            # 发布最终的测试代码生成结果
            await self.publish_message(
                TestGenerationResult(
                    test_file_path=str(test_file_path),  # 将Path对象转换为字符串
                    base_url=message.base_url,
                    enable_review=message.enable_review,
                    user_review=message.user_review,
                    use_local_executor=message.use_local_executor,
                    test_code=code_content,
                    review_notes={
                        "test": test_result["review_notes"]
                    }
                ),
                topic_id=TopicId(type=TopicTypes.TEST_EXECUTOR, source="test_generator")
            )

        except Exception as e:
            error_msg = f"测试代码生成失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self.publish_message(
                TestGenerationResult(
                    test_file_path=str(self._work_dir / "test_script.py"),  # 使用默认的测试文件路径
                    base_url=message.base_url,
                    enable_review=message.enable_review,
                    user_review=message.user_review,
                    use_local_executor=message.use_local_executor,
                    test_code="",
                    review_notes={"error": [error_msg]}
                ),
                topic_id=TopicId(type=TopicTypes.TEST_RESULT, source="test_generator")
            )


# 测试执行器智能体
@type_subscription(topic_type=TopicTypes.TEST_EXECUTOR)
class TestExecutorAgent(RoutedAgent):
    """测试执行智能体，专注于执行测试用例"""

    def __init__(self, work_dir: Path, use_local_executor: bool = True):
        super().__init__("test_executor_agent")
        self._code_executor = None
        self._use_local_executor = use_local_executor
        self._work_dir = work_dir

    async def _init_executor(self) -> None:
        """初始化代码执行器"""
        if self._code_executor is None:
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

    @message_handler
    async def handle_message(self, message: TestGenerationResult, ctx: MessageContext) -> None:
        """处理测试执行请求"""
        try:
            # 获取测试文件路径
            test_file_path = message.test_file_path
            test_dir = message.test_dir if hasattr(message, 'test_dir') and message.test_dir else None
            test_params = message.test_params if hasattr(message, 'test_params') else {}
            pytest_options = message.pytest_options if hasattr(message, 'pytest_options') else ""

            logger.info(f"准备执行测试: {test_file_path}")
            logger.info(f"测试参数: {test_params}")
            logger.info(f"Pytest选项: {pytest_options}")

            # 验证测试文件是否存在
            if not os.path.exists(test_file_path):
                error_msg = f"测试文件不存在: {test_file_path}"
                logger.error(error_msg)
                await publish_error_message(self, error_msg, "test_executor")
                return

            # 设置工作目录
            test_file_path = os.path.abspath(test_file_path)
            self._work_dir = os.path.dirname(test_file_path)
            if test_dir and os.path.exists(test_dir):
                self._work_dir = os.path.abspath(test_dir)

            logger.info(f"测试执行工作目录: {self._work_dir}")

            # 用户评审环节，如果需要
            if message.enable_review and message.user_review:
                await publish_log_message(self, "等待用户评审测试代码...", "test_executor")
                await publish_progress_message(
                    self, "review", 76, "等待用户评审", "test_executor"
                )
                await publish_log_message(self, "用户评审完成，准备执行测试", "test_executor")

            # 初始化执行器
            await self._init_executor()

            # 发送测试开始的消息
            await publish_log_message(self, "开始执行测试...\n\n", "test_executor")
            await publish_progress_message(
                self, "execute", 80, "初始化测试环境", "test_executor"
            )

            try:
                # 构建测试命令
                work_dir = os.path.normpath(self._work_dir)
                test_file = os.path.basename(test_file_path)

                # 构建pytest命令
                pytest_cmd = f'python -m pytest "{test_file}" '
                pytest_cmd += '-v --html=report.html --json-report --json-report-file=report.json '
                pytest_cmd += '--alluredir=./allure-results'
                pytest_cmd += f' --base-url="{message.base_url}"'

                if pytest_options:
                    pytest_cmd += f' {pytest_options}'

                # 设置环境变量
                env = {
                    "PYTHONIOENCODING": "utf-8",
                    "PYTHONUTF8": "1",
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONPATH": f"{work_dir}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"
                }

                # 执行测试命令
                await publish_log_message(self, f"执行测试命令: {pytest_cmd}\n\n", "test_executor")
                test_result = await self._code_executor.execute_command(pytest_cmd, env=env)

                # 输出测试结果
                output = test_result.get("output", "")
                exit_code = test_result.get("exit_code", -1)

                logger.info(f"测试执行完成，退出码: {exit_code}")
                await publish_log_message(self, f"测试执行完成，退出码: {exit_code}\n\n", "test_executor")

                # 检查报告文件
                report_path = os.path.join(self._work_dir, "report.html")
                json_report_path = os.path.join(self._work_dir, "report.json")
                allure_results_dir = os.path.join(self._work_dir, "allure-results")

                # 将HTML报告文件路径转换为URL格式
                report_url = None
                if os.path.exists(report_path):
                    static_dir = os.path.join(os.getcwd(), "static")
                    if not os.path.exists(static_dir):
                        os.makedirs(static_dir)

                    report_filename = f"report_{uuid.uuid4().hex[:8]}.html"
                    static_report_path = os.path.join(static_dir, report_filename)
                    shutil.copy2(report_path, static_report_path)

                    report_url = f"/static/{report_filename}"
                    logger.info(f"报告URL: {report_url}")

                # 提取测试统计信息
                test_stats = {}
                try:
                    summary_pattern = r'(\d+) passed,?\s*(\d+) failed,?\s*(\d+) error(?:ed)?,?\s*(\d+) skipped'
                    alt_summary_pattern = r'(\d+) passed,?\s*(\d+) failed,?\s*(\d+) skipped'

                    summary_match = re.search(summary_pattern, output)
                    if summary_match:
                        test_stats["passed"] = int(summary_match.group(1))
                        test_stats["failed"] = int(summary_match.group(2))
                        test_stats["error"] = int(summary_match.group(3))
                        test_stats["skipped"] = int(summary_match.group(4))
                    else:
                        alt_match = re.search(alt_summary_pattern, output)
                        if alt_match:
                            test_stats["passed"] = int(alt_match.group(1))
                            test_stats["failed"] = int(alt_match.group(2))
                            test_stats["skipped"] = int(alt_match.group(3))
                            test_stats["error"] = 0

                    test_stats["total"] = test_stats.get("passed", 0) + test_stats.get("failed", 0) + test_stats.get(
                        "error", 0) + test_stats.get("skipped", 0)

                    duration_pattern = r'in\s+([\d\.]+)s'
                    duration_match = re.search(duration_pattern, output)
                    if duration_match:
                        test_stats["duration"] = float(duration_match.group(1))
                except Exception as e:
                    logger.warning(f"从输出提取测试统计失败: {str(e)}")

                # 1. 首先发送测试结果到前端
                await self.publish_message(
                    WebSocketMessage(
                        type="test_result",
                        content={
                            "test_result": {
                                "stats": test_stats,
                                "output": output,
                                "duration": test_stats.get("duration", 0),
                                "status": "success" if exit_code == 0 else "error",
                                "exit_code": exit_code
                            },
                            "report_data": {
                                "analysis": None,  # 将由分析器填充
                                "html_report": report_url,
                                "allure_report": None  # 先置为None，稍后处理
                            },
                            "test_file_path": test_file_path,
                            "test_params": test_params
                        },
                        source="test_executor"
                    ),
                    topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=self.id.key)
                )

                # 添加一个额外消息来确保前端收到测试结果
                await self.publish_message(
                    WebSocketMessage(
                        type="result",
                        content={
                            "test_result": {
                                "stats": test_stats,
                                "output": output,
                                "duration": test_stats.get("duration", 0),
                                "status": "success" if exit_code == 0 else "error",
                                "exit_code": exit_code
                            },
                            "test_file_path": test_file_path,
                            "test_params": test_params
                        },
                        source="test_executor"
                    ),
                    topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=self.id.key)
                )

                # 2. 然后，异步处理Allure报告
                if os.path.exists(allure_results_dir):
                    try:
                        await publish_log_message(self, "正在生成Allure报告...", "test_executor")
                        connect_operator = ";" if sys.platform == "win32" else "&&"

                        # 生成Allure报告
                        allure_report_dir = os.path.join(self._work_dir, "allure-report")
                        allure_cmd = f"cd {self._work_dir} {connect_operator} allure generate allure-results -o allure-report --clean"
                        executor = UniversalExecutor(
                            work_dir=self._work_dir,
                            use_local_executor=True
                        )
                        allure_result = await executor.execute_command(allure_cmd)

                        if allure_result.get("exit_code", -1) == 0 and os.path.exists(allure_report_dir):
                            # 将报告复制到前端的static目录
                            web_static_dir = os.path.join(os.getcwd(), "web", "static")
                            if not os.path.exists(web_static_dir):
                                os.makedirs(web_static_dir)

                            # 创建唯一的目录名
                            allure_dir_name = f"allure_{uuid.uuid4().hex[:8]}"
                            web_static_allure_dir = os.path.join(web_static_dir, allure_dir_name)

                            try:
                                # 复制整个目录
                                logger.info(f"开始复制Allure报告: 源={allure_report_dir}, 目标={web_static_allure_dir}")
                                shutil.copytree(allure_report_dir, web_static_allure_dir)

                                # 验证复制是否成功
                                if os.path.exists(os.path.join(web_static_allure_dir, "index.html")):
                                    logger.info(f"成功复制Allure报告，index.html存在")
                                else:
                                    logger.error(f"复制Allure报告后index.html不存在！")

                                # 设置文件权限确保可访问 (对于Unix系统)
                                if not sys.platform.startswith('win'):
                                    os.chmod(web_static_allure_dir, 0o755)
                                    for root, dirs, files in os.walk(web_static_allure_dir):
                                        for d in dirs:
                                            os.chmod(os.path.join(root, d), 0o755)
                                        for f in files:
                                            os.chmod(os.path.join(root, f), 0o644)
                                    logger.info(f"已设置Allure报告目录权限")
                            except Exception as copy_error:
                                logger.error(f"复制Allure报告出错: {str(copy_error)}", exc_info=True)
                                raise

                            # 生成相对URL路径（不含端口号）
                            allure_report_url = f"/static/{allure_dir_name}/index.html"

                            # 记录调试信息
                            logger.info(f"Allure报告URL: {allure_report_url}")
                            logger.info(f"Web静态目录路径: {web_static_dir}")
                            logger.info(f"Allure报告目录: {web_static_allure_dir}")
                            logger.info(f"验证Web静态目录存在: {os.path.exists(web_static_dir)}")
                            logger.info(f"验证Allure报告目录存在: {os.path.exists(web_static_allure_dir)}")
                            logger.info(
                                f"验证Allure报告文件存在: {os.path.exists(os.path.join(web_static_allure_dir, 'index.html'))}")

                            # 打印目录下的文件列表，帮助调试
                            try:
                                web_static_files = os.listdir(web_static_dir)
                                logger.info(f"Web静态目录内容: {web_static_files}")

                                allure_files = os.listdir(web_static_allure_dir)
                                logger.info(
                                    f"Allure报告目录内容: {allure_files if len(allure_files) < 20 else f'{len(allure_files)}个文件'}")

                                # 检查index.html文件
                                index_path = os.path.join(web_static_allure_dir, "index.html")
                                if os.path.exists(index_path):
                                    index_size = os.path.getsize(index_path)
                                    logger.info(f"index.html大小: {index_size} 字节")

                                    # 读取文件的前100个字符进行验证
                                    with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        content_start = f.read(100)
                                        logger.info(f"index.html内容开头: {content_start}")
                            except Exception as e:
                                logger.error(f"列出目录内容时出错: {str(e)}", exc_info=True)

                            # 3. 单独发送Allure报告URL到前端
                            await self.publish_message(
                                WebSocketMessage(
                                    type="allure_report",
                                    content={
                                        "allure_report_url": allure_report_url,  # 使用相对URL
                                        "report_data": {
                                            "allure_report": allure_report_url  # 使用相对URL
                                        }
                                    },
                                    source="test_executor"
                                ),
                                topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=self.id.key)
                            )

                            # 为前端提供额外的路径信息，帮助诊断
                            await publish_log_message(
                                self,
                                f"Allure报告生成完成。\n"
                                f"- 报告URL: {allure_report_url}\n"
                                f"如果内嵌报告不能正常显示，请刷新页面或检查前端静态资源是否正确加载。",
                                "test_executor"
                            )
                    except Exception as e:
                        logger.error(f"生成Allure报告失败: {str(e)}", exc_info=True)
                        await publish_error_message(self, f"生成Allure报告失败: {str(e)}", "test_executor")

                # 4. 发送测试执行输出到分析智能体
                await self.publish_message(
                    TestExecutionOutput(
                        test_file_path=test_file_path,
                        output=output,
                        exit_code=exit_code,
                        stats=test_stats,
                        report_path=report_url,
                        json_report_path=json_report_path if os.path.exists(json_report_path) else None,
                        allure_results_dir=allure_results_dir if os.path.exists(allure_results_dir) else None,
                        test_params=test_params
                    ),
                    topic_id=TopicId(type=TopicTypes.TEST_RESULT_ANALYZER, source=self.id.key)
                )

                logger.info("测试执行结果已发送到前端和分析智能体")

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
            if self._work_dir and Path(self._work_dir).exists():
                cleanup_dir(Path(self._work_dir))
                logger.info(f"已清理测试执行器工作目录: {self._work_dir}")
        except Exception as e:
            logger.error(f"清理资源失败: {str(e)}")


# 测试结果分析智能体
@type_subscription(topic_type=TopicTypes.TEST_RESULT_ANALYZER)
class TestResultAnalyzerAgent(RoutedAgent):
    """测试结果分析智能体，专注于分析测试结果并生成报告"""

    def __init__(self):
        super().__init__("test_result_analyzer_agent")

    @message_handler
    async def handle_message(self, message: TestExecutionOutput, ctx: MessageContext) -> None:
        """处理测试执行输出并生成分析报告"""
        try:
            await publish_progress_message(self, "analyze", 85, "开始分析测试结果", "test_result_analyzer")

            # 分析测试结果
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
{message.output[:4000] if len(message.output) > 4000 else message.output}
```

测试统计信息：
- 总测试数: {message.stats.get('total', 'N/A')}
- 通过: {message.stats.get('passed', 'N/A')}
- 失败: {message.stats.get('failed', 'N/A')}
- 错误: {message.stats.get('error', 'N/A')}
- 跳过: {message.stats.get('skipped', 'N/A')}
- 执行时间: {message.stats.get('duration', 'N/A')} 秒

请提供全面、客观的分析，重点指出发现的问题和改进建议。
"""

            # 生成分析报告
            analysis_agent = AssistantAgent(
                name="test_analyzer",
                model_client=model_client,
                system_message="你是一位专业的测试分析专家，负责分析测试结果并提供详细的分析报告和改进建议。",
                model_client_stream=True
            )

            analysis_stream = analysis_agent.run_stream(task=analysis_question)

            analysis_result = ""
            await publish_log_message(self, "正在分析测试结果...\n\n", "test_result_analyzer")

            async for msg in analysis_stream:
                if isinstance(msg, ModelClientStreamingChunkEvent):
                    await publish_log_message(self, msg.content, "test_result_analyzer")
                    # 分析阶段进度更新
                    content_length = len(msg.content)
                    # 基于内容长度估算进度，区间为85-92%
                    estimated_progress = 85 + min(7, int(content_length / 100))
                    await publish_progress_message(
                        self,
                        "analyze",
                        estimated_progress,
                        "分析测试执行结果",
                        "test_result_analyzer"
                    )

                if isinstance(msg, TaskResult):
                    analysis_result = msg.messages[-1].content

            # 发送分析报告到前端 - 修改消息类型和数据结构以匹配前端期望
            await self.publish_message(
                WebSocketMessage(
                    type="analysis",  # 将类型从"test_analysis"改为"analysis"
                    content={
                        "analysis": analysis_result,  # 直接提供analysis字段
                        "test_stats": message.stats,
                        "test_file_path": message.test_file_path,
                        "test_params": message.test_params
                    },
                    source="test_result_analyzer"
                ),
                topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=self.id.key)
            )

            # 同时也发送带有report_data结构的test_result消息，保持与其他智能体的一致性
            await self.publish_message(
                WebSocketMessage(
                    type="test_result",
                    content={
                        "report_data": {
                            "analysis": analysis_result,
                            "html_report": message.report_path,  # 保持原有HTML报告
                            "allure_report": None  # 保持原有Allure报告
                        },
                        "test_stats": message.stats,
                        "test_file_path": message.test_file_path,
                        "test_params": message.test_params
                    },
                    source="test_result_analyzer"
                ),
                topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=self.id.key)
            )

            logger.info("测试分析报告已发送到前端")

            # 发送到下一个智能体
            await self.publish_message(
                TestExecutionResult(
                    test_result={"stats": message.stats},
                    test_file_path=message.test_file_path,
                    analysis=analysis_result,
                    report_url=message.report_path,
                    allure_results_dir=message.allure_results_dir,
                    test_params=message.test_params
                ),
                topic_id=TopicId(type=TopicTypes.TEST_REPORT_ENHANCER, source=self.id.key)
            )

            await publish_progress_message(
                self, "analyze", 93, "测试结果分析完成，等待报告生成", "test_result_analyzer"
            )

            logger.info("测试分析完成，结果已发送到报告增强器")

        except Exception as e:
            error_msg = f"分析测试结果出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await publish_error_message(self, error_msg, "test_result_analyzer")


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
        logger.info(f"收到的报告URL: {message.report_url}")
        logger.info(f"收到的Allure结果目录: {message.allure_results_dir}")

        try:
            # 处理HTML报告
            if not message.report_url:
                await publish_log_message(self, "没有找到HTML报告URL，无法增强报告", "report_enhancer")
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

            enhancement_code = []

            # 使用流式模式
            stream = report_enhancer.run_stream(task=question)

            async for msg in stream:
                if isinstance(msg, ModelClientStreamingChunkEvent):
                    await publish_log_message(self, msg.content, "report_enhancer")

                if isinstance(msg, TaskResult):
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

            # 写入增强后的报告到原路径
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(enhanced_report_content)

            # 将增强后的报告复制到web/static目录 - 与Allure报告一致
            web_static_dir = os.path.join(os.getcwd(), "web", "static")
            if not os.path.exists(web_static_dir):
                os.makedirs(web_static_dir)

            # 生成唯一的报告文件名
            report_filename = f"enhanced_report_{uuid.uuid4().hex[:8]}.html"
            web_static_report_path = os.path.join(web_static_dir, report_filename)

            try:
                # 复制增强后的报告
                logger.info(f"复制增强后的HTML报告: 源={report_path}, 目标={web_static_report_path}")
                shutil.copy2(report_path, web_static_report_path)

                # 验证复制是否成功
                if os.path.exists(web_static_report_path):
                    logger.info(f"成功复制增强后的HTML报告")
                else:
                    logger.error(f"复制增强后的HTML报告失败！")

                # 设置文件权限 (对于Unix系统)
                if not sys.platform.startswith('win'):
                    os.chmod(web_static_report_path, 0o644)
                    logger.info(f"已设置HTML报告文件权限")

                # 生成相对URL路径
                web_report_url = f"/static/{report_filename}"

                logger.info(f"增强后的HTML报告URL: {web_report_url}")
                logger.info(f"Web静态目录路径: {web_static_dir}")
                logger.info(f"HTML报告文件存在: {os.path.exists(web_static_report_path)}")

                # 更新报告URL为新的路径
                report_url = web_report_url

            except Exception as copy_error:
                logger.error(f"复制增强后的HTML报告出错: {str(copy_error)}", exc_info=True)
                # 继续使用原始路径的报告
                logger.info(f"将使用原路径的增强报告: {report_url}")

            await publish_progress_message(
                self, "analyze", 95, "增强测试报告可视化效果", "report_enhancer"
            )
            await publish_log_message(self, f"报告增强完成: {report_url}\n\n", "report_enhancer")

            # 发送增强后的HTML报告URL到前端
            await self.publish_message(
                WebSocketMessage(
                    type="enhanced_report",
                    content={
                        "report_data": {
                            "analysis": None,  # 保持原有分析报告
                            "html_report": report_url,
                        },
                        "enhancement_applied": True
                    },
                    source="report_enhancer"
                ),
                topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=self.id.key)
            )

            # 最后发送100%进度完成的消息
            await publish_progress_message(
                self, "complete", 100, "测试自动化流程全部完成", "report_enhancer"
            )

            logger.info("测试报告增强完成，所有结果已发送")

        except Exception as e:
            error_msg = f"增强测试报告出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await publish_error_message(self, error_msg, "report_enhancer")

    def _apply_enhancements(self, original_html: str, enhancements: List) -> str:
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

            # 清理HTML代码中的无效标签字符
            # 修复问题: 'invalid-first-character-of-tag-name'
            import re

            # 1. 处理原始HTML内容，清理无效字符
            def clean_html_content(content):
                # 确保正确处理HTML标签
                # 1.1 处理不正确的标签开始符号
                cleaned = re.sub(r'<(\s*[^a-zA-Z/!\?])', r'&lt;\1', content)

                # 1.2 特殊处理常见的无效标签情况
                cleaned = cleaned.replace('<>', '&lt;&gt;')
                cleaned = cleaned.replace('< ', '&lt; ')
                cleaned = cleaned.replace('<\n', '&lt;\n')

                # 1.3 处理特殊字符在标签内的情况
                cleaned = re.sub(r'<([a-zA-Z][^<>]*?)([<>])([^<>]*?)>', r'<\1"\2"\3>', cleaned)

                # 1.4 处理标签内不正确的属性定义
                cleaned = re.sub(r'=([^"\'][^\s>]*)', r'="\1"', cleaned)

                return cleaned

            # 2. 应用清理函数
            html_code = clean_html_content(html_code)

            # 3. 对整个增强后的HTML应用相同的清理步骤
            # 这确保了不仅注入的代码是有效的，原始HTML也会被清理
            def sanitize_complete_html(html_content):
                """对HTML进行全面清理，防止解析错误"""
                # 3.1 修复尖括号 '<' 和 '>' 被错误使用的情况
                # 保护已有的合法HTML标签
                protected = []

                def protect_tags(match):
                    protected.append(match.group(0))
                    return f"__PROTECTED_TAG_{len(protected) - 1}__"

                # 保护合法的HTML标签
                pattern = r'</?[a-zA-Z][a-zA-Z0-9]*(?:\s+[a-zA-Z_:][a-zA-Z0-9_:.-]*(?:\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\'"\s>]*))?)*\s*/?>|<!DOCTYPE[^>]*>'
                temp_html = re.sub(pattern, protect_tags, html_content)

                # 转义其他所有尖括号
                temp_html = temp_html.replace('<', '&lt;').replace('>', '&gt;')

                # 恢复受保护的标签
                for i, tag in enumerate(protected):
                    temp_html = temp_html.replace(f"__PROTECTED_TAG_{i}__", tag)

                return temp_html

            # 4. 增强注入的HTML处理
            enhanced_html = original_html  # 先使用原始HTML

            logger.info(f"HTML代码清理完成，准备注入到报告中")

            # 通过简单的字符串替换注入增强内容
            # 继续...

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
                # 避免直接替换，而是使用更安全的DOM解析方式
                try:
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

                    logger.info(f"HTML代码成功注入到报告中")
                except Exception as html_error:
                    logger.error(f"HTML注入错误: {str(html_error)}")
                    # 出错时，跳过HTML注入，但仍保留CSS和JS增强
                    logger.warning("由于HTML注入错误，将跳过HTML增强，仅使用CSS和JS增强")

            # 特别修复已知问题区域
            logger.info("执行特定HTML区域修复...")
            try:
                # 修复媒体区域标签问题
                media_pattern = r'<div class="media">(.*?)<div class="media__counter"></div>\s*</div>'
                media_fix = lambda m: m.group(0).replace('</div>', '').replace('<div class="media__counter">',
                                                                               '<div class="media__counter">')
                enhanced_html = re.sub(media_pattern, media_fix, enhanced_html, flags=re.DOTALL)

                # 修复logwrapper区域标签问题
                log_pattern = r'<div class="logwrapper">(.*?)</div>'
                log_fix = lambda m: re.sub(r'<([^a-zA-Z/])', r'&lt;\1', m.group(0))
                enhanced_html = re.sub(log_pattern, log_fix, enhanced_html, flags=re.DOTALL)

                # 修复任何剩余的无效标签
                enhanced_html = re.sub(r'<([^a-zA-Z/!\?])', r'&lt;\1', enhanced_html)
                logger.info("特定HTML区域修复完成")
            except Exception as fix_error:
                logger.error(f"修复特定HTML区域时出错: {str(fix_error)}")

            # 最终应用全面的HTML清理和转义
            sanitized_html = sanitize_complete_html(enhanced_html)

            logger.info(f"增强报告HTML处理完成，总长度: {len(sanitized_html)}")
            return sanitized_html
        except Exception as e:
            logger.error(f"应用报告增强失败: {str(e)}")
            return original_html  # 返回原始内容


# 启动运行时并执行API自动化测试流程
async def start_api_test_runtime(
        api_input: APIDocsInput,
        client_id: Optional[str] = None,
        result_handler: Optional[Callable[[ClosureContext, WebSocketMessage, MessageContext], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """启动API测试运行时"""
    try:
        # 使用tempfile创建临时目录
        work_dir = Path(tempfile.mkdtemp(prefix="api_test_"))
        logger.info(f"创建临时工作目录: {work_dir}")

        # 创建运行时
        runtime = SingleThreadedAgentRuntime()

        # 注册所有智能体
        await APIDocsFetcherAgent.register(
            runtime,
            TopicTypes.API_DOCS_FETCHER,
            lambda: APIDocsFetcherAgent()
        )

        await APIAnalyzerAgent.register(
            runtime,
            TopicTypes.API_ANALYZER,
            lambda: APIAnalyzerAgent()
        )

        await TestCaseDesignerAgent.register(
            runtime,
            TopicTypes.TEST_CASE_DESIGNER,
            lambda: TestCaseDesignerAgent()
        )

        # 注册测试生成器,使用代码生成团队
        await TestGeneratorAgent.register(
            runtime,
            TopicTypes.TEST_GENERATOR,
            lambda: TestGeneratorAgent(work_dir=work_dir)
        )

        await TestExecutorAgent.register(
            runtime,
            TopicTypes.TEST_EXECUTOR,
            lambda: TestExecutorAgent(work_dir=work_dir, use_local_executor=api_input.use_local_executor)
        )

        await TestResultAnalyzerAgent.register(
            runtime,
            TopicTypes.TEST_RESULT_ANALYZER,
            lambda: TestResultAnalyzerAgent()
        )

        await TestReportEnhancerAgent.register(
            runtime,
            TopicTypes.TEST_REPORT_ENHANCER,
            lambda: TestReportEnhancerAgent()
        )

        # 注册结果处理回调
        if result_handler:
            await ClosureAgent.register_closure(
                runtime,
                "result_collector",
                result_handler,
                subscriptions=lambda: [
                    TypeSubscription(topic_type=TopicTypes.TEST_RESULT, agent_type="result_collector")
                ],
            )

        # 启动运行时
        runtime.start()

        # 发布初始消息
        await runtime.publish_message(
            api_input,
            topic_id=TopicId(type=TopicTypes.API_DOCS_FETCHER, source="api_router")
        )

        # 如果不使用回调，则等待运行时完成
        if not (result_handler or client_id):
            logger.info("等待API测试流程完成...")
            await runtime.stop_when_idle()
            # 清理资源
            cleanup_dir(work_dir)

        return {"status": "success", "message": "测试流程已启动"}
    except Exception as e:
        logger.error(f"API测试运行时启动失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"API测试运行时启动失败: {str(e)}"
        }


