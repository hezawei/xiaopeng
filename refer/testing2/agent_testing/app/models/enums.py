from enum import Enum, StrEnum  # Python 内置的枚举类


class EnumBase(Enum):
    """
    自定义的基础枚举类，扩展了 Enum 的功能。
    """

    @classmethod
    def get_member_values(cls):
        """
        获取枚举类中所有成员的值。

        返回:
            list: 包含所有枚举成员值的列表。
        """
        return [item.value for item in cls._member_map_.values()]

    @classmethod
    def get_member_names(cls):
        """
        获取枚举类中所有成员的名称。

        返回:
            list: 包含所有枚举成员名称的列表。
        """
        return [name for name in cls._member_names_]


class MethodType(StrEnum):
    """
    定义 HTTP 请求方法的枚举类型。
    """
    GET = "GET"  # GET 请求方法
    POST = "POST"  # POST 请求方法
    PUT = "PUT"  # PUT 请求方法
    DELETE = "DELETE"  # DELETE 请求方法
    PATCH = "PATCH"  # PATCH 请求方法

class Priority(StrEnum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"

class Status(StrEnum):
    NOT_STARTED = "未开始"
    IN_PROGRESS = "进行中"
    PASSED = "通过"
    FAILED = "失败"
    BLOCKED = "阻塞"

class TestCaseTag(StrEnum):
    UNIT_TEST = "单元测试"
    FUNCTIONAL_TEST = "功能测试"
    INTEGRATION_TEST = "集成测试"
    SYSTEM_TEST = "系统测试"
    SMOKE_TEST = "冒烟测试"
    VERSION_VERIFICATION = "版本验证"