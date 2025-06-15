"""
索引管理器

负责管理Milvus向量索引，包括：
1. 创建和管理Milvus集合
2. 向量索引的创建、更新和删除
3. 向量搜索功能
4. 索引配置的持久化
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from llama_index.core import Document, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pymilvus import MilvusClient

# 设置日志
logger = logging.getLogger(__name__)


class IndexManager:
    """
    索引管理器
    
    负责管理Milvus向量索引的创建、更新、删除和查询。
    封装了所有与Milvus相关的底层操作。
    """
    
    def __init__(
        self,
        base_dir: Path,
        embedding_model_name: str = "BAAI/bge-small-zh-v1.5",
        milvus_uri: str = "tcp://localhost:19530",
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """
        初始化索引管理器
        
        Args:
            base_dir: 基础目录
            embedding_model_name: 嵌入模型名称
            milvus_uri: Milvus服务URI
            chunk_size: 文档分块大小
            chunk_overlap: 分块重叠大小
        """
        self.base_dir = Path(base_dir)
        self.milvus_uri = milvus_uri
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 初始化嵌入模型
        self.embedding_model_name = embedding_model_name
        self.embedding_model = HuggingFaceEmbedding(model_name=embedding_model_name)
        Settings.embed_model = self.embedding_model
        
        # 创建Milvus客户端
        self.milvus_client = MilvusClient(uri=self.milvus_uri)
        
        # 获取嵌入维度
        self.embedding_dim = self._get_embedding_dimension()
        
        logger.info(f"索引管理器初始化完成，Milvus URI: {self.milvus_uri}, 嵌入维度: {self.embedding_dim}")
    
    def _get_embedding_dimension(self) -> int:
        """
        获取嵌入模型的维度
        
        Returns:
            嵌入维度
        """
        try:
            sample_text = "这是一个测试文本，用于确定嵌入维度"
            sample_embedding = self.embedding_model.get_text_embedding(sample_text)
            return len(sample_embedding)
        except Exception as e:
            logger.error(f"获取嵌入维度失败: {str(e)}")
            # 返回默认维度
            return 512
    
    def _get_collection_name(self, business_id: str) -> str:
        """
        获取业务对应的集合名称
        
        Args:
            business_id: 业务ID
            
        Returns:
            集合名称
        """
        return f"business_{business_id}"
    
    def _save_index_config(self, business_id: str, config: Dict[str, Any]) -> bool:
        """
        保存索引配置
        
        Args:
            business_id: 业务ID
            config: 配置信息
            
        Returns:
            是否保存成功
        """
        try:
            index_dir = self.base_dir / business_id / "index"
            index_dir.mkdir(exist_ok=True, parents=True)
            
            config_file = index_dir / "milvus_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"保存索引配置失败: {str(e)}")
            return False
    
    def _load_index_config(self, business_id: str) -> Optional[Dict[str, Any]]:
        """
        加载索引配置
        
        Args:
            business_id: 业务ID
            
        Returns:
            配置信息，如果不存在则返回None
        """
        try:
            index_dir = self.base_dir / business_id / "index"
            config_file = index_dir / "milvus_config.json"
            
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"加载索引配置失败: {str(e)}")
            return None
    
    # ==================== 集合管理接口 ====================
    
    def create_collection(self, business_id: str) -> bool:
        """
        创建Milvus集合
        
        Args:
            business_id: 业务ID
            
        Returns:
            是否创建成功
        """
        try:
            collection_name = self._get_collection_name(business_id)
            
            # 检查集合是否已存在
            collections = self.milvus_client.list_collections()
            if collection_name in collections:
                logger.info(f"集合 {collection_name} 已存在，先删除")
                self.milvus_client.drop_collection(collection_name)
            
            # 创建新集合
            self.milvus_client.create_collection(
                collection_name=collection_name,
                dimension=self.embedding_dim,
                primary_field_name="pk_id",
                vector_field_name="vector",
                auto_id=False
            )
            
            logger.info(f"成功创建集合: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建集合失败: {str(e)}")
            return False
    
    def delete_collection(self, business_id: str) -> bool:
        """
        删除Milvus集合
        
        Args:
            business_id: 业务ID
            
        Returns:
            是否删除成功
        """
        try:
            collection_name = self._get_collection_name(business_id)
            collections = self.milvus_client.list_collections()
            
            if collection_name in collections:
                self.milvus_client.drop_collection(collection_name)
                logger.info(f"成功删除集合: {collection_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"删除集合失败: {str(e)}")
            return False
    
    def collection_exists(self, business_id: str) -> bool:
        """
        检查集合是否存在
        
        Args:
            business_id: 业务ID
            
        Returns:
            集合是否存在
        """
        try:
            collection_name = self._get_collection_name(business_id)
            collections = self.milvus_client.list_collections()
            return collection_name in collections
        except Exception as e:
            logger.error(f"检查集合存在性失败: {str(e)}")
            return False
    
    def get_collection_stats(self, business_id: str) -> Dict[str, Any]:
        """
        获取集合统计信息
        
        Args:
            business_id: 业务ID
            
        Returns:
            集合统计信息
        """
        try:
            collection_name = self._get_collection_name(business_id)
            
            if not self.collection_exists(business_id):
                return {"exists": False, "row_count": 0}
            
            stats = self.milvus_client.get_collection_stats(collection_name)
            return {
                "exists": True,
                "row_count": stats.get("row_count", 0)
            }
            
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {str(e)}")
            return {"exists": False, "row_count": 0, "error": str(e)}
    
    # ==================== 索引管理接口 ====================
    
    async def create_index(self, business_id: str, documents: List[Document]) -> bool:
        """
        创建索引
        
        Args:
            business_id: 业务ID
            documents: 文档列表
            
        Returns:
            是否创建成功
        """
        try:
            # 创建集合
            if not self.create_collection(business_id):
                return False
            
            # 分割文档为节点
            node_parser = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            
            nodes = node_parser.get_nodes_from_documents(documents)
            logger.info(f"生成了 {len(nodes)} 个节点")
            
            if not nodes:
                logger.warning("没有生成任何节点")
                return False
            
            # 为节点生成嵌入
            for node in nodes:
                if not hasattr(node, 'embedding') or node.embedding is None:
                    node_text = node.get_content()
                    node.embedding = self.embedding_model.get_text_embedding(node_text)
            
            # 准备数据
            entities = []
            collection_name = self._get_collection_name(business_id)
            
            for i, node in enumerate(nodes):
                entities.append({
                    "pk_id": i + 1,
                    "vector": node.embedding,
                    "text": node.get_content()
                })
            
            # 插入数据
            if entities:
                insert_result = self.milvus_client.insert(
                    collection_name=collection_name,
                    data=entities
                )
                logger.info(f"插入结果: {insert_result}")
                
                # 加载集合以便搜索
                self.milvus_client.load_collection(collection_name)
                
                # 保存索引配置
                config = {
                    "collection_name": collection_name,
                    "uri": self.milvus_uri,
                    "dim": self.embedding_dim,
                    "created_at": datetime.now().isoformat(),
                    "node_count": len(nodes),
                    "primary_field": "pk_id",
                    "vector_field": "vector"
                }
                
                self._save_index_config(business_id, config)
                
                logger.info(f"业务 '{business_id}' 的索引创建成功")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"创建索引失败: {str(e)}")
            return False
    
    async def update_index(self, business_id: str, documents: List[Document]) -> bool:
        """
        更新索引
        
        Args:
            business_id: 业务ID
            documents: 文档列表
            
        Returns:
            是否更新成功
        """
        # 目前的实现是重建索引
        return await self.create_index(business_id, documents)
    
    async def rebuild_index(self, business_id: str) -> bool:
        """
        重建索引
        
        Args:
            business_id: 业务ID
            
        Returns:
            是否重建成功
        """
        try:
            # 删除现有集合
            self.delete_collection(business_id)
            
            # 这里需要从元数据管理器获取活跃文档
            # 由于这是底层模块，我们返回True，让上层调用者处理
            logger.info(f"业务 '{business_id}' 的索引重建请求已处理")
            return True
            
        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            return False
    
    def delete_business_index(self, business_id: str) -> bool:
        """
        删除业务索引
        
        Args:
            business_id: 业务ID
            
        Returns:
            是否删除成功
        """
        return self.delete_collection(business_id)
    
    # ==================== 搜索接口 ====================
    
    async def search(
        self,
        business_id: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        向量搜索
        
        Args:
            business_id: 业务ID
            query: 查询文本
            top_k: 返回的结果数量
            
        Returns:
            搜索结果列表
        """
        try:
            collection_name = self._get_collection_name(business_id)
            
            # 检查集合是否存在
            if not self.collection_exists(business_id):
                logger.warning(f"集合 {collection_name} 不存在")
                return []
            
            # 生成查询嵌入
            query_embedding = self.embedding_model.get_text_embedding(query)
            
            # 执行搜索
            search_results = self.milvus_client.search(
                collection_name=collection_name,
                data=[query_embedding],
                field_name="vector",
                limit=top_k,
                output_fields=["text"]
            )
            
            # 处理搜索结果
            results = []
            if search_results and len(search_results) > 0:
                for hit in search_results[0]:
                    results.append({
                        "text": hit.get("entity", {}).get("text", ""),
                        "score": hit.get("distance", 0),
                        "id": hit.get("id", "")
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {str(e)}")
            return []
