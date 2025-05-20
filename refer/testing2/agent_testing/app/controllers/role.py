# 导入必要的模块
from typing import List  # 用于类型提示

from app.core.crud import CRUDBase  # CRUD 基类，提供通用的增删改查方法
from app.models.admin import Api, Menu, Role  # 定义 API、菜单和角色模型的 Tortoise ORM 类
from app.schemas.roles import RoleCreate, RoleUpdate  # 定义角色创建和更新的 Pydantic 模型


class RoleController(CRUDBase[Role, RoleCreate, RoleUpdate]):
    """
    角色控制器类，用于管理角色数据。
    """
    def __init__(self):
        super().__init__(model=Role)  # 初始化父类，指定模型为 Role

    async def is_exist(self, name: str) -> bool:
        """
        检查角色名称是否已存在。
        参数:
            name (str): 角色名称
        返回:
            bool: 如果角色名称存在则返回 True，否则返回 False
        """
        return await self.model.filter(name=name).exists()  # 使用 Tortoise ORM 的 exists 方法检查角色名称是否存在

    async def update_roles(self, role: Role, menu_ids: List[int], api_infos: List[dict]) -> None:
        """
        更新角色的菜单和 API 权限。
        参数:
            role (Role): 角色对象
            menu_ids (List[int]): 菜单 ID 列表
            api_infos (List[dict]): API 信息列表，包含 path 和 method 字段
        """
        # 清空角色的菜单权限
        await role.menus.clear()
        for menu_id in menu_ids:  # 遍历菜单 ID 列表
            menu_obj = await Menu.filter(id=menu_id).first()  # 查询对应的菜单对象
            if menu_obj:  # 如果菜单对象存在
                await role.menus.add(menu_obj)  # 将菜单添加到角色的菜单权限中

        # 清空角色的 API 权限
        await role.apis.clear()
        for item in api_infos:  # 遍历 API 信息列表
            api_obj = await Api.filter(path=item.get("path"), method=item.get("method")).first()  # 查询对应的 API 对象
            if api_obj:  # 如果 API 对象存在
                await role.apis.add(api_obj)  # 将 API 添加到角色的 API 权限中


# 实例化角色控制器
role_controller = RoleController()