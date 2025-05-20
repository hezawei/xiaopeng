from pydantic import BaseModel, Field
from typing import Optional

class TestStepBase(BaseModel):
    description: str = Field(..., description="测试步骤的描述")
    expected_result: str = Field(..., description="测试步骤的预期结果")
    test_case_id: int = Field(..., description="关联的测试用例ID")

class TestStepCreate(TestStepBase):
    test_case_id: int = Field(..., description="关联的测试用例ID")

class TestStep(TestStepBase):
    step_id: int = Field(..., description="测试步骤的唯一标识")
    test_case_id: int = Field(..., description="关联的测试用例ID")

class TestStepUpdate(TestStepBase):
    id: int
    step_id: int = Field(..., description="测试步骤的唯一标识")
    test_case_id: int = Field(..., description="关联的测试用例ID")