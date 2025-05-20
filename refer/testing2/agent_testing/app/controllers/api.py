# 导入必要的模块
from fastapi.routing import APIRoute  # FastAPI 的路由类

from app.core.crud import CRUDBase  # CRUD 基类，提供通用的增删改查方法
from app.log import logger  # 日志记录器
from app.models.admin import Api  # 定义 API 模型的 Tortoise ORM 类
from app.schemas.apis import ApiCreate, ApiUpdate  # 定义 API 创建和更新的 Pydantic 模型


class ApiController(CRUDBase[Api, ApiCreate, ApiUpdate]):
    """
    API 控制器类，用于管理 API 数据。
    """
    def __init__(self):
        super().__init__(model=Api)  # 初始化父类，指定模型为 Api

    async def refresh_api(self):
        """
        同步 FastAPI 路由中的 API 数据到数据库中。
        """
        from app import app  # 导入 FastAPI 应用实例

        # 删除废弃的 API 数据
        all_api_list = []  # 存储所有需要保留的 API 列表
        for route in app.routes:  # 遍历 FastAPI 应用的所有路由
            # 只处理有鉴权依赖的 API（即需要认证的 API）
            if isinstance(route, APIRoute) and len(route.dependencies) > 0:
                all_api_list.append((list(route.methods)[0], route.path_format))  # 提取方法和路径

        delete_api = []  # 存储需要删除的 API 列表
        for api in await Api.all():  # 遍历数据库中的所有 API
            if (api.method, api.path) not in all_api_list:  # 如果数据库中的 API 不在需要保留的列表中
                delete_api.append((api.method, api.path))  # 添加到删除列表

        for item in delete_api:  # 删除废弃的 API
            method, path = item
            logger.debug(f"API Deleted {method} {path}")  # 记录日志
            await Api.filter(method=method, path=path).delete()  # 删除数据库中的对应记录

        # 更新或创建新的 API 数据
        for route in app.routes:  # 再次遍历 FastAPI 应用的所有路由
            if isinstance(route, APIRoute) and len(route.dependencies) > 0:  # 只处理有鉴权依赖的 API
                method = list(route.methods)[0]  # 提取请求方法
                path = route.path_format  # 提取路径
                summary = route.summary  # 提取简介
                tags = list(route.tags)[0] if route.tags else ""  # 提取标签

                # 查询数据库中是否存在对应的 API
                api_obj = await Api.filter(method=method, path=path).first()
                if api_obj:  # 如果存在，则更新
                    await api_obj.update_from_dict(dict(method=method, path=path, summary=summary, tags=tags)).save()
                else:  # 如果不存在，则创建
                    logger.debug(f"API Created {method} {path}")  # 记录日志
                    await Api.create(**dict(method=method, path=path, summary=summary, tags=tags))


# 实例化 API 控制器
api_controller = ApiController()