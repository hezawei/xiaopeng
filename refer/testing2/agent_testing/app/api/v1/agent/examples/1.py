import json

from pydantic import BaseModel, Field, validator, field_validator
from typing import List, Optional
from enum import Enum

# 枚举类定义
class Priority(str, Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"

class Status(str, Enum):
    NOT_STARTED = "未开始"
    IN_PROGRESS = "进行中"
    PASSED = "通过"
    FAILED = "失败"
    BLOCKED = "阻塞"

class TestCaseTag(str, Enum):
    UNIT_TEST = "单元测试"
    FUNCTIONAL_TEST = "功能测试"
    INTEGRATION_TEST = "集成测试"
    SYSTEM_TEST = "系统测试"
    SMOKE_TEST = "冒烟测试"
    VERSION_VERIFICATION = "版本验证"

# 测试步骤模型
class TestStepBase(BaseModel):
    description: str = Field(..., description="测试步骤的描述。")
    expected_result: str = Field(..., description="测试步骤的预期结果。")


# 测试用例模型
class TestCaseBase(BaseModel):
    title: str = Field(..., max_length=200, description="测试用例的标题。")
    desc: str = Field(None, max_length=1000, description="测试用例的详细描述。")
    priority: str = Field(..., description="测试用例的优先级：[高/中/低]")
    status: str = Field(default="未开始", description="测试用例的当前状态：[未开始/进行中/通过/失败/阻塞]")
    preconditions: Optional[str] = Field(None, description="测试用例的前置条件。")
    postconditions: Optional[str] = Field(None, description="测试用例的后置条件。")
    tags: Optional[str] = Field(..., description="测试类型标签：[单元测试/接口测试/功能测试/性能测试/安全测试]")
    requirement_id: int = Field(..., description="关联需求ID。")
    project_id: int = Field(..., description="关联项目ID。")
    creator: str = Field(default="田威峰", max_length=100, description="测试用例的创建者姓名。")



class CaseCreate(TestCaseBase):
    steps: Optional[List[TestStepBase]] = Field(None, description="测试步骤列表。")
class TestCaseList(BaseModel):
    testcases: list[CaseCreate] = Field(..., description="测试用例列表")



# ss = """[ {
#   "title" : "配置评级模型适配性-正常场景",
#   "desc" : "验证系统能够正确配置评级模型的适配性，适用于不同的客户类型和业务场景",
#   "priority" : "高",
#   "status" : "未开始",
#   "preconditions" : "1. 用户已登录系统 2. 用户具有风险管理部员工权限",
#   "postconditions" : "评级模型适配性配置成功",
#   "tags" : "功能测试",
#   "requirement_id" : 1,
#   "project_id" : 1,
#   "creator" : "田威峰",
#   "steps" : [ {
#     "description" : "进入评级模型配置页面",
#     "expected_result" : "页面加载成功，显示当前评级模型配置信息"
#   }, {
#     "description" : "选择客户类型为'企业客户'",
#     "expected_result" : "客户类型选择成功，相关配置项更新"
#   }, {
#     "description" : "选择业务场景为'信贷审批'",
#     "expected_result" : "业务场景选择成功，相关配置项更新"
#   }, {
#     "description" : "点击'保存'按钮",
#     "expected_result" : "系统提示'配置保存成功'"
#   } ]
# }, {
#   "title" : "配置评级模型适配性-边界场景-最小客户类型",
#   "desc" : "验证系统能够处理最小数量的客户类型配置",
#   "priority" : "中",
#   "status" : "未开始",
#   "preconditions" : "1. 用户已登录系统 2. 用户具有风险管理部员工权限",
#   "postconditions" : "评级模型适配性配置成功",
#   "tags" : "功能测试",
#   "requirement_id" : 1,
#   "project_id" : 1,
#   "creator" : "田威峰",
#   "steps" : [ {
#     "description" : "进入评级模型配置页面",
#     "expected_result" : "页面加载成功，显示当前评级模型配置信息"
#   }, {
#     "description" : "选择客户类型为'个人客户'",
#     "expected_result" : "客户类型选择成功，相关配置项更新"
#   }, {
#     "description" : "选择业务场景为'风险评估'",
#     "expected_result" : "业务场景选择成功，相关配置项更新"
#   }, {
#     "description" : "点击'保存'按钮",
#     "expected_result" : "系统提示'配置保存成功'"
#   } ]
# }, {
#   "title" : "配置评级模型适配性-异常场景-未选择客户类型",
#   "desc" : "验证系统能够正确处理未选择客户类型的情况",
#   "priority" : "中",
#   "status" : "未开始",
#   "preconditions" : "1. 用户已登录系统 2. 用户具有风险管理部员工权限",
#   "postconditions" : "系统提示错误信息",
#   "tags" : "功能测试",
#   "requirement_id" : 1,
#   "project_id" : 1,
#   "creator" : "田威峰",
#   "steps" : [ {
#     "description" : "进入评级模型配置页面",
#     "expected_result" : "页面加载成功，显示当前评级模型配置信息"
#   }, {
#     "description" : "不选择客户类型，直接选择业务场景为'信贷审批'",
#     "expected_result" : "系统提示'请选择客户类型'"
#   }, {
#     "description" : "点击'保存'按钮",
#     "expected_result" : "系统提示'配置保存失败，请检查必填项'"
#   } ]
# }, {
#   "title" : "配置评级模型适配性-性能测试-并发配置",
#   "desc" : "验证系统能够处理多个用户同时配置评级模型适配性的情况",
#   "priority" : "高",
#   "status" : "未开始",
#   "preconditions" : "1. 多个用户已登录系统 2. 用户具有风险管理部员工权限",
#   "postconditions" : "所有配置请求处理成功",
#   "tags" : "性能测试",
#   "requirement_id" : 1,
#   "project_id" : 1,
#   "creator" : "田威峰",
#   "steps" : [ {
#     "description" : "使用性能测试工具模拟10个用户同时进入评级模型配置页面",
#     "expected_result" : "页面加载成功，响应时间小于2秒"
#   }, {
#     "description" : "模拟10个用户同时选择不同的客户类型和业务场景",
#     "expected_result" : "配置操作成功，响应时间小于1秒"
#   }, {
#     "description" : "模拟10个用户同时点击'保存'按钮",
#     "expected_result" : "系统提示'配置保存成功'，响应时间小于1秒"
#   } ]
# }, {
#   "title" : "配置评级模型适配性-安全测试-权限验证",
#   "desc" : "验证系统能够正确处理无权限用户尝试配置评级模型适配性的情况",
#   "priority" : "高",
#   "status" : "未开始",
#   "preconditions" : "1. 用户已登录系统 2. 用户不具有风险管理部员工权限",
#   "postconditions" : "系统拒绝访问",
#   "tags" : "安全测试",
#   "requirement_id" : 1,
#   "project_id" : 1,
#   "creator" : "田威峰",
#   "steps" : [ {
#     "description" : "尝试访问评级模型配置页面",
#     "expected_result" : "系统提示'您没有权限访问此页面'"
#   }, {
#     "description" : "尝试通过API直接调用配置接口",
#     "expected_result" : "系统返回403 Forbidden状态码"
#   } ]
# } ]
# """
# test_case_list = TestCaseList(testcases=json.loads(ss))
#
#
s = json.dumps(TestCaseList.model_json_schema(),ensure_ascii=False)
print(s)
s = """
#
# """