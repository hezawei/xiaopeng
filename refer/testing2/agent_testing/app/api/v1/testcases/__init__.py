from fastapi import APIRouter

from .testcases import router

testcases_router = APIRouter()
testcases_router.include_router(router, tags=["测试用例模块"])

__all__ = ["testcases_router"]