"""
工具模块 V2 - 重构版本

提供通用的工具函数和辅助功能，包括：
1. 文件操作工具
2. JSON数据处理
3. 日志配置
4. 常用验证函数
"""

import json
import logging
import hashlib
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime


def setup_logging(
    level: int = logging.INFO,
    format_string: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
) -> logging.Logger:
    """
    设置日志配置
    
    Args:
        level: 日志级别
        format_string: 日志格式
        
    Returns:
        配置好的logger
    """
    logging.basicConfig(level=level, format=format_string)
    return logging.getLogger(__name__)


def load_json_file(file_path: Path, default_value: Any = None) -> Any:
    """
    加载JSON文件
    
    Args:
        file_path: 文件路径
        default_value: 默认值
        
    Returns:
        JSON数据或默认值
    """
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return default_value
    except Exception as e:
        logging.error(f"加载JSON文件失败: {str(e)}")
        return default_value


def save_json_file(file_path: Path, data: Any) -> bool:
    """
    保存JSON文件
    
    Args:
        file_path: 文件路径
        data: 要保存的数据
        
    Returns:
        是否保存成功
    """
    try:
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"保存JSON文件失败: {str(e)}")
        return False


def calculate_file_hash(file_path: Path, algorithm: str = 'md5') -> str:
    """
    计算文件哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法，支持 md5, sha1, sha256
        
    Returns:
        文件哈希值
    """
    try:
        if algorithm == 'md5':
            hasher = hashlib.md5()
        elif algorithm == 'sha1':
            hasher = hashlib.sha1()
        elif algorithm == 'sha256':
            hasher = hashlib.sha256()
        else:
            raise ValueError(f"不支持的哈希算法: {algorithm}")
        
        with open(file_path, 'rb') as f:
            # 分块读取，避免大文件内存问题
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    except Exception as e:
        logging.error(f"计算文件哈希失败: {str(e)}")
        return ""


def backup_file(source_path: Path, backup_dir: Path) -> Optional[Path]:
    """
    备份文件
    
    Args:
        source_path: 源文件路径
        backup_dir: 备份目录
        
    Returns:
        备份文件路径，失败时返回None
    """
    try:
        if not source_path.exists():
            return None
        
        # 确保备份目录存在
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
        backup_path = backup_dir / backup_name
        
        # 复制文件
        if source_path.is_file():
            shutil.copy2(source_path, backup_path)
        elif source_path.is_dir():
            shutil.copytree(source_path, backup_path)
        
        return backup_path
    except Exception as e:
        logging.error(f"备份文件失败: {str(e)}")
        return None


def validate_business_id(business_id: str) -> bool:
    """
    验证业务ID格式
    
    Args:
        business_id: 业务ID
        
    Returns:
        是否有效
    """
    if not business_id:
        return False
    
    # 业务ID应该是字母、数字、下划线的组合，长度在1-50之间
    import re
    pattern = r'^[a-zA-Z0-9_]{1,50}$'
    return bool(re.match(pattern, business_id))


def validate_file_path(file_path: str) -> bool:
    """
    验证文件路径
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否有效
    """
    try:
        path = Path(file_path)
        return path.exists() and path.is_file()
    except Exception:
        return False


def get_file_size_human_readable(file_path: Path) -> str:
    """
    获取人类可读的文件大小
    
    Args:
        file_path: 文件路径
        
    Returns:
        格式化的文件大小
    """
    try:
        size = file_path.stat().st_size
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        
        return f"{size:.1f} PB"
    except Exception:
        return "未知"


def clean_text(text: str) -> str:
    """
    清理文本内容
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return ""
    
    # 移除多余的空白字符
    import re
    
    # 替换多个空格为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 移除首尾空白
    text = text.strip()
    
    return text


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    从文本中提取关键词
    
    Args:
        text: 文本内容
        max_keywords: 最大关键词数量
        
    Returns:
        关键词列表
    """
    try:
        import re
        from collections import Counter
        
        # 提取中文词汇（2-6个字符）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
        
        # 提取英文词汇（3个字符以上）
        english_words = re.findall(r'[A-Za-z]{3,}', text)
        
        # 合并词汇
        all_words = chinese_words + english_words
        
        # 过滤停用词
        stop_words = {
            '的', '是', '在', '有', '和', '与', '或', '但', '而', '了', '也', '就', '都',
            'the', 'and', 'or', 'but', 'with', 'for', 'to', 'of', 'in', 'on', 'at'
        }
        
        filtered_words = [word for word in all_words if word.lower() not in stop_words]
        
        # 统计词频
        word_counts = Counter(filtered_words)
        
        # 返回最常见的关键词
        return [word for word, count in word_counts.most_common(max_keywords)]
        
    except Exception as e:
        logging.error(f"提取关键词失败: {str(e)}")
        return []


def format_timestamp(timestamp: Optional[str] = None) -> str:
    """
    格式化时间戳
    
    Args:
        timestamp: ISO格式的时间戳，如果为None则使用当前时间
        
    Returns:
        格式化的时间字符串
    """
    try:
        if timestamp:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = datetime.now()
        
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "未知时间"


def create_directory_structure(base_dir: Path, subdirs: List[str]) -> bool:
    """
    创建目录结构
    
    Args:
        base_dir: 基础目录
        subdirs: 子目录列表
        
    Returns:
        是否创建成功
    """
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
        
        for subdir in subdirs:
            (base_dir / subdir).mkdir(exist_ok=True)
        
        return True
    except Exception as e:
        logging.error(f"创建目录结构失败: {str(e)}")
        return False


def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息
    
    Returns:
        系统信息字典
    """
    try:
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('C:').percent
        }
    except Exception as e:
        logging.error(f"获取系统信息失败: {str(e)}")
        return {"error": str(e)}


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise e
                    
                    logging.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {str(e)}")
                    time.sleep(delay)
            
        return wrapper
    return decorator


class ProgressTracker:
    """
    进度跟踪器
    """
    
    def __init__(self, total: int, description: str = "处理中"):
        """
        初始化进度跟踪器
        
        Args:
            total: 总数量
            description: 描述
        """
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = datetime.now()
    
    def update(self, increment: int = 1):
        """
        更新进度
        
        Args:
            increment: 增量
        """
        self.current += increment
        
        if self.current % 10 == 0 or self.current == self.total:
            percentage = (self.current / self.total) * 100
            elapsed = datetime.now() - self.start_time
            
            logging.info(f"{self.description}: {self.current}/{self.total} ({percentage:.1f}%) - 耗时: {elapsed}")
    
    def finish(self):
        """
        完成进度跟踪
        """
        elapsed = datetime.now() - self.start_time
        logging.info(f"{self.description}完成: {self.current}/{self.total} - 总耗时: {elapsed}")


def validate_config(config: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    验证配置字典
    
    Args:
        config: 配置字典
        required_keys: 必需的键列表
        
    Returns:
        是否有效
    """
    try:
        for key in required_keys:
            if key not in config:
                logging.error(f"配置中缺少必需的键: {key}")
                return False
        
        return True
    except Exception as e:
        logging.error(f"验证配置失败: {str(e)}")
        return False
