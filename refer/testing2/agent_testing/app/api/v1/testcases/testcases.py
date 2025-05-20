from fastapi import APIRouter, Query
from app.controllers.testcase import testcase_controller
from app.controllers.requirement import requirement_controller
from app.controllers.project import project_controller
from app.schemas.testcases import *
from app.schemas.base import Success, SuccessExtra
from tortoise.expressions import Q
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create", summary="创建测试用例")
async def create_testcase(
    case_in: CaseCreate,
):
    """
    创建新需求。
    """
    await testcase_controller.create(obj_in=case_in)
    return Success(msg="Created Successfully")


@router.get("/list", summary="查看测试用例列表")
async def list_testcase(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    project_id: int = Query(None, description="项目名称，用于查询"),
    requirement_id: int = Query(None, description="需求ID，用于查询"),
):
    """
    获取测试用例列表。
    """
    q = Q()
    if project_id is not None:
        q &= Q(project_id=project_id)
    if requirement_id is not None:
        q &= Q(requirement_id=requirement_id)
        # 调用控制器的 list 方法
        total, testcase_objs = await testcase_controller.list(page=page, page_size=page_size, search=q)

        # 将结果转换为字典格式，并处理外键字段
        data = [await obj.to_dict(m2m=True) for obj in testcase_objs]
        for item in data:
            # 替换 project_id 为项目详情
            project_id = item.pop("project_id", None)
            item["project"] = await (await project_controller.get(id=project_id)).to_dict() if project_id else {}

            # 替换 requirement_id 为需求详情
            requirement_id = item.pop("requirement_id", None)
            item["requirement"] = await (
                await requirement_controller.get(id=requirement_id)).to_dict() if requirement_id else {}

        return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="查看测试用例详情")
async def get_testcase(
    id: str = Query(..., description="用例ID"),
):
    """
    获取单个用例详情。
    """
    case_obj = await testcase_controller.get(id=id)
    return Success(data=await case_obj.to_dict())


@router.put("/update", summary="更新用例")
async def update_testcase(
    case_in: CaseUpdate
):
    """
    更新需求信息。
    """
    await testcase_controller.update_requirement(obj_in=case_in)
    return Success(msg="Update Successfully")


@router.delete("/delete", summary="删除用例")
async def delete_testcase(
    case_id: int = Query(..., description="用例ID")
):
    """
    删除需求。
    """
    await testcase_controller.remove(id=case_id)
    return Success(msg="Deleted Successfully")