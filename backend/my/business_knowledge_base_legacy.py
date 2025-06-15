"""
业务知识库管理系统 - 重构版本

本模块实现基于LlamaIndex和Milvus向量数据库的业务知识库管理功能，包括：
1. 创建和管理不同业务领域的知识库
2. 添加文档到指定业务知识库
3. 从知识库中删除指定文档
4. 基于知识库进行查询和分析
5. 支持跨业务的混合搜索和关联关系构建

注意：这是重构后的版本，原始文件已保留作为备份。

使用方法:
```python
# 创建知识库管理器
manager = BusinessKnowledgeBaseManager()

# 创建业务知识库
manager.create_business_kb("intelligent_chassis")

# 添加文档到知识库
doc_ids = manager.add_documents_to_kb("intelligent_chassis", ["doc1.pdf", "doc2.docx"])

# 删除知识库中的文档
manager.remove_document_from_kb("intelligent_chassis", doc_ids[0])

# 基于知识库进行查询
results = manager.query_business_kb("intelligent_chassis", "智能底盘的核心功能是什么?")

# 跨业务混合搜索
results = manager.query_with_cross_business("intelligent_chassis", "相关技术", expand_to_related=True)
```
"""

import os
import json
import uuid
import shutil
import asyncio
import hashlib
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

