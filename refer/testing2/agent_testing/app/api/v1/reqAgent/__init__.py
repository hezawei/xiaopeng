from fastapi import APIRouter

from .reqAgent import router

reqAgent_router = APIRouter()
reqAgent_router.include_router(router, tags=["需求分析模块"])

__all__ = ["reqAgent_router"]
