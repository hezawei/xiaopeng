from pydantic import BaseModel, Field
from typing import Optional


class BaseRequirement(BaseModel):
    """
    需求的基础模型，包含通用字段。
    """
    name: str = Field(..., description="需求名称")
    content: str = Field(..., description="需求描述")
    project_id: int = Field(..., gt=0, description="所属项目ID")  # 确保 project_id 是正整数
    remark: Optional[str] = Field(None, description="备注")


class ReqCreate(BaseRequirement):
    """
    创建需求时的输入模型。
    """
    name: str = Field(..., description="需求名称")
    content: str = Field(..., description="需求描述")
    project_id: int = Field(..., gt=0, description="所属项目 ID")  # 确保 project_id 是正整数
    remark: Optional[str] = Field(None, description="备注")


class ReqUpdate(BaseRequirement):
    """
    更新需求时的输入模型。
    """
    id: int
    name: str = Field()
    content: str = Field()
    project_id: int = Field()
    remark: str = Field()


class ReqDelete(BaseModel):
    """
    删除需求时的输入模型。
    """
    id: int
