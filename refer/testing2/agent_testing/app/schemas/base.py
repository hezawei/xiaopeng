# 导入必要的模块
from typing import Any, Optional  # 提供类型提示支持
from fastapi.responses import JSONResponse  # FastAPI 的 JSON 响应类


class Success(JSONResponse):
    """
    成功响应类，用于返回成功的 API 响应。
    """
    def __init__(
        self,
        code: int = 200,  # HTTP 状态码，默认为 200（成功）
        msg: Optional[str] = "OK",  # 响应消息，默认为 "OK"
        data: Optional[Any] = None,  # 响应数据，默认为 None
        **kwargs,  # 允许传递额外的关键字参数
    ):
        # 构造响应内容
        content = {"code": code, "msg": msg, "data": data}  # 初始化基础响应字段
        content.update(kwargs)  # 将额外的关键字参数合并到响应内容中
        # 调用父类构造函数，生成 JSON 响应
        super().__init__(content=content, status_code=code)


class Fail(JSONResponse):
    """
    失败响应类，用于返回失败的 API 响应。
    """
    def __init__(
        self,
        code: int = 400,  # HTTP 状态码，默认为 400（客户端错误）
        msg: Optional[str] = None,  # 响应消息，默认为 None
        data: Optional[Any] = None,  # 响应数据，默认为 None
        **kwargs,  # 允许传递额外的关键字参数
    ):
        # 构造响应内容
        content = {"code": code, "msg": msg, "data": data}  # 初始化基础响应字段
        content.update(kwargs)  # 将额外的关键字参数合并到响应内容中
        # 调用父类构造函数，生成 JSON 响应
        super().__init__(content=content, status_code=code)


class SuccessExtra(JSONResponse):
    """
    带分页信息的成功响应类，用于返回带有分页信息的成功 API 响应。
    """
    def __init__(
        self,
        code: int = 200,  # HTTP 状态码，默认为 200（成功）
        msg: Optional[str] = None,  # 响应消息，默认为 None
        data: Optional[Any] = None,  # 响应数据，默认为 None
        total: int = 0,  # 数据总数，默认为 0
        page: int = 1,  # 当前页码，默认为 1
        page_size: int = 20,  # 每页数据量，默认为 20
        **kwargs,  # 允许传递额外的关键字参数
    ):
        # 构造响应内容
        content = {
            "code": code,  # HTTP 状态码
            "msg": msg,  # 响应消息
            "data": data,  # 响应数据
            "total": total,  # 数据总数
            "page": page,  # 当前页码
            "page_size": page_size,  # 每页数据量
        }
        content.update(kwargs)  # 将额外的关键字参数合并到响应内容中
        # 调用父类构造函数，生成 JSON 响应
        super().__init__(content=content, status_code=code)