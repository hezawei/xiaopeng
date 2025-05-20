from pydantic import BaseModel, Field


class BaseCase(BaseModel):
    """
    测试用例的基础模型，包含通用字段
    """
    testcase_title: str = Field(..., description="用例标题")
    testcase_desc: str = Field(..., description="用例描述")
    testcase_preconditions: str = Field(..., description="前置条件")
    testcase_steps: str = Field(..., description="用例步骤")
    testcase_posconditions: str = Field(..., description="后置条件")
    testcase_priority: str = Field(..., description="用例优先级")  # 假设优先级为整数类型
    testcase_status: str = Field(..., description="用例状态")  # 假设状态为字符串类型
    testcase_tags: str = Field(..., description="用例标签")  # 标签可以是 JSON 列表
    requirement_id: int = Field(..., gt=0, description="关联需求")
    project_id: int = Field(..., gt=0, description="关联项目")
    creator: str = Field(..., description="创建者")


class CaseCreate(BaseCase):
    """
    创建测试用例的输入模型
    """
    testcase_title: str = Field(..., description="用例标题")
    testcase_desc: str = Field(..., description="用例描述")
    testcase_preconditions: str = Field(..., description="前置条件")
    testcase_steps: str = Field(..., description="用例步骤")
    testcase_postconditions: str = Field(..., description="后置条件")
    testcase_priority: str = Field(..., description="用例优先级")  # 假设优先级为整数类型
    testcase_status: str = Field(..., description="用例状态")  # 假设状态为字符串类型
    testcase_tags: str = Field(..., description="用例标签")  # 标签可以是 JSON 列表
    requirement_id: int = Field(..., gt=0, description="关联需求")
    project_id: int = Field(..., gt=0, description="关联项目")
    creator: str = Field(..., description="创建者")


class CaseUpdate(BaseCase):
    """
    更新测试用例的输入模型。
    """
    id: int
    testcase_title: str = Field(..., description="用例标题")
    testcase_desc: str = Field(..., description="用例描述")
    testcase_preconditions: str = Field(..., description="前置条件")
    testcase_steps: str = Field(..., description="用例步骤")
    testcase_postconditions: str = Field(..., description="后置条件")
    testcase_priority: str = Field(..., description="用例优先级")  # 假设优先级为整数类型
    testcase_status: str = Field(..., description="用例状态")  # 假设状态为字符串类型
    testcase_tags: str = Field(..., description="用例标签")  # 标签可以是 JSON 列表
    requirement_id: int = Field(..., gt=0, description="关联需求")
    project_id: int = Field(..., gt=0, description="关联项目")
    creator: str = Field(..., description="创建者")

class CaseDel(CaseCreate):
    """
    删除测试用例。
    """
    id: int