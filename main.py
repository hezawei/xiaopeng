#!/usr/bin/env python
"""
AI测试平台一键启动脚本
同时启动前端和后端服务
"""
import os
import sys
import subprocess
import time
import webbrowser
import signal
import platform
from pathlib import Path

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = ROOT_DIR / "backend"  # 修改为直接指向backend目录
FRONTEND_DIR = ROOT_DIR / "web" / "front-ai-testing-platform"

# 定义颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def check_requirements():
    """检查必要的依赖是否已安装"""
    print(f"{Colors.BLUE}[*] 检查环境依赖...{Colors.ENDC}")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print(f"{Colors.RED}[!] 错误: 需要Python 3.8或更高版本{Colors.ENDC}")
        return False
    
    # 检查Node.js
    try:
        node_version = subprocess.check_output(["node", "--version"], text=True).strip()
        print(f"{Colors.GREEN}[✓] 检测到Node.js: {node_version}{Colors.ENDC}")
    except (subprocess.SubprocessError, FileNotFoundError):
        print(f"{Colors.RED}[!] 错误: 未检测到Node.js，请安装Node.js (https://nodejs.org){Colors.ENDC}")
        return False
    
    # 检查pnpm - 关键修复
    try:
        # 1. 使用shell=True以确保使用与终端相同的环境
        # 2. 在Windows上，使用cmd.exe来执行命令，确保与PowerShell环境一致
        if platform.system() == "Windows":
            pnpm_version = subprocess.check_output("cmd.exe /c pnpm --version", shell=True, text=True).strip()
        else:
            pnpm_version = subprocess.check_output("pnpm --version", shell=True, text=True).strip()
        
        print(f"{Colors.GREEN}[✓] 检测到pnpm: {pnpm_version}{Colors.ENDC}")
        package_manager = "pnpm"
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"{Colors.RED}[!] 错误: 未检测到pnpm: {str(e)}{Colors.ENDC}")
        print(f"{Colors.RED}[!] 本项目必须使用pnpm作为包管理器{Colors.ENDC}")
        return False
    
    # 检查FastAPI
    try:
        import fastapi
        print(f"{Colors.GREEN}[✓] 检测到FastAPI: {fastapi.__version__}{Colors.ENDC}")
    except ImportError:
        print(f"{Colors.YELLOW}[!] 警告: 未检测到FastAPI，将尝试安装...{Colors.ENDC}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]"])
            print(f"{Colors.GREEN}[✓] FastAPI安装成功{Colors.ENDC}")
        except subprocess.SubprocessError:
            print(f"{Colors.RED}[!] 错误: FastAPI安装失败{Colors.ENDC}")
            return False
    
    return True, package_manager

