from fastapi.exceptions import (
    HTTPException,  # FastAPI 的 HTTP 异常类
    RequestValidationError,  # 请求验证错误
    ResponseValidationError,  # 响应验证错误
)
from fastapi.requests import Request  # FastAPI 的请求对象
from fastapi.responses import JSONResponse  # 返回 JSON 格式的响应
from tortoise.exceptions import DoesNotExist, IntegrityError  # Tortoise ORM 的异常类


class SettingNotFound(Exception):
    """
    自定义异常：设置未找到。
    """
    pass


async def DoesNotExistHandle(req: Request, exc: DoesNotExist) -> JSONResponse:
    """
    处理 Tortoise ORM 的 DoesNotExist 异常。
    参数:
        req (Request): 请求对象
        exc (DoesNotExist): 异常对象
    返回:
        JSONResponse: 返回 JSON 格式的响应
    """
    content = dict(
        code=404,  # 状态码
        msg=f"Object has not found, exc: {exc}, query_params: {req.query_params}",  # 错误信息
    )
    return JSONResponse(content=content, status_code=404)  # 返回 404 响应


async def IntegrityHandle(_: Request, exc: IntegrityError) -> JSONResponse:
    """
    处理 Tortoise ORM 的 IntegrityError 异常。
    参数:
        _ (Request): 请求对象（未使用）
        exc (IntegrityError): 异常对象
    返回:
        JSONResponse: 返回 JSON 格式的响应
    """
    content = dict(
        code=500,  # 状态码
        msg=f"IntegrityError，{exc}",  # 错误信息
    )
    return JSONResponse(content=content, status_code=500)  # 返回 500 响应


async def HttpExcHandle(_: Request, exc: HTTPException) -> JSONResponse:
    """
    处理 FastAPI 的 HTTPException 异常。
    参数:
        _ (Request): 请求对象（未使用）
        exc (HTTPException): 异常对象
    返回:
        JSONResponse: 返回 JSON 格式的响应
    """
    content = dict(
        code=exc.status_code,  # 使用异常中的状态码
        msg=exc.detail,  # 使用异常中的详细信息
        data=None,  # 数据为空
    )
    return JSONResponse(content=content, status_code=exc.status_code)  # 返回对应状态码的响应


async def RequestValidationHandle(_: Request, exc: RequestValidationError) -> JSONResponse:
    """
    处理 FastAPI 的 RequestValidationError 异常。
    参数:
        _ (Request): 请求对象（未使用）
        exc (RequestValidationError): 异常对象
    返回:
        JSONResponse: 返回 JSON 格式的响应
    """
    content = dict(
        code=422,  # 状态码
        msg=f"RequestValidationError, {exc}",  # 错误信息
    )
    return JSONResponse(content=content, status_code=422)  # 返回 422 响应


async def ResponseValidationHandle(_: Request, exc: ResponseValidationError) -> JSONResponse:
    """
    处理 FastAPI 的 ResponseValidationError 异常。
    参数:
        _ (Request): 请求对象（未使用）
        exc (ResponseValidationError): 异常对象
    返回:
        JSONResponse: 返回 JSON 格式的响应
    """
    content = dict(
        code=500,  # 状态码
        msg=f"ResponseValidationError, {exc}",  # 错误信息
    )
    return JSONResponse(content=content, status_code=500)  # 返回 500 响应