"""
业务知识库管理器 - 重构版本

本模块是业务知识库系统的核心管理器，负责：
1. 协调各个子模块的工作
2. 提供统一的对外接口
3. 管理业务知识库的生命周期

重构设计原则：
- 单一职责：每个模块只负责特定功能
- 依赖注入：通过构造函数注入依赖
- 接口隔离：提供清晰的接口定义
- 开闭原则：易于扩展新功能
"""

import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# 导入子模块
from metadata_manager import MetadataManager
from index_manager import IndexManager
from document_processor_v2 import DocumentProcessor
from query_engine import QueryEngine
from sync_manager import SyncManager
from relation_manager_v2 import RelationManager
from hybrid_search_engine import HybridSearchEngine

# 设置日志
logger = logging.getLogger(__name__)

# 常量定义
DOC_STATUS_ACTIVE = "active"
DOC_STATUS_DELETED = "deleted"
DOC_STATUS_CORRUPTED = "corrupted"

SYNC_RESULT_OK = "ok"
SYNC_RESULT_WARNING = "warning"
SYNC_RESULT_ERROR = "error"


class BusinessKnowledgeBaseManager:
    """
    业务知识库管理器
    
    这是系统的核心管理器，负责协调各个子模块的工作，
    提供统一的对外接口。
    """
    
    def __init__(
        self,
        embedding_model_name: str = "BAAI/bge-small-zh-v1.5",
        milvus_uri: str = "tcp://localhost:19530",
        auto_sync: bool = False,
        base_dir: Optional[str] = None
    ):
        """
        初始化业务知识库管理器
        
        Args:
            embedding_model_name: 嵌入模型名称
            milvus_uri: Milvus服务URI
            auto_sync: 是否自动同步
            base_dir: 基础目录，如果为None则使用默认目录
        """
        # 设置基础目录
        if base_dir is None:
            script_dir = Path(__file__).parent.parent.absolute()
            self.base_dir = script_dir / "business_knowledge_base"
        else:
            self.base_dir = Path(base_dir)
        
        self.base_dir.mkdir(exist_ok=True, parents=True)
        
        # 初始化配置
        self.embedding_model_name = embedding_model_name
        self.milvus_uri = milvus_uri
        self.auto_sync = auto_sync
        
        # 初始化子模块
        self._init_submodules()
        
        logger.info(f"业务知识库管理器初始化完成，基础目录: {self.base_dir}")
    
    def _init_submodules(self):
        """初始化所有子模块"""
        # 元数据管理器
        self.metadata_manager = MetadataManager(self.base_dir)
        
        # 索引管理器
        self.index_manager = IndexManager(
            base_dir=self.base_dir,
            embedding_model_name=self.embedding_model_name,
            milvus_uri=self.milvus_uri
        )
        
        # 文档处理器
        self.document_processor = DocumentProcessor()
        
        # 关联关系管理器
        self.relation_manager = RelationManager(self.base_dir)
        
        # 混合搜索引擎
        self.hybrid_search_engine = HybridSearchEngine(
            index_manager=self.index_manager,
            relation_manager=self.relation_manager,
            metadata_manager=self.metadata_manager
        )
        
        # 查询引擎
        self.query_engine = QueryEngine(
            index_manager=self.index_manager,
            hybrid_search_engine=self.hybrid_search_engine
        )
        
        # 同步管理器
        self.sync_manager = SyncManager(
            base_dir=self.base_dir,
            metadata_manager=self.metadata_manager,
            index_manager=self.index_manager
        )
    
    # ==================== 业务知识库管理接口 ====================
    
    def create_business_kb(
        self,
        business_id: str,
        name: Optional[str] = None,
        description: str = ""
    ) -> bool:
        """
        创建业务知识库
        
        Args:
            business_id: 业务ID
            name: 业务名称
            description: 业务描述
            
        Returns:
            是否创建成功
        """
        return self.metadata_manager.create_business(business_id, name, description)
    
    def delete_business_kb(self, business_id: str) -> bool:
        """
        删除业务知识库
        
        Args:
            business_id: 业务ID
            
        Returns:
            是否删除成功
        """
        # 删除索引
        self.index_manager.delete_business_index(business_id)
        
        # 删除元数据
        return self.metadata_manager.delete_business(business_id)
    
    def list_businesses(self) -> List[Dict[str, Any]]:
        """
        列出所有业务知识库
        
        Returns:
            业务知识库列表
        """
        return self.metadata_manager.list_businesses()
    
    def get_business_info(self, business_id: str) -> Dict[str, Any]:
        """
        获取业务知识库信息
        
        Args:
            business_id: 业务ID
            
        Returns:
            业务知识库信息
        """
        return self.metadata_manager.get_business_info(business_id)
    
    # ==================== 文档管理接口 ====================
    
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
        # 检查业务是否存在
        if not self.metadata_manager.business_exists(business_id):
            self.create_business_kb(business_id)

        # 处理文档
        doc_ids = []
        processed_documents = []

        for file_path in file_paths:
            try:
                # 处理单个文档
                doc_id, document = await self._process_single_document(
                    business_id, file_path
                )

                if doc_id and document:
                    doc_ids.append(doc_id)
                    processed_documents.append(document)

            except Exception as e:
                logger.error(f"处理文档 '{file_path}' 失败: {str(e)}")

        # 更新索引
        if processed_documents:
            await self.index_manager.update_index(business_id, processed_documents)

        return doc_ids
    
    async def _process_single_document(
        self,
        business_id: str,
        file_path: str
    ) -> tuple:
        """
        处理单个文档

        Args:
            business_id: 业务ID
            file_path: 文档路径

        Returns:
            (文档ID, 文档对象) 的元组
        """
        # 处理文档内容（自动判断是否需要图片处理）
        document = await self.document_processor.process_document(file_path)
        
        if not document:
            return None, None
        
        # 添加业务信息到元数据
        document.metadata["business_id"] = business_id
        
        # 提取实体并构建关联关系
        entities = self.relation_manager.extract_entities_from_document(document)
        document.metadata["entities"] = entities
        
        # 构建业务关联
        self.relation_manager.build_relations_from_entities(business_id, entities)
        
        # 保存文档元数据
        doc_id = self.metadata_manager.add_document(business_id, file_path, document)
        
        return doc_id, document
    
    async def remove_document_from_kb(self, business_id: str, doc_id: str) -> bool:
        """
        从知识库中删除文档
        
        Args:
            business_id: 业务ID
            doc_id: 文档ID
            
        Returns:
            是否删除成功
        """
        # 删除文档元数据
        success = self.metadata_manager.remove_document(business_id, doc_id)
        
        if success:
            # 重建索引
            await self.index_manager.rebuild_index(business_id)
        
        return success
    
    # ==================== 查询接口 ====================
    
    async def query_business_kb(
        self,
        business_id: str,
        query: str,
        similarity_top_k: int = 3,
        response_mode: str = "compact"
    ) -> Dict[str, Any]:
        """
        查询业务知识库
        
        Args:
            business_id: 业务ID
            query: 查询文本
            similarity_top_k: 返回的相似结果数量
            response_mode: 响应模式
            
        Returns:
            查询结果
        """
        return await self.query_engine.query_single_business(
            business_id, query, similarity_top_k, response_mode
        )
    
    async def query_with_cross_business(
        self,
        business_id: str,
        query: str,
        expand_to_related: bool = True,
        max_related_businesses: int = 2,
        response_mode: str = "compact"
    ) -> Dict[str, Any]:
        """
        跨业务查询
        
        Args:
            business_id: 主业务ID
            query: 查询文本
            expand_to_related: 是否扩展到相关业务
            max_related_businesses: 最大相关业务数量
            response_mode: 响应模式
            
        Returns:
            查询结果
        """
        return await self.hybrid_search_engine.cross_business_search(
            business_id, query, expand_to_related, max_related_businesses, response_mode
        )
    
    # ==================== 同步接口 ====================
    
    async def sync_all_businesses(self) -> Dict[str, Any]:
        """
        同步所有业务知识库
        
        Returns:
            同步结果
        """
        return await self.sync_manager.sync_all_businesses()
    
    async def sync_business_kb(self, business_id: str) -> Dict[str, Any]:
        """
        同步业务知识库
        
        Args:
            business_id: 业务ID
            
        Returns:
            同步结果
        """
        return await self.sync_manager.sync_business(business_id)
