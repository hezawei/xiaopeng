# 导入必要的模块
from typing import Optional  # 用于类型提示

from app.core.crud import CRUDBase  # CRUD 基类，提供通用的增删改查方法
from app.models.admin import Menu  # 定义菜单模型的 Tortoise ORM 类
from app.schemas.menus import MenuCreate, MenuUpdate  # 定义菜单创建和更新的 Pydantic 模型


class MenuController(CRUDBase[Menu, MenuCreate, MenuUpdate]):
    """
    菜单控制器类，用于管理菜单数据。
    """
    def __init__(self):
        super().__init__(model=Menu)  # 初始化父类，指定模型为 Menu

    async def get_by_menu_path(self, path: str) -> Optional["Menu"]:
        """
        根据菜单路径获取菜单。
        参数:
            path (str): 菜单路径
        返回:
            Optional[Menu]: 如果找到菜单则返回菜单对象，否则返回 None
        """
        return await self.model.filter(path=path).first()  # 使用 Tortoise ORM 的 filter 方法查询菜单


# 实例化菜单控制器
menu_controller = MenuController()