import asyncio  # 用于异步操作
from datetime import datetime  # 用于处理日期和时间

from tortoise import fields, models  # Tortoise ORM 提供的字段和模型基类
from app.settings import settings  # 项目配置文件，包含 DATETIME_FORMAT 等设置


class BaseModel(models.Model):
    """
    基础模型类，提供通用字段和序列化方法。
    """
    id = fields.BigIntField(pk=True, index=True)  # 主键字段，使用大整数类型，并添加索引

    async def to_dict(self, m2m: bool = False, exclude_fields: list[str] | None = None):
        """
        将模型对象转换为字典。

        参数:
            m2m (bool): 是否包含多对多字段，默认为 False。
            exclude_fields (list[str]): 需要排除的字段列表，默认为空。

        返回:
            dict: 模型对象的字典表示。
        """
        if exclude_fields is None:  # 如果未提供 exclude_fields，则初始化为空列表
            exclude_fields = []

        d = {}  # 初始化结果字典
        for field in self._meta.db_fields:  # 遍历数据库字段
            if field not in exclude_fields:  # 如果字段不在排除列表中
                value = getattr(self, field)  # 获取字段值
                if isinstance(value, datetime):  # 如果值是 datetime 类型
                    value = value.strftime(settings.DATETIME_FORMAT)  # 格式化为指定的时间格式
                d[field] = value  # 将字段名和值添加到结果字典中

        if m2m:  # 如果需要包含多对多字段
            tasks = [  # 创建异步任务列表，用于获取所有多对多字段的值
                self.__fetch_m2m_field(field, exclude_fields)
                for field in self._meta.m2m_fields
                if field not in exclude_fields
            ]
            results = await asyncio.gather(*tasks)  # 并行执行所有任务
            for field, values in results:  # 遍历任务结果
                d[field] = values  # 将多对多字段及其值添加到结果字典中

        return d  # 返回结果字典

    async def __fetch_m2m_field(self, field, exclude_fields):
        """
        异步获取多对多字段的值，并格式化为字典。

        参数:
            field (str): 多对多字段名。
            exclude_fields (list[str]): 需要排除的字段列表。

        返回:
            tuple: 包含字段名和格式化后的值的元组。
        """
        values = await getattr(self, field).all().values()  # 获取多对多字段的所有值
        formatted_values = []  # 初始化格式化后的值列表
        for value in values:  # 遍历每个值
            formatted_value = {}  # 初始化单个值的字典
            for k, v in value.items():  # 遍历值中的键值对
                if k not in exclude_fields:  # 如果键不在排除列表中
                    if isinstance(v, datetime):  # 如果值是 datetime 类型
                        formatted_value[k] = v.strftime(settings.DATETIME_FORMAT)  # 格式化为指定的时间格式
                    else:
                        formatted_value[k] = v  # 否则直接添加到字典中
            formatted_values.append(formatted_value)  # 将格式化后的值添加到列表中

        return field, formatted_values  # 返回字段名和格式化后的值

    class Meta:
        abstract = True  # 声明这是一个抽象类，不能直接实例化


class UUIDModel:
    """
    UUID 模型类，提供一个唯一的 UUID 字段。
    """
    uuid = fields.UUIDField(unique=True, pk=False, index=True)  # UUID 字段，唯一且添加索引


class TimestampMixin:
    """
    时间戳混入类，提供创建时间和更新时间字段。
    """
    created_at = fields.DatetimeField(auto_now_add=True, index=True)  # 创建时间字段，自动填充为当前时间，并添加索引
    updated_at = fields.DatetimeField(auto_now=True, index=True)  # 更新时间字段，每次保存时自动更新为当前时间，并添加索引