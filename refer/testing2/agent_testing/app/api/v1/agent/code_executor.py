# 添加到api_agents.py文件中

import os
import sys
import asyncio
import tempfile
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import subprocess
import logging

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock, CodeExecutor
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor

logger = logging.getLogger("universal_executor")


class UniversalExecutor:
    """
    通用脚本执行器，支持跨平台执行shell和python脚本
    在Linux上使用原生执行器，在Windows上使用线程池绕过事件循环问题
    """

    """
    通用脚本执行器，支持跨平台执行shell和python脚本
    在Linux上使用原生执行器，在Windows上使用线程池绕过事件循环问题
    """

    def __init__(self, work_dir: Union[str, Path], timeout: int = 300, use_local_executor: bool = False):
        """
        初始化执行器

        Args:
            work_dir: 工作目录路径
            timeout: 执行超时时间(秒)
            use_local_executor: 是否使用本地执行器
        """
        self.work_dir = Path(work_dir) if isinstance(work_dir, str) else work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.use_local_executor = use_local_executor
        self.is_windows = sys.platform == "win32"
        self.executor = None

        # 初始化执行器
        try:
            # 基于Linux平台的执行器
            if not self.is_windows:
                # 在Linux上初始化执行器
                if not use_local_executor:
                    self.executor = DockerCommandLineCodeExecutor(
                        work_dir=str(self.work_dir),
                        timeout=timeout,
                    )
                else:
                    self.executor = LocalCommandLineCodeExecutor(
                        work_dir=str(self.work_dir),
                        timeout=timeout
                    )
                logger.info(f"在Linux平台上初始化{'Docker' if not use_local_executor else '本地'}执行器")
            else:
                # 在Windows上也尝试初始化本地执行器
                self.executor = LocalCommandLineCodeExecutor(
                    work_dir=str(self.work_dir),
                    timeout=timeout
                )
                logger.info("在Windows平台上初始化本地执行器")
        except Exception as e:
            logger.error(f"初始化执行器失败: {str(e)}")
            self.executor = None

    async def execute_python(self, code: str, args: List[str] = None) -> Dict[str, Any]:
        """
        执行Python代码

        Args:
            code: Python代码内容
            args: 传递给Python脚本的命令行参数

        Returns:
            包含执行结果的字典
        """
        if self.is_windows or self.executor is None:
            # Windows平台使用线程池执行
            return await self._execute_in_thread_pool(code, "python", args)
        else:
            # Linux平台使用原生执行器
            code_block = CodeBlock(code=code, language="python")
            try:
                return await self.executor.execute_code_blocks(
                    [code_block],
                    cancellation_token=CancellationToken()
                )
            except Exception as e:
                logger.error(f"执行Python代码失败: {str(e)}")
                return {
                    'exit_code': -1,
                    'output': f"执行出错: {str(e)}"
                }

    async def execute_shell(self, code: str, args: List[str] = None) -> Dict[str, Any]:
        """
        执行Shell脚本

        Args:
            code: Shell脚本内容
            args: 传递给Shell脚本的命令行参数

        Returns:
            包含执行结果的字典
        """
        script_language = "powershell" if self.is_windows else "bash"

        if self.is_windows or self.executor is None:
            # Windows平台使用线程池执行
            return await self._execute_in_thread_pool(code, script_language, args)
        else:
            # Linux平台使用原生执行器
            code_block = CodeBlock(code=code, language=script_language)
            try:
                return await self.executor.execute_code_blocks(
                    [code_block],
                    cancellation_token=CancellationToken()
                )
            except Exception as e:
                logger.error(f"执行Shell脚本失败: {str(e)}")
                return {
                    'exit_code': -1,
                    'output': f"执行出错: {str(e)}"
                }

    async def _execute_in_thread_pool(self, code: str, language: str, args: List[str] = None) -> Dict[str, Any]:
        """
            在线程池中执行代码

            Args:
                code: 代码内容
                language: 代码语言 (python/bash/powershell)
                args: 命令行参数

            Returns:
                包含执行结果的字典
            """

        def run_script():
            # 临时文件后缀
            suffix = ".py" if language == "python" else (".ps1" if language == "powershell" else ".sh")

            # 创建临时文件
            fd, temp_file = tempfile.mkstemp(suffix=suffix)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(code)

                # 构建命令
                if language == "python":
                    cmd = [sys.executable, temp_file]
                elif language == "powershell":
                    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_file]
                else:  # bash
                    cmd = ["bash", temp_file]

                # 添加额外参数
                if args:
                    cmd.extend(args)

                # 设置环境变量，确保Python进程使用UTF-8
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                env['PYTHONUTF8'] = '1'

                # 执行命令 - 关键修改:不使用text=True，而是明确指定编码
                process = subprocess.run(
                    cmd,
                    cwd=str(self.work_dir),
                    capture_output=True,
                    text=False,  # 不使用文本模式，使用二进制模式
                    timeout=self.timeout,
                    env=env
                )

                # 明确使用UTF-8解码输出
                try:
                    stdout = process.stdout.decode('utf-8') if process.stdout else ''
                except UnicodeDecodeError:
                    # 如果UTF-8解码失败，使用忽略错误的方式解码
                    stdout = process.stdout.decode('utf-8', errors='ignore') if process.stdout else ''

                try:
                    stderr = process.stderr.decode('utf-8') if process.stderr else ''
                except UnicodeDecodeError:
                    stderr = process.stderr.decode('utf-8', errors='ignore') if process.stderr else ''

                return {
                    'exit_code': process.returncode,
                    'output': stdout + stderr,
                    'code_file': temp_file  # 保留临时文件路径供调试
                }
            except subprocess.TimeoutExpired:
                return {
                    'exit_code': -1,
                    'output': f"执行超时 (>{self.timeout}秒)"
                }
            except Exception as e:
                return {
                    'exit_code': -1,
                    'output': f"执行出错: {str(e)}"
                }
            finally:
                # 不要删除临时文件，可能需要调试
                pass

        # 使用线程池异步执行
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(pool, run_script)

    async def install_packages(self, packages: List[str]) -> Dict[str, Any]:
        """安装Python包"""
        packages_str = " ".join(packages)

        # 构建命令
        if self.is_windows:
            # Windows下避免编码问题
            cmd = f"python -m pip install {packages_str} -i https://pypi.tuna.tsinghua.edu.cn/simple"
        else:
            cmd = f"pip install {packages_str} -i https://pypi.tuna.tsinghua.edu.cn/simple"

        # 环境变量确保UTF-8编码
        env = {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1"
        }

        # 根据平台选择执行方式
        if self.is_windows:
            # Windows平台使用线程池
            code = f"""
import subprocess
import sys

try:
    cmd = [{', '.join(f'"{p}"' for p in packages)}]
    for package in cmd:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, 
                              "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
                             encoding="utf-8")
    print("依赖安装成功!")
except Exception as e:
    print(f"安装依赖出错: {{str(e)}}")
    sys.exit(1)
"""
            return await self._execute_in_thread_pool(code, "python")
        else:
            # 非Windows平台使用执行器
            if self.executor is None:
                return {
                    "exit_code": -1,
                    "output": "执行器未初始化，无法安装依赖"
                }

            try:
                result = await self.executor.execute_code_blocks([
                    CodeBlock(language="bash", code=cmd)
                ], environment=env)

                return {
                    "exit_code": result.exit_code,
                    "output": result.output
                }
            except Exception as e:
                logger.error(f"安装依赖出错: {str(e)}")
                return {
                    "exit_code": -1,
                    "output": f"安装依赖出错: {str(e)}"
                }

    async def execute_command(self, cmd: str, env: Dict[str, str] = None) -> Dict[str, Any]:
            """执行命令行命令"""
            # 基础环境变量
            environment = {
                "PYTHONIOENCODING": "utf-8",  # 确保Python使用UTF-8编码
                "PYTHONUTF8": "1"  # 强制Python使用UTF-8
            }
            # 合并传入的环境变量
            if env:
                environment.update(env)

            # 根据平台选择执行方式
            if self.is_windows:
                # Windows平台使用线程池
                # 对于Windows系统，将命令转换为可在PowerShell中执行的形式
                powershell_code = f"""
    $ErrorActionPreference = "Stop"
    # 设置环境变量
    {os.linesep.join([f'$env:{k}="{v}"' for k, v in environment.items()])}

    # 执行命令
    cd {self.work_dir}
    {cmd}
    if ($LASTEXITCODE -ne 0) {{
        Write-Error "命令执行失败，退出码: $LASTEXITCODE"
        exit $LASTEXITCODE
    }}
    """
                return await self._execute_in_thread_pool(powershell_code, "powershell")
            else:
                # 非Windows平台使用执行器
                if self.executor is None:
                    return {
                        "exit_code": -1,
                        "output": "执行器未初始化，无法执行命令"
                    }

                try:
                    result = await self.executor.execute_code_blocks([
                        CodeBlock(language="bash", code=cmd)
                    ], environment=environment)

                    return {
                        "exit_code": result.exit_code,
                        "output": result.output
                    }
                except Exception as e:
                    logger.error(f"执行命令出错: {str(e)}")
                    return {
                        "exit_code": -1,
                        "output": f"执行命令出错: {str(e)}"
                    }

    async def execute_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        执行指定文件

        Args:
            file_path: 文件路径

        Returns:
            执行结果
        """
        path = Path(file_path) if isinstance(file_path, str) else file_path

        if not path.exists():
            return {
                'exit_code': -1,
                'output': f"文件不存在: {path}"
            }

        # 读取文件内容
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()

        # 根据扩展名决定执行方式
        suffix = path.suffix.lower()
        if suffix == '.py':
            return await self.execute_python(code)
        elif suffix in ['.sh', '.bash']:
            return await self.execute_shell(code)
        elif suffix == '.ps1':
            if not self.is_windows:
                return {
                    'exit_code': -1,
                    'output': "不能在非Windows平台上执行PowerShell脚本"
                }
            return await self.execute_shell(code)
        else:
            return {
                'exit_code': -1,
                'output': f"不支持的文件类型: {suffix}"
            }


# 在TestExecutorAgent中添加示例测试方法
async def test_universal_executor(self):
    """测试通用执行器功能"""
    # 创建执行器
    executor = UniversalExecutor(work_dir=Path("coding").resolve())

    # 测试Python代码执行
    python_result = await executor.execute_python("""
import platform
import sys

print(f"Python版本: {sys.version}")
print(f"平台: {platform.platform()}")
print("Hello from Python!")
""")
    print("Python执行结果:", python_result)

    # 测试包安装
    install_result = await executor.install_packages(["matplotlib", "pytest"])
    print("包安装结果:", install_result)

    # 测试Shell执行
    if sys.platform == "win32":
        # Windows上执行PowerShell
        shell_result = await executor.execute_shell("""
Write-Host "当前目录: $(Get-Location)"
Write-Host "Hello from PowerShell!"
Get-Process | Select-Object -First 3
""")
    else:
        # Linux上执行Bash
        shell_result = await executor.execute_shell("""
echo "当前目录: $(pwd)"
echo "Hello from Bash!"
ls -la | head -n 5
""")
    print("Shell执行结果:", shell_result)

    return {
        "python": python_result,
        "install": install_result,
        "shell": shell_result
    }