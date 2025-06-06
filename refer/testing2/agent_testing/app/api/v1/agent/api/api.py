import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from autogen_core import ClosureContext, MessageContext, TopicId
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# 导入智能体模块
from .api_agents import (
    start_api_test_runtime,
    TestExecutorAgent,
    TestGenerationResult,
    TopicTypes
)
from .models import APIDocsInput, WebSocketMessage
from .utils.message_utils import create_system_message

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_router")

# 配置常量
WEBSOCKET_TIMEOUT = 3600  # WebSocket连接超时时间（秒）
CLEANUP_INTERVAL = 600    # 清理不活跃连接的间隔（秒）
MAX_IDLE_MINUTES = 60     # 最大允许的闲置时间（分钟）

# 创建路由器
router = APIRouter()

# WebSocket连接管理
class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.last_activity: Dict[str, datetime] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """建立WebSocket连接"""
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            self.last_activity[client_id] = datetime.now()
            logger.info(f"WebSocket连接已建立: {client_id}")
            return True
        except Exception as e:
            logger.error(f"连接建立失败: {str(e)}")
            return False

    async def disconnect(self, client_id: str) -> None:
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        # 同时清理活动记录
        if client_id in self.last_activity:
            del self.last_activity[client_id]

        logger.info(f"连接已移除: {client_id}")

    async def send_json(self, message: Dict, client_id: str) -> bool:
        """发送JSON消息"""
        if client_id not in self.active_connections:
            logger.warning(f"连接不存在: {client_id}")
            return False

        try:
            # 更新活动时间
            self.last_activity[client_id] = datetime.now()

            # 发送消息
            await self.active_connections[client_id].send_json(message)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return False

    async def clean_stale_connections(self, max_idle_minutes: int = MAX_IDLE_MINUTES) -> None:
        """清理长时间不活跃的连接"""
        try:
            current_time = datetime.now()
            inactive_clients = []

            # 找出不活跃的连接
            for client_id, last_time in list(self.last_activity.items()):
                idle_minutes = (current_time - last_time).total_seconds() / 60
                if idle_minutes > max_idle_minutes:
                    inactive_clients.append(client_id)

            # 断开不活跃的连接
            for client_id in inactive_clients:
                logger.info(f"清理不活跃连接: {client_id}, 已闲置超过{max_idle_minutes}分钟")
                await self.disconnect(client_id)

        except Exception as e:
            logger.error(f"清理连接时出错: {str(e)}")

# 创建连接管理器实例
manager = ConnectionManager()

# 定期清理过期连接
@asynccontextmanager
async def lifespan(app):
    # 启动定期清理任务
    cleanup_task = asyncio.create_task(schedule_cleanup())
    yield
    # 取消清理任务
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

async def schedule_cleanup():
    """定期执行清理任务"""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        await manager.clean_stale_connections()

