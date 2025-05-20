from tortoise.expressions import Q
from tortoise.transactions import atomic
from app.core.crud import CRUDBase
from app.models.admin import Requirement
from app.schemas.requirements import (
    RequirementCreate,
    RequirementUpdate,
    REQUIREMENT_CATEGORIES,
    RequirementDelete
)


class RequirementController(CRUDBase[Requirement, RequirementCreate, RequirementUpdate]):
    """
    优化后的需求控制器，继承自CRUDBase并增强功能：
    1. 增加事务管理
    2. 补充复合查询能力
    3. 优化方法命名规范
    """

    def __init__(self):
        super().__init__(model=Requirement)

    @atomic()
    async def create(self, obj_in: RequirementCreate) -> Requirement:
        """带事务的创建方法"""
        return await super().create(obj_in=obj_in)

    @atomic()
    async def update(self, id: int, obj_in: RequirementUpdate) -> int:
        """带事务的更新方法"""
        return await super().update(id, obj_in=obj_in)

    @atomic()
    async def delete(self, id: int):
        """带事务的删除方法"""
        await super().remove(id)

    async def exists(self, *expressions) -> bool:
        """增强存在性检查，支持复合条件查询"""
        return await self.model.filter(*expressions).exists()

    async def list_with_project(self, search: Q, order_by: list = None):
        """带项目信息的联表查询"""
        query = self.model.filter(search).prefetch_related("project")
        if order_by:
            query = query.order_by(*order_by)
        return await query


# 实例化控制器（保持全局单例）
requirement_controller = RequirementController()