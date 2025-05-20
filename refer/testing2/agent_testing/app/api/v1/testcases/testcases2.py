from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.controllers.testcase import TestCaseController
from app.schemas.testcases import *

router = APIRouter()
controller = TestCaseController()

@router.post("/create", response_model=TestCase, summary="创建测试用例")
async def create_test_case(test_case_in: TestCaseCreate):
    return await controller.create_test_case(test_case_in)

@router.get("/get", response_model=TestCase, summary="获取测试用例详情")
async def get_test_case(test_case_id: int):
    return await controller.get_test_case(test_case_id)

@router.get("/list", response_model=dict, summary="查询测试用例列表")
async def list_test_cases(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    priority: Optional[Priority] = None,
    status: Optional[Status] = None,
    tags: Optional[List[TestCaseTag]] = None,
):
    return await controller.list_test_cases(page, page_size, search, priority, status, tags)

@router.put("/update", response_model=TestCase, summary="更新测试用例")
async def update_test_case(test_case_id: int, test_case_in: TestCaseCreate):
    return await controller.update_test_case(test_case_id, test_case_in)

@router.delete("/delete", response_model=dict, summary="删除测试用例")
async def delete_test_case(test_case_id: int):
    return await controller.delete_test_case(test_case_id)