from tortoise import fields  # Tortoise ORM 提供的字段类型
from tortoise.contrib.pydantic import pydantic_model_creator
from enum import Enum
from app.schemas.menus import MenuType  # 定义菜单类型的枚举类
from .base import BaseModel, TimestampMixin  # 基础模型类和时间戳混入类
from .enums import MethodType, Priority, Status, TestCaseTag # 定义 HTTP 请求方法的枚举类

class User(BaseModel, TimestampMixin):
    """
    用户模型，用于存储系统用户信息。
    """
    username = fields.CharField(max_length=20, unique=True, description="用户名称", index=True)  # 用户名字段，唯一且添加索引
    alias = fields.CharField(max_length=30, null=True, description="姓名", index=True)  # 真实姓名字段，可为空
    email = fields.CharField(max_length=255, unique=True, description="邮箱", index=True)  # 邮箱字段，唯一且添加索引
    phone = fields.CharField(max_length=20, null=True, description="电话", index=True)  # 手机号字段，可为空
    password = fields.CharField(max_length=128, null=True, description="密码")  # 密码字段，可为空
    is_active = fields.BooleanField(default=True, description="是否激活", index=True)  # 是否激活字段，默认为 True
    is_superuser = fields.BooleanField(default=False, description="是否为超级管理员", index=True)  # 是否为超级管理员字段，默认为 False
    last_login = fields.DatetimeField(null=True, description="最后登录时间", index=True)  # 最后登录时间字段，可为空
    roles = fields.ManyToManyField("models.Role", related_name="user_roles")  # 多对多关联角色模型
    dept_id = fields.IntField(null=True, description="部门ID", index=True)  # 部门 ID 字段，可为空

    class Meta:
        table = "user"  # 数据库表名为 "user"


class Role(BaseModel, TimestampMixin):
    """
    角色模型，用于存储系统角色信息。
    """
    name = fields.CharField(max_length=20, unique=True, description="角色名称", index=True)  # 角色名称字段，唯一且添加索引
    desc = fields.CharField(max_length=500, null=True, description="角色描述")  # 角色描述字段，可为空
    menus = fields.ManyToManyField("models.Menu", related_name="role_menus")  # 多对多关联菜单模型
    apis = fields.ManyToManyField("models.Api", related_name="role_apis")  # 多对多关联 API 模型

    class Meta:
        table = "role"  # 数据库表名为 "role"


class Api(BaseModel, TimestampMixin):
    """
    API 模型，用于存储系统 API 信息。
    """
    path = fields.CharField(max_length=100, description="API路径", index=True)  # API 路径字段，添加索引
    method = fields.CharEnumField(MethodType, description="请求方法", index=True)  # 请求方法字段，使用 MethodType 枚举
    summary = fields.CharField(max_length=500, description="请求简介", index=True)  # 请求简介字段，添加索引
    tags = fields.CharField(max_length=100, description="API标签", index=True)  # API 标签字段，添加索引

    class Meta:
        table = "api"  # 数据库表名为 "api"


class Menu(BaseModel, TimestampMixin):
    """
    菜单模型，用于存储系统菜单信息。
    """
    name = fields.CharField(max_length=20, description="菜单名称", index=True)  # 菜单名称字段，添加索引
    remark = fields.JSONField(null=True, description="保留字段")  # 保留字段，JSON 类型，可为空
    menu_type = fields.CharEnumField(MenuType, null=True, description="菜单类型")  # 菜单类型字段，使用 MenuType 枚举
    icon = fields.CharField(max_length=100, null=True, description="菜单图标")  # 菜单图标字段，可为空
    path = fields.CharField(max_length=100, description="菜单路径", index=True)  # 菜单路径字段，添加索引
    order = fields.IntField(default=0, description="排序", index=True)  # 排序字段，默认值为 0
    parent_id = fields.IntField(default=0, max_length=10, description="父菜单ID", index=True)  # 父菜单 ID 字段，默认值为 0
    is_hidden = fields.BooleanField(default=False, description="是否隐藏")  # 是否隐藏字段，默认值为 False
    component = fields.CharField(max_length=100, description="组件")  # 组件字段
    keepalive = fields.BooleanField(default=True, description="存活")  # 存活字段，默认值为 True
    redirect = fields.CharField(max_length=100, null=True, description="重定向")  # 重定向字段，可为空

    class Meta:
        table = "menu"  # 数据库表名为 "menu"


class Dept(BaseModel, TimestampMixin):
    """
    部门模型，用于存储系统部门信息。
    """
    name = fields.CharField(max_length=20, unique=True, description="部门名称", index=True)  # 部门名称字段，唯一且添加索引
    desc = fields.CharField(max_length=500, null=True, description="备注")  # 备注字段，可为空
    is_deleted = fields.BooleanField(default=False, description="软删除标记", index=True)  # 软删除标记字段，默认值为 False
    order = fields.IntField(default=0, description="排序", index=True)  # 排序字段，默认值为 0
    parent_id = fields.IntField(default=0, max_length=10, description="父部门ID", index=True)  # 父部门 ID 字段，默认值为 0

    class Meta:
        table = "dept"  # 数据库表名为 "dept"