# LlamaIndex相关导入
from llama_index.core import (
    SimpleDirectoryReader,
    Document,
    VectorStoreIndex,
    StorageContext,
    Settings,
    load_index_from_storage
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.milvus import MilvusVectorStore

# 文档处理相关导入
from docling.document_converter import DocumentConverter

# 嵌入模型相关导入
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 多模态处理相关导入
from document_image_processor import DocumentImageProcessor
from document_processor_factory import DocumentProcessorFactory

# 日志相关导入
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 常量定义
DOC_STATUS_ACTIVE = "active"
DOC_STATUS_DELETED = "deleted"
DOC_STATUS_CORRUPTED = "corrupted"

SYNC_RESULT_OK = "ok"
SYNC_RESULT_WARNING = "warning"
SYNC_RESULT_ERROR = "error"

from pymilvus import MilvusClient
from business_relation_manager import BusinessRelationManager
from sklearn.feature_extraction.text import TfidfVectorizer

class BusinessKnowledgeBaseManager:
    """业务知识库管理系统"""
    
    def __init__(
        self,
        embedding_model_name: str = "BAAI/bge-small-zh-v1.5",
        milvus_uri: str = "tcp://localhost:19530",
        auto_sync: bool = False
    ):
        """
        初始化业务知识库管理器
        
        Args:
            embedding_model_name: 嵌入模型名称
            milvus_uri: Milvus服务URI，默认使用本地Docker部署的Milvus
            auto_sync: 是否在初始化时自动同步数据
        """
        # 获取脚本所在目录的绝对路径
        script_dir = Path(__file__).parent.absolute()
        # 直接定义基础目录为脚本所在目录下的business_knowledge_base目录
        self.base_dir = script_dir / "business_knowledge_base"
        self.base_dir.mkdir(exist_ok=True, parents=True)
        
        # 设置Milvus URI
        self.milvus_uri = milvus_uri
        logger.info(f"连接到Milvus服务: {self.milvus_uri}")
        
        # 固定文档分块参数
        self.chunk_size = 512
        self.chunk_overlap = 50
        self.max_retry_attempts = 3
        self.retry_delay = 2
        
        # 设置嵌入模型
        self.embedding_model_name = embedding_model_name
        self.embedding_model = HuggingFaceEmbedding(model_name=embedding_model_name)
        Settings.embed_model = self.embedding_model
        
        # 文档转换器
        self.doc_converter = DocumentConverter()
        
        # 多模态处理器
        self.image_processor = DocumentImageProcessor()
        
        # 业务知识库元数据
        self.metadata_file = self.base_dir / "kb_metadata.json"
        self.kb_metadata = self._load_metadata()
        
        # 初始化业务关联管理器
        self.relation_manager = BusinessRelationManager(self.base_dir)
        
        # 同步锁，防止并发操作
        self.sync_lock = threading.RLock()
        
        # 备份目录
        self.backup_dir = self.base_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # 标记是否需要同步
        self.auto_sync = auto_sync
        
        logger.info(f"业务知识库管理器初始化完成，基础目录: {self.base_dir}")

    def sync_all_businesses_sync(self):
        """同步版本的sync_all_businesses方法"""
        # 创建一个新的事件循环
        loop = asyncio.new_event_loop()
        try:
            # 运行异步方法
            result = loop.run_until_complete(self.sync_all_businesses())
            return result
        finally:
            # 关闭事件循环
            loop.close()
    
    # 添加新方法：提取文档实体并构建业务关联
    def _extract_entities_and_build_relations(self, business_id: str, document: Document) -> List[str]:
        """
        从文档中提取实体并构建业务关联
        
        Args:
            business_id: 业务ID
            document: 文档对象
            
        Returns:
            提取的实体列表
        """
        # 获取文档文本
        text = document.text
        
        # 提取实体
        entities = self.relation_manager.extract_entities(text, max_entities=15)
        
        # 构建业务关联
        self.relation_manager.build_relations_from_entities(business_id, entities)
        
        return entities
    
    # 修改添加文档方法，增加实体提取和关联构建
    async def add_documents_to_kb(
        self,
        business_id: str,
        file_paths: List[str],
        process_images: bool = True
    ) -> List[str]:
        """添加文档到业务知识库"""
        try:
            # 检查业务是否存在
            if business_id not in self.kb_metadata["businesses"]:
                self.create_business_kb(business_id)
            
            # 获取业务目录
            business_dir = self.base_dir / business_id
            documents_dir = business_dir / "documents"
            documents_dir.mkdir(exist_ok=True, parents=True)
            
            # 处理文档
            doc_ids = []
            processed_documents = []
            
            for file_path in file_paths:
                try:
                    # 生成文档ID
                    doc_id = str(uuid.uuid4())
                    
                    # 复制文件到知识库目录
                    original_path = Path(file_path)
                    file_name = original_path.name
                    kb_path = str(documents_dir / file_name)
                    
                    # 复制文件
                    shutil.copy2(file_path, kb_path)
                    
                    # 计算文件指纹
                    file_fingerprint = self._calculate_file_fingerprint(kb_path)
                    
                    # 处理文档内容
                    if process_images and self.image_processor:
                        # 使用图片处理器处理文档
                        try:
                            markdown_content = await self.image_processor.process_document(kb_path)
                            logger.info(f"文档 '{file_name}' 图片处理完成")
                        except Exception as e:
                            logger.error(f"处理文档图片失败: {str(e)}")
                            # 如果图片处理失败，使用普通方式处理
                            markdown_content = self.doc_converter.convert_to_text(kb_path)
                    else:
                        # 普通方式处理文档
                        markdown_content = self.doc_converter.convert_to_text(kb_path)
                    
                    # 创建Document对象
                    document = Document(
                        text=markdown_content,
                        metadata={
                            "doc_id": doc_id,
                            "file_name": file_name,
                            "original_path": str(original_path),
                            "kb_path": kb_path,
                            "business_id": business_id
                        }
                    )
                    
                    # 提取实体并构建业务关联
                    entities = self._extract_entities_and_build_relations(business_id, document)
                    document.metadata["entities"] = entities
                    
                    # 添加到处理后的文档列表
                    processed_documents.append(document)
                    
                    # 更新元数据
                    self.kb_metadata["businesses"][business_id]["documents"][doc_id] = {
                        "file_name": file_name,
                        "original_path": str(original_path),
                        "kb_path": kb_path,
                        "status": DOC_STATUS_ACTIVE,
                        "file_fingerprint": file_fingerprint,
                        "added_at": datetime.now().isoformat(),
                        "entities": entities
                    }
                    
                    # 添加到文档ID列表
                    doc_ids.append(doc_id)
                    
                except Exception as e:
                    logger.error(f"处理文档 '{file_path}' 失败: {str(e)}")
            
            # 保存元数据
            self._save_metadata()
            
            # 更新索引
            if processed_documents:
                self._update_index(business_id, processed_documents)
            
            return doc_ids
            
        except Exception as e:
            logger.error(f"添加文档到业务知识库失败: {str(e)}")
            raise
    
    # 添加跨业务查询方法
    async def query_with_cross_business(
        self, 
        business_id: str, 
        query: str, 
        expand_to_related: bool = True,
        max_related_businesses: int = 2,
        response_mode: str = "compact"
    ) -> Dict[str, Any]:
        """
        跨业务查询，可以查询相关业务的知识库
        
        Args:
            business_id: 主业务ID
            query: 查询文本
            expand_to_related: 是否扩展到相关业务
            max_related_businesses: 最大相关业务数量
            response_mode: 响应模式，可选值：compact（紧凑）、detailed（详细）
        
        Returns:
            查询结果
        """
        try:
            # 首先查询主业务
            main_result = await self.query_business_kb(
                business_id=business_id,
                query=query
            )
            
            # 如果不需要扩展到相关业务，直接返回主业务结果
            if not expand_to_related:
                return main_result
            
            # 获取相关业务
            related_businesses = self.relation_manager.get_related_businesses(business_id)
            if not related_businesses:
                return main_result
            
            # 限制相关业务数量
            related_businesses = related_businesses[:max_related_businesses]
            
            # 查询相关业务
            related_results = []
            for related_id in related_businesses:
                try:
                    # 确保相关业务存在
                    if related_id not in self.kb_metadata["businesses"]:
                        continue
                    
                    # 查询相关业务
                    related_result = await self.query_business_kb(
                        business_id=related_id,
                        query=query
                    )
                    
                    related_results.append({
                        "business_id": related_id,
                        "business_name": self.kb_metadata["businesses"][related_id].get("name", related_id),
                        "result": related_result
                    })
                except Exception as e:
                    logger.error(f"查询相关业务 '{related_id}' 失败: {str(e)}")
            
            # 如果没有相关业务结果，直接返回主业务结果
            if not related_results:
                return main_result
            
            # 合并结果
            if response_mode == "detailed":
                # 详细模式：返回主业务和相关业务的完整结果
                return {
                    "response": main_result["response"],
                    "source_nodes": main_result["source_nodes"],
                    "related_businesses": related_results
                }
            else:
                # 紧凑模式：合并所有业务的结果
                all_source_nodes = main_result["source_nodes"].copy()
                
                # 收集所有相关业务的源节点
                for related in related_results:
                    for node in related["result"]["source_nodes"]:
                        # 添加业务信息
                        node["business_id"] = related["business_id"]
                        node["business_name"] = related["business_name"]
                        all_source_nodes.append(node)
                
                # 按相关度排序
                all_source_nodes.sort(key=lambda x: x.get("score", 0), reverse=True)
                
                # 生成综合回答
                combined_response = main_result["response"]
                for related in related_results:
                    related_response = related["result"]["response"]
                    if related_response and related_response != main_result["response"]:
                        combined_response += f"\n\n此外，来自{related['business_name']}的信息：{related_response}"
                
                return {
                    "response": combined_response,
                    "source_nodes": all_source_nodes
                }
        except Exception as e:
            logger.error(f"跨业务查询失败: {str(e)}")
            return {
                "response": f"查询失败: {str(e)}",
                "source_nodes": []
            }
    
    def _build_response(self, query: str, nodes: List[Dict], response_mode: str) -> Dict[str, Any]:
        """
        构建查询响应
        
        Args:
            query: 查询文本
            nodes: 查询结果节点
            response_mode: 响应模式，可选值: compact, tree_summarize, refine
            
        Returns:
            构建的响应
        """
        if response_mode == "compact":
            return self._build_compact_response(query, nodes)
        elif response_mode == "tree_summarize":
            return self._build_tree_summarize_response(query, nodes)
        elif response_mode == "refine":
            return self._build_refine_response(query, nodes)
        else:
            raise ValueError(f"未知的响应模式: {response_mode}")

    def _build_compact_response(self, query: str, nodes: List[Dict]) -> Dict[str, Any]:
        """
        构建紧凑模式的响应
        
        Args:
            query: 查询文本
            nodes: 查询结果节点
            
        Returns:
            紧凑模式的响应
        """
        response_text = f"根据查询 '{query}'，找到以下相关信息:\n\n"
        for i, node in enumerate(nodes):
            response_text += f"{i+1}. {node['text'][:200]}...\n\n"
        return {
            "response": response_text,
            "source_nodes": nodes
        }

    def _build_tree_summarize_response(self, query: str, nodes: List[Dict]) -> Dict[str, Any]:
        """
        构建树状总结模式的响应
        
        Args:
            query: 查询文本
            nodes: 查询结果节点
            
        Returns:
            树状总结模式的响应
        """
        # 这里可以实现更复杂的树状总结逻辑
        # 为了简化，我们暂时使用紧凑模式的响应
        return self._build_compact_response(query, nodes)

    def _build_refine_response(self, query: str, nodes: List[Dict]) -> Dict[str, Any]:
        """
        构建细化模式的响应
        
        Args:
            query: 查询文本
            nodes: 查询结果节点
            
        Returns:
            细化模式的响应
        """
        # 这里可以实现更复杂的细化逻辑
        # 为了简化，我们暂时使用紧凑模式的响应
        return self._build_compact_response(query, nodes)
    
    def _load_metadata(self) -> Dict[str, Any]:
        """加载知识库元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # # 兼容旧版本元数据
                # if "businesses" not in metadata:
                #     metadata = {"businesses": metadata}
                
                # 确保每个文档都有状态字段
                for business_id, business_info in metadata["businesses"].items():
                    if "documents" in business_info:
                        for doc_id, doc_info in business_info["documents"].items():
                            if "status" not in doc_info:
                                doc_info["status"] = DOC_STATUS_ACTIVE
                
                return metadata
            except Exception as e:
                logger.error(f"加载元数据失败: {str(e)}")
                # 备份损坏的元数据文件
                self._backup_file(self.metadata_file)
                return {"businesses": {}}
        else:
            return {"businesses": {}}
    
    def _save_metadata(self):
        """保存知识库元数据"""
        with self.sync_lock:
            try:
                # 备份现有元数据
                if self.metadata_file.exists():
                    self._backup_file(self.metadata_file)
                
                # 保存新元数据
                with open(self.metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(self.kb_metadata, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"保存元数据失败: {str(e)}")
    
    def _backup_file(self, file_path: Path) -> Optional[Path]:
        """
        备份文件
        
        Args:
            file_path: 要备份的文件路径
            
        Returns:
            备份文件路径
        """
        try:
            # 如果是目录，使用shutil.copytree
            if file_path.is_dir():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.backup_dir / f"{file_path.name}_{timestamp}"
                shutil.copytree(file_path, backup_path)
                return backup_path
            
            # 如果是文件，使用shutil.copy2
            elif file_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.backup_dir / f"{file_path.name}_{timestamp}"
                shutil.copy2(file_path, backup_path)
                return backup_path
            
            return None
        except Exception as e:
            logger.error(f"备份文件失败: {str(e)}")
            return None
    
    def _calculate_file_fingerprint(self, file_path: str) -> str:
        """
        计算文件指纹
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件指纹
        """
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                # 读取文件的前10MB计算指纹，避免处理大文件时性能问题
                buf = f.read(10 * 1024 * 1024)
                hasher.update(buf)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"计算文件指纹失败: {str(e)}")
            return ""
    
    async def sync_all_businesses(self) -> Dict[str, Any]:
        """
        同步所有业务知识库
        
        Returns:
            同步结果
        """
        with self.sync_lock:
            logger.info("开始同步所有业务知识库...")
            
            result = {
                "total_businesses": len(self.kb_metadata["businesses"]),
                "synced_businesses": 0,
                "businesses": {}
            }
            
            for business_id in list(self.kb_metadata["businesses"].keys()):
                try:
                    # 直接await异步方法
                    business_result = await self.sync_business_kb(business_id)
                    result["businesses"][business_id] = business_result
                    
                    if business_result["status"] != SYNC_RESULT_ERROR:
                        result["synced_businesses"] += 1
                except Exception as e:
                    logger.error(f"同步业务 '{business_id}' 失败: {str(e)}")
                    result["businesses"][business_id] = {
                        "status": SYNC_RESULT_ERROR,
                        "message": f"同步失败: {str(e)}"
                    }
            
            logger.info(f"同步完成，共同步 {result['synced_businesses']}/{result['total_businesses']} 个业务")
            return result
    
    async def sync_business_kb(self, business_id: str) -> Dict[str, Any]:
        """
        同步业务知识库
        
        Args:
            business_id: 业务ID
        
        Returns:
            同步结果
        """
        with self.sync_lock:
            if business_id not in self.kb_metadata["businesses"]:
                return {
                    "status": SYNC_RESULT_ERROR,
                    "message": f"业务知识库 '{business_id}' 不存在"
                }
            
            logger.info(f"开始同步业务知识库 '{business_id}'...")
            
            # 初始化结果
            result = {
                "status": SYNC_RESULT_OK,
                "message": "",
                "file_validation": {},
                "fingerprint_validation": {},
                "vector_validation": {},
                "needs_rebuild": False
            }
            
            # 验证本地文件
            business_dir = self.base_dir / business_id
            documents_dir = business_dir / "documents"
            
            if not documents_dir.exists():
                documents_dir.mkdir(exist_ok=True, parents=True)
            
            # 验证本地文件与元数据是否一致
            result["file_validation"] = self._validate_local_files(business_id, documents_dir)
            
            # 验证文件指纹
            result["fingerprint_validation"] = self._validate_file_fingerprints(business_id)
            
            # 验证Milvus向量数据
            result["vector_validation"] = self._validate_milvus_vectors(business_id)
            
            # 判断是否需要重建索引
            needs_rebuild = False
            
            # 如果有文件缺失或内容变更，需要重建索引
            if result["file_validation"]["missing"] > 0 or result["fingerprint_validation"]["changed"] > 0:
                needs_rebuild = True
                result["message"] = "检测到文件变更，需要重建索引"
            
            # 如果Milvus集合不存在或状态异常，需要重建索引
            if result["vector_validation"]["status"] != SYNC_RESULT_OK:
                needs_rebuild = True
                if not result["message"]:
                    result["message"] = result["vector_validation"]["message"]
            
            result["needs_rebuild"] = needs_rebuild
            
            # 如果需要重建索引，执行重建
            if needs_rebuild:
                try:
                    logger.info(f"业务 '{business_id}' 需要重建索引")
                    rebuild_result = await self._rebuild_index(business_id)
                    result["status"] = SYNC_RESULT_OK
                    result["message"] += "，索引已重建"
                except Exception as e:
                    logger.error(f"重建索引失败: {str(e)}")
                    result["status"] = SYNC_RESULT_ERROR
                    result["message"] = f"重建索引失败: {str(e)}"
            
            # 保存元数据
            self._save_metadata()
            
            logger.info(f"业务 '{business_id}' 同步完成，状态: {result['status']}")
            return result
    
    def list_businesses(self) -> List[Dict[str, Any]]:
        """
        列出所有业务知识库
        
        Returns:
            业务知识库列表，每个元素包含业务ID、名称、文档数量等信息
        """
        result = []
        for business_id, info in self.kb_metadata["businesses"].items():
            # 计算活跃文档数量
            active_docs = 0
            if "documents" in info:
                for doc_info in info["documents"].values():
                    if doc_info.get("status") == DOC_STATUS_ACTIVE:
                        active_docs += 1
            
            result.append({
                "business_id": business_id,
                "name": info.get("name", business_id),
                "description": info.get("description", ""),
                "document_count": active_docs,
                "created_at": info.get("created_at", ""),
                "updated_at": info.get("updated_at", "")
            })
        return result
    
    def create_business_kb(
        self,
        business_id: str,
        name: Optional[str] = None,
        description: str = ""
    ) -> bool:
        """
        创建业务知识库
        
        Args:
            business_id: 业务ID，用作知识库唯一标识
            name: 业务名称，如果为None则使用business_id
            description: 业务描述
            
        Returns:
            创建是否成功
        """
        with self.sync_lock:
            # 检查业务ID是否已存在
            if business_id in self.kb_metadata["businesses"]:
                logger.warning(f"业务知识库 '{business_id}' 已存在")
                return False
            
            # 创建业务目录
            business_dir = self.base_dir / business_id
            business_dir.mkdir(exist_ok=True, parents=True)
            
            # 创建子目录
            (business_dir / "documents").mkdir(exist_ok=True)
            (business_dir / "index").mkdir(exist_ok=True)
            
            # 更新元数据
            now = datetime.now().isoformat()
            self.kb_metadata["businesses"][business_id] = {
                "name": name or business_id,
                "description": description,
                "created_at": now,
                "updated_at": now,
                "documents": {}
            }
            self._save_metadata()
            
            logger.info(f"业务知识库 '{business_id}' 创建成功")
            return True
    
    def delete_business_kb(self, business_id: str) -> bool:
        """
        删除业务知识库
        
        Args:
            business_id: 业务ID
            
        Returns:
            删除是否成功
        """
        with self.sync_lock:
            if business_id not in self.kb_metadata["businesses"]:
                logger.warning(f"业务知识库 '{business_id}' 不存在")
                return False
            
            # 删除业务目录
            business_dir = self.base_dir / business_id
            if business_dir.exists():
                # 备份后删除
                self._backup_file(business_dir)
                shutil.rmtree(business_dir)
            
            # 删除Milvus集合
            collection_name = f"business_{business_id}"
            try:
                from pymilvus import MilvusClient
                client = MilvusClient(uri=self.milvus_uri)
                collections = client.list_collections()
                if collection_name in collections:
                    client.drop_collection(collection_name)
                    logger.info(f"已删除Milvus集合: {collection_name}")
            except Exception as e:
                logger.warning(f"删除Milvus集合失败: {str(e)}")
            
            # 更新元数据
            del self.kb_metadata["businesses"][business_id]
            self._save_metadata()
            
            logger.info(f"业务知识库 '{business_id}' 删除成功")
            return True
    
    async def add_documents_to_kb(
        self,
        business_id: str,
        file_paths: List[str]
    ) -> List[str]:
        """
        添加文档到业务知识库
        
        Args:
            business_id: 业务ID
            file_paths: 文档路径列表
            
        Returns:
            添加的文档ID列表
        """
        if business_id not in self.kb_metadata["businesses"]:
            logger.error(f"业务知识库 '{business_id}' 不存在")
            return []
        
        business_dir = self.base_dir / business_id
        documents_dir = business_dir / "documents"
        
        # 处理每个文档
        document_ids = []
        processed_documents = []
        
        for file_path in file_paths:
            try:
                # 生成文档ID
                doc_id = str(uuid.uuid4())
                document_ids.append(doc_id)
                
                # 复制文档到知识库目录
                file_name = os.path.basename(file_path)
                doc_path = documents_dir / f"{doc_id}_{file_name}"
                shutil.copy2(file_path, doc_path)
                
                # 计算文件指纹
                file_fingerprint = self._calculate_file_fingerprint(str(doc_path))
                
                # 处理文档内容
                doc_content = await self._process_document(file_path)
                
                # 创建LlamaIndex文档对象
                metadata = {
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "original_path": file_path,
                    "business_id": business_id,
                    "added_at": datetime.now().isoformat()
                }
                
                processed_doc = Document(text=doc_content, metadata=metadata)
                processed_documents.append(processed_doc)
                
                # 更新元数据
                with self.sync_lock:
                    self.kb_metadata["businesses"][business_id]["documents"][doc_id] = {
                        "file_name": file_name,
                        "original_path": file_path,
                        "kb_path": str(doc_path),
                        "added_at": metadata["added_at"],
                        "file_fingerprint": file_fingerprint,
                        "status": DOC_STATUS_ACTIVE
                    }
                
                logger.info(f"文档 '{file_name}' 添加到业务 '{business_id}' 成功，文档ID: {doc_id}")
                
            except Exception as e:
                logger.error(f"处理文档 '{file_path}' 失败: {str(e)}")
        
        if processed_documents:
            # 更新知识库索引
            self._update_index(business_id, processed_documents)
            
            # 更新元数据
            self.kb_metadata["businesses"][business_id]["updated_at"] = datetime.now().isoformat()
            self._save_metadata()
        
        return document_ids
    
    async def _process_document(self, file_path: str) -> str:
        """
        处理文档，提取文本内容
        
        Args:
            file_path: 文档路径
            
        Returns:
            处理后的文档内容
        """
        try:
            logger.info(f"开始处理文档: {file_path}")
            
            # 获取文件扩展名
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # 如果是文本文件，直接读取
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                return content
            
            # 使用docling处理文档
            try:
                # 转换文档
                result = self.doc_converter.convert(file_path)
                
                # 始终处理图片（如果图像处理器可用）
                if self.image_processor and result.document.images:
                    logger.info(f"文档包含 {len(result.document.images)} 张图片，开始处理...")
                    
                    # 处理图片
                    image_descriptions = await self.image_processor.process_document_images(result.document)
                    
                    # 将图片描述添加到文档中
                    markdown_content = result.document.export_to_markdown()
                    for image_id, description in image_descriptions.items():
                        # 在Markdown中查找图片标记
                        image_marker = f"![{image_id}]"
                        if image_marker in markdown_content:
                            # 在图片下方添加描述
                            markdown_content = markdown_content.replace(
                                image_marker,
                                f"{image_marker}\n\n图片描述: {description}\n"
                            )
                    
                    return markdown_content
                else:
                    # 导出为Markdown格式
                    return result.document.export_to_markdown()
            
            except Exception as e:
                logger.error(f"使用docling处理文档失败: {str(e)}")
                
                # 尝试使用LlamaIndex的SimpleDirectoryReader
                reader = SimpleDirectoryReader(input_files=[file_path])
                docs = reader.load_data()
                if docs:
                    return docs[0].text
                else:
                    raise ValueError(f"无法提取文档内容: {file_path}")
        
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            return f"文档处理失败: {str(e)}"
    
    def _update_index(self, business_id: str, documents: List[Document]):
        """
        更新业务知识库索引
        
        Args:
            business_id: 业务ID
            documents: 文档列表
        """
        try:
            # 创建节点解析器
            node_parser = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            
            # 将文档分割为节点
            logger.info(f"将 {len(documents)} 个文档分割为节点")
            nodes = node_parser.get_nodes_from_documents(documents)
            logger.info(f"生成了 {len(nodes)} 个节点")
            
            # 获取嵌入维度 - 先生成一个示例嵌入以确定实际维度
            sample_text = "这是一个测试文本，用于确定嵌入维度"
            sample_embedding = self.embedding_model.get_text_embedding(sample_text)
            actual_dim = len(sample_embedding)
            logger.info(f"检测到嵌入维度: {actual_dim}")
            
            # 创建向量存储
            collection_name = f"business_{business_id}"
            
            # 确保所有节点都有嵌入向量
            for node in nodes:
                if not hasattr(node, 'embedding') or node.embedding is None:
                    node_text = node.get_content()
                    node.embedding = self.embedding_model.get_text_embedding(node_text)
            
            # 使用MilvusClient而不是pymilvus直接操作
            from pymilvus import MilvusClient

            # 确保连接已建立
            client = MilvusClient(uri=self.milvus_uri)
            logger.info(f"已连接到Milvus服务: {self.milvus_uri}")
            
            # 获取所有集合
            collections = client.list_collections()
            logger.info(f"Milvus中的集合列表: {collections}")
            
            # 检查集合是否存在
            if collection_name in collections:
                client.drop_collection(collection_name)
                logger.info(f"删除现有集合: {collection_name}")
            
            # 创建集合 - 注意：MilvusClient自动创建的ID字段是int64类型
            # 创建集合时会自动为向量字段创建索引，不需要再次创建
            client.create_collection(
                collection_name=collection_name,
                dimension=actual_dim,
                primary_field_name="pk_id",  # 使用自定义主键名称
                vector_field_name="vector",  # 使用自定义向量字段名称
                auto_id=False  # 不自动生成ID
            )
            logger.info(f"创建新集合: {collection_name}")
            
            # 准备数据
            entities = []
            
            for i, node in enumerate(nodes):
                # 使用数字ID而不是字符串
                node_id = i + 1
                node_text = node.get_content()
                node_embedding = node.embedding
                
                entities.append({
                    "pk_id": node_id,  # 使用数字ID
                    "vector": node_embedding,
                    "text": node_text
                })
            
            # 插入数据
            if entities:  # 只有在有数据时才插入
                logger.info(f"使用 {len(entities)} 个节点创建索引")
                insert_result = client.insert(
                    collection_name=collection_name,
                    data=entities
                )
                logger.info(f"插入结果: {insert_result}")
                
                # 不需要再次创建索引，因为创建集合时已经自动创建了
                # 只需要加载集合以便搜索
                client.load_collection(collection_name)
                logger.info(f"已加载集合: {collection_name}")
                
                # 验证数据是否插入成功 - 使用正确的方法获取集合中的实体数量
                count = client.get_collection_stats(collection_name)["row_count"]
                logger.info(f"索引创建后集合 {collection_name} 中的实体数量: {count}")
                
                # 查询测试
                if len(entities) > 0:
                    search_result = client.search(
                        collection_name=collection_name,
                        data=[entities[0]["vector"]],
                        limit=1,
                        output_fields=["text"]
                    )
                    logger.info(f"搜索测试结果: {search_result}")
            
            # 持久化索引
            index_dir = self.base_dir / business_id / "index"
            logger.info(f"索引目录路径: {index_dir}")
            
            # 确保索引目录存在
            index_dir.mkdir(exist_ok=True, parents=True)
            
            # 创建一个简单的索引配置文件，记录Milvus集合信息
            index_config = {
                "collection_name": collection_name,
                "uri": self.milvus_uri,
                "dim": actual_dim,
                "created_at": datetime.now().isoformat(),
                "node_count": len(nodes),
                "primary_field": "pk_id",
                "vector_field": "vector"
            }
            
            with open(index_dir / "milvus_config.json", "w", encoding="utf-8") as f:
                json.dump(index_config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"业务 '{business_id}' 的索引创建成功")
        
        except Exception as e:
            logger.error(f"更新索引失败: {str(e)}", exc_info=True)
            raise
    
    async def remove_document_from_kb(self, business_id: str, doc_id: str) -> bool:
        """
        从知识库中删除文档
        
        Args:
            business_id: 业务ID
            doc_id: 文档ID
            
        Returns:
            删除是否成功
        """
        if business_id not in self.kb_metadata["businesses"]:
            logger.error(f"业务知识库 '{business_id}' 不存在")
            return False
        
        business_info = self.kb_metadata["businesses"][business_id]
        if doc_id not in business_info["documents"]:
            logger.error(f"文档ID '{doc_id}' 在业务 '{business_id}' 中不存在")
            return False
        
        try:
            # 删除文档文件
            doc_info = business_info["documents"][doc_id]
            doc_path = Path(doc_info["kb_path"])
            if doc_path.exists():
                doc_path.unlink()
            
            # 从元数据中删除文档信息
            del business_info["documents"][doc_id]
            business_info["updated_at"] = datetime.now().isoformat()
            self._save_metadata()
            
            # 重建索引
            await self._rebuild_index(business_id)
            
            logger.info(f"文档 '{doc_id}' 从业务 '{business_id}' 中删除成功")
            return True
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return False
    
    async def _rebuild_index(self, business_id: str) -> bool:
        """
        重建业务知识库索引
        
        Args:
            business_id: 业务ID
        
        Returns:
            是否成功
        """
        try:
            logger.info(f"开始重建业务 '{business_id}' 的索引")
            
            # 获取业务目录
            business_dir = self.base_dir / business_id
            if not business_dir.exists():
                logger.error(f"业务目录不存在: {business_dir}")
                return False
            
            # 获取文档目录
            docs_dir = business_dir / "documents"
            if not docs_dir.exists():
                logger.error(f"文档目录不存在: {docs_dir}")
                return False
            
            # 查找所有活跃文档
            active_docs = []
            for doc_id, doc_info in self.kb_metadata["businesses"][business_id]["documents"].items():
                if doc_info.get("status") != "deleted":
                    doc_path = docs_dir / f"{doc_id}_{doc_info['file_name']}"
                    if doc_path.exists():
                        active_docs.append(doc_path)
            
            logger.info(f"找到 {len(active_docs)} 个活跃文档")
            if not active_docs:
                logger.warning(f"业务 '{business_id}' 没有活跃文档，无法重建索引")
                return False
            
            
            # 创建文档处理器
            processor = DocumentProcessorFactory.create_processor("text")
            
            # 处理文档
            nodes = []
            for doc_path in active_docs:
                try:
                    doc_nodes = processor.process_document(str(doc_path))
                    nodes.extend(doc_nodes)
                except Exception as e:
                    logger.error(f"处理文档 '{doc_path}' 失败: {str(e)}")
            
            # 创建索引
            if nodes:
                return self._create_index(business_id, nodes)
            else:
                logger.error(f"没有从文档中提取到节点，无法创建索引")
                return False
        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            return False
    
    async def query_business_kb(
        self,
        business_id: str,
        query: str
    ) -> Dict[str, Any]:
        """
        查询业务知识库
        
        Args:
            business_id: 业务ID
            query: 查询文本
        
        Returns:
            查询结果，包含回答和相关文档节点
        """
        try:
            # 固定参数
            similarity_top_k = 3
            response_mode = "compact"
            
            # 检查业务是否存在
            if business_id not in self.kb_metadata["businesses"]:
                raise ValueError(f"业务 '{business_id}' 不存在")
            
            # 获取业务索引目录
            index_dir = self.base_dir / business_id / "index"
            logger.info(f"索引目录路径: {index_dir}")
            logger.info(f"索引目录是否存在: {index_dir.exists()}")
            
            # 检查索引目录中的文件
            if index_dir.exists():
                files = list(index_dir.glob("*"))
                logger.info(f"索引目录中的文件数量: {len(files)}")
                for file in files:
                    logger.info(f"索引文件: {file.name}, 大小: {file.stat().st_size} 字节")
            
            # 检查Milvus配置文件是否存在
            milvus_config_file = index_dir / "milvus_config.json"
            if not milvus_config_file.exists():
                logger.warning(f"Milvus配置文件不存在，需要重建索引")
                await self._rebuild_index(business_id)
                
                # 重新检查配置文件
                if not milvus_config_file.exists():
                    raise ValueError(f"重建索引后Milvus配置文件仍然不存在")
            
            # 读取Milvus配置
            with open(milvus_config_file, "r", encoding="utf-8") as f:
                milvus_config = json.load(f)
            
            collection_name = milvus_config["collection_name"]
            vector_field = milvus_config.get("vector_field", "vector")
            logger.info(f"使用集合名称: {collection_name}")
            
            # 使用MilvusClient
            from pymilvus import MilvusClient
            
            # 创建客户端
            client = MilvusClient(uri=self.milvus_uri)
            logger.info(f"已连接到Milvus服务: {self.milvus_uri}")
            
            # 获取所有集合
            collections = client.list_collections()
            logger.info(f"Milvus中的集合列表: {collections}")
            logger.info(f"集合 {collection_name} 是否存在: {collection_name in collections}")
            
            # 检查集合是否存在
            if collection_name not in collections:
                logger.warning(f"集合 {collection_name} 不存在，需要重建索引")
                await self._rebuild_index(business_id)
                
                # 重新检查集合
                collections = client.list_collections()
                if collection_name not in collections:
                    raise ValueError(f"重建索引后集合 {collection_name} 仍然不存在")
            
            # 检查集合中的数据量
            count = client.get_collection_stats(collection_name)["row_count"]
            logger.info(f"集合 {collection_name} 中的实体数量: {count}")
            
            # 如果集合中没有数据，重建索引
            if count == 0:
                # 检查业务中是否有活跃文档
                active_docs = self._get_active_documents(business_id)
                if not active_docs:
                    return {
                        "response": f"业务 '{business_id}' 中没有活跃文档，无法进行查询。",
                        "source_nodes": []
                    }
                
                logger.warning(f"集合 {collection_name} 中没有数据，需要重建索引")
                await self._rebuild_index(business_id)
                
                # 重新检查集合中的数据量
                count = client.get_collection_stats(collection_name)["row_count"]
                logger.info(f"重建索引后集合 {collection_name} 中的实体数量: {count}")
                
                if count == 0:
                    # 如果仍然没有数据，但我们确定有活跃文档，则使用备用方法
                    return await self._fallback_query(business_id, query, similarity_top_k)
            
            # 生成查询嵌入
            query_embedding = self.embedding_model.get_text_embedding(query)
            
            # 执行向量搜索
            search_results = client.search(
                collection_name=collection_name,
                data=[query_embedding],
                field_name=vector_field,  # 使用配置中的向量字段名称
                limit=similarity_top_k,
                output_fields=["text"]
            )
            
            # 处理搜索结果
            source_nodes = []
            if search_results and len(search_results) > 0:
                for hit in search_results[0]:
                    source_nodes.append({
                        "text": hit.get("entity", {}).get("text", ""),
                        "score": hit.get("distance", 0),
                        "id": hit.get("id", "")
                    })
            
            # 构建响应
            response_text = ""
            if source_nodes:
                # 根据响应模式生成回答
                if response_mode == "compact":
                    # 简单拼接相关文本
                    response_text = f"根据查询 '{query}'，找到以下相关信息:\n\n"
                    for i, node in enumerate(source_nodes):
                        response_text += f"{i+1}. {node['text']}\n\n"
                else:
                    # 使用LLM生成回答（这里需要集成LLM，暂时使用简单拼接）
                    response_text = f"根据查询 '{query}'，找到以下相关信息:\n\n"
                    for i, node in enumerate(source_nodes):
                        response_text += f"{i+1}. {node['text']}\n\n"
            else:
                response_text = f"未找到与查询 '{query}' 相关的信息。"
            
            return {
                "response": response_text,
                "source_nodes": source_nodes
            }
            
        except Exception as e:
            logger.error(f"查询业务知识库失败: {str(e)}", exc_info=True)
            raise

    async def _fallback_query(self, business_id: str, query: str, similarity_top_k: int = 3) -> Dict[str, Any]:
        """
        备用查询方法，当Milvus查询失败时使用
        
        Args:
            business_id: 业务ID
            query: 查询文本
            similarity_top_k: 返回的相似度最高的结果数量
        
        Returns:
            查询结果
        """
        try:
            # 使用本地导入而不是相对导入
            try:
                # 尝试直接导入
                from document_processor_factory import DocumentProcessorFactory
            except ImportError:
                # 如果直接导入失败，尝试从当前目录导入
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from document_processor_factory import DocumentProcessorFactory
            
            # 获取业务目录
            business_dir = self.base_dir / business_id
            docs_dir = business_dir / "documents"
            
            # 查找所有活跃文档
            active_docs = []
            for doc_id, doc_info in self.kb_metadata["businesses"][business_id]["documents"].items():
                if doc_info.get("status") != "deleted":
                    doc_path = docs_dir / f"{doc_id}_{doc_info['file_name']}"
                    if doc_path.exists():
                        active_docs.append((doc_id, doc_path, doc_info))
            
            if not active_docs:
                return {
                    "response": "没有找到相关信息。",
                    "source_nodes": []
                }
            
            # 创建文档处理器
            processor = DocumentProcessorFactory.create_processor("text")
            
            # 处理文档
            all_nodes = []
            for doc_id, doc_path, doc_info in active_docs:
                try:
                    doc_nodes = processor.process_document(str(doc_path))
                    for node in doc_nodes:
                        node.metadata["doc_id"] = doc_id
                        node.metadata["file_name"] = doc_info["file_name"]
                    all_nodes.extend(doc_nodes)
                except Exception as e:
                    logger.error(f"处理文档 '{doc_path}' 失败: {str(e)}")
            
            if not all_nodes:
                return {
                    "response": "处理文档时出错，无法提供回答。",
                    "source_nodes": []
                }
            
            # 计算查询嵌入
            query_embedding = self.embedding_model.get_text_embedding(query)
            
            # 计算所有节点的嵌入
            node_embeddings = []
            for node in all_nodes:
                node_embedding = self.embedding_model.get_text_embedding(node.text)
                node_embeddings.append(node_embedding)
            
            # 计算相似度
            similarities = []
            for i, node_embedding in enumerate(node_embeddings):
                similarity = self._cosine_similarity(query_embedding, node_embedding)
                similarities.append((i, similarity))
            
            # 排序并获取前K个结果
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_k_indices = [idx for idx, _ in similarities[:similarity_top_k]]
            
            # 获取相关节点
            source_nodes = []
            for idx in top_k_indices:
                node = all_nodes[idx]
                source_nodes.append({
                    "text": node.text,
                    "doc_id": node.metadata.get("doc_id", ""),
                    "file_name": node.metadata.get("file_name", ""),
                    "score": similarities[idx][1]
                })
            
            # 生成回答
            response = "根据相关文档，"
            if source_nodes:
                response += source_nodes[0]["text"]
            else:
                response += "没有找到相关信息。"
            
            return {
                "response": response,
                "source_nodes": source_nodes
            }
        except Exception as e:
            logger.error(f"备用查询失败: {str(e)}")
            return {
                "response": f"查询失败: {str(e)}",
                "source_nodes": []
            }

    def _cosine_similarity(self, vec1, vec2):
        """计算两个向量的余弦相似度"""
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def get_business_info(self, business_id: str) -> Dict[str, Any]:
        """
        获取业务知识库信息
        
        Args:
            business_id: 业务ID
            
        Returns:
            业务知识库信息
        """
        if business_id not in self.kb_metadata["businesses"]:
            return {"error": f"业务知识库 '{business_id}' 不存在"}
        
        business_info = self.kb_metadata["businesses"][business_id]
        
        # 统计文档数量
        doc_count = 0
        for doc_info in business_info.get("documents", {}).values():
            if doc_info.get("status") == DOC_STATUS_ACTIVE:
                doc_count += 1
        
        # 获取文档列表
        documents = []
        for doc_id, doc_info in business_info.get("documents", {}).items():
            # 只返回活跃状态的文档
            if doc_info.get("status") == DOC_STATUS_ACTIVE:
                documents.append({
                    "doc_id": doc_id,
                    "file_name": doc_info.get("file_name", ""),
                    "original_path": doc_info.get("original_path", ""),
                    "added_at": doc_info.get("added_at", "")
                })
        
        return {
            "business_id": business_id,
            "name": business_info.get("name", business_id),
            "description": business_info.get("description", ""),
            "created_at": business_info.get("created_at", ""),
            "updated_at": business_info.get("updated_at", ""),
            "document_count": doc_count,
            "documents": documents
        }
    
    def _get_active_documents(self, business_id: str) -> Dict[str, Dict[str, Any]]:
        """
        获取业务中的活跃文档
        
        Args:
            business_id: 业务ID
        
        Returns:
            活跃文档字典，键为文档ID，值为文档信息
        """
        if business_id not in self.kb_metadata["businesses"]:
            return {}
        
        active_docs = {}
        for doc_id, doc_info in self.kb_metadata["businesses"][business_id]["documents"].items():
            if doc_info.get("status") == DOC_STATUS_ACTIVE:
                active_docs[doc_id] = doc_info
        
        return active_docs
    
    def _validate_local_files(self, business_id: str, documents_dir: Path) -> Dict[str, Any]:
        """
        验证本地文件与元数据是否一致
        
        Args:
            business_id: 业务ID
            documents_dir: 文档目录
            
        Returns:
            验证结果
        """
        result = {
            "total": 0,
            "missing": 0,
            "extra": 0,
            "valid": 0
        }
        
        # 获取元数据中的文档信息
        business_info = self.kb_metadata["businesses"][business_id]
        metadata_docs = business_info.get("documents", {})
        result["total"] = len(metadata_docs)
        
        # 检查元数据中的文档是否存在于本地
        for doc_id, doc_info in metadata_docs.items():
            doc_path = Path(doc_info["kb_path"])
            if not doc_path.exists():
                result["missing"] += 1
                # 标记文档状态为已删除
                doc_info["status"] = DOC_STATUS_DELETED
                logger.warning(f"文档 '{doc_id}' 在本地不存在，已标记为已删除")
            else:
                # 确保文档状态为活跃
                if doc_info.get("status") != DOC_STATUS_ACTIVE:
                    doc_info["status"] = DOC_STATUS_ACTIVE
                result["valid"] += 1
        
        # 检查本地文件是否存在于元数据中
        local_files = list(documents_dir.glob("*"))
        for file_path in local_files:
            # 检查文件是否在元数据中
            file_in_metadata = False
            for doc_info in metadata_docs.values():
                if Path(doc_info["kb_path"]) == file_path:
                    file_in_metadata = True
                    break
            
            if not file_in_metadata:
                result["extra"] += 1
                logger.warning(f"本地文件 '{file_path}' 不在元数据中")
        
        return result
    
    def _validate_file_fingerprints(self, business_id: str) -> Dict[str, Any]:
        """
        验证文件指纹
        
        Args:
            business_id: 业务ID
            
        Returns:
            验证结果
        """
        result = {
            "total": 0,
            "changed": 0,
            "unchanged": 0,
            "missing": 0
        }
        
        # 获取元数据中的文档信息
        business_info = self.kb_metadata["businesses"][business_id]
        metadata_docs = business_info.get("documents", {})
        result["total"] = len(metadata_docs)
        
        # 检查每个文档的指纹
        for doc_id, doc_info in metadata_docs.items():
            # 跳过已删除的文档
            if doc_info.get("status") != DOC_STATUS_ACTIVE:
                result["missing"] += 1
                continue
                
            doc_path = Path(doc_info["kb_path"])
            if not doc_path.exists():
                result["missing"] += 1
                continue
            
            # 获取存储的指纹
            stored_fingerprint = doc_info.get("file_fingerprint", "")
            
            # 计算当前指纹
            current_fingerprint = self._calculate_file_fingerprint(str(doc_path))
            
            # 比较指纹
            if stored_fingerprint and current_fingerprint and stored_fingerprint != current_fingerprint:
                result["changed"] += 1
                # 标记文档需要重新处理
                doc_info["needs_reprocessing"] = True
                doc_info["file_fingerprint"] = current_fingerprint
                logger.warning(f"文档 '{doc_id}' 内容已变更，需要重新处理")
            else:
                result["unchanged"] += 1
                # 确保文档不需要重新处理
                doc_info.pop("needs_reprocessing", None)
        
        return result
    
    def _validate_milvus_vectors(self, business_id: str) -> Dict[str, Any]:
        """
        验证Milvus向量数据
        
        Args:
            business_id: 业务ID
        
        Returns:
            验证结果
        """
        result = {
            "status": SYNC_RESULT_OK,
            "message": "",
            "collection_exists": False,
            "entity_count": 0
        }
        
        collection_name = f"business_{business_id}"
        
        try:
            from pymilvus import MilvusClient
            client = MilvusClient(uri=self.milvus_uri)
            
            # 检查集合是否存在
            collections = client.list_collections()
            if collection_name not in collections:
                result["status"] = SYNC_RESULT_WARNING
                result["message"] = f"Milvus集合 '{collection_name}' 不存在"
                return result
            
            result["collection_exists"] = True
            
            # 获取集合统计信息
            stats = client.get_collection_stats(collection_name)
            entity_count = stats.get("row_count", 0)
            result["entity_count"] = entity_count
            
            # 检查集合是否为空
            if entity_count == 0:
                result["status"] = SYNC_RESULT_WARNING
                result["message"] = f"Milvus集合 '{collection_name}' 为空"
            
            return result
        
        except Exception as e:
            logger.error(f"验证Milvus向量数据失败: {str(e)}")
            result["status"] = SYNC_RESULT_ERROR
            result["message"] = f"验证Milvus向量数据失败: {str(e)}"
            return result


# 导入必要的库
import logging
from llama_index.core import (
    SimpleDirectoryReader,
    Document,
    VectorStoreIndex,
    Settings,
    load_index_from_storage,
    StorageContext
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BusinessKB")


# 测试代码
async def test_business_kb():
    """测试业务知识库功能"""
    print("=== 业务知识库测试 ===")
    
    # 获取脚本所在目录的绝对路径
    script_dir = Path(__file__).parent.absolute()
    
    # 创建知识库管理器，使用脚本目录下的test_business_kb目录
    kb_manager = BusinessKnowledgeBaseManager(
        milvus_uri="http://10.193.200.230:19530"  # 使用本地Docker部署的Milvus
    )
    
    # 测试创建业务知识库
    business_id = "test_business"
    
    # 如果业务已存在，先删除
    if business_id in kb_manager.kb_metadata["businesses"]:
        print(f"删除已存在的业务 '{business_id}'")
        kb_manager.delete_business_kb(business_id)
    
    print(f"\n1. 创建业务知识库 '{business_id}'")
    success = kb_manager.create_business_kb(
        business_id=business_id,
        name="测试业务",
        description="这是一个测试业务知识库"
    )
    print(f"创建结果: {'成功' if success else '失败'}")
    
    # 测试添加文档
    print("\n2. 添加文档到业务知识库")
    # 替换为实际的文档路径
    test_docs = [
        script_dir / "test_docs/sample1.pdf",
        script_dir / "test_docs/sample2.docx",
        script_dir / "test_docs/sample3.txt"
    ]
    
    # 检查测试文档是否存在
    existing_docs = []
    for doc in test_docs:
        if doc.exists():
            existing_docs.append(str(doc))
        else:
            print(f"警告: 测试文档 '{doc}' 不存在")
    
    if existing_docs:
        doc_ids = await kb_manager.add_documents_to_kb(
            business_id=business_id,
            file_paths=existing_docs
        )
        print(f"添加了 {len(doc_ids)} 个文档，文档ID: {doc_ids}")
    else:
        print("没有可用的测试文档")
        # 创建一个简单的测试文档
        test_doc = script_dir / "test_sample.txt"
        with open(test_doc, "w", encoding="utf-8") as f:
            f.write("这是一个测试文档，用于测试业务知识库功能。\n")
            f.write("业务知识库可以按业务分类管理文档，支持添加、删除和查询功能。\n")
            f.write("每个业务知识库都是基于LlamaIndex和向量数据库实现的。\n")
        
        doc_ids = await kb_manager.add_documents_to_kb(
            business_id=business_id,
            file_paths=[str(test_doc)]
        )
        print(f"创建并添加了测试文档，文档ID: {doc_ids}")
    
    # 测试查询
    if doc_ids:
        print("\n3. 查询业务知识库")
        query = "业务知识库的主要功能是什么?"
        result = await kb_manager.query_business_kb(
            business_id=business_id,
            query=query
        )
        
        print(f"查询: {query}")
        print(f"回答: {result['response']}")
        print("\n相关文本片段:")
        for i, node in enumerate(result["source_nodes"]):
            print(f"片段 {i+1} (相关度: {node.get('score', 0):.4f}):")
            print(f"文档: {node.get('file_name', 'unknown')}")
            print(f"内容: {node.get('text', '')[:200]}...\n")
        
        # 测试删除文档
        if doc_ids:
            print("\n4. 删除文档")
            doc_id_to_delete = doc_ids[0]
            success = await kb_manager.remove_document_from_kb(
                business_id=business_id,
                doc_id=doc_id_to_delete
            )
            print(f"删除文档 '{doc_id_to_delete}' 结果: {'成功' if success else '失败'}")
        
        # 测试获取业务信息
        print("\n5. 获取业务信息")
        business_info = kb_manager.get_business_info(business_id)
        print(f"业务名称: {business_info.get('name', '')}")
        print(f"业务描述: {business_info.get('description', '')}")
        print(f"文档数量: {business_info.get('document_count', 0)}")
        print(f"文档列表:")
        for doc in business_info.get("documents", []):
            print(f"  - {doc.get('file_name', '')} (ID: {doc.get('doc_id', '')})")
    
    # 测试删除业务知识库
    print("\n6. 删除业务知识库")
    success = kb_manager.delete_business_kb(business_id)
    print(f"删除业务知识库 '{business_id}' 结果: {'成功' if success else '失败'}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_business_kb())










































































