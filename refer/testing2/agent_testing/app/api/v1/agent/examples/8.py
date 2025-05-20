import asyncio
import venv
import sys
from pathlib import Path
from types import SimpleNamespace

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

# Windows平台设置事件循环策略
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 使用绝对路径创建工作目录
work_dir = Path("coding").resolve()
work_dir.mkdir(exist_ok=True)

# 创建虚拟环境目录
venv_dir = work_dir / ".venv"
venv_builder = venv.EnvBuilder(with_pip=True)
venv_builder.create(venv_dir)

# 获取虚拟环境中Python的绝对路径
scripts_dir = venv_dir / "Scripts"
venv_python = scripts_dir / "python.exe"

# 创建虚拟环境上下文
venv_context = SimpleNamespace(
    env_exe=str(venv_python),
    bin_path=str(scripts_dir)
)

# 初始化执行器
local_executor = LocalCommandLineCodeExecutor(
    work_dir=work_dir,
    virtual_env_context=venv_context,
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