import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console

from agent_system.llms import model_client

testcase_writer = AssistantAgent(
    name="testcase_writer",
    model_client=model_client,
    system_message="""
    注意：严格按照用户的指令完成用例数量的编写。
    
    你是一位高级用例编写工程师，请按照如下规则编写：
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
async def main():
    await Console(testcase_writer.run_stream(task="""
    编写3条用户登录的测试用例
    具体的业务需求如下：
    
    Api- Customer 登录提交
1.   一：请求部分
2.   二：返回部分
用户在 http://demo.fancyecommerce.com/#/customer/account/login 页面，
输入 email 和 password， 点击 Sign In 按钮后执行的 api
URL: /customer/login/account
格式：json
方式：post
一：请求部分
1.Request Header
参数名称
述
从 localStorage 取出来的值，识别用户登录状态的标示，用户登录成
access-token         必须   String                                     ge 取出来放到request header 中
fecshop-currency  必须   String  从 localStorage 取出来的值，当前的货币值
fecshop-lang         必须   String  从 localStorage 取出来的值，当前的语言code
2.Request Body Form-Data：
参数名称    是否必须   类型   描述
email            必须       String    用户的email 账户
password     必须       String    用户的密码
captcha        必须       String    用户登录填写的验证码，这个在服务端要求填写的时候，才会填写验证
请求参数示例如下：
{
email: "2358269014@qq.com",
password: "xxxx",
captcha:""}

二：返回部分
1.Reponse Header
参数名称     是否必须  类型  描述
access-token  选填     String  用户登录成功，服务端返回 access-token，VUE 保存到 localStorage 中
2.Reponse Body Form-Data：
格式：json
参数名称        是否必须        类型         描述
code                     必须            Number             返回状态码，200 代表完成，完整的返回状态码详细
message              必须            String               返回状态字符串描述
data                      必须            Array                返回详细数据
3.参数code 所有返回状态码：（完整的返回状态码详细参看:Api- 状
态码 ）
code Value                                                       描述
200                                                                    成功状态码
1100006                                                            登录：用户已经登录
1000007                                                            无效数据：验证码错误
1100002                                                            登录：账户的邮箱或者密码不正确
4.返回数据举例：
{
"code": 200,
"message": "process success",
"data": []}

    """))

asyncio.run(main())