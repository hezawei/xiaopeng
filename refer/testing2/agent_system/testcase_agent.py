import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import TextMentionTermination, SourceMatchTermination
from autogen_agentchat.messages import ModelClientStreamingChunkEvent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from docling.document_converter import DocumentConverter
from pydantic import BaseModel, Field


async def get_file_content():
    """获取需求文件内容"""
    source = "api_doc.pdf"  # document per local path or URL
    converter = DocumentConverter()
    result = converter.convert(source)
    return result.document.export_to_markdown()

class TestCase(BaseModel):
    id: str = Field(..., description="用例ID")
    title: str = Field(..., description="用例标题")
    pre_conditions: str = Field(..., description="前置条件")
    priority: str = Field(..., description="优先级")
    steps: list[str] = Field(..., description="步骤")
    expected_result: list[str] = Field(..., description="预期结果")

class TestCaseList(BaseModel):
    testcases: list[TestCase] = Field(..., description="测试用例列表")
async def structure_testcase(content: str):
    """结构化测试用例"""
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIModel

    model = OpenAIModel(
        'deepseek-chat',
        base_url='https://api.deepseek.com',
        api_key='sk-e5b2a319f9ce4d0fb71c5dc96596a69d',
    )
    agent = Agent(model, result_type=TestCaseList)
    result = await agent.run(user_prompt=f"对下面内容进行结构化输出:\n{content}")
    return result.data

from agent_system.llms import model_client

testcase_orign = AssistantAgent(
    name="testcase_orign",
    model_client=model_client,
    tools=[get_file_content],
    system_message="调用工具获取文档内容",
    model_client_stream=False,  # Enable streaming tokens from the model client.
)

testcase_writer = AssistantAgent(
    name="testcase_writer",
    model_client=model_client,
    system_message="""
    根据`testcase_orign`读取到的内容完成测试用例编写
    注意：只生成用户指定条数的测试用例

    根据获取的需求从以下角度（不限于）编写测试用例：
    一、考虑使用如下用例设计方法及整合使用
    1、基础设计方法组合应用
    等价类划分：划分有效/无效等价类（如金额范围0.01-200元10）
    边界值分析：覆盖最小值、最大值及±1临界值（如微信红包0.01/200.01边界10）
    因果图与判定表：处理多输入条件组合（如用户登录场景：账号存在+密码正确/错误2）
    场景法：主流程+备选流覆盖（如电商下单：正常购买、库存不足、支付失败10）
    错误推测法：基于历史缺陷库设计异常路径（如输入特殊字符、超长字段2）
    2、高级设计方法补充
    正交试验法：针对多参数组合场景（如API接口参数组合优化测试）
    状态迁移法：适用于状态机驱动的功能（如订单状态流转：待支付→已取消→已退款）
    探索式测试：结合Session-Based Testing动态补充用例（复杂业务流程快速覆盖）
    二、保障测试用例的全面性
    1、多维度覆盖
    功能测试：正向流程+异常分支（如支付成功/余额不足/网络超时）
    性能测试：负载、压力、稳定性（如高并发下单场景8）
    安全测试：SQL注入、XSS、越权访问（垂直/水平权限校验11）
    兼容性测试：多OS（Windows/macOS）、浏览器（Chrome/Firefox）、分辨率适配
    用户体验测试：界面一致性、操作流畅性、提示友好性（如错误信息可读性7）
    2、数据驱动与参数化
    数据分离：外部CSV/Excel管理测试数据（如百种用户角色权限组合6）
    动态参数注入：通过变量实现用例复用（如API请求参数模板化）
    三、用例编写规范
    1、结构化要素
    - **用例编号**：模块_子功能_序列（如PAY_REFUND_001）
    - **前置条件**：明确环境依赖（如数据库版本、第三方服务状态）
    - **测试步骤**：原子化操作（步骤≤7步[7]()）
    - **预期结果**：量化验证点（如响应时间≤2s，数据库记录变更数=1）
    - **优先级**：P0（核心流程）→P3（边缘场景）
    2、是否考虑介入自动化测试
    可脚本化：步骤需支持转化为自动化脚本（如Selenium/Pytest）
    断言精准：包含数据库、日志、UI多维度校验点

    四、用例示例：电商购物车测试用例
    **用例ID**：CART_ADD_ITEM_001
    **标题**：添加商品边界值验证（库存最大值+1）
    **优先级**：P1
    **前置条件**：商品A库存=100
    **步骤**：
    1. 进入商品详情页
    2. 输入购买数量101
    3. 点击“加入购物车”
    **预期结果**：
    - 页面提示“库存不足”
    - 购物车商品数量未更新
    - 后端日志记录库存校验失败事件
    """,
    model_client_stream=True,
)
testcase_structure = AssistantAgent(
    name="testcase_structure",
    model_client=model_client,
    tools=[structure_testcase],
    system_message="调用工具对用例内容进行格式化，任务完成输出 `FINISHED`",
    model_client_stream=False,
)
text_termination = TextMentionTermination("FINISHED")
source_termination = SourceMatchTermination(sources=["testcase_structure"])

team = RoundRobinGroupChat([testcase_orign, testcase_writer, testcase_structure],
                           termination_condition=text_termination | source_termination)
async def main1():
    async for message in team.run_stream(task="编写3条测试用例"):  # type: ignore
        if isinstance(message, TaskResult):
            print("Stop Reason:", message.stop_reason)
        else:
            print(message)
async def main2():
    await Console(team.run_stream(task="编写2条测试用例"))

async def main3():
    # When running inside a script, use a async main function and call it from `asyncio.run(...)`.
    # await team.reset()  # Reset the team for a new task.
    async for message in team.run_stream(task="编写3条测试用例"):  # type: ignore
        if isinstance(message, TaskResult):
            print("Stop Reason:", message.stop_reason)
        else:
            print(message)
asyncio.run(main2())

