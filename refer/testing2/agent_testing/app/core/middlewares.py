import re  # 正则表达式模块，用于路径匹配
from datetime import datetime  # 日期时间模块，用于计算请求处理时间

from fastapi import FastAPI  # FastAPI 框架
from fastapi.responses import Response  # 响应对象
from fastapi.routing import APIRoute  # 路由对象
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint  # Starlette 中间件基类
from starlette.requests import Request  # 请求对象
from starlette.types import ASGIApp, Receive, Scope, Send  # ASGI 相关类型定义

from app.core.dependency import AuthControl  # 用户认证控制类
from app.models.admin import AuditLog, User  # 数据库模型
from .bgtask import BgTasks  # 后台任务管理工具


class SimpleBaseMiddleware:
    """
    简单的基础中间件类。
    """

    def __init__(self, app: ASGIApp) -> None:
        """
        初始化中间件。
        参数:
            app (ASGIApp): 应用实例
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        中间件的调用方法。
        参数:
            scope (Scope): 请求范围
            receive (Receive): 接收消息的函数
            send (Send): 发送消息的函数
        """
        if scope["type"] != "http":  # 如果不是 HTTP 请求，直接调用下一个中间件
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)  # 构造请求对象

        response = await self.before_request(request) or self.app  # 执行 before_request 方法
        await response(request.scope, request.receive, send)  # 调用下一个中间件或应用
        await self.after_request(request)  # 执行 after_request 方法

    async def before_request(self, request: Request):
        """
        在请求处理之前执行的逻辑。
        参数:
            request (Request): 当前请求对象
        返回:
            ASGIApp 或 None
        """
        return self.app

    async def after_request(self, request: Request):
        """
        在请求处理之后执行的逻辑。
        参数:
            request (Request): 当前请求对象
        """
        return None


class BackGroundTaskMiddleware(SimpleBaseMiddleware):
    """
    后台任务中间件。
    """

    async def before_request(self, request: Request):
        """
        在请求处理之前初始化后台任务对象。
        """
        await BgTasks.init_bg_tasks_obj()  # 初始化后台任务实例

    async def after_request(self, request: Request):
        """
        在请求处理之后执行后台任务。
        """
        await BgTasks.execute_tasks()  # 执行所有后台任务


class HttpAuditLogMiddleware(BaseHTTPMiddleware):
    """
    HTTP 请求审计日志中间件。
    """

    def __init__(self, app, methods: list, exclude_paths: list):
        """
        初始化审计日志中间件。
        参数:
            app (ASGIApp): 应用实例
            methods (list): 需要记录的日志请求方法
            exclude_paths (list): 不需要记录日志的路径
        """
        super().__init__(app)
        self.methods = methods  # 需要记录日志的请求方法
        self.exclude_paths = exclude_paths  # 不需要记录日志的路径

    async def get_request_log(self, request: Request, response: Response) -> dict:
        """
        根据请求和响应对象获取对应的日志记录数据。
        参数:
            request (Request): 当前请求对象
            response (Response): 当前响应对象
        返回:
            dict: 日志记录数据
        """
        data: dict = {
            "path": request.url.path,  # 请求路径
            "status": response.status_code,  # 响应状态码
            "method": request.method,  # 请求方法
        }

        # 获取路由信息
        app: FastAPI = request.app
        for route in app.routes:
            if (
                isinstance(route, APIRoute)  # 确保是 API 路由
                and route.path_regex.match(request.url.path)  # 匹配路径
                and request.method in route.methods  # 匹配请求方法
            ):
                data["module"] = ",".join(route.tags)  # 获取模块标签
                data["summary"] = route.summary  # 获取接口描述

        # 获取用户信息
        try:
            token = request.headers.get("token")  # 获取 Token
            user_obj: User = None
            if token:
                user_obj: User = await AuthControl.is_authed(token)  # 验证用户身份
            data["user_id"] = user_obj.id if user_obj else 0  # 用户 ID
            data["username"] = user_obj.username if user_obj else ""  # 用户名
        except Exception as e:
            data["user_id"] = 0  # 默认用户 ID
            data["username"] = ""  # 默认用户名

        return data

    async def before_request(self, request: Request):
        """
        在请求处理之前执行的逻辑。
        """
        pass

    async def after_request(self, request: Request, response: Response, process_time: int):
        """
        在请求处理之后记录日志。
        参数:
            request (Request): 当前请求对象
            response (Response): 当前响应对象
            process_time (int): 请求处理时间（毫秒）
        """
        if request.method in self.methods:  # 如果请求方法在记录范围内
            for path in self.exclude_paths:
                if re.search(path, request.url.path, re.I):  # 如果路径在排除范围内
                    return
            data: dict = await self.get_request_log(request=request, response=response)  # 获取日志数据
            data["response_time"] = process_time  # 添加响应时间
            await AuditLog.create(**data)  # 创建日志记录

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        中间件的调度方法。
        参数:
            request (Request): 当前请求对象
            call_next (RequestResponseEndpoint): 下一个中间件或应用的调用方法
        返回:
            Response: 响应对象
        """
        start_time: datetime = datetime.now()  # 记录请求开始时间
        await self.before_request(request)  # 执行 before_request 方法
        response = await call_next(request)  # 调用下一个中间件或应用
        end_time: datetime = datetime.now()  # 记录请求结束时间
        process_time = int((end_time.timestamp() - start_time.timestamp()) * 1000)  # 计算请求处理时间
        await self.after_request(request, response, process_time)  # 执行 after_request 方法
        return response