from fastapi import APIRouter

from .projects import router

projects_router = APIRouter()
projects_router.include_router(router, tags=["项目模块"])

__all__ = ["projects_router"]
