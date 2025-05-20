# 导入所需的模块
from passlib import pwd  # 用于生成随机密码
from passlib.context import CryptContext  # 用于密码加密和验证

# 创建密码加密上下文对象，指定使用 argon2 加密算法
# schemes=["argon2"] 表示仅支持 argon2 算法
# deprecated="auto" 表示自动标记过时的加密算法
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码是否与已加密的密码匹配。

    参数:
        plain_password (str): 用户输入的明文密码。
        hashed_password (str): 数据库中存储的已加密密码。

    返回:
        bool: 如果密码匹配返回 True，否则返回 False。
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    将明文密码加密为哈希值。

    参数:
        password (str): 明文密码。

    返回:
        str: 加密后的密码哈希值。
    """
    return pwd_context.hash(password)


def generate_password() -> str:
    """
    生成一个随机的密码字符串。

    返回:
        str: 随机生成的密码。
    """
    return pwd.genword()