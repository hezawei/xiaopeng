from pydantic import BaseModel, Field
from datetime import datetime


class BaseProject(BaseModel):
    name: str = Field(..., description="项目名称（主键）", example="项目A")
    desc: str = Field(..., description="项目描述", example="项目A描述")


class ProjectCreate(BaseProject):
    name: str = Field(example="项目A")
    desc: str = Field(example="项目A描述")


class ProjectUpdate(BaseProject):
    id: int = Field(example=1)
    name: str = Field(example="项目A")
    desc: str = Field(example="项目A描述")

class ProjectDel(ProjectCreate):
    created_at: datetime

