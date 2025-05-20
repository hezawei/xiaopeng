import contextvars  # 导入 contextvars 模块，用于管理上下文变量

from starlette.background import BackgroundTasks  # 导入 Starlette 的后台任务类


# 定义上下文变量 CTX_USER_ID，用于存储当前用户的 ID
CTX_USER_ID: contextvars.ContextVar[int] = contextvars.ContextVar("user_id", default=0)
"""
CTX_USER_ID 是一个上下文变量，用于存储当前用户的 ID。
- 类型: int
- 默认值: 0（表示未登录或匿名用户）
"""

# 定义上下文变量 CTX_BG_TASKS，用于存储当前请求的后台任务实例
CTX_BG_TASKS: contextvars.ContextVar[BackgroundTasks] = contextvars.ContextVar("bg_task", default=None)
"""
CTX_BG_TASKS 是一个上下文变量，用于存储当前请求的后台任务实例。
- 类型: BackgroundTasks
- 默认值: None（表示当前请求没有后台任务）
"""