from fastapi import APIRouter, Query
from app.controllers.project import project_controller
from app.schemas.projects import *
from app.schemas.base import Success, SuccessExtra
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.models.admin import Project
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create", summary="创建项目")
async def create_project(
    project_in: ProjectCreate,
):
    """
    创建新项目。
    """
    if await project_controller.is_exist(name=project_in.name):
        raise HTTPException(
            status_code=400,
            detail="The project already exists in the system.",
        )
    await project_controller.create(obj_in=project_in)
    return Success(msg="Created Successfully")



@router.get("/list", summary="查看项目列表")
async def list_project(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    project_name: str = Query("", description="项目名称，用于查询"),
):
    """
    获取项目列表。
    """
    q = Q()
    if project_name:
        q = Q(name__contains=project_name)
    total, project_objs = await project_controller.list(page=page, page_size=page_size, search=q)
    data = [await obj.to_dict() for obj in project_objs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="查看项目详情")
async def get_project(
    id: str = Query(..., description="项目名称ID"),
):
    """
    获取单个项目详情。
    """
    project_obj = await project_controller.get(id=id)
    return Success(data=await project_obj.to_dict())


@router.post("/update", summary="更新项目")
async def update_project(
    project_in: ProjectUpdate
):
    """
    更新项目信息。
    """
    await project_controller.update_project(obj_in=project_in)
    return Success(msg="Update Successfully")


@router.delete("/delete", summary="删除项目")
async def delete_project(
    proj_id: int = Query(..., description="项目ID")
):
    """
    删除项目。
    """
    await project_controller.remove(id=proj_id)
    return Success(msg="Deleted Successfully")
