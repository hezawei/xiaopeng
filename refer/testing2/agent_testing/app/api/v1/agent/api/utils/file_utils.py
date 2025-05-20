# file_utils.py
# 文件处理工具类

import os
import uuid
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any

# 配置日志
logger = logging.getLogger("file_utils")

def create_temp_dir(prefix: str = "api_test_") -> Path:
    """创建临时目录"""
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        logger.info(f"创建临时目录: {temp_dir}")
        return temp_dir
    except Exception as e:
        logger.error(f"创建临时目录失败: {e}")
        raise


def save_code_to_file(code: str, file_path: Path) -> None:
    """保存代码到文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        logger.info(f"代码已保存到: {file_path}")
    except Exception as e:
        logger.error(f"保存代码到文件失败: {e}")
        raise


def save_multiple_files(files_dict: Dict[str, str], base_dir: Path) -> Dict[str, Path]:
    """保存多个文件到指定目录

    Args:
        files_dict: 字典，键为文件名，值为文件内容
        base_dir: 基础目录

    Returns:
        字典，键为文件名，值为文件路径
    """
    result = {}
    try:
        for file_name, content in files_dict.items():
            file_path = base_dir / file_name
            save_code_to_file(content, file_path)
            result[file_name] = file_path
        return result
    except Exception as e:
        logger.error(f"保存多个文件失败: {e}")
        raise


def cleanup_dir(dir_path: Path) -> None:
    """清理目录"""
    try:
        if dir_path.exists():
            shutil.rmtree(dir_path, ignore_errors=True)
            logger.info(f"目录已清理: {dir_path}")
    except Exception as e:
        logger.error(f"清理目录失败: {e}")


def parse_test_files(test_code: str) -> Dict[str, str]:
    """解析测试代码中的多个测试文件

    Args:
        test_code: 测试代码内容

    Returns:
        字典，键为文件名，值为文件内容
    """
    test_files = {}

    # 尝试识别多个测试文件（如果有明确的分隔标记）
    file_pattern = re.compile(r'# (?:FILE|File|file)[:\s]+([a-zA-Z0-9_]+\.py)', re.MULTILINE)
    file_matches = list(file_pattern.finditer(test_code))

    if file_matches:
        # 多个文件情况
        for i in range(len(file_matches)):
            file_name = file_matches[i].group(1)
            start_pos = file_matches[i].end()

            # 确定结束位置
            end_pos = len(test_code)
            if i < len(file_matches) - 1:
                end_pos = file_matches[i + 1].start()

            # 提取文件内容
            file_content = test_code[start_pos:end_pos].strip()
            test_files[file_name] = file_content
    else:
        # 单文件情况，使用默认文件名
        default_name = f"test_api_{uuid.uuid4().hex[:8]}.py"
        test_files[default_name] = test_code

    return test_files


def read_file_content(file_path: Path) -> Optional[str]:
    """读取文件内容"""
    try:
        if not file_path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取文件内容失败: {e}")
        return None

# 确保import依赖存在
try:
    import re
except ImportError:
    pass 