def start_backend():
    """启动后端服务"""
    print(f"{Colors.BLUE}[*] 启动后端服务...{Colors.ENDC}")
    
    # 确保上传目录存在
    uploads_dir = BACKEND_DIR / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    
    # 获取app.py的完整路径
    app_path = BACKEND_DIR / "app.py"
    
    # 直接运行app.py文件
    backend_cmd = [sys.executable, str(app_path)]
    
    # 在Windows上使用不同的方式启动进程
    if platform.system() == "Windows":
        backend_process = subprocess.Popen(
            backend_cmd, 
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        # 在Unix系统上，使用nohup确保进程在后台运行
        backend_process = subprocess.Popen(
            ["nohup"] + backend_cmd + ["&"], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setpgrp  # 在新进程组中运行，防止信号传递
        )
    
    # 等待后端服务启动
    print(f"{Colors.YELLOW}[*] 等待后端服务启动...{Colors.ENDC}")
    
    # 尝试连接后端健康检查接口，最多等待30秒
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            import urllib.request
            response = urllib.request.urlopen("http://localhost:8000/api/health", timeout=1)
            if response.status == 200:
                print(f"{Colors.GREEN}[✓] 后端服务已成功启动 (PID: {backend_process.pid}){Colors.ENDC}")
                print(f"{Colors.GREEN}[✓] 后端API地址: http://localhost:8000{Colors.ENDC}")
                return backend_process
        except Exception:
            # 如果连接失败，等待1秒后重试
            time.sleep(1)
    
    # 如果超过最大尝试次数仍未成功，则认为启动失败
    print(f"{Colors.RED}[!] 后端服务启动超时，请检查日志{Colors.ENDC}")
    try:
        backend_process.terminate()
    except:
        pass
    return None

def start_frontend(package_manager):
    """启动前端服务"""
    print(f"{Colors.BLUE}[*] 启动前端服务...{Colors.ENDC}")
    
    # 检查前端依赖是否已安装
    node_modules_path = FRONTEND_DIR / "node_modules"
    if not node_modules_path.exists():
        print(f"{Colors.YELLOW}[!] 前端依赖未安装，正在安装...{Colors.ENDC}")
        os.chdir(FRONTEND_DIR)
        try:
            if platform.system() == "Windows":
                subprocess.check_call("cmd.exe /c pnpm install", shell=True)
            else:
                subprocess.check_call(["pnpm", "install"])
            print(f"{Colors.GREEN}[✓] 前端依赖安装成功{Colors.ENDC}")
        except subprocess.SubprocessError as e:
            print(f"{Colors.RED}[!] 错误: 前端依赖安装失败: {str(e)}{Colors.ENDC}")
            return None
    
    # 启动前端开发服务器
    os.chdir(FRONTEND_DIR)
    
    # 在Windows上使用cmd.exe来执行pnpm命令，并在新控制台窗口中启动
    if platform.system() == "Windows":
        frontend_process = subprocess.Popen(
            "cmd.exe /c pnpm run dev",
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        try:
            # 在Unix系统上，使用nohup确保进程在后台运行
            frontend_process = subprocess.Popen(
                ["nohup", "pnpm", "run", "dev", "&"], 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setpgrp  # 在新进程组中运行，防止信号传递
            )
        except Exception as e:
            print(f"{Colors.RED}[!] 启动前端服务失败: {str(e)}{Colors.ENDC}")
            return None
    
    # 等待前端服务启动
    print(f"{Colors.YELLOW}[*] 等待前端服务启动...{Colors.ENDC}")
    
    # 尝试连接前端服务，最多等待15秒
    max_attempts = 15
    for attempt in range(max_attempts):
        try:
            import urllib.request
            response = urllib.request.urlopen("http://localhost:5173", timeout=1)
            if response.status == 200:
                print(f"{Colors.GREEN}[✓] 前端服务已成功启动 (PID: {frontend_process.pid}){Colors.ENDC}")
                print(f"{Colors.GREEN}[✓] 前端地址: http://localhost:5173{Colors.ENDC}")
                return frontend_process
        except Exception:
            # 如果连接失败，等待1秒后重试
            time.sleep(1)
    
    # 如果超过最大尝试次数仍未成功，则认为启动失败
    print(f"{Colors.RED}[!] 前端服务启动超时，请检查日志{Colors.ENDC}")
    try:
        frontend_process.terminate()
    except:
        pass
    return None

def open_browser():
    """打开浏览器访问前端页面"""
    print(f"{Colors.BLUE}[*] 正在打开浏览器...{Colors.ENDC}")
    time.sleep(3)  # 增加等待时间，确保服务完全启动
    
    # 先检查前端服务是否可访问
    try:
        import urllib.request
        response = urllib.request.urlopen("http://localhost:5173", timeout=2)
        if response.status == 200:
            webbrowser.open("http://localhost:5173")
            print(f"{Colors.GREEN}[✓] 已在浏览器中打开前端页面{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}[!] 前端服务返回非200状态码，未自动打开浏览器{Colors.ENDC}")
            print(f"{Colors.YELLOW}[!] 请手动访问: http://localhost:5173{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.YELLOW}[!] 无法连接到前端服务，未自动打开浏览器: {str(e)}{Colors.ENDC}")
        print(f"{Colors.YELLOW}[!] 请稍后手动访问: http://localhost:5173{Colors.ENDC}")

def handle_shutdown(backend_process, frontend_process):
    """处理关闭信号，确保子进程被正确终止"""
    def signal_handler(sig, frame):
        print(f"\n{Colors.YELLOW}[!] 接收到终止信号，正在关闭服务...{Colors.ENDC}")
        
        if frontend_process and frontend_process.poll() is None:
            print(f"{Colors.BLUE}[*] 正在终止前端服务 (PID: {frontend_process.pid})...{Colors.ENDC}")
            try:
                if platform.system() == "Windows":
                    # 使用stderr=subprocess.DEVNULL来抑制错误输出
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)], 
                                   stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                else:
                    try:
                        frontend_process.terminate()
                        frontend_process.wait(timeout=5)
                    except:
                        # 如果等待超时，强制杀死
                        try:
                            os.kill(frontend_process.pid, signal.SIGKILL)
                        except:
                            pass
            except Exception as e:
                # 忽略任何错误
                pass
        
        if backend_process and backend_process.poll() is None:
            print(f"{Colors.BLUE}[*] 正在终止后端服务 (PID: {backend_process.pid})...{Colors.ENDC}")
            try:
                if platform.system() == "Windows":
                    # 使用stderr=subprocess.DEVNULL来抑制错误输出
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(backend_process.pid)],
                                   stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                else:
                    try:
                        backend_process.terminate()
                        backend_process.wait(timeout=5)
                    except:
                        # 如果等待超时，强制杀死
                        try:
                            os.kill(backend_process.pid, signal.SIGKILL)
                        except:
                            pass
            except Exception as e:
                # 忽略任何错误
                pass
        
        print(f"{Colors.GREEN}[✓] 所有服务已关闭{Colors.ENDC}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    if platform.system() != "Windows":
        signal.signal(signal.SIGTERM, signal_handler)

def main():
    """主函数"""
    # 检查环境依赖
    check_result = check_requirements()
    if not check_result:
        print(f"{Colors.RED}[!] 环境检查失败，请安装必要的依赖后重试{Colors.ENDC}")
        return
    
    success, package_manager = check_result
    
    # 启动后端服务
    backend_process = start_backend()
    if not backend_process:
        return
    
    # 启动前端服务
    frontend_process = start_frontend(package_manager)
    if not frontend_process:
        # 如果前端启动失败，终止后端
        backend_process.terminate()
        return
    
    # 设置关闭处理
    handle_shutdown(backend_process, frontend_process)
    
    # 打开浏览器
    open_browser()
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}[✓] AI测试平台已成功启动!{Colors.ENDC}")
    print(f"{Colors.YELLOW}[*] 按Ctrl+C可以关闭所有服务{Colors.ENDC}")
    
    # 保持主进程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()









