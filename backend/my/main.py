# backend/my/main.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from llamaindex_document_processor import LlamaIndexDocumentProcessor
import os
import uuid
import shutil

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上传目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    description: str = Form(""),
    chunk_method: str = Form("sentence")
):
    """文件分析接口"""
    try:
        # 生成唯一文件名
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")

        # 保存上传文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 初始化处理器
        processor = LlamaIndexDocumentProcessor()

        # 执行分析
        result = processor.process_and_query(
            file_path=file_path,
            query=description or "进行需求分析",
            chunk_method=chunk_method
        )

        return {
            "code": 200,
            "message": "分析成功",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
import asyncio
import argparse
from requirement_analysis_agent import RequirementAnalysisAgent
from autogen_agentchat.ui import Console

async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='需求分析系统')
    parser.add_argument('--file', type=str, required=True, help='需求文档路径')
    args = parser.parse_args()

    # 创建需求分析智能体
    agent = RequirementAnalysisAgent(files=[args.file])
    team = await agent.create_team()

    # 运行需求分析并输出结果
    print(f"开始分析需求文件: {args.file}")
    await Console(team.run_stream(task="开始需求分析"))
    print("需求分析完成")

if __name__ == "__main__":
    asyncio.run(main())


