from tortoise.expressions import Q
from tortoise.transactions import atomic
from app.core.crud import CRUDBase
from app.models.admin import TestCase
from app.schemas.testcases import *


class TestCaseController(CRUDBase[TestCase, CaseCreate, CaseUpdate]):
    """
    测试用例控制器类，用于管理测试用例数据。
    """

    def __init__(self):
        super().__init__(model=TestCase)

    @atomic()
    async def create_TestCase(self, obj_in: CaseCreate):
        """
        创建新测试用例。
        参数:
            obj_in (CaseCreate): 测试用例创建模型
        """
        obj_in_dict = obj_in.model_dump()
        return await self.create(obj_in=obj_in_dict)

    async def get_TestCase_by_id(self, case_id: int):
        """
        根据测试用例ID获取测试用例详情。
        参数:
            ID (int): 测试用例ID
        """
        return await self.get(id=case_id)

    @atomic()
    async def update_TestCase(self, obj_in: CaseUpdate):
        """
        更新测试用例信息。
        参数:
            obj_in (CaseUpdate): 测试用例更新模型
        返回:
            TestCase: 更新后的测试用例对象
        """
        TestCase_obj = await self.get(id=obj_in.id)
        TestCase_obj.update_from_dict(obj_in.model_dump(exclude_unset=True))  # 只更新传递的字段
        await TestCase_obj.save()

    @atomic()
    async def delete_TestCase(self, case_id: int):
        """
        删除测试用例。
        参数:
            ID (int): 测试用例ID（主键）
        """
        await self.remove(id=case_id)


# 实例化项目控制器
testcase_controller = TestCaseController()