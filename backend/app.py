import os
import json
import asyncio
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 导入LlamaIndex文档处理器
from my.llamaindex_document_processor import LlamaIndexDocumentProcessor

# 创建FastAPI应用
app = FastAPI(title="AI测试平台API", description="AI测试平台后端API")

# 添加CORS支持
from fastapi.middleware.cors import CORSMiddleware

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建上传文件目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        """同步方法，移除连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, client_id: str, message: str):
        """异步方法，发送消息"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)
    
    async def close_connection(self, client_id: str):
        """异步方法，主动关闭WebSocket连接"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].close()
            except Exception as e:
                print(f"关闭WebSocket连接出错: {str(e)}")
            finally:
                self.disconnect(client_id)  # 注意这里是同步调用

manager = ConnectionManager()

# 请求模型
class AnalysisRequest(BaseModel):
    file_ids: List[str]
    description: str
    query: str = "分析这个文档的主要需求和功能点"

class AnalysisResponse(BaseModel):
    status: str
    message: str
    result: Optional[Dict[str, Any]] = None

# 文件上传处理
@app.post("/api/upload", response_model=Dict[str, Any])
async def upload_files(files: List[UploadFile] = File(...)):
    result = []
    
    for file in files:
        # 生成唯一文件ID
        file_id = str(uuid.uuid4())
        
        # 获取文件扩展名
        file_ext = os.path.splitext(file.filename)[1]
        
        # 创建保存路径
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
        
        # 保存文件
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 添加到结果列表
        result.append({
            "id": file_id,
            "filename": file.filename,
            "path": file_path,
            "size": len(content)
        })
    
    return {"status": "success", "files": result}

# 文档分析HTTP接口
@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_document(request: AnalysisRequest):
    try:
        # 初始化文档处理器
        processor = LlamaIndexDocumentProcessor(
            embedding_model_type="huggingface",
            embedding_model_name="BAAI/bge-small-zh-v1.5",
            use_deepseek_llm=True
        )
        
        # 获取文件路径
        file_paths = []
        for file_id in request.file_ids:
            # 查找匹配的文件
            for filename in os.listdir(UPLOAD_DIR):
                if filename.startswith(file_id):
                    file_paths.append(os.path.join(UPLOAD_DIR, filename))
                    break
        
        if not file_paths:
            return AnalysisResponse(
                status="error",
                message="未找到指定的文件"
            )
        
        # 处理文档并执行查询
        result = await processor.process_and_query(
            file_path=file_paths[0],  # 目前只处理第一个文件
            query=request.query,
            chunk_method="sentence"
        )
        
        return AnalysisResponse(
            status="success",
            message="分析完成",
            result=result
        )
        
    except Exception as e:
        return AnalysisResponse(
            status="error",
            message=f"分析过程中出错: {str(e)}"
        )

# WebSocket接口 - 实时文档分析
@app.websocket("/ws/analyze/{client_id}")
async def websocket_analyze(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    print(f"客户端 {client_id} 已连接")
    
    try:
        # 只处理一次请求，不使用无限循环
        print(f"等待客户端 {client_id} 发送消息...")
        
        # 尝试不同的接收方法
        try:
            # 先尝试接收JSON
            data = await websocket.receive_json()
            print(f"成功接收JSON消息: {data}")
        except Exception as e:
            print(f"接收JSON失败，尝试接收文本: {str(e)}")
            # 如果JSON解析失败，尝试接收文本
            text_data = await websocket.receive_text()
            print(f"接收到文本消息: {text_data}")
            try:
                data = json.loads(text_data)
                print(f"成功解析文本为JSON: {data}")
            except:
                print(f"无法解析文本为JSON，使用空字典")
                data = {}
        
        # 发送确认消息
        await manager.send_message(client_id, json.dumps({
            "type": "status",
            "message": "开始处理文档分析请求..."
        }))
        print(f"已发送确认消息给客户端 {client_id}")
        
        # 使用文档处理器工厂创建统一处理器
        from my.document_processor_factory import DocumentProcessorFactory
        processor = DocumentProcessorFactory.create_processor({
            "embedding": {
                "model_type": "huggingface",
                "model_name": "BAAI/bge-small-zh-v1.5"
            },
            "llm": {
                "use_deepseek": True
            },
            "multimodal": {
                "api_base": "https://api.moonshot.cn/v1",
                "model": "moonshot-v1-32k-vision-preview",
                "max_concurrent": 4
            }
        })
        
        # 获取文件路径
        file_paths = []
        for file_id in data.get("file_ids", []):
            # 查找匹配的文件
            for filename in os.listdir(UPLOAD_DIR):
                if filename.startswith(file_id):
                    file_paths.append(os.path.join(UPLOAD_DIR, filename))
                    break
        
        if not file_paths:
            await manager.send_message(client_id, json.dumps({
                "type": "error",
                "message": "未找到指定的文件"
            }))
            return
        
        # 发送处理状态更新
        await manager.send_message(client_id, json.dumps({
            "type": "status",
            "message": "正在处理文档，这可能需要一些时间..."
        }))
        
        # 处理文档并执行查询
        result = await processor.process_and_query(
            file_path=file_paths[0],  # 目前只处理第一个文件
            query=data.get("query", "分析这个文档的主要需求和功能点"),
            chunk_method="sentence"
        )

        # 打印相关文本块到终端
        print("\n===== 相关文本块 =====")
        for i, node in enumerate(result.get("source_nodes", [])):
            print(f"\n--- 文本块 {i+1} (相关度: {node.get('score', 0):.4f}) ---")
            print(node.get("text", ""))
        print("=====================\n")

        # 只发送回答部分给前端
        frontend_result = {
            "query": result.get("query", ""),
            "response": result.get("response", "")
            # 不包含source_nodes
        }

        # 发送最终结果
        await manager.send_message(client_id, json.dumps({
            "type": "result",
            "data": frontend_result
        }))
        
        # 等待一段时间，让客户端有机会处理结果
        await asyncio.sleep(2)
        
    except WebSocketDisconnect:
        print(f"客户端 {client_id} 断开连接")
        manager.disconnect(client_id)  # 同步方法，不需要await
    except Exception as e:
        error_msg = f"处理请求时出错: {str(e)}"
        print(error_msg)
        try:
            await manager.send_message(client_id, json.dumps({
                "type": "error",
                "message": error_msg
            }))
        except:
            pass
        finally:
            manager.disconnect(client_id)  # 同步方法，不需要await
    finally:
        print(f"客户端 {client_id} 已断开连接")

# 添加健康检查接口
@app.get("/api/health")
async def health_check():
    """
    健康检查接口，用于前端检测后端服务是否可用
    """
    return {"status": "success", "message": "Service is running"}

# 添加文件删除API
@app.post("/api/delete-file", response_model=Dict[str, Any])
async def delete_file(request: Dict[str, Any]):
    """
    删除单个文件
    """
    try:
        file_id = request.get("file_id")
        if not file_id:
            return {"status": "error", "message": "未提供文件ID"}
        
        # 查找匹配的文件
        deleted = False
        for filename in os.listdir(UPLOAD_DIR):
            if filename.startswith(file_id):
                file_path = os.path.join(UPLOAD_DIR, filename)
                os.remove(file_path)
                deleted = True
                break
        
        if deleted:
            return {"status": "success", "message": "文件已删除"}
        else:
            return {"status": "error", "message": "未找到指定的文件"}
    
    except Exception as e:
        return {"status": "error", "message": f"删除文件时出错: {str(e)}"}

# 添加批量删除文件API
@app.post("/api/delete-files", response_model=Dict[str, Any])
async def delete_files(request: Dict[str, Any]):
    """
    批量删除文件
    """
    try:
        file_ids = request.get("file_ids", [])
        if not file_ids:
            return {"status": "error", "message": "未提供文件ID列表"}
        
        deleted_count = 0
        for file_id in file_ids:
            for filename in os.listdir(UPLOAD_DIR):
                if filename.startswith(file_id):
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    os.remove(file_path)
                    deleted_count += 1
                    break
        
        return {
            "status": "success", 
            "message": f"已删除 {deleted_count} 个文件",
            "deleted_count": deleted_count
        }
    
    except Exception as e:
        return {"status": "error", "message": f"批量删除文件时出错: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)













