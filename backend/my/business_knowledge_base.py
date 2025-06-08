"""
业务知识库管理系统

本模块实现基于LlamaIndex和向量数据库的业务知识库管理功能，包括：
1. 创建和管理不同业务领域的知识库
2. 添加文档到指定业务知识库
3. 从知识库中删除指定文档
4. 基于知识库进行查询和分析

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
```
"""

import os
import json
import uuid
import shutil
import asyncio
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

# 日志相关导入
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BusinessKnowledgeBaseManager:
    """
    业务知识库管理器
    
    该类提供了创建、管理和查询不同业务领域知识库的功能。
    每个业务知识库都是基于LlamaIndex和Milvus向量数据库实现的。
    """
    
    def __init__(
        self,
        base_dir: str = None,
        embedding_model_name: str = "BAAI/bge-small-zh-v1.5",
        milvus_uri: str = "http://localhost:19530",  # 默认使用本地Docker部署的Milvus
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """
        初始化业务知识库管理器
        
        Args:
            base_dir: 知识库基础目录
            embedding_model_name: 嵌入模型名称
            milvus_uri: Milvus服务URI，默认使用本地Docker部署的Milvus
            chunk_size: 文档分块大小
            chunk_overlap: 文档分块重叠大小
        """
        # 获取脚本所在目录的绝对路径
        script_dir = Path(__file__).parent.absolute()
        
        # 如果没有提供base_dir，则使用脚本所在目录下的business_knowledge_base目录
        if base_dir is None:
            self.base_dir = script_dir / "business_knowledge_base"
        else:
            # 如果提供的是相对路径，则相对于脚本目录
            base_path = Path(base_dir)
            if not base_path.is_absolute():
                self.base_dir = script_dir / base_path
            else:
                self.base_dir = base_path
        
        self.base_dir.mkdir(exist_ok=True, parents=True)
        
        # 设置Milvus URI
        self.milvus_uri = milvus_uri
        logger.info(f"连接到Milvus服务: {self.milvus_uri}")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 设置嵌入模型
        self.embedding_model_name = embedding_model_name
        self.embedding_model = HuggingFaceEmbedding(model_name=embedding_model_name)
        Settings.embed_model = self.embedding_model
        
        # 文档转换器
        self.doc_converter = DocumentConverter()
        
        # 多模态处理器
        self.image_processor = self._setup_image_processor()
        
        # 业务知识库元数据
        self.metadata_file = self.base_dir / "kb_metadata.json"
        self.kb_metadata = self._load_metadata()
        
        logger.info(f"业务知识库管理器初始化完成，基础目录: {self.base_dir}")
    
    def _setup_image_processor(self) -> Optional[DocumentImageProcessor]:
        """设置图像处理器"""
        try:
            # 这里可以从环境变量或配置文件中读取API密钥
            api_keys = [
                "sk-FefbDs44DxjdtEeQMBpWDe1WZtAFHsle55dSnTUuGv50uUXx",
                "sk-dVPXuV51GCEMFOOnOqQeZotbfZEZjjfxkoeFSXgpGFgjGySg",
                "sk-u0hQz4udGiB92w8MrOQPra0ygcknMMcMxNZbVA3c8TjHVA1n",
                "sk-6rcTKDTON9y0FVM4Dy6eHQHFAqdIyJaD5X8ZgrUNzYP8z0zC",
                "sk-dYB0ZVpD7mstEcvbR97jwuKqAEgZEsvY45qR8cPVruoX7XA1"
            ]
            
            # 使用基础目录下的temp_images目录作为临时目录
            temp_images_dir = str(self.base_dir / "temp_images")
            
            return DocumentImageProcessor(
                api_keys=api_keys,
                api_base="https://api.moonshot.cn/v1",
                multimodal_model="moonshot-v1-32k-vision-preview",
                max_concurrent_requests=1,
                temp_dir=temp_images_dir
            )
        except Exception as e:
            logger.warning(f"图像处理器初始化失败: {str(e)}")
            return None
    
    def _load_metadata(self) -> Dict[str, Any]:
        """加载知识库元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载元数据失败: {str(e)}")
                return {"businesses": {}}
        else:
            return {"businesses": {}}
    
    def _save_metadata(self):
        """保存知识库元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.kb_metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存元数据失败: {str(e)}")
    
    def list_businesses(self) -> List[Dict[str, Any]]:
        """
        列出所有业务知识库
        
        Returns:
            业务知识库列表，每个元素包含业务ID、名称、文档数量等信息
        """
        result = []
        for business_id, info in self.kb_metadata["businesses"].items():
            result.append({
                "business_id": business_id,
                "name": info.get("name", business_id),
                "description": info.get("description", ""),
                "document_count": len(info.get("documents", {})),
                "created_at": info.get("created_at", ""),
                "updated_at": info.get("updated_at", "")
            })
        return result
    
    def create_business_kb(
        self,
        business_id: str,
        name: Optional[str] = None,
        description: str = "",
        overwrite: bool = False
    ) -> bool:
        """
        创建业务知识库
        
        Args:
            business_id: 业务ID，用作知识库唯一标识
            name: 业务名称，如果为None则使用business_id
            description: 业务描述
            overwrite: 是否覆盖已存在的同名知识库
            
        Returns:
            创建是否成功
        """
        # 检查业务ID是否已存在
        if business_id in self.kb_metadata["businesses"] and not overwrite:
            logger.warning(f"业务知识库 '{business_id}' 已存在")
            return False
        
        # 创建业务目录
        business_dir = self.base_dir / business_id
        if business_dir.exists() and overwrite:
            shutil.rmtree(business_dir)
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
        if business_id not in self.kb_metadata["businesses"]:
            logger.warning(f"业务知识库 '{business_id}' 不存在")
            return False
        
        # 删除业务目录
        business_dir = self.base_dir / business_id
        if business_dir.exists():
            shutil.rmtree(business_dir)
        
        # 更新元数据
        del self.kb_metadata["businesses"][business_id]
        self._save_metadata()
        
        logger.info(f"业务知识库 '{business_id}' 删除成功")
        return True
    
    async def add_documents_to_kb(
        self,
        business_id: str,
        file_paths: List[str],
        process_images: bool = True
    ) -> List[str]:
        """
        添加文档到业务知识库
        
        Args:
            business_id: 业务ID
            file_paths: 文档路径列表
            process_images: 是否处理文档中的图片
            
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
                
                # 处理文档内容
                doc_content = await self._process_document(file_path, process_images)
                
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
                self.kb_metadata["businesses"][business_id]["documents"][doc_id] = {
                    "file_name": file_name,
                    "original_path": file_path,
                    "kb_path": str(doc_path),
                    "added_at": metadata["added_at"]
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
    
    async def _process_document(self, file_path: str, process_images: bool) -> str:
        """处理文档内容"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 如果是PDF或DOCX文件，使用DocumentConverter
        if file_ext in ['.pdf', '.docx']:
            # 如果需要处理图片且图片处理器可用
            if process_images and self.image_processor:
                try:
                    logger.info(f"使用多模态处理器处理文档: {file_path}")
                    return await self.image_processor.process_document_to_text(file_path)
                except Exception as e:
                    logger.error(f"多模态处理失败，回退到普通处理: {str(e)}")
            
            # 普通文档处理
            logger.info(f"使用DocumentConverter处理文档: {file_path}")
            result = self.doc_converter.convert(file_path)
            return result.document.export_to_markdown()
        
        # 其他类型文件，使用LlamaIndex的SimpleDirectoryReader
        else:
            logger.info(f"使用SimpleDirectoryReader处理文档: {file_path}")
            reader = SimpleDirectoryReader(input_files=[file_path])
            docs = reader.load_data()
            return "\n\n".join([doc.text for doc in docs])
    
    def _update_index(self, business_id: str, documents: List[Document]):
        """更新知识库索引"""
        try:
            # 创建节点解析器
            node_parser = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            
            # 从文档中获取节点
            nodes = node_parser.get_nodes_from_documents(documents)
            logger.info(f"从 {len(documents)} 个文档中生成了 {len(nodes)} 个节点")
            
            # 创建或加载向量存储
            collection_name = f"business_{business_id}"
            
            # 获取嵌入维度 - 先生成一个示例嵌入以确定实际维度
            sample_text = "这是一个测试文本，用于确定嵌入维度"
            sample_embedding = self.embedding_model.get_text_embedding(sample_text)
            actual_dim = len(sample_embedding)
            logger.info(f"检测到嵌入维度: {actual_dim}")
            
            # 检查集合是否存在
            try:
                from pymilvus import MilvusClient
                client = MilvusClient(uri=self.milvus_uri)
                collections = client.list_collections()
                collection_exists = collection_name in collections
            except Exception as e:
                logger.warning(f"检查Milvus集合失败: {str(e)}")
                collection_exists = False
            
            # 创建向量存储
            if collection_exists:
                # 如果集合已存在，使用现有集合
                logger.info(f"使用现有集合: {collection_name}")
                vector_store = MilvusVectorStore(
                    uri=self.milvus_uri,
                    collection_name=collection_name,
                    dim=actual_dim,
                    overwrite=False  # 不覆盖现有集合
                )
                
                # 创建存储上下文
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                
                # 加载现有索引
                index_dir = self.base_dir / business_id / "index"
                if index_dir.exists():
                    try:
                        # 尝试加载现有索引
                        index = load_index_from_storage(
                            storage_context=storage_context,
                            persist_dir=str(index_dir)
                        )
                        # 将新节点添加到现有索引
                        for node in nodes:
                            index.insert(node)
                        logger.info(f"已将新节点添加到现有索引")
                    except Exception as e:
                        logger.warning(f"加载现有索引失败，将创建新索引: {str(e)}")
                        # 创建新索引并添加节点
                        index = VectorStoreIndex(nodes, storage_context=storage_context)
                else:
                    # 创建新索引并添加节点
                    index = VectorStoreIndex(nodes, storage_context=storage_context)
            else:
                # 如果集合不存在，创建新集合
                logger.info(f"创建新集合: {collection_name}")
                vector_store = MilvusVectorStore(
                    uri=self.milvus_uri,
                    collection_name=collection_name,
                    dim=actual_dim,
                    overwrite=True  # 创建新集合
                )
                
                # 创建存储上下文
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                
                # 创建索引并添加节点
                index = VectorStoreIndex(nodes, storage_context=storage_context)
            
            # 保存索引元数据
            index_dir = self.base_dir / business_id / "index"
            index.storage_context.persist(persist_dir=str(index_dir))
            
            logger.info(f"业务 '{business_id}' 的索引更新成功")
            
        except Exception as e:
            logger.error(f"更新索引失败: {str(e)}")
            raise
    
    def remove_document_from_kb(self, business_id: str, doc_id: str) -> bool:
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
            self._rebuild_index(business_id)
            
            logger.info(f"文档 '{doc_id}' 从业务 '{business_id}' 中删除成功")
            return True
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return False
    
    def _rebuild_index(self, business_id: str):
        """重建业务知识库索引"""
        try:
            business_dir = self.base_dir / business_id
            documents_dir = business_dir / "documents"
            index_dir = business_dir / "index"
            
            # 检查集合是否存在
            collection_name = f"business_{business_id}"
            try:
                from pymilvus import MilvusClient
                client = MilvusClient(uri=self.milvus_uri)
                collections = client.list_collections()
                if collection_name in collections:
                    # 删除现有集合
                    client.drop_collection(collection_name)
                    logger.info(f"已删除现有集合: {collection_name}")
            except Exception as e:
                logger.warning(f"检查或删除Milvus集合失败: {str(e)}")
            
            # 获取嵌入维度 - 先生成一个示例嵌入以确定实际维度
            sample_text = "这是一个测试文本，用于确定嵌入维度"
            sample_embedding = self.embedding_model.get_text_embedding(sample_text)
            actual_dim = len(sample_embedding)
            logger.info(f"检测到嵌入维度: {actual_dim}")
            
            # 创建向量存储
            vector_store = MilvusVectorStore(
                uri=self.milvus_uri,
                collection_name=collection_name,
                dim=actual_dim,
                overwrite=True  # 覆盖现有集合
            )
            
            # 如果没有文档，创建空索引
            if not self.kb_metadata["businesses"][business_id]["documents"]:
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                index = VectorStoreIndex([], storage_context=storage_context)
                index.storage_context.persist(persist_dir=str(index_dir))
                logger.info(f"业务 '{business_id}' 创建了空索引")
                return
            
            # 加载所有文档
            all_docs = []
            for doc_id, doc_info in self.kb_metadata["businesses"][business_id]["documents"].items():
                doc_path = Path(doc_info["kb_path"])
                if doc_path.exists():
                    try:
                        # 使用SimpleDirectoryReader加载文档
                        reader = SimpleDirectoryReader(input_files=[str(doc_path)])
                        docs = reader.load_data()
                        
                        # 添加元数据
                        for doc in docs:
                            doc.metadata.update({
                                "doc_id": doc_id,
                                "file_name": doc_info["file_name"],
                                "business_id": business_id
                            })
                            all_docs.append(doc)
                    except Exception as e:
                        logger.error(f"加载文档 '{doc_path}' 失败: {str(e)}")
            
            # 创建节点解析器
            node_parser = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            
            # 从文档中获取节点
            nodes = node_parser.get_nodes_from_documents(all_docs)
            
            # 创建存储上下文
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # 创建索引
            index = VectorStoreIndex(nodes, storage_context=storage_context)
            
            # 保存索引
            index.storage_context.persist(persist_dir=str(index_dir))
            
            logger.info(f"业务 '{business_id}' 的索引重建成功，包含 {len(all_docs)} 个文档")
            
        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            raise
    
    def query_business_kb(
        self,
        business_id: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        查询业务知识库
        
        Args:
            business_id: 业务ID
            query: 查询文本
            top_k: 返回的最相关结果数量
            similarity_threshold: 相似度阈值，低于此值的结果将被过滤
        
        Returns:
            查询结果，包含回答和相关文档信息
        """
        if business_id not in self.kb_metadata["businesses"]:
            logger.error(f"业务知识库 '{business_id}' 不存在")
            return {
                "query": query,
                "response": f"错误: 业务知识库 '{business_id}' 不存在",
                "source_nodes": []
            }
        
        try:
            # 检查索引目录是否存在
            index_dir = self.base_dir / business_id / "index"
            if not index_dir.exists():
                logger.error(f"业务 '{business_id}' 的索引不存在")
                return {
                    "query": query,
                    "response": f"错误: 业务 '{business_id}' 的索引不存在",
                    "source_nodes": []
                }
            
            # 获取嵌入维度 - 先生成一个示例嵌入以确定实际维度
            sample_text = "这是一个测试文本，用于确定嵌入维度"
            sample_embedding = self.embedding_model.get_text_embedding(sample_text)
            actual_dim = len(sample_embedding)
            
            # 创建向量存储
            collection_name = f"business_{business_id}"
            vector_store = MilvusVectorStore(
                uri=self.milvus_uri,
                collection_name=collection_name,
                dim=actual_dim
            )
            
            # 加载存储上下文
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # 加载索引
            index = load_index_from_storage(storage_context, persist_dir=str(index_dir))
            
            # 创建查询引擎
            query_engine = index.as_query_engine(
                similarity_top_k=top_k,
                node_postprocessors=[]
            )
            
            # 执行查询
            response = query_engine.query(query)
            
            # 处理结果
            source_nodes = []
            for node in response.source_nodes:
                # 过滤低相似度的结果
                if node.score and node.score < similarity_threshold:
                    continue
                
                # 提取文档信息
                metadata = node.node.metadata
                doc_id = metadata.get("doc_id", "unknown")
                file_name = metadata.get("file_name", "unknown")
                
                source_nodes.append({
                    "text": node.node.text,
                    "score": node.score,
                    "doc_id": doc_id,
                    "file_name": file_name
                })
            
            return {
                "query": query,
                "response": response.response,
                "source_nodes": source_nodes
            }
            
        except Exception as e:
            logger.error(f"查询业务知识库失败: {str(e)}")
            return {
                "query": query,
                "response": f"查询失败: {str(e)}",
                "source_nodes": []
            }
    
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
        doc_count = len(business_info.get("documents", {}))
        
        # 获取文档列表
        documents = []
        for doc_id, doc_info in business_info.get("documents", {}).items():
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


# 测试代码
async def test_business_kb():
    """测试业务知识库功能"""
    print("=== 业务知识库测试 ===")
    
    # 获取脚本所在目录的绝对路径
    script_dir = Path(__file__).parent.absolute()
    
    # 创建知识库管理器，使用脚本目录下的test_business_kb目录
    kb_manager = BusinessKnowledgeBaseManager(
        base_dir=script_dir / "test_business_kb",
        milvus_uri="http://localhost:19530"  # 使用本地Docker部署的Milvus
    )
    
    # 测试创建业务知识库
    business_id = "test_business"
    print(f"\n1. 创建业务知识库 '{business_id}'")
    success = kb_manager.create_business_kb(
        business_id=business_id,
        name="测试业务",
        description="这是一个测试业务知识库",
        overwrite=True
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
        result = kb_manager.query_business_kb(
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
            success = kb_manager.remove_document_from_kb(
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
















