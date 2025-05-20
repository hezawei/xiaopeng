from fastapi import APIRouter

from .requirements import router

requirements_router = APIRouter()
requirements_router.include_router(router, tags=["需求模块"])

__all__ = ["requirements_router"]
