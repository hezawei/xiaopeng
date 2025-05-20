# message_utils.py
# 消息处理工具类

import logging
from datetime import datetime
from typing import Optional, Any, Dict
from autogen_core import RoutedAgent, TopicId
import re

from ..models import WebSocketMessage, TopicTypes

# 配置日志
logger = logging.getLogger("message_utils")

# 添加全局变量，用于记录每个智能体的最新进度
_agent_progress = {}

async def publish_log_message(agent: RoutedAgent, content: str, source: str) -> None:
    """发布日志消息到结果主题"""
    message = WebSocketMessage(
        type="log",
        content=content,
        source=source
    )

    await agent.publish_message(
        message,
        topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=agent.id.key)
    )


async def publish_progress_message(
    agent: RoutedAgent, 
    stage: str, 
    percentage: int, 
    message: str, 
    source: str
) -> None:
    """发布进度消息到结果主题
    
    Args:
        agent: 路由智能体实例
        stage: 当前阶段名称（fetch/analyze/design/generate/execute/review/complete）
        percentage: 进度百分比（0-100）
        message: 进度描述消息
        source: 消息来源标识
    """
    # 阶段进度范围映射 - 为每个阶段分配进度区间
    stage_ranges = {
        "fetch": (0, 10),      # 0-10%
        "analyze": (10, 30),   # 10-30%
        "design": (30, 50),    # 30-50%
        "generate": (50, 75),  # 50-75%
        "review": (75, 85),    # 75-85%
        "execute": (85, 95),   # 85-95%
        "complete": (95, 100)  # 95-100%
    }
    
    # 进度阶段名称映射（英文->中文）
    stage_names = {
        "fetch": "获取API文档",
        "analyze": "分析API接口",
        "design": "设计测试用例",
        "generate": "生成测试代码",
        "review": "评审测试方案",
        "execute": "执行测试用例",
        "complete": "完成测试流程"
    }
    
    # 获取当前阶段的进度范围
    stage_start, stage_end = stage_ranges.get(stage, (0, 100))
    
    # 计算阶段内相对进度（0-100）
    relative_percentage = max(0, min(100, percentage))
    
    # 将阶段内相对进度映射到全局进度范围
    global_percentage = stage_start + (stage_end - stage_start) * relative_percentage / 100
    
    # 进行平滑处理，确保进度值合理（保留整数）
    global_percentage = int(global_percentage)
    global_percentage = max(stage_start, min(stage_end, global_percentage))
    
    # 检查进度是否倒退 - 使用智能体ID作为键来存储每个智能体的最新进度
    agent_key = agent.id.key
    previous_percentage = _agent_progress.get(agent_key, 0)
    
    # 仅当新进度大于之前的进度时才更新，避免出现倒退现象
    global_percentage = max(previous_percentage, global_percentage)
    
    # 保存最新进度
    _agent_progress[agent_key] = global_percentage
    
    # 美化进度描述
    stage_name = stage_names.get(stage, stage)
    
    # 构建进度文本，确保包含百分比信息
    if "%" in message:
        # 如果消息已包含百分比，替换为当前计算的百分比
        message = re.sub(r'\s*\(\d+%\)', '', message)
    
    # 根据格式构建消息
    if message.startswith(stage_name) or any(message.startswith(name) for name in stage_names.values()):
        formatted_message = f"{message} ({global_percentage}%)"
    else:
        formatted_message = f"{stage_name} - {message} ({global_percentage}%)"
        
    # 构建安全的content字典
    content = {
        "stage": stage,
        "progress": global_percentage,
        "message": formatted_message if isinstance(formatted_message, str) else str(formatted_message)
    }

    # 使用WebSocketMessage对象
    msg = WebSocketMessage(
        type="progress",
        content=content,
        source=source
    )

    # 发布WebSocketMessage对象
    await agent.publish_message(
        msg,
        topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=agent.id.key)
    )


async def publish_error_message(agent: RoutedAgent, error_message: str, source: str) -> None:
    """发布错误消息到结果主题"""
    # 确保错误消息是字符串
    if not isinstance(error_message, str):
        error_message = str(error_message)

    # 使用WebSocketMessage对象
    message = WebSocketMessage(
        type="error",
        content=error_message,
        source=source
    )

    # 发布WebSocketMessage对象
    await agent.publish_message(
        message,
        topic_id=TopicId(type=TopicTypes.TEST_RESULT, source=agent.id.key)
    )


def create_system_message(msg_type: str, content: str) -> Dict[str, Any]:
    """创建系统消息"""
    return {
        "type": msg_type,
        "content": content,
        "source": "system",
        "timestamp": datetime.now().isoformat()
    } 