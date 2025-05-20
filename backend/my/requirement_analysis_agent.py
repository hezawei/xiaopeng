import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.messages import ToolCallSummaryMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from docling.document_converter import DocumentConverter
from llama_index.core import SimpleDirectoryReader, Document

from llms import model_client
from pydantic import BaseModel, Field
from typing import List, Optional

class BusinessRequirement(BaseModel):
    requirement_id: str = Field(..., description="需求编号(业务缩写+需求类型+随机3位数字)")
    requirement_name: str = Field(..., description="需求名称")
    requirement_type: str = Field(..., description="功能需求/性能需求/安全需求/其它需求")
    parent_requirement: Optional[str] = Field(None, description="该需求的上级需求")
    module: str = Field(..., description="所属的业务模块")
    requirement_level: str = Field(..., description="需求层级[BR]")
    reviewer: str = Field(..., description="审核人")
    estimated_hours: int = Field(..., description="预计完成工时(整数类型)")
    description: str = Field(..., description="需求描述")
    acceptance_criteria: str = Field(..., description="验收标准")

class BusinessRequirementList(BaseModel):
    requirements: List[BusinessRequirement] = Field(..., description="需求列表")

async def get_document_from_llama_index_file(files: list[str]) -> str:
    """
    使用LlamaIndex从文件中获取文档内容
    :param files: 文件路径列表
    :return: 文档内容
    """
    try:
        # 如果是PDF文件或Word文档(.docx)，使用DocumentConverter
        if any(file.endswith(('.pdf', '.docx')) for file in files):
            converter = DocumentConverter()
            result = converter.convert(files[0])
            content = result.document.export_to_markdown()
            print(f"使用Docling处理{'PDF' if files[0].endswith('.pdf') else 'Word'}文档")
        else:
            # 使用LlamaIndex读取文件
            reader = SimpleDirectoryReader(input_files=files)
            docs = reader.load_data()
            content = "\n\n".join([doc.text for doc in docs])

        # 限制文档长度，防止超出模型上下文长度
        max_chars = 30000  # 大约10000个token
        if len(content) > max_chars:
            print(f"文档过长，进行截断处理。原长度: {len(content)} 字符")
            # 提取文档的前半部分和后半部分
            first_part = content[:max_chars//2]
            last_part = content[-max_chars//2:]
            content = first_part + "\n\n...[文档中间部分已省略]...\n\n" + last_part
            print(f"截断后长度: {len(content)} 字符")

        return content
    except Exception as e:
        import traceback
        print(f"读取文件失败，详细错误: {traceback.format_exc()}")
        return f"读取文件失败: {str(e)}"

async def structure_requirement(content: str) -> BusinessRequirementList:
    """
    对需求列表内容进行结构化
    :param content: 需求内容列表
    :return: 结构化的需求列表
    """
    # 简化版本，直接返回示例数据
    # 实际项目中应该调用LLM进行结构化
    return BusinessRequirementList(
        requirements=[
            BusinessRequirement(
                requirement_id="TEST001",
                requirement_name="示例需求",
                requirement_type="功能需求",
                module="测试模块",
                requirement_level="BR",
                reviewer="审核人",
                estimated_hours=8,
                description="这是一个示例需求描述",
                acceptance_criteria="验收标准示例"
            )
        ]
    )

async def insert_into_database(requirements: BusinessRequirementList):
    """将需求数据插入数据库"""
    # 简化版本，直接打印需求数据
    for req in requirements.requirements:
        print(f"需求ID: {req.requirement_id}")
        print(f"需求名称: {req.requirement_name}")
        print(f"需求类型: {req.requirement_type}")
        print(f"所属模块: {req.module}")
        print(f"需求层级: {req.requirement_level}")
        print(f"审核人: {req.reviewer}")
        print(f"预计工时: {req.estimated_hours}小时")
        print(f"需求描述: {req.description}")
        print(f"验收标准: {req.acceptance_criteria}")
        print("-" * 50)
    return f"完成【{len(requirements.requirements)}】条需求入库。"

class RequirementAnalysisAgent:
    def __init__(self, files: list[str]):
        self.files = files

    async def create_team(self) -> RoundRobinGroupChat:
        # 需求获取智能体
        requirement_acquisition_agent = AssistantAgent(
            name="requirement_acquisition_agent",
            model_client=model_client,
            tools=[get_document_from_llama_index_file],
            system_message=f"调用工具获取文档内容，传递给工具的文件参数是：{self.files}",
            model_client_stream=False,
        )

        # 需求分析智能体
        req_analysis_prompt = """
        根据如下格式的需求文档，进行需求分析，输出需求分析报告：

        ## 1. Profile
        **角色**：高级测试需求分析师
        **核心能力**：
        - 需求结构化拆解与可测试性转化
        - 风险驱动的测试策略设计
        - 全链路需求追溯能力
        ## 2. 需求结构化框架
        ### 2.1 功能需求分解
        ```markdown
        - [必选] 使用Markdown无序列表展示功能模块
        - [必选] 标注规则：
          - 核心功能：★（影响核心业务流程）
          - 高风险功能：⚠️（含外部依赖/复杂逻辑）
        - 示例：
          - 订单风控引擎（★⚠️）：实时交易风险评估
        ```

        ### 2.2 非功能需求矩阵
        ```markdown
        | 需求类型 | 关键指标 | 目标值 | 测试方法 |
        |---------|---------|--------|---------|
        | 性能 | 响应时间 | <200ms | JMeter |
        | 安全 | 数据加密 | AES-256 | 安全扫描 |
        ```

        ### 2.3 测试需求映射
        ```markdown
        **功能测试**：
        - 正向流程验证
        - 边界条件测试
        - 异常场景恢复

        **非功能测试**：
        - 负载测试（并发用户：1000）
        - 安全渗透测试（OWASP Top 10）
        ```

        ## 3. 风险分析框架
        ### 3.1 技术风险评估
        ```markdown
        | 风险点 | 影响范围 | 严重程度 | 缓解措施 |
        |-------|---------|---------|---------|
        | API超时 | 订单流程 | 高 | 重试机制 |
        | 数据丢失 | 用户资产 | 严重 | 事务+日志 |
        ```

        ### 3.2 测试覆盖策略
        ```markdown
        **核心流程**：
        - 100%功能覆盖
        - 80%代码覆盖率
        **边缘场景**：
        - 关键错误路径测试
        - 数据迁移验证
        ```

        ### 3.3 风险热点地图
        ```markdown
        🔥 高风险区（立即处理）：
        - 第三方身份认证服务降级
        - 支付金额计算精度丢失

        🛡️ 缓解措施：
        - 实施接口mock方案
        - 增加金额四舍五入审计日志
        ```

        ## 4. 增强版输出规范
        ### 4.1 文档结构
        ```markdown
        ## 四、测试追踪矩阵
        | 需求ID | 测试类型 | 用例数 | 自动化率 | 验收证据 |
        |--------|----------|--------|----------|----------|

        ## 五、环境拓扑图
        - 测试集群配置：4C8G*3节点
        - 特殊设备：iOS/Android真机测试架
        ```

        ### 4.2 用例设计规范
        ```markdown
        **TC-风险场景验证**：
        - 破坏性测试步骤：
          1. 模拟第三方API返回500错误
          2. 连续发送异常报文10次
        - 预期韧性表现：
          - 系统自动切换备用服务节点
          - 触发告警通知运维人员
        ```

        ## 5. 智能增强模块
        ```markdown
        [!AI辅助提示] 建议执行：
        1. 使用决策表分析登录模块的组合场景
        2. 对核心API进行Swagger规范校验
        3. 生成需求覆盖率热力图（使用JaCoCo）
        ```
        """

        requirement_analysis_agent = AssistantAgent(
            name="requirement_analysis_agent",
            model_client=model_client,
            system_message=req_analysis_prompt,
            model_client_stream=False,
        )

        # 需求输出智能体
        requirement_output_agent = AssistantAgent(
            name="requirement_output_agent",
            model_client=model_client,
            system_message="""
            请根据需求分析报告进行详细的需求整理，尽量覆盖到报告中呈现所有的需求内容，每条需求信息都参考如下格式，生成合适条数的需求项。最终以 JSON 形式输出：
            requirements:
            requirement_id:[需求编号(业务缩写+需求类型+随机3位数字)]
            requirement_name:[需求名称]
            requirement_type:[功能需求/性能需求/安全需求/其它需求]
            parent_requirement:[该需求的上级需求]
            module:[所属的业务模块]
            requirement_level:需求层级[BR]
            reviewer:[田老师]
            estimated_hours:[预计完成工时(整数类型)]
            description:[需求描述] 作为一个<某类型的用户>，我希望<达成某些目的>，这样可以<开发的价值>。\n 验收标准：[明确的验收标准]
            acceptance_criteria:[验收标准]
            """,
            model_client_stream=False,
        )

        # 需求入库智能体
        requirement_into_db_agent = AssistantAgent(
            name="requirement_into_db_agent",
            model_client=model_client,
            tools=[insert_into_database],
            system_message="""调用工具将需求数据插入到数据库""",
            model_client_stream=False,
        )

        source_termination = SourceMatchTermination(sources=["requirement_into_db_agent"])

        team = RoundRobinGroupChat([requirement_acquisition_agent, requirement_analysis_agent, requirement_output_agent,
                                    requirement_into_db_agent],
                                   termination_condition=source_termination)
        return team

