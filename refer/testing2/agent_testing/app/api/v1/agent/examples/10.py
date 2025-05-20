import asyncio
from pathlib import Path

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
# 使用绝对路径创建工作目录
work_dir = Path("coding").resolve()
work_dir.mkdir(exist_ok=True)

# 初始化执行器
local_executor = LocalCommandLineCodeExecutor(
    work_dir=work_dir,
    timeout=300
)

async def main():
    # 使用Python代码块安装matplotlib
    python_code = """
import subprocess
import sys

try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib", "pytest"])
    print("matplotlib安装成功")
except Exception as e:
    print(f"安装失败: {e}")
"""

    s = await local_executor.execute_code_blocks(
        code_blocks=[
            CodeBlock(language="python", code=python_code),
        ],
        cancellation_token=CancellationToken(),
    )
    print(s)


asyncio.run(main())