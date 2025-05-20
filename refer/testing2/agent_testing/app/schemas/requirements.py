from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal

# 常量定义（提高可维护性）
REQUIREMENT_CATEGORIES = Literal["功能", "性能", "安全", "接口", "体验", "改进", "其它"]

class RequirementBase(BaseModel):
    """
    需求基础模型（所有操作的共用字段）
    """
    name: str = Field(..., min_length=1, max_length=100, description="业务需求名称")
    description: str = Field(..., min_length=1, description="需求描述")  # 对应数据库 description 字段
    category: str = Field(..., description="需求类别:[功能/性能/安全/接口/体验/改进/其它]")
    parent: Optional[str] = Field(None, max_length=50, description="父需求")
    module: str = Field(..., min_length=1, max_length=50, description="所属模块")
    level: str = Field(..., min_length=1, max_length=20, description="需求层级")
    reviewer: str = Field(..., min_length=1, max_length=50, description="评审人")
    estimate: int = Field(default=4, gt=0, description="预计完成工时（小时）")
    criteria: str = Field(..., min_length=1, description="验收标准")
    remark: str = Field("", max_length=500, description="备注")  # 数据库 NOT NULL 默认空字符串
    keywords: str = Field(..., min_length=1, max_length=100, description="关键词（逗号分隔）")
    project_id: int = Field(..., gt=0, description="所属项目ID")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()  # 将datetime转换为ISO格式字符串
        }

class RequirementCreate(RequirementBase):
    pass
    """
    创建需求专用模型（可扩展创建时特有逻辑）
    """
    # @field_validator('keywords')
    # def validate_keywords(cls, v):
    #     if len(v.split(',')) > 10:
    #         raise ValueError("关键词最多10个")
    #     return v

class RequirementUpdate(RequirementBase):
    """
    更新需求专用模型（所有字段可选 + 强制ID）
    """
    id: int = Field(..., description="需求ID")

    class Config:
        from_attributes = True

class RequirementSelect(RequirementBase):
    """
    查询需求专用模型（所有字段可选 + 强制ID）
    """
    id: int = Field(..., description="需求ID")

    class Config:
        from_attributes = True

class RequirementDelete(BaseModel):
    """
    删除需求专用模型
    """
    id: int = Field(..., description="需求ID")
    project_id: int = Field(..., gt=0, description="项目ID（用于权限校验）")

    @field_validator('id')
    def validate_id(cls, v):
        if v <= 0:
            raise ValueError("无效的需求ID")
        return v