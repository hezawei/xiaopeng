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

class TestStepCreate(TestStepBase):
    pass

class TestStep(TestStepBase):
    step_id: int = Field(..., description="测试步骤的唯一标识。")

    class Config:
        from_attributes = True

# 测试用例模型
class TestCaseBase(BaseModel):
    title: str = Field(..., max_length=200, description="测试用例的标题。")
    desc: Optional[str] = Field(None, max_length=1000, description="测试用例的详细描述。")
    priority: Priority = Field(..., description="测试用例的优先级。")
    status: Status = Field(default=Status.NOT_STARTED, description="测试用例的当前状态。")
    preconditions: Optional[str] = Field(None, description="测试用例的前置条件。")
    postconditions: Optional[str] = Field(None, description="测试用例的后置条件。")
    tags: Optional[str] = Field(None, description="测试用例的标签列表，用于分类或过滤。")
    requirement_id: int = Field(..., description="关联需求ID。")
    project_id: int = Field(..., description="关联项目ID。")
    creator: str = Field(..., max_length=100, description="测试用例的创建者姓名。")

class TestCase(TestCaseBase):
    test_case_id: int = Field(..., description="测试用例的唯一标识。", alias="id")
    created_time: Optional[str] = Field(None, description="测试用例的创建时间。")
    steps: Optional[List[TestStep]] = Field(None, description="测试步骤列表。")

    class Config:
        from_attributes = True
        populate_by_name = True  # 允许通过别名访问字段
    @field_validator("created_time", mode="before")
    def parse_created_time(cls, value):
        return value.isoformat() if value else None

class CaseCreate(TestCaseBase):
    steps: Optional[List[TestStepCreate]] = Field(None, description="测试步骤列表。")

# 更新测试用例模型
class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="测试用例的标题。")
    desc: Optional[str] = Field(None, max_length=1000, description="测试用例的详细描述。")
    priority: Optional[Priority] = Field(None, description="测试用例的优先级。")
    status: Optional[Status] = Field(None, description="测试用例的当前状态。")
    preconditions: Optional[str] = Field(None, description="测试用例的前置条件。")
    postconditions: Optional[str] = Field(None, description="测试用例的后置条件。")
    tags: Optional[List[TestCaseTag]] = Field(None, description="测试用例的标签列表，用于分类或过滤。")
    requirement_id: Optional[int] = Field(None, description="关联需求ID。")
    project_id: Optional[int] = Field(None, description="关联项目ID。")
    creator: Optional[str] = Field(None, max_length=100, description="测试用例的创建者姓名。")
    steps: Optional[List[TestStepCreate]] = Field(None, description="测试步骤列表。")

    class Config:
        from_attributes = True

# 删除测试用例模型
class TestCaseDelete(BaseModel):
    test_case_id: int = Field(..., description="要删除的测试用例ID。")

    class Config:
        from_attributes = True
