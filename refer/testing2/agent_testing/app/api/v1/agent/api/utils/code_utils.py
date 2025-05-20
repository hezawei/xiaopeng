# code_utils.py
# 代码处理工具类

import re
import logging
from typing import List, Dict, Any

from autogen_core.code_executor import CodeBlock

# 配置日志
logger = logging.getLogger("code_utils")

def extract_code_blocks(markdown_text: str) -> List[CodeBlock]:
    """从Markdown文本中提取代码块"""
    pattern = re.compile(r"```(?:\s*([\w\+\-]+))?\n([\s\S]*?)```")
    matches = pattern.findall(markdown_text)
    code_blocks: List[CodeBlock] = []
    for match in matches:
        language = match[0].strip() if match[0] else ""
        code_content = match[1]
        code_blocks.append(CodeBlock(code=code_content, language=language))
    return code_blocks


def extract_python_code(markdown_text: str) -> str:
    """提取Markdown中的Python代码"""
    result = ""
    # 尝试提取```python格式
    if "```python" in markdown_text:
        parts = markdown_text.split("```python")
        for part in parts[1:]:
            if "```" in part:
                code = part.split("```")[0].strip()
                result += code + "\n\n"
    # 尝试提取普通```格式
    elif "```" in markdown_text:
        parts = markdown_text.split("```")
        for i in range(1, len(parts), 2):
            if i < len(parts):
                code = parts[i].strip()
                # 简单检查是否为Python代码
                if "import" in code or "def " in code or "class " in code:
                    result += code + "\n\n"

    return result.strip()


def extract_interfaces(code: str) -> Dict[str, Any]:
    """从代码中提取类和方法定义"""
    result = {"classes": {}, "functions": []}
    
    # 提取类定义
    class_pattern = r"class\s+(\w+)(?:\(.*?\))?:"
    class_matches = re.finditer(class_pattern, code)
    
    for match in class_matches:
        class_name = match.group(1)
        class_code = extract_class_code(code, match.start())
        methods = extract_methods(class_code)
        result["classes"][class_name] = {"methods": methods}
    
    # 提取顶级函数
    function_pattern = r"(?:^|\n)def\s+(\w+)\s*\((.*?)\):"
    function_matches = re.finditer(function_pattern, code, re.DOTALL)
    
    for match in function_matches:
        if is_top_level_function(code, match.start()):
            func_name = match.group(1)
            func_params = match.group(2)
            result["functions"].append({
                "name": func_name,
                "parameters": func_params
            })
    
    return result


def extract_class_code(code: str, start_pos: int) -> str:
    """提取类定义的代码块"""
    # 从start_pos开始找到完整的类代码块
    lines = code[start_pos:].split('\n')
    class_code = lines[0] + '\n'
    indentation = 0
    
    # 找到类定义行的缩进级别
    for char in lines[0]:
        if char == ' ':
            indentation += 1
        else:
            break
    
    # 收集所有属于这个类的代码行
    for line in lines[1:]:
        current_indent = 0
        for char in line:
            if char == ' ':
                current_indent += 1
            else:
                break
        
        if not line.strip() or current_indent > indentation:
            class_code += line + '\n'
        else:
            break
    
    return class_code


def extract_methods(class_code: str) -> List[Dict[str, str]]:
    """从类代码中提取方法定义"""
    methods = []
    method_pattern = r"def\s+(\w+)\s*\((self(?:,\s*.*?)?)\):"
    method_matches = re.finditer(method_pattern, class_code)
    
    for match in method_matches:
        method_name = match.group(1)
        params_str = match.group(2)
        
        # 删除self参数并解析其余参数
        params = params_str.replace("self", "").strip()
        if params.startswith(","):
            params = params[1:].strip()
        
        methods.append({
            "name": method_name,
            "parameters": params
        })
    
    return methods


def is_top_level_function(code: str, start_pos: int) -> bool:
    """检查函数是否为顶级函数（不在类内部）"""
    line_start = code.rfind('\n', 0, start_pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1
    
    # 检查函数定义前的缩进
    indentation = start_pos - line_start
    
    # 如果缩进为0，则为顶级函数
    return indentation == 0 