class DeptClosure(BaseModel, TimestampMixin):
    """
    部门闭包模型，用于存储部门之间的层级关系。
    """
    ancestor = fields.IntField(description="父代", index=True)  # 父代字段，添加索引
    descendant = fields.IntField(description="子代", index=True)  # 子代字段，添加索引
    level = fields.IntField(default=0, description="深度", index=True)  # 深度字段，默认值为 0

    class Meta:
        table = "dept_closure"  # 数据库表名为 "dept_closure"


class AuditLog(BaseModel, TimestampMixin):
    """
    审计日志模型，用于存储系统操作日志。
    """
    user_id = fields.IntField(description="用户ID", index=True)  # 用户 ID 字段，添加索引
    username = fields.CharField(max_length=64, default="", description="用户名称", index=True)  # 用户名称字段，默认值为空字符串
    module = fields.CharField(max_length=64, default="", description="功能模块", index=True)  # 功能模块字段，默认值为空字符串
    summary = fields.CharField(max_length=128, default="", description="请求描述", index=True)  # 请求描述字段，默认值为空字符串
    method = fields.CharField(max_length=10, default="", description="请求方法", index=True)  # 请求方法字段，默认值为空字符串
    path = fields.CharField(max_length=255, default="", description="请求路径", index=True)  # 请求路径字段，默认值为空字符串
    status = fields.IntField(default=-1, description="状态码", index=True)  # 状态码字段，默认值为 -1
    response_time = fields.IntField(default=0, description="响应时间(单位ms)", index=True)  # 响应时间字段，默认值为 0

    class Meta:
        table = "audit_log"  # 数据库表名为 "audit_log"

class Project(BaseModel, TimestampMixin):
    """
    项目模型，用于存储项目信息。
    """
    name = fields.CharField(max_length=255, null=False, unique=True, description="项目名称")  # 主键
    desc = fields.TextField(max_length=255, null=False, description="项目内容")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")  # 创建时间

    class Meta:
        table = "project"  # 数据库表名为 "project"

class Requirement(BaseModel, TimestampMixin):
    """
    需求模型，用于存储需求信息。
    """
    name = fields.CharField(max_length=255, null=False, unique=True, description="需求名称")  # 主键
    description = fields.TextField(null=False, description="需求描述")
    category = fields.CharField(max_length=20, null=False, description="需求类别")
    parent = fields.CharField(max_length=50, null=True, description="父需求名称")
    module = fields.CharField(max_length=50, null=True, description="所属模块")
    level = fields.CharField(max_length=20, null=False, description="需求层级")
    reviewer = fields.CharField(max_length=50, null=True, description="评审人")
    keywords = fields.CharField(max_length=100, null=True, description="关键词")
    estimate = fields.IntField(gt=0, description="预计完成工时（小时）")
    criteria = fields.TextField(null=True, description="验收标准")
    remark = fields.TextField(null=True, description="备注")  # 备注
    project_id = fields.IntField(null=False, index=True, description="关联项目")  # 所属项目
    created_at = fields.DatetimeField(null=True, auto_now_add=True, description="创建时间")  # 创建时间
    updated_at = fields.DatetimeField(null=True, auto_now=True, description="更新时间")  # 更新时间
    class Meta:
        table = "requirement"  # 数据库表名为 "requirement"

# 定义测试步骤子模型
class TestStep(BaseModel, TimestampMixin):
    """测试用例步骤模型"""
    step_id = fields.IntField(index=True, description="测试步骤的唯一标识。")  # 主键字段
    test_case_id = fields.IntField(index=True, description="关联的测试用例ID。")  # 手动定义外键字段
    description = fields.TextField(description="测试步骤的描述。")
    expected_result = fields.TextField(description="测试步骤的预期结果。")

    class Meta:
        table = "test_steps"

# 定义测试用例模型
class TestCase(BaseModel, TimestampMixin):
    """测试用例模型"""
    test_case_id = fields.IntField(index=True, description="测试用例的唯一标识。")  # 主键字段
    title = fields.CharField(max_length=200, description="测试用例的标题。")
    desc = fields.TextField(null=True, description="测试用例的详细描述。")
    priority = fields.CharEnumField(Priority, description="测试用例的优先级。")
    status = fields.CharEnumField(Status, default=Status.NOT_STARTED, description="测试用例的当前状态。")
    preconditions = fields.TextField(null=True, description="测试用例的前置条件。")
    postconditions = fields.TextField(null=True, description="测试用例的后置条件。")
    tags = fields.CharEnumField(TestCaseTag, default=TestCaseTag.FUNCTIONAL_TEST, description="测试用例的标签列表，用于分类或过滤。")
    steps = fields.ManyToManyField("models.TestStep", related_name="test_cases", description="测试步骤列表。")
    requirement_id = fields.IntField(index=True, description="测试用例的相关需求。", null=False)
    project_id = fields.IntField(index=True, description="测试用例的相关项目。",null=False)
    creator = fields.CharField(max_length=100, description="测试用例的创建者姓名。")

    class Meta:
        table = "test_cases"
