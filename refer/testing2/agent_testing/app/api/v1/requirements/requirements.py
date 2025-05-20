from fastapi import APIRouter, Query, Depends, status, Path
from app.controllers.requirement import requirement_controller
from app.schemas.requirements import (
    RequirementCreate,
    RequirementUpdate,
    RequirementDelete,
    REQUIREMENT_CATEGORIES, RequirementBase, RequirementSelect
)
from app.schemas.base import Success, SuccessExtra
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["需求管理"])


@router.post("/create", summary="创建需求", status_code=status.HTTP_201_CREATED)
async def create_requirement(
        requirement_in: RequirementCreate,
):
    """
    创建新需求（需校验项目存在性）
    - **category**: 必须为预定义枚举值
    - **keywords**: 最多支持10个逗号分隔关键词
    """
    # 复合唯一性校验（同一项目下需求名称唯一）
    if await requirement_controller.exists(
            Q(name=requirement_in.name, project_id=requirement_in.project_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同一项目中需求名称必须唯一"
        )

    try:
        await requirement_controller.create(obj_in=requirement_in)
    except Exception as e:
        logger.error(f"创建需求失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部错误"
        )
    return Success(msg="创建成功", code=status.HTTP_201_CREATED)


@router.get("/list", summary="分页筛选需求列表")
async def list_requirements(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        limit: int = Query(100, ge=1, le=1000, description="最大数量"),
        project_id: int = Query(None, gt=0, description="项目ID精准筛选"),
        category: REQUIREMENT_CATEGORIES = Query(None, description="需求类别筛选"),
        keyword: str = Query(None, min_length=1, description="关键词模糊搜索")
):
    """
    多条件分页查询需求
    - 支持项目ID精准筛选
    - 支持需求类别过滤
    - 支持关键词模糊匹配（名称/描述/备注）
    """
    query = Q()
    if project_id:
        query &= Q(project_id=project_id)
    if category:
        query &= Q(category=category)
    if keyword:
        query &= Q(Q(name__icontains=keyword) |
                   Q(description__icontains=keyword) |
                   Q(remark__icontains=keyword))

    total, req_objs = await requirement_controller.list_limit(
        page=page,
        page_size=page_size,
        search=query,
        order=["-created_at"],  # 按创建时间倒序
        limit=limit
    )

    # 使用 Pydantic 模型序列化结果
    # data1 = [await obj.to_dict() for obj in req_objs]
    data = [RequirementSelect.model_validate(obj).model_dump(mode="json") for obj in req_objs]
    return SuccessExtra(
        data=data,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/get", summary="获取需求详情")
async def get_requirement(
        id: int = Query(..., description="需求ID"),
):
    """根据ID获取需求详情（包含关联项目基础信息）"""
    req_obj = await requirement_controller.get(id=id)
    if not req_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="需求不存在"
        )

    # 联表查询项目信息
    await req_obj.fetch_related("project")
    return Success(data=RequirementBase.model_validate(req_obj).model_dump())


@router.put("/update", summary="全量更新需求")
async def update_requirement(
        requirement_in: RequirementUpdate,
):
    """全量更新需求字段（需传递所有必填字段）"""
    if not await requirement_controller.exists(id=requirement_in.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="需求不存在"
        )

    try:
        await requirement_controller.update(obj_in=requirement_in)
    except Exception as e:
        logger.error(f"更新需求失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新失败"
        )
    return Success(msg="更新成功")


@router.delete("/delete", summary="删除需求")
async def delete_requirement(
        id: int = Query(..., description="需求ID"),
        project_id: int = Query(..., description="项目ID"),
):
    """
    删除需求（需二次校验项目ID）
    - 防止越权删除
    """
    req_obj = await requirement_controller.get(id=id)
    if not req_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="需求不存在"
        )

    if req_obj.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除其他项目需求"
        )

    try:
        await requirement_controller.remove(id=id)
    except Exception as e:
        logger.error(f"删除失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除失败"
        )
    return Success(msg="删除成功")