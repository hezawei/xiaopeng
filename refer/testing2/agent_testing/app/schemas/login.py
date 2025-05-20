from datetime import datetime  # 用于处理日期和时间
from pydantic import BaseModel, Field  # Pydantic 提供的数据模型和字段验证


class CredentialsSchema(BaseModel):
    """
    用户登录凭证模型，用于验证用户输入的用户名和密码。
    """
    username: str = Field(..., description="用户名称", example="admin")  # 用户名字段，必填，描述为“用户名称”，示例值为 "admin"
    password: str = Field(..., description="密码", example="123456")  # 密码字段，必填，描述为“密码”，示例值为 "123456"


class JWTOut(BaseModel):
    """
    JWT 输出模型，表示返回给客户端的 JWT Token 和相关信息。
    """
    access_token: str  # JWT Token 字符串
    username: str  # 用户名


class JWTPayload(BaseModel):
    """
    JWT 负载模型，表示 JWT Token 中存储的用户信息和过期时间。
    """
    user_id: int  # 用户 ID，整数类型
    username: str  # 用户名，字符串类型
    is_superuser: bool  # 是否为超级用户，布尔类型
    exp: datetime  # Token 的过期时间，datetime 类型