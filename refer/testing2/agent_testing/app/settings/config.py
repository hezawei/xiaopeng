import os  # 用于操作文件路径和环境变量
import typing  # 提供类型提示支持

from pydantic_settings import BaseSettings  # Pydantic 的配置类基类


# 定义配置类 Settings，继承自 BaseSettings
class Settings(BaseSettings):
    # 基础信息
    VERSION: str = "0.1.0"  # 项目版本号
    APP_TITLE: str = "Testing AI"  # 应用标题
    PROJECT_NAME: str = "Testing AI"  # 项目名称
    APP_DESCRIPTION: str = "Description"  # 应用描述

    # CORS 配置（跨域资源共享）
    CORS_ORIGINS: typing.List = ["*"]  # 允许的跨域请求来源，默认允许所有来源
    CORS_ALLOW_CREDENTIALS: bool = True  # 是否允许携带凭证（如 Cookie）
    CORS_ALLOW_METHODS: typing.List = ["*"]  # 允许的 HTTP 方法，默认允许所有方法
    CORS_ALLOW_HEADERS: typing.List = ["*"]  # 允许的 HTTP 请求头，默认允许所有头

    # 调试模式
    DEBUG: bool = True  # 调试模式开关，默认开启

    # 目录路径
    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))  # 项目的根目录
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))  # 项目的基目录
    LOGS_ROOT: str = os.path.join(BASE_DIR, "app/logs")  # 日志文件存储路径

    # JWT 配置
    SECRET_KEY: str = "3488a63e1765035d386f05409663f55c83bfae3b3c61a932744b20ad14244dcf"  # JWT 签名密钥（可通过 openssl rand -hex 32 生成）
    JWT_ALGORITHM: str = "HS256"  # JWT 签名算法
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # JWT Token 的过期时间，默认为 7 天

    # 数据库配置（使用 Tortoise ORM）
    TORTOISE_ORM: dict = {
        "connections": {  # 数据库连接配置
            "default": f"sqlite:///{os.path.join(BASE_DIR,  'db.sqlite3')}",
            # SQLite 配置
            # "sqlite": {
            #     "engine": "tortoise.backends.sqlite",  # 使用 SQLite 引擎
            #     "credentials": {"file_path": f"{BASE_DIR}/db.sqlite3"},  # SQLite 数据库文件路径
            # },
            # MySQL/MariaDB 配置（示例，未启用）
            # Install with: tortoise-orm[asyncmy]
            # "mysql": {
            #     "engine": "tortoise.backends.mysql",  # 使用 MySQL 引擎
            #     "credentials": {
            #         "host": "localhost",  # 数据库主机地址
            #         "port": 3306,  # 数据库端口
            #         "user": "yourusername",  # 数据库用户名
            #         "password": "yourpassword",  # 数据库密码
            #         "database": "yourdatabase",  # 数据库名称
            #     },
            # },
            # PostgreSQL 配置（示例，未启用）
            # Install with: tortoise-orm[asyncpg]
            # "postgres": {
            #     "engine": "tortoise.backends.asyncpg",  # 使用 PostgreSQL 引擎
            #     "credentials": {
            #         "host": "localhost",  # 数据库主机地址
            #         "port": 5432,  # 数据库端口
            #         "user": "yourusername",  # 数据库用户名
            #         "password": "yourpassword",  # 数据库密码
            #         "database": "yourdatabase",  # 数据库名称
            #     },
            # },
            # MSSQL/Oracle 配置（示例，未启用）
            # Install with: tortoise-orm[asyncodbc]
            # "oracle": {
            #     "engine": "tortoise.backends.asyncodbc",  # 使用 Oracle 引擎
            #     "credentials": {
            #         "host": "localhost",  # 数据库主机地址
            #         "port": 1433,  # 数据库端口
            #         "user": "yourusername",  # 数据库用户名
            #         "password": "yourpassword",  # 数据库密码
            #         "database": "yourdatabase",  # 数据库名称
            #     },
            # },
            # SQLServer 配置（示例，未启用）
            # Install with: tortoise-orm[asyncodbc]
            # "sqlserver": {
            #     "engine": "tortoise.backends.asyncodbc",  # 使用 SQLServer 引擎
            #     "credentials": {
            #         "host": "localhost",  # 数据库主机地址
            #         "port": 1433,  # 数据库端口
            #         "user": "yourusername",  # 数据库用户名
            #         "password": "yourpassword",  # 数据库密码
            #         "database": "yourdatabase",  # 数据库名称
            #     },
            # },
        },
        "apps": {  # 定义应用及其对应的模型
            "models": {
                "models": ["app.models", "aerich.models"],  # 包含的模型模块
                "default_connection": "default",  # 默认使用的数据库连接
            },
        },
        "use_tz": False,  # 是否使用时区感知的时间，默认关闭
        "timezone": "Asia/Shanghai",  # 时区设置，默认为上海时区
    }

    # 日期格式
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"  # 日期时间格式


# 实例化配置对象，加载所有配置
settings = Settings()

# 将 TORTOISE_ORM 配置直接暴露为模块级别的变量
TORTOISE_ORM = settings.TORTOISE_ORM