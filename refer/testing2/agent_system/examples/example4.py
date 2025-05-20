from pydantic import BaseModel, Field


class TestCase(BaseModel):
    id: str = Field(..., description="用例ID")
    title: str = Field(..., description="用例标题")
    pre_conditions: str = Field(..., description="前置条件")
    priority: str = Field(..., description="优先级")
    steps: list[str] = Field(..., description="步骤")
    expected_result: list[str] = Field(..., description="预期结果")

def structure_testcase(content: str):
    """结构化测试用例"""
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIModel

    model = OpenAIModel(
        'deepseek-chat',
        base_url='https://api.deepseek.com',
        api_key='sk-e5b2a319f9ce4d0fb71c5dc96596a69d',
    )
    agent = Agent(model, result_type=TestCase)
    return agent.run_sync(user_prompt=f"对下面内容进行结构化输出:\n{content}")
test_case_content = """
**用例ID**：CUSTOMER_LOGIN_001
**标题**：用户登录成功验证
**优先级**：P0
**前置条件**：
1. 用户未登录
2. 用户邮箱和密码正确
3. 验证码正确（如果需要）

**步骤**：
1. 在登录页面输入有效的邮箱地址（如：2358269014@qq.com）
2. 输入正确的密码（如：xxxx）
3. 如果需要，输入正确的验证码
4. 点击“Sign In”按钮
5. 发送POST请求到 `/customer/login/account`，包含以下内容：
   - **Request Header**:
     - `access-token`: 从localStorage获取的值
     - `fecshop-currency`: 当前货币值（如：USD）
     - `fecshop-lang`: 当前语言code（如：en）
   - **Request Body**:
     - `email`: "2358269014@qq.com"
     - `password`: "xxxx"
     - `captcha`: ""（如果需要）

**预期结果**：
1. **Response Header**:
   - 返回 `access-token`，并保存到localStorage
2. **Response Body**:
   - 返回状态码 `200`
   - 返回消息 `"process success"`
   - `data` 字段为空数组 `[]`
3. 用户成功登录，页面跳转到用户主页
"""
result = structure_testcase(content=test_case_content)
print(result)