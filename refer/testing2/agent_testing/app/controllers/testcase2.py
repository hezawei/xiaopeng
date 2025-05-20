from tortoise.expressions import Q
from tortoise.transactions import atomic
from app.core.crud import CRUDBase
from app.models.admin import TestCase, TestStep, TestCase_Pydantic
from app.schemas.testcases import *

from fastapi import HTTPException
from tortoise.expressions import Q
from tortoise.transactions import in_transaction
from typing import List, Optional
from datetime import datetime


class TestCaseController:
    async def create_test_case(self, test_case_in: CaseCreate) -> TestCase:
        """
        创建新测试用例。
        """
        # 验证 tags 是否合法
        if test_case_in.tags:
            valid_tags = set(tag.value for tag in TestCaseTag)
            invalid_tags = set(tag.value for tag in test_case_in.tags) - valid_tags
            if invalid_tags:
                raise HTTPException(status_code=400, detail=f"无效的标签: {', '.join(invalid_tags)}")

        async with in_transaction():
            test_case_data = test_case_in.dict(exclude_unset=True)
            test_steps = test_case_data.pop("steps", [])

            # 创建测试用例主表记录
            test_case_obj = await TestCase.create(**test_case_data)

            # 创建测试步骤子表记录
            for step in test_steps:
                step["test_case_id"] = test_case_obj.test_case_id
                await TestStep.create(**step)
        return test_case_obj
        # return await TestCase_Pydantic.from_tortoise_orm(test_case_obj)

    async def get_test_case(self, test_case_id: int) -> TestCase:
        """
        获取单个测试用例及其步骤。
        """
        test_case_obj = await TestCase.get_or_none(test_case_id=test_case_id).prefetch_related("steps")
        if not test_case_obj:
            raise HTTPException(status_code=404, detail="测试用例不存在")
        return await TestCase_Pydantic.from_tortoise_orm(test_case_obj)

    async def list_test_cases(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        priority: Optional[Priority] = None,
        status: Optional[Status] = None,
        tags: Optional[List[TestCaseTag]] = None,
    ) -> List[TestCase]:
        """
        查询测试用例列表。
        """
        query = Q()
        if search:
            query &= Q(title__icontains=search) | Q(desc__icontains=search)
        if priority:
            query &= Q(priority=priority)
        if status:
            query &= Q(status=status)
        if tags:
            query &= Q(tags__contains=[tag.value for tag in tags])

        total = await TestCase.filter(query).count()
        test_cases = await TestCase.filter(query).offset((page - 1) * page_size).limit(page_size).prefetch_related("steps")
        return {"total": total, "data": [await TestCase_Pydantic.from_tortoise_orm(tc) for tc in test_cases]}

    async def update_test_case(self, test_case_id: int, test_case_in: TestCaseUpdate) -> TestCase:
        """
        更新测试用例信息。
        """
        test_case_obj = await TestCase.get_or_none(test_case_id=test_case_id)
        if not test_case_obj:
            raise HTTPException(status_code=404, detail="测试用例不存在")

        async with in_transaction():
            # 更新测试用例主表字段
            test_case_data = test_case_in.dict(exclude_unset=True)
            for key, value in test_case_data.items():
                setattr(test_case_obj, key, value)
            await test_case_obj.save()

            # 更新或删除测试步骤
            existing_step_ids = {step.step_id for step in await test_case_obj.steps.all()}
            new_steps = test_case_data.get("steps", [])
            new_step_ids = {step.step_id for step in new_steps if hasattr(step, "step_id")}

            # 删除不再存在的步骤
            for step_id in existing_step_ids - new_step_ids:
                await TestStep.filter(step_id=step_id).delete()

            # 添加或更新步骤
            for step in new_steps:
                if hasattr(step, "step_id") and step.step_id in existing_step_ids:
                    await TestStep.filter(step_id=step.step_id).update(**step.dict(exclude_unset=True))
                else:
                    step["test_case_id"] = test_case_obj.test_case_id
                    await TestStep.create(**step)

        return await TestCase_Pydantic.from_tortoise_orm(test_case_obj)

    async def delete_test_case(self, test_case_in: TestCaseDelete) -> dict:
        """
        删除测试用例。
        """
        deleted_count = await TestCase.filter(test_case_id=test_case_in.test_case_id).delete()
        if not deleted_count:
            raise HTTPException(status_code=404, detail="测试用例不存在")
        return {"message": "删除成功"}