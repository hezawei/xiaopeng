import jwt  # 用于生成和解析 JWT Token

from app.schemas.login import JWTPayload  # 定义了 JWT 负载的数据模型
from app.settings.config import settings  # 项目配置文件，包含 SECRET_KEY 和 JWT_ALGORITHM


def create_access_token(*, data: JWTPayload):
    """
    创建一个 JWT Token。

    参数:
        data (JWTPayload): 包含用户信息的负载数据，类型为 JWTPayload。

    返回:
        str: 生成的 JWT Token 字符串。
    """
    # 将 JWTPayload 对象转换为字典形式
    payload = data.model_dump().copy()

    # 使用 PyJWT 库对负载进行编码，生成 JWT Token
    # 参数说明：
    # - payload: 要编码的负载数据
    # - settings.SECRET_KEY: 签名密钥，用于加密 Token
    # - algorithm=settings.JWT_ALGORITHM: 指定使用的加密算法
    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # 返回生成的 JWT Token
    return encoded_jwt