# 健康检查接口
@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# API测试WebSocket端点
@router.websocket("/ws/apitest/{client_id}")
async def websocket_api_test(websocket: WebSocket, client_id: str):
    """API测试WebSocket端点"""
    # 连接建立
    if not await manager.connect(websocket, client_id):
        return

    try:
        # 发送欢迎消息
        await manager.send_json(
            create_system_message("log", "连接已建立，等待配置..."), 
            client_id
        )

        # 等待配置数据
        data = await websocket.receive_json()
        logger.info(f"收到配置: {data}")

        # 创建API输入
        try:
            input_data = APIDocsInput(
                api_docs_url=data.get('api_docs_url'),
                base_url=data.get('base_url', ''),
                enable_review=data.get('enable_review', True),
                user_review=data.get('user_review', False),
                use_local_executor=data.get('use_local_executor', False),
                api_doc_supplement=data.get('api_doc_supplement', ''),
                test_focus=data.get('test_focus', '')
            )
        except Exception as e:
            logger.error(f"创建API输入失败: {str(e)}")
            await manager.send_json(
                create_system_message("error", f"配置数据无效: {str(e)}"),
                client_id
            )
            return

        # 发送开始消息
        await manager.send_json(
            create_system_message("log", "开始API测试..."),
            client_id
        )

        # 结果处理函数
        async def handle_result(ctx: ClosureContext, message: WebSocketMessage, msg_ctx: MessageContext) -> None:
            try:
                # 将消息转换为字典格式
                message_dict = message.to_dict()
                
                # 测试代码标签优化 - 统一展示conftest.py, utils.py和测试代码
                if message_dict.get("type") == "code" and isinstance(message_dict.get("content"), dict):
                    content = message_dict.get("content", {})
                    # 检查是否包含各种测试相关代码
                    if any(k in content for k in ["test_code", "conftest_code", "utils_code"]):
                        # 统一标记为测试代码类型
                        message_dict["type"] = "test_code"
                        
                        # 增加代码类型标识，提高区分度
                        for code_type in ["test_code", "conftest_code", "utils_code"]:
                            if code_type in content and content[code_type]:
                                # 添加代码类型前缀，增加区分度
                                prefix = ""
                                if code_type == "test_code":
                                    prefix = "# === 测试代码 ===\n"
                                elif code_type == "conftest_code":
                                    prefix = "# === Conftest 配置代码 ===\n"
                                elif code_type == "utils_code":
                                    prefix = "# === 工具函数代码 ===\n"
                                
                                content[code_type] = prefix + content[code_type]
                
                # 修复报告标签问题
                if message_dict.get("type") == "result" and isinstance(message_dict.get("content"), dict):
                    content = message_dict.get("content", {})
                    
                    # 检查是否包含报告数据
                    if "report_data" in content:
                        report_data = content.get("report_data", {})
                        
                        # 修复分析报告
                        if "analysis" in report_data:
                            message_dict["has_analysis_report"] = True
                        
                        # 修复HTML报告
                        if "html_report" in report_data:
                            message_dict["has_html_report"] = True
                            
                        # 修复Allure报告
                        if "allure_report" in report_data:
                            message_dict["has_allure_report"] = True
                
                # 确保字典包含所有必要的键
                if "type" not in message_dict:
                    message_dict["type"] = "log"
                if "content" not in message_dict:
                    message_dict["content"] = "无内容"
                if "source" not in message_dict:
                    message_dict["source"] = "system"
                if message_dict["timestamp"] is None:
                    message_dict["timestamp"] = datetime.now().isoformat()
                
                # 确保消息内容可序列化
                try:
                    json.dumps(message_dict)
                except (TypeError, ValueError, OverflowError):
                    # 如果序列化失败，将content转换为字符串
                    if isinstance(message_dict["content"], dict):
                        for key, value in message_dict["content"].items():
                            if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                                message_dict["content"][key] = str(value)
                    else:
                        message_dict["content"] = str(message_dict["content"])
                
                # 发送消息
                await manager.send_json(message_dict, client_id)
                
                # 检查是否是最终消息
                if message_dict.get("type") == "result" or (
                        message_dict.get("type") == "progress" and
                        isinstance(message_dict.get("content"), dict) and
                        message_dict.get("content", {}).get("percentage") == 100
                ):
                    # 发送完成通知
                    await manager.send_json(
                        create_system_message("complete", "API测试流程已完成"),
                        client_id
                    )
            except Exception as e:
                logger.error(f"处理WebSocket消息时出错: {str(e)}", exc_info=True)
                await manager.send_json(
                    create_system_message("error", f"处理消息出错: {str(e)}"),
                    client_id
                )

        # 启动测试
        try:
            await start_api_test_runtime(
                api_input=input_data,
                client_id=None,  # 不使用client_id方式，转而使用回调
                result_handler=handle_result
            )
        except Exception as e:
            logger.error(f"启动API测试失败: {str(e)}")
            await manager.send_json(
                create_system_message("error", f"启动测试失败: {str(e)}"),
                client_id
            )

        # 保持连接并处理后续命令
        while True:
            try:
                # 设置超时防止永久阻塞
                command = await asyncio.wait_for(
                    websocket.receive_json(), 
                    timeout=WEBSOCKET_TIMEOUT
                )

                # 处理客户端命令
                if command.get("action") == "disconnect":
                    logger.info(f"客户端请求断开连接: {client_id}")
                    break
                elif command.get("action") == "new_test":
                    # 处理新的测试请求
                    logger.info(f"收到新的测试请求: {client_id}")
                    await manager.send_json(
                        create_system_message("log", "收到新的测试请求，开始处理..."),
                        client_id
                    )
                    
                    # 这里可以处理新的测试请求
                    # TODO: 实现新测试请求的处理逻辑
                elif command.get("run_test"):
                    await handle_run_test_command(command, client_id)
                elif command.get("update_test_code"):
                    await handle_update_test_code_command(command, client_id)
                else:
                    await manager.send_json(
                        create_system_message("warn", f"未知命令: {command.get('action')}"),
                        client_id
                    )
            except asyncio.TimeoutError:
                # 超时但继续保持连接，发送ping
                await manager.send_json(
                    create_system_message("ping", "保持连接"),
                    client_id
                )
            except WebSocketDisconnect:
                logger.info(f"客户端断开连接: {client_id}")
                break
            except Exception as e:
                logger.error(f"处理客户端命令出错: {str(e)}")
                # 发送错误但保持连接
                await manager.send_json(
                    create_system_message("error", f"处理命令出错: {str(e)}"),
                    client_id
                )

    except WebSocketDisconnect:
        logger.info(f"客户端断开连接: {client_id}")
    except Exception as e:
        logger.error(f"处理出错: {str(e)}")
        # 尝试发送错误消息
        try:
            await manager.send_json(
                create_system_message("error", f"出错: {str(e)}"),
                client_id
            )
        except:
            pass  # 忽略发送错误消息时的异常
    finally:
        # 这里不主动断开连接，由客户端或清理任务处理
        pass


