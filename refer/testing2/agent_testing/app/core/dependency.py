from typing import Optional

import jwt  # 用于解析 JWT Token
from fastapi import Depends, Header, HTTPException, Request  # FastAPI 相关模块

from app.core.ctx import CTX_USER_ID  # 上下文变量，存储当前用户 ID
from app.models import Role, User  # 数据库模型
from app.settings import settings  # 配置文件


class AuthControl:
    """
    用户认证控制类。
    """

    @classmethod
    async def is_authed(cls, token: str = Header(..., description="token验证")) -> Optional["User"]:
        """
        验证用户是否已登录并返回用户对象。
        参数:
            token (str): 请求头中的 Token
        返回:
            Optional[User]: 认证成功时返回用户对象，失败时抛出异常
        """
        try:
            if token == "dev":  # 开发模式下直接获取第一个用户
                user = await User.filter().first()
                user_id = user.id
            else:  # 正常模式下解析 JWT Token
                decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
                user_id = decode_data.get("user_id")  # 从解码数据中提取用户 ID
            user = await User.filter(id=user_id).first()  # 查询用户
            if not user:  # 如果用户不存在
                raise HTTPException(status_code=401, detail="Authentication failed")
            CTX_USER_ID.set(int(user_id))  # 将用户 ID 设置到上下文中
            return user  # 返回用户对象
        except jwt.DecodeError:  # Token 解码错误
            raise HTTPException(status_code=401, detail="无效的Token")
        except jwt.ExpiredSignatureError:  # Token 过期
            raise HTTPException(status_code=401, detail="登录已过期")
        except Exception as e:  # 其他异常
            raise HTTPException(status_code=500, detail=f"{repr(e)}")


class PermissionControl:
    """
    权限控制类。
    """

    @classmethod
    async def has_permission(
        cls, request: Request, current_user: User = Depends(AuthControl.is_authed)
    ) -> None:
        """
        检查用户是否有访问当前 API 的权限。
        参数:
            request (Request): 当前请求对象
            current_user (User): 当前用户对象（由 AuthControl.is_authed 提供）
        异常:
            HTTPException: 如果用户没有权限，则抛出 403 错误
        """
        if current_user.is_superuser:  # 超级管理员直接通过
            return
        method = request.method  # 获取请求方法（如 GET、POST 等）
        path = request.url.path  # 获取请求路径
        roles: list[Role] = await current_user.roles  # 获取用户的角色列表
        if not roles:  # 如果用户没有绑定角色
            raise HTTPException(status_code=403, detail="The user is not bound to a role")
        apis = [await role.apis for role in roles]  # 获取角色对应的 API 权限列表
        permission_apis = list(set((api.method, api.path) for api in sum(apis, [])))  # 去重后的权限列表
        if (method, path) not in permission_apis:  # 如果当前请求不在权限范围内
            raise HTTPException(
                status_code=403, detail=f"Permission denied method:{method} path:{path}"
            )


# 定义依赖项
DependAuth = Depends(AuthControl.is_authed)  # 用户认证依赖
DependPermisson = Depends(PermissionControl.has_permission)  # 权限控制依赖