from fastapi import APIRouter

from .requirements import router as requirements_router
from .testcase import router as testcase_router
from .api.api import router as api_router
from .performance import router as performance_router
agent_router = APIRouter()
agent_router.include_router(requirements_router, tags=["智能体"])
agent_router.include_router(testcase_router, tags=["智能体"])
agent_router.include_router(api_router, tags=["API自动化测试"])
agent_router.include_router(performance_router, tags=["性能测试"])
__all__ = ["agent_router"]