# 导入必要的模块
from datetime import datetime  # 用于处理日期和时间
from typing import List, Optional  # 用于类型提示

from fastapi.exceptions import HTTPException  # FastAPI 的异常类

from app.core.crud import CRUDBase  # CRUD 基类，提供通用的增删改查方法
from app.models.admin import User  # 定义用户模型的 Tortoise ORM 类
from app.schemas.login import CredentialsSchema  # 定义登录凭据的 Pydantic 模型
from app.schemas.users import UserCreate, UserUpdate  # 定义用户创建和更新的 Pydantic 模型
from app.utils.password import get_password_hash, verify_password  # 密码加密和验证工具

from .role import role_controller  # 角色控制器


class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    """
    用户控制器类，用于管理用户数据。
    """
    def __init__(self):
        super().__init__(model=User)  # 初始化父类，指定模型为 User

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱获取用户。
        参数:
            email (str): 用户邮箱
        返回:
            Optional[User]: 如果找到用户则返回用户对象，否则返回 None
        """
        return await self.model.filter(email=email).first()

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户。
        参数:
            username (str): 用户名
        返回:
            Optional[User]: 如果找到用户则返回用户对象，否则返回 None
        """
        return await self.model.filter(username=username).first()

    async def create_user(self, obj_in: UserCreate) -> User:
        """
        创建新用户。
        参数:
            obj_in (UserCreate): 用户创建模型
        返回:
            User: 创建的用户对象
        """
        obj_in.password = get_password_hash(password=obj_in.password)  # 对密码进行哈希加密
        obj = await self.create(obj_in)  # 调用父类的 create 方法创建用户
        return obj

    async def update_last_login(self, id: int) -> None:
        """
        更新用户的最后登录时间。
        参数:
            id (int): 用户 ID
        """
        user = await self.model.get(id=id)  # 获取用户对象
        user.last_login = datetime.now()  # 设置最后登录时间为当前时间
        await user.save()  # 保存更新

    async def authenticate(self, credentials: CredentialsSchema) -> Optional["User"]:
        """
        用户认证。
        参数:
            credentials (CredentialsSchema): 登录凭据
        返回:
            Optional[User]: 如果认证成功则返回用户对象，否则抛出异常
        """
        user = await self.model.filter(username=credentials.username).first()  # 根据用户名查询用户
        if not user:  # 如果用户不存在
            raise HTTPException(status_code=400, detail="无效的用户名")  # 抛出异常
        verified = verify_password(credentials.password, user.password)  # 验证密码
        if not verified:  # 如果密码不正确
            raise HTTPException(status_code=400, detail="密码错误!")  # 抛出异常
        if not user.is_active:  # 如果用户未激活
            raise HTTPException(status_code=400, detail="用户已被禁用")  # 抛出异常
        return user  # 认证成功，返回用户对象

    async def update_roles(self, user: User, role_ids: List[int]) -> None:
        """
        更新用户的角色。
        参数:
            user (User): 用户对象
            role_ids (List[int]): 角色 ID 列表
        """
        await user.roles.clear()  # 清空用户的所有角色
        for role_id in role_ids:  # 遍历角色 ID 列表
            role_obj = await role_controller.get(id=role_id)  # 获取角色对象
            await user.roles.add(role_obj)  # 将角色添加到用户的角色列表中

    async def reset_password(self, user_id: int):
        """
        重置用户的密码。
        参数:
            user_id (int): 用户 ID
        """
        user_obj = await self.get(id=user_id)  # 获取用户对象
        if user_obj.is_superuser:  # 如果用户是超级管理员
            raise HTTPException(status_code=403, detail="不允许重置超级管理员密码")  # 抛出异常
        user_obj.password = get_password_hash(password="123456")  # 重置密码为默认值 "123456"
        await user_obj.save()  # 保存更新


# 实例化用户控制器
user_controller = UserController()