"""
业务知识库系统 - 重构版本

这是重构后的业务知识库系统，采用模块化设计，提高了代码的可读性、可维护性和可扩展性。

主要模块：
1. BusinessKnowledgeBaseManager - 核心管理器，提供统一的对外接口
2. MetadataManager - 元数据管理器，负责业务和文档信息的存储
3. IndexManager - 索引管理器，负责Milvus向量索引的管理
4. DocumentProcessor - 文档处理器，负责文档内容的提取和预处理
5. RelationManager - 关联关系管理器，负责业务间关联关系的构建和管理
6. EntityExtractor - 实体提取器，负责从文档中提取实体
7. HybridSearchEngine - 混合搜索引擎，负责跨业务的混合搜索
8. QueryEngine - 查询引擎，负责查询逻辑的处理和结果格式化
9. SyncManager - 同步管理器，负责数据同步和一致性检查

重构设计原则：
- 单一职责：每个模块只负责特定功能
- 依赖注入：通过构造函数注入依赖
- 接口隔离：提供清晰的接口定义
- 开闭原则：易于扩展新功能
- 关注点分离：将复杂的混合搜索逻辑独立拆分

使用方法：
```python
from backend.my.knowledge_base import BusinessKnowledgeBaseManager

# 创建管理器
manager = BusinessKnowledgeBaseManager()

# 创建业务知识库
manager.create_business_kb("intelligent_chassis", "智能底盘", "智能底盘相关技术文档")

# 添加文档
doc_ids = await manager.add_documents_to_kb("intelligent_chassis", ["doc1.pdf", "doc2.docx"])

# 查询
results = await manager.query_business_kb("intelligent_chassis", "智能底盘的核心功能")

# 跨业务查询
cross_results = await manager.query_with_cross_business(
    "intelligent_chassis", "相关技术", expand_to_related=True
)
```
"""

# 导入重构后的模块
from .business_knowledge_base_manager import BusinessKnowledgeBaseManager
from .metadata_manager import MetadataManager
from .index_manager import IndexManager
from .document_processor_v2 import DocumentProcessor
from .relation_manager_v2 import RelationManager
from .entity_extractor import EntityExtractor
from .hybrid_search_engine import HybridSearchEngine
from .query_engine import QueryEngine
from .sync_manager import SyncManager
from .utils_v2 import (
    setup_logging,
    load_json_file,
    save_json_file,
    calculate_file_hash,
    backup_file,
    validate_business_id,
    validate_file_path,
    clean_text,
    extract_keywords,
    ProgressTracker
)

# 版本信息
__version__ = "2.0.0"
__author__ = "AI Assistant"
__description__ = "重构版业务知识库管理系统"

# 导出的主要类
__all__ = [
    # 核心管理器
    "BusinessKnowledgeBaseManager",
    
    # 子模块
    "MetadataManager",
    "IndexManager", 
    "DocumentProcessor",
    "RelationManager",
    "EntityExtractor",
    "HybridSearchEngine",
    "QueryEngine",
    "SyncManager",
    
    # 工具函数
    "setup_logging",
    "load_json_file",
    "save_json_file",
    "calculate_file_hash",
    "backup_file",
    "validate_business_id",
    "validate_file_path",
    "clean_text",
    "extract_keywords",
    "ProgressTracker",
    
    # 版本信息
    "__version__",
    "__author__",
    "__description__"
]

# 常量定义
DOC_STATUS_ACTIVE = "active"
DOC_STATUS_DELETED = "deleted"
DOC_STATUS_CORRUPTED = "corrupted"

SYNC_RESULT_OK = "ok"
SYNC_RESULT_WARNING = "warning"
SYNC_RESULT_ERROR = "error"

RELATION_TYPE_SHARED_ENTITY = "shared_entity"
RELATION_TYPE_QUERY_USAGE = "query_usage"
RELATION_TYPE_MANUAL = "manual"

# 默认配置
DEFAULT_CONFIG = {
    "embedding_model_name": "BAAI/bge-small-zh-v1.5",
    "milvus_uri": "tcp://localhost:19530",
    "chunk_size": 512,
    "chunk_overlap": 50,
    "max_entities": 15,
    "similarity_top_k": 3,
    "max_related_businesses": 2
}


def create_knowledge_base_manager(
    embedding_model_name: str = None,
    milvus_uri: str = None,
    auto_sync: bool = False,
    base_dir: str = None
) -> BusinessKnowledgeBaseManager:
    """
    创建业务知识库管理器的便捷函数
    
    Args:
        embedding_model_name: 嵌入模型名称
        milvus_uri: Milvus服务URI
        auto_sync: 是否自动同步
        base_dir: 基础目录
        
    Returns:
        业务知识库管理器实例
    """
    config = DEFAULT_CONFIG.copy()
    
    if embedding_model_name:
        config["embedding_model_name"] = embedding_model_name
    if milvus_uri:
        config["milvus_uri"] = milvus_uri
    
    return BusinessKnowledgeBaseManager(
        embedding_model_name=config["embedding_model_name"],
        milvus_uri=config["milvus_uri"],
        auto_sync=auto_sync,
        base_dir=base_dir
    )


def get_version_info() -> dict:
    """
    获取版本信息
    
    Returns:
        版本信息字典
    """
    return {
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "modules": [
            "BusinessKnowledgeBaseManager",
            "MetadataManager",
            "IndexManager",
            "DocumentProcessor",
            "RelationManager",
            "EntityExtractor", 
            "HybridSearchEngine",
            "QueryEngine",
            "SyncManager"
        ]
    }


def validate_system_requirements() -> dict:
    """
    验证系统要求
    
    Returns:
        验证结果
    """
    requirements = {
        "python_version": "3.8+",
        "required_packages": [
            "llama-index",
            "pymilvus",
            "docling",
            "scikit-learn",
            "pathlib"
        ],
        "optional_packages": [
            "psutil",
            "spacy",
            "jieba"
        ]
    }
    
    results = {
        "requirements": requirements,
        "status": "checking",
        "details": {}
    }
    
    try:
        import sys
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        results["details"]["python_version"] = python_version
        
        # 检查必需包
        missing_packages = []
        for package in requirements["required_packages"]:
            try:
                __import__(package.replace("-", "_"))
                results["details"][package] = "已安装"
            except ImportError:
                missing_packages.append(package)
                results["details"][package] = "未安装"
        
        if missing_packages:
            results["status"] = "missing_requirements"
            results["missing_packages"] = missing_packages
        else:
            results["status"] = "ok"
            
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
    
    return results


# 设置默认日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 模块级别的logger
logger = logging.getLogger(__name__)
logger.info(f"业务知识库系统 v{__version__} 已加载")
