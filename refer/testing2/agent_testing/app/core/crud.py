from typing import Any, Dict, Generic, List, NewType, Tuple, Type, TypeVar, Union

from pydantic import BaseModel  # Pydantic 的数据验证模型
from tortoise.expressions import Q  # Tortoise ORM 的查询条件构造工具
from tortoise.models import Model  # Tortoise ORM 的模型基类


# 定义类型别名
Total = NewType("Total", int)  # 总数类型
ModelType = TypeVar("ModelType", bound=Model)  # 数据库模型类型
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)  # 创建时的 Pydantic 模型类型
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)  # 更新时的 Pydantic 模型类型


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    基于 Tortoise ORM 和 Pydantic 的通用 CRUD 操作类。
    """

    def __init__(self, model: Type[ModelType]):
        """
        初始化 CRUD 类。
        参数:
            model (Type[ModelType]): 数据库模型类
        """
        self.model = model  # 绑定数据库模型

    async def get(self, id: int) -> ModelType:
        """
        根据 ID 获取单个对象。
        参数:
            id (int): 对象的主键 ID
        返回:
            ModelType: 查询到的对象
        """
        return await self.model.get(id=id)  # 使用 Tortoise ORM 的 get 方法查询对象

    async def list(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Q = Q(),  # 默认空查询条件
        order: list = [],  # 默认无排序
    ) -> Tuple[Total, List[ModelType]]:
        """
        分页查询对象列表。
        参数:
            page (int): 当前页码
            page_size (int): 每页大小
            search (Q): 查询条件，默认为空
            order (list): 排序字段，默认无排序
        返回:
            Tuple[Total, List[ModelType]]: (总记录数, 查询结果列表)
        """
        print(type(self.model))  # 应该输出 <class 'tortoise.models.Model'>
        query = self.model.filter(search)  # 构造查询条件
        total = await query.count()  # 计算总记录数
        results = await query.offset((page - 1) * page_size).limit(page_size).order_by(*order)  # 分页查询
        return Total(total), results  # 返回总数和结果列表

    async def list_limit(
            self,
            page: int = 1,
            page_size: int = 10,
            search: Q = Q(),  # 默认空查询条件
            order: list = [],  # 默认无排序
            limit: int = 100
    ) -> Tuple[Total, List[ModelType]]:
        """
        分页查询对象列表。
        参数:
            page (int): 当前页码
            page_size (int): 每页大小
            search (Q): 查询条件，默认为空
            order (list): 排序字段，默认无排序
        返回:
            Tuple[Total, List[ModelType]]: (总记录数, 查询结果列表)
        """
        print(type(self.model))  # 应该输出 <class 'tortoise.models.Model'>
        query = self.model.filter(search)  # 构造查询条件
        total = await query.count()  # 计算总记录数
        results = await query.offset((page - 1) * page_size).limit(page_size).order_by(*order).limit(limit)  # 分页查询
        return Total(total), results  # 返回总数和结果列表

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        创建新对象。
        参数:
            obj_in (CreateSchemaType): 创建时的数据模型
        返回:
            ModelType: 创建成功的对象
        """
        if isinstance(obj_in, Dict):  # 如果输入是字典
            obj_dict = obj_in
        else:  # 如果输入是 Pydantic 模型
            obj_dict = obj_in.model_dump()  # 将模型转换为字典
        obj = self.model(**obj_dict)  # 使用字典创建模型实例
        await obj.save()  # 保存到数据库
        return obj  # 返回创建成功的对象

    async def update(self, id: int, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """
        更新现有对象。
        参数:
            id (int): 对象的主键 ID
            obj_in (Union[UpdateSchemaType, Dict[str, Any]]): 更新时的数据模型或字典
        返回:
            ModelType: 更新后的对象
        """
        if isinstance(obj_in, Dict):  # 如果输入是字典
            obj_dict = obj_in
        else:  # 如果输入是 Pydantic 模型
            obj_dict = obj_in.model_dump(exclude_unset=True, exclude={"id"})  # 转换为字典，排除未设置的字段和主键
        obj = await self.get(id=id)  # 获取要更新的对象
        obj.update_from_dict(obj_dict)  # 使用字典更新对象属性
        await obj.save()  # 保存到数据库
        return obj  # 返回更新后的对象

    async def remove(self, id: int) -> None:
        """
        删除指定对象。
        参数:
            id (int): 对象的主键 ID
        """
        obj = await self.get(id=id)  # 获取要删除的对象
        await obj.delete()  # 删除对象