async def handle_run_test_command(command: Dict[str, Any], client_id: str):
    """处理运行测试命令"""
    # 提取测试文件路径和参数
    test_file_path = command.get("test_file_path")
    test_params = command.get("test_params", {})
    
    logger.info(f"收到测试执行请求: {test_file_path}, 参数: {test_params}")
    
    # 发送日志
    await manager.send_json(
        create_system_message("log", f"开始执行测试: {test_file_path}"),
        client_id
    )
    
    # 启动测试执行
    try:
        # 回调函数，用于处理测试结果
        async def test_result_handler(ctx, message, msg_ctx):
            # 确保测试结果包含报告信息
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump()
            else:
                message_dict = message if isinstance(message, dict) else {"content": str(message)}
                
            # 为测试结果添加报告相关标志
            if message_dict.get("type") == "result" and isinstance(message_dict.get("content"), dict):
                content = message_dict.get("content", {})
                
                # 检查是否包含报告数据
                if "report_data" in content:
                    report_data = content.get("report_data", {})
                    
                    # 修复分析报告
                    if "analysis" in report_data:
                        message_dict["has_analysis_report"] = True
                    
                    # 修复HTML报告
                    if "html_report" in report_data:
                        message_dict["has_html_report"] = True
                        
                    # 修复Allure报告
                    if "allure_report" in report_data:
                        message_dict["has_allure_report"] = True

                # 确保报告数据结构完整，即使为空
                if "report_data" not in content:
                    content["report_data"] = {
                        "analysis": {},
                        "html_report": "",
                        "allure_report": ""
                    }
                    message_dict["content"] = content
            
            await manager.send_json(
                message_dict,
                client_id
            )
        
        # 创建执行运行时
        from autogen_core import SingleThreadedAgentRuntime, TypeSubscription, ClosureAgent
        
        runtime = SingleThreadedAgentRuntime()
        await TestExecutorAgent.register(
            runtime, 
            TopicTypes.TEST_EXECUTOR, 
            lambda: TestExecutorAgent(test_params.get("use_local_executor", True))
        )
        
        # 注册结果处理
        await ClosureAgent.register_closure(
            runtime,
            "result_collector",
            test_result_handler,
            subscriptions=lambda: [
                TypeSubscription(topic_type=TopicTypes.TEST_RESULT, agent_type="result_collector")],
        )
        
        # 启动运行时
        runtime.start()
        
        # 构建pytest命令参数
        pytest_options = ""
        
        # 应用超时参数
        if "timeout" in test_params:
            timeout = test_params.get("timeout")
            if timeout and int(timeout) > 0:
                pytest_options += f" --timeout={timeout}"
                
        # 应用重试参数
        if "retries" in test_params:
            retries = test_params.get("retries")
            if retries and int(retries) > 0:
                pytest_options += f" --reruns={retries}"
                
        # 应用并行参数
        if test_params.get("parallel", False):
            pytest_options += " -xvs"  # 添加并行执行标志
            
        # 应用详细日志参数
        if test_params.get("verbose", True):
            pytest_options += " -v"
            
        # 应用标签参数
        if "tags" in test_params and test_params["tags"]:
            tags = ",".join(test_params["tags"])
            pytest_options += f" -m \"{tags}\""
            
        # 应用自定义选项
        if "custom_options" in test_params and test_params["custom_options"]:
            pytest_options += f" {test_params['custom_options']}"

        # 记录完整的pytest选项
        logger.info(f"构建的pytest选项: {pytest_options}")
        
        # 将构建好的pytest选项添加到日志
        await manager.send_json(
            create_system_message("log", f"使用pytest选项: {pytest_options}"),
            client_id
        )
        
        # 发送执行请求
        await runtime.publish_message(
            TestGenerationResult(
                test_file_path=test_file_path,
                base_url=test_params.get('base_url', command.get('base_url', '')),
                enable_review=False,  # 执行时不需要审查
                user_review=False,
                use_local_executor=test_params.get("use_local_executor", True),
                test_params=test_params,  # 添加测试参数
                pytest_options=pytest_options  # 添加构建好的pytest选项
            ),
            topic_id=TopicId(type=TopicTypes.TEST_EXECUTOR, source="api_router")
        )
        
        logger.info(f"测试执行请求已发送: {test_file_path}")
    except Exception as e:
        logger.error(f"执行测试失败: {str(e)}")
        await manager.send_json(
            create_system_message("error", f"执行测试失败: {str(e)}"),
            client_id
        )


async def handle_update_test_code_command(command: Dict[str, Any], client_id: str):
    """处理更新测试代码命令"""
    # 提取测试文件路径和代码
    test_file_path = command.get("test_file_path")
    code = command.get("code")
    
    if not test_file_path or not code:
        await manager.send_json(
            create_system_message("error", "更新测试代码失败: 缺少文件路径或代码内容"),
            client_id
        )
        return
    
    logger.info(f"收到更新测试代码请求: {test_file_path}")
    
    try:
        # 更新测试代码文件
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        await manager.send_json(
            create_system_message("log", f"测试代码已更新: {test_file_path}"),
            client_id
        )
    except Exception as e:
        logger.error(f"更新测试代码失败: {str(e)}")
        await manager.send_json(
            create_system_message("error", f"更新测试代码失败: {str(e)}"),
            client_id
        )