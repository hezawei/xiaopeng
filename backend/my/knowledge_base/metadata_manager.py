"""
元数据管理器

负责管理业务知识库的元数据，包括：
1. 业务信息的存储和管理
2. 文档信息的存储和管理
3. 元数据的持久化和加载
4. 数据一致性检查
"""

import json
import uuid
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from llama_index.core import Document

# 设置日志
import logging
logger = logging.getLogger(__name__)

# 常量定义
DOC_STATUS_ACTIVE = "active"
DOC_STATUS_DELETED = "deleted"
DOC_STATUS_CORRUPTED = "corrupted"


class MetadataManager:
    """
    元数据管理器
    
    负责管理业务知识库的所有元数据，包括业务信息、文档信息等。
    提供线程安全的元数据操作接口。
    """
    
    def __init__(self, base_dir: Path):
        """
        初始化元数据管理器
        
        Args:
            base_dir: 基础目录
        """
        self.base_dir = Path(base_dir)
        self.metadata_file = self.base_dir / "kb_metadata.json"
        
        # 同步锁，确保线程安全
        self.sync_lock = threading.RLock()
        
        # 备份目录
        self.backup_dir = self.base_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # 加载元数据
        self.metadata = self._load_metadata()
        
        logger.info(f"元数据管理器初始化完成，元数据文件: {self.metadata_file}")
    
    def _load_metadata(self) -> Dict[str, Any]:
        """
        加载元数据
        
        Returns:
            元数据字典
        """
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # 确保每个文档都有状态字段
                for business_id, business_info in metadata.get("businesses", {}).items():
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
    
    def _save_metadata(self) -> bool:
        """
        保存元数据
        
        Returns:
            是否保存成功
        """
        with self.sync_lock:
            try:
                # 备份现有元数据
                if self.metadata_file.exists():
                    self._backup_file(self.metadata_file)
                
                # 保存新元数据
                with open(self.metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                logger.error(f"保存元数据失败: {str(e)}")
                return False
    
    def _backup_file(self, file_path: Path) -> Optional[Path]:
        """
        备份文件
        
        Args:
            file_path: 要备份的文件路径
            
        Returns:
            备份文件路径
        """
        try:
            if file_path.exists():
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
            import hashlib
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                # 读取文件的前10MB计算指纹，避免处理大文件时性能问题
                buf = f.read(10 * 1024 * 1024)
                hasher.update(buf)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"计算文件指纹失败: {str(e)}")
            return ""
    
    # ==================== 业务管理接口 ====================
    
    def create_business(
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
        with self.sync_lock:
            # 检查业务ID是否已存在
            if business_id in self.metadata["businesses"]:
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
            self.metadata["businesses"][business_id] = {
                "name": name or business_id,
                "description": description,
                "created_at": now,
                "updated_at": now,
                "documents": {}
            }
            
            success = self._save_metadata()
            if success:
                logger.info(f"业务知识库 '{business_id}' 创建成功")
            
            return success
    
    def delete_business(self, business_id: str) -> bool:
        """
        删除业务知识库
        
        Args:
            business_id: 业务ID
            
        Returns:
            是否删除成功
        """
        with self.sync_lock:
            if business_id not in self.metadata["businesses"]:
                logger.warning(f"业务知识库 '{business_id}' 不存在")
                return False
            
            # 删除业务目录
            business_dir = self.base_dir / business_id
            if business_dir.exists():
                # 备份后删除
                self._backup_file(business_dir)
                shutil.rmtree(business_dir)
            
            # 更新元数据
            del self.metadata["businesses"][business_id]
            success = self._save_metadata()
            
            if success:
                logger.info(f"业务知识库 '{business_id}' 删除成功")
            
            return success
    
    def business_exists(self, business_id: str) -> bool:
        """
        检查业务是否存在
        
        Args:
            business_id: 业务ID
            
        Returns:
            业务是否存在
        """
        return business_id in self.metadata["businesses"]
    
    def list_businesses(self) -> List[Dict[str, Any]]:
        """
        列出所有业务知识库
        
        Returns:
            业务知识库列表
        """
        result = []
        for business_id, info in self.metadata["businesses"].items():
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
    
    def get_business_info(self, business_id: str) -> Dict[str, Any]:
        """
        获取业务知识库信息
        
        Args:
            business_id: 业务ID
            
        Returns:
            业务知识库信息
        """
        if business_id not in self.metadata["businesses"]:
            return {"error": f"业务知识库 '{business_id}' 不存在"}
        
        business_info = self.metadata["businesses"][business_id]
        
        # 统计文档数量
        doc_count = 0
        for doc_info in business_info.get("documents", {}).values():
            if doc_info.get("status") == DOC_STATUS_ACTIVE:
                doc_count += 1
        
        # 获取文档列表
        documents = []
        for doc_id, doc_info in business_info.get("documents", {}).items():
            if doc_info.get("status") == DOC_STATUS_ACTIVE:
                documents.append({
                    "doc_id": doc_id,
                    "file_name": doc_info.get("file_name", ""),
                    "added_at": doc_info.get("added_at", ""),
                    "entities": doc_info.get("entities", [])
                })
        
        return {
            "business_id": business_id,
            "name": business_info.get("name", business_id),
            "description": business_info.get("description", ""),
            "document_count": doc_count,
            "created_at": business_info.get("created_at", ""),
            "updated_at": business_info.get("updated_at", ""),
            "documents": documents
        }
    
    # ==================== 文档管理接口 ====================
    
    def add_document(
        self,
        business_id: str,
        file_path: str,
        document: Document
    ) -> str:
        """
        添加文档到业务知识库
        
        Args:
            business_id: 业务ID
            file_path: 文档路径
            document: 文档对象
            
        Returns:
            文档ID
        """
        with self.sync_lock:
            # 生成文档ID
            doc_id = str(uuid.uuid4())
            
            # 复制文件到知识库目录
            original_path = Path(file_path)
            file_name = original_path.name
            business_dir = self.base_dir / business_id
            documents_dir = business_dir / "documents"
            documents_dir.mkdir(exist_ok=True, parents=True)
            
            kb_path = str(documents_dir / file_name)
            shutil.copy2(file_path, kb_path)
            
            # 计算文件指纹
            file_fingerprint = self._calculate_file_fingerprint(kb_path)
            
            # 更新元数据
            self.metadata["businesses"][business_id]["documents"][doc_id] = {
                "file_name": file_name,
                "original_path": str(original_path),
                "kb_path": kb_path,
                "status": DOC_STATUS_ACTIVE,
                "file_fingerprint": file_fingerprint,
                "added_at": datetime.now().isoformat(),
                "entities": document.metadata.get("entities", [])
            }
            
            # 更新业务的更新时间
            self.metadata["businesses"][business_id]["updated_at"] = datetime.now().isoformat()
            
            # 保存元数据
            self._save_metadata()
            
            logger.info(f"文档 '{file_name}' 添加到业务 '{business_id}' 成功，文档ID: {doc_id}")
            return doc_id
    
    def remove_document(self, business_id: str, doc_id: str) -> bool:
        """
        删除文档
        
        Args:
            business_id: 业务ID
            doc_id: 文档ID
            
        Returns:
            是否删除成功
        """
        with self.sync_lock:
            if business_id not in self.metadata["businesses"]:
                logger.error(f"业务知识库 '{business_id}' 不存在")
                return False
            
            business_info = self.metadata["businesses"][business_id]
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
                
                success = self._save_metadata()
                if success:
                    logger.info(f"文档 '{doc_id}' 从业务 '{business_id}' 中删除成功")
                
                return success
                
            except Exception as e:
                logger.error(f"删除文档失败: {str(e)}")
                return False
    
    def get_active_documents(self, business_id: str) -> List[Dict[str, Any]]:
        """
        获取业务的活跃文档列表
        
        Args:
            business_id: 业务ID
            
        Returns:
            活跃文档列表
        """
        if business_id not in self.metadata["businesses"]:
            return []
        
        active_docs = []
        business_info = self.metadata["businesses"][business_id]
        
        for doc_id, doc_info in business_info.get("documents", {}).items():
            if doc_info.get("status") == DOC_STATUS_ACTIVE:
                active_docs.append({
                    "doc_id": doc_id,
                    "file_name": doc_info.get("file_name", ""),
                    "kb_path": doc_info.get("kb_path", ""),
                    "file_fingerprint": doc_info.get("file_fingerprint", ""),
                    "added_at": doc_info.get("added_at", ""),
                    "entities": doc_info.get("entities", [])
                })
        
        return active_docs
    
    def get_all_metadata(self) -> Dict[str, Any]:
        """
        获取所有元数据
        
        Returns:
            所有元数据
        """
        return self.metadata.copy()
