from tortoise.expressions import Q
from tortoise.transactions import atomic
from app.core.crud import CRUDBase
from app.models.admin import Project
from app.schemas.projects import *


class ProjectController(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    """
    项目控制器类，用于管理项目数据。
    """

    def __init__(self):
        super().__init__(model=Project)

    async def is_exist(self, name: str) -> bool:
        """
        检查项目名称是否已存在。
        参数:
            name (str): 项目名称
        返回:
            bool: 如果项目名称存在则返回 True，否则返回 False
        """
        return await self.model.filter(name=name).exists()

    @atomic()
    async def create_project(self, obj_in: ProjectCreate):
        """
        创建新项目。
        参数:
            obj_in (ProjectCreate): 项目创建模型
        """
        obj_in_dict = obj_in.model_dump()
        return await self.create(obj_in=obj_in_dict)

    async def get_project_list(self, name_contains: str = ""):
        """
        获取项目列表。
        参数:
            name_contains (str): 项目名称（可选），用于模糊过滤项目
        返回:
            list: 项目列表
        """
        q = Q()
        if name_contains:
            q &= Q(name__contains=name_contains)
        return await self.model.filter(q).all()

    async def get_project_by_name(self, name: str):
        """
        根据项目名称获取项目详情。
        参数:
            name (str): 项目名称
        """
        return await self.get(name=name)

    @atomic()
    async def update_project(self, obj_in: ProjectUpdate):
        """
        更新项目信息。
        参数:
            name (str): 项目名称（主键）
            obj_in (ProjectUpdate): 项目更新模型
        """
        project_obj = await self.get(id=obj_in.id)
        project_obj.update_from_dict(obj_in.model_dump(exclude_unset=True))
        await project_obj.save()

    @atomic()
    async def delete_project(self, proj_id: int):
        """
        删除项目。
        参数:
            name (str): 项目名称（主键）
        """
        await self.delete(id=proj_id)


# 实例化项目控制器
project_controller = ProjectController()