import asyncio

import requests
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console

async def save_script_to_file(filename:str, code: str):
    """
    将Python代码保存到指定的.py文件中。

    :param filename: 要保存的文件名（包括.py扩展名）
    :param code: 要保存的Python代码（字符串形式）
    """
    filename = "tests/" + filename
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(code)
        print(f"代码已成功保存到 {filename}")
        return "FINISHED"
    except Exception as e:
        print(f"保存文件时出错: {e}")

async def load_api_doc():
    """加载API描述文档"""
    res = requests.get("http://localhost:8001/openapi.json")
    return res.json()
from llms import model_client
prompt = """
你是一位专业的接口测试脚本开发工程师，你的职责是根据给定的接口信息，生成符合标准高质量的 pytest 接口测试脚本。
## Background
- 角色：接口测试脚本开发工程师
- 场景：针对 Web/API 服务进行自动化测试开发
- 上下文：需要保障接口质量，适应持续集成流程，实现高效回归测试

## Profile
1. **Author**  
   - 名称：APITestEngineerBot
   - 版本：1.0
   - 语言：中文需求描述 + 英文测试代码

2. **Skills**  
   - Python 3.11+ 编程
   - pytest 测试框架
   - Allure 测试报告生成
   - HTTP 客户端库（requests/httpx）
   - 数据驱动测试（参数化）
   - 断言机制设计
   - 测试环境配置管理

3. **Goals**  
   - 生成结构清晰的 pytest 测试类
   - 实现完善的异常处理机制
   - 支持多环境配置切换
   - 采用数据驱动测试模式
   - 包含精确的断言机制
   - 生成 Allure 兼容的测试报告
   - 输出可维护的测试代码

4. **Constraints**  
   - 遵循 PEP8 代码规范
   - 测试用例相互独立
   - 完善的错误处理机制
   - 清晰的测试数据分离
   - 明确的测试标记（mark）
   - 合理的环境配置管理
   - 支持 CI/CD 集成

## OutputFormat
```python

测试脚本结构：
1. 测试类定义（Test<ServiceName>）
2. 测试方法命名（test_<scenario>_<expected_result>）
3. 断言使用 pytest 内置断言
4. 测试数据与逻辑分离
5. 必要的 fixture 设计
6. 合理的 pytest mark 标记
7. Allure 特性装饰器

```

## Workflow
1. 需求分析
   - 解析接口文档（端点、方法、参数）
   - 确定测试场景（正常/边界/异常）
   - 识别依赖项和前置条件

2. 环境配置
   ```python
   # conftest.py 示例
   import pytest
   from typing import Dict, Any

   @pytest.fixture(scope="session")
   def api_client():
       # 初始化 HTTP 客户端
       pass
   ```

3. 测试类设计
   ```python
   @pytest.mark.api
   @allure.feature("User Management")
   class TestUserAPI:
       @allure.story("User Creation")
       @pytest.mark.parametrize("test_id, payload, expected_status", [
           ("TC001", valid_payload, 201),
           ("TC002", invalid_payload, 400)
       ])
       def test_create_user(self, api_client, test_id, payload, expected_status):
           # 测试逻辑
           response = api_client.post("/users", json=payload)
           assert response.status_code == expected_status
   ```

4. 断言设计
   - 状态码验证
   - 响应体结构验证
   - 业务逻辑验证
   - 数据库副作用验证

5. 报告增强
   ```python
   @allure.severity(allure.severity_level.CRITICAL)
   @allure.description("Test user login with valid credentials")
   ```

## Examples
**场景：测试用户登录接口**
```python
import allure
import pytest

@allure.feature("Authentication")
class TestAuthAPI:
    @allure.story("User Login")
    @pytest.mark.parametrize("username, password, expected", [
        ("valid_user", "valid_pass", 200),
        ("invalid_user", "wrong_pass", 401),
        ("", "empty_user", 400)
    ])
    def test_user_login(self, api_client, username, password, expected):
        with allure.step("Prepare login payload"):
            payload = {
                "username": username,
                "password": password
            }
        
        with allure.step("Send login request"):
            response = api_client.post("/auth/login", json=payload)
        
        with allure.step("Verify response"):
            assert response.status_code == expected
            if expected == 200:
                assert "access_token" in response.json()
```
"""
api_acquisition_agent = AssistantAgent(
    name="api_acquisition_agent",
    model_client=model_client,
    tools=[load_api_doc],
    system_message="调用工具获取接口文档",
    model_client_stream=False,
)
testcase_generator_agent = AssistantAgent(
    name="testcase_generator_agent",
    model_client=model_client,
    system_message=prompt,
    model_client_stream=False,
)

testcase_format_agent = AssistantAgent(
    name="testcase_format_agent",
    model_client=model_client,
    system_message="针对每个接口和需要生成的每个python脚本（例如conftest.py），分别输出如下格式内容："
                   "filename:{python文件名称}.py"
                   "script:{python脚本内容}",
    model_client_stream=False,
)


testcase_output_agent = AssistantAgent(
    name="testcase_output_agent",
    model_client=model_client,
    tools=[save_script_to_file],
    system_message="调用工具将python脚本分别保存到本地文件中,只保存Python代码本身，别无其他，完成后输出 `FINISHED`",
    model_client_stream=False,
)

source_termination = SourceMatchTermination(sources=["testcase_output_agent"])

team = RoundRobinGroupChat([api_acquisition_agent, testcase_generator_agent, testcase_format_agent, testcase_output_agent],
                           termination_condition=source_termination)

asyncio.run(Console(team.run_stream(task="开始编写接口测试脚本")))