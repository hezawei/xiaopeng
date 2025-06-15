"""
关联关系管理器 V2 - 重构版本

负责管理业务间的关联关系，包括：
1. 实体提取和管理
2. 业务关联关系的构建和维护
3. 基于实体的关系发现
4. 关联强度的计算和更新

这是混合搜索功能的核心组件，被独立拆分以提高可维护性。
"""

import json
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from llama_index.core import Document

# 设置日志
logger = logging.getLogger(__name__)

# 关系类型常量
RELATION_TYPE_SHARED_ENTITY = "shared_entity"
RELATION_TYPE_QUERY_USAGE = "query_usage"
RELATION_TYPE_MANUAL = "manual"


class RelationManager:
    """
    关联关系管理器
    
    这是混合搜索功能的核心组件，负责：
    1. 从文档中提取实体
    2. 基于共享实体构建业务关联
    3. 管理业务间的关联关系
    4. 支持跨业务的关联查询
    """
    
    def __init__(self, base_dir: Path):
        """
        初始化关联关系管理器
        
        Args:
            base_dir: 基础目录
        """
        self.base_dir = Path(base_dir)
        self.relations_file = self.base_dir / "business_relations.json"
        self.entities_file = self.base_dir / "business_entities.json"
        
        # 同步锁，确保线程安全
        self.sync_lock = threading.RLock()
        
        # 加载数据
        self.relations = self._load_relations()
        self.entities = self._load_entities()
        
        # 实体提取器（延迟加载）
        self._entity_extractor = None
        
        logger.info(f"关联关系管理器初始化完成，基础目录: {self.base_dir}")
    
    def _load_relations(self) -> Dict[str, Any]:
        """
        加载关联关系数据
        
        Returns:
            关联关系数据
        """
        default_data = {
            "version": "2.0",
            "relations": {},  # business_a -> business_b -> {type, weight, entities}
            "metadata": {
                "created_at": "",
                "updated_at": ""
            }
        }
        
        if self.relations_file.exists():
            try:
                with open(self.relations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 确保数据结构完整
                if "relations" not in data:
                    data["relations"] = {}
                if "metadata" not in data:
                    data["metadata"] = {"created_at": "", "updated_at": ""}
                
                return data
            except Exception as e:
                logger.error(f"加载关联关系数据失败: {str(e)}")
                return default_data
        else:
            return default_data
    
    def _load_entities(self) -> Dict[str, Any]:
        """
        加载实体数据
        
        Returns:
            实体数据
        """
        default_data = {
            "version": "2.0",
            "business_entities": {},  # business_id -> [entities]
            "entity_businesses": {},  # entity -> [business_ids]
            "metadata": {
                "created_at": "",
                "updated_at": ""
            }
        }
        
        if self.entities_file.exists():
            try:
                with open(self.entities_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 确保数据结构完整
                if "business_entities" not in data:
                    data["business_entities"] = {}
                if "entity_businesses" not in data:
                    data["entity_businesses"] = {}
                if "metadata" not in data:
                    data["metadata"] = {"created_at": "", "updated_at": ""}
                
                return data
            except Exception as e:
                logger.error(f"加载实体数据失败: {str(e)}")
                return default_data
        else:
            return default_data
    
    def _save_relations(self) -> bool:
        """
        保存关联关系数据
        
        Returns:
            是否保存成功
        """
        with self.sync_lock:
            try:
                from datetime import datetime
                self.relations["metadata"]["updated_at"] = datetime.now().isoformat()
                
                with open(self.relations_file, 'w', encoding='utf-8') as f:
                    json.dump(self.relations, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                logger.error(f"保存关联关系数据失败: {str(e)}")
                return False
    
    def _save_entities(self) -> bool:
        """
        保存实体数据
        
        Returns:
            是否保存成功
        """
        with self.sync_lock:
            try:
                from datetime import datetime
                self.entities["metadata"]["updated_at"] = datetime.now().isoformat()
                
                with open(self.entities_file, 'w', encoding='utf-8') as f:
                    json.dump(self.entities, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                logger.error(f"保存实体数据失败: {str(e)}")
                return False
    
    @property
    def entity_extractor(self):
        """
        延迟加载实体提取器
        
        Returns:
            实体提取器实例
        """
        if self._entity_extractor is None:
            try:
                from entity_extractor import EntityExtractor
                self._entity_extractor = EntityExtractor()
                logger.info("实体提取器加载成功")
            except ImportError as e:
                logger.warning(f"无法加载实体提取器: {str(e)}")
                # 使用简单的实体提取器
                self._entity_extractor = SimpleEntityExtractor()
        
        return self._entity_extractor
    
    # ==================== 实体管理接口 ====================
    
    def extract_entities_from_document(self, document: Document) -> List[str]:
        """
        从文档中提取实体
        
        Args:
            document: 文档对象
            
        Returns:
            提取的实体列表
        """
        try:
            text = document.text
            entities = self.entity_extractor.extract_entities(text, max_entities=15)
            
            logger.info(f"从文档中提取到 {len(entities)} 个实体")
            return entities
            
        except Exception as e:
            logger.error(f"提取实体失败: {str(e)}")
            return []
    
    def add_business_entities(self, business_id: str, entities: List[str]) -> bool:
        """
        添加业务实体
        
        Args:
            business_id: 业务ID
            entities: 实体列表
            
        Returns:
            是否添加成功
        """
        with self.sync_lock:
            # 更新业务实体映射
            if business_id not in self.entities["business_entities"]:
                self.entities["business_entities"][business_id] = []
            
            # 合并实体列表，去重
            existing_entities = set(self.entities["business_entities"][business_id])
            new_entities = set(entities)
            all_entities = list(existing_entities | new_entities)
            
            self.entities["business_entities"][business_id] = all_entities
            
            # 更新实体到业务的反向映射
            for entity in entities:
                if entity not in self.entities["entity_businesses"]:
                    self.entities["entity_businesses"][entity] = []
                
                if business_id not in self.entities["entity_businesses"][entity]:
                    self.entities["entity_businesses"][entity].append(business_id)
            
            return self._save_entities()
    
    def get_business_entities(self, business_id: str) -> List[str]:
        """
        获取业务的实体列表
        
        Args:
            business_id: 业务ID
            
        Returns:
            实体列表
        """
        return self.entities["business_entities"].get(business_id, [])
    
    def get_businesses_by_entity(self, entity: str) -> List[str]:
        """
        获取包含指定实体的业务列表
        
        Args:
            entity: 实体名称
            
        Returns:
            业务ID列表
        """
        return self.entities["entity_businesses"].get(entity, [])
    
    def get_shared_entities(self, business_a: str, business_b: str) -> List[str]:
        """
        获取两个业务的共享实体
        
        Args:
            business_a: 业务A的ID
            business_b: 业务B的ID
            
        Returns:
            共享实体列表
        """
        entities_a = set(self.get_business_entities(business_a))
        entities_b = set(self.get_business_entities(business_b))
        
        return list(entities_a & entities_b)
    
    # ==================== 关联关系管理接口 ====================
    
    def build_relations_from_entities(self, business_id: str, entities: List[str]) -> bool:
        """
        基于实体构建业务关联关系
        
        Args:
            business_id: 业务ID
            entities: 实体列表
            
        Returns:
            是否构建成功
        """
        try:
            # 添加业务实体
            self.add_business_entities(business_id, entities)
            
            # 查找共享实体的其他业务
            related_businesses = set()
            for entity in entities:
                businesses = self.get_businesses_by_entity(entity)
                for other_business in businesses:
                    if other_business != business_id:
                        related_businesses.add(other_business)
            
            # 为每个相关业务计算关联强度并添加关系
            for other_business in related_businesses:
                shared_entities = self.get_shared_entities(business_id, other_business)
                if shared_entities:
                    # 计算关联权重
                    weight = self._calculate_relation_weight(business_id, other_business, shared_entities)
                    
                    # 添加关联关系
                    self.add_relation(
                        business_a=business_id,
                        business_b=other_business,
                        relation_type=RELATION_TYPE_SHARED_ENTITY,
                        weight=weight,
                        shared_entities=shared_entities
                    )
            
            logger.info(f"为业务 '{business_id}' 构建了与 {len(related_businesses)} 个业务的关联关系")
            return True
            
        except Exception as e:
            logger.error(f"构建关联关系失败: {str(e)}")
            return False
    
    def add_relation(
        self,
        business_a: str,
        business_b: str,
        relation_type: str = RELATION_TYPE_SHARED_ENTITY,
        weight: float = 1.0,
        shared_entities: Optional[List[str]] = None
    ) -> bool:
        """
        添加业务关联关系
        
        Args:
            business_a: 业务A的ID
            business_b: 业务B的ID
            relation_type: 关系类型
            weight: 关系权重
            shared_entities: 共享实体列表
            
        Returns:
            是否添加成功
        """
        with self.sync_lock:
            if business_a == business_b:
                return False  # 不添加自身关联
            
            # 确保关系字典存在
            if business_a not in self.relations["relations"]:
                self.relations["relations"][business_a] = {}
            
            # 添加或更新关系
            if business_b in self.relations["relations"][business_a]:
                # 更新现有关系
                existing = self.relations["relations"][business_a][business_b]
                existing["weight"] = max(existing["weight"], weight)
                if shared_entities:
                    existing_entities = set(existing.get("entities", []))
                    new_entities = set(shared_entities)
                    existing["entities"] = list(existing_entities | new_entities)
            else:
                # 创建新关系
                self.relations["relations"][business_a][business_b] = {
                    "type": relation_type,
                    "weight": weight,
                    "entities": shared_entities or []
                }
            
            # 添加反向关系（双向）
            if business_b not in self.relations["relations"]:
                self.relations["relations"][business_b] = {}
            
            if business_a in self.relations["relations"][business_b]:
                # 更新现有反向关系
                existing = self.relations["relations"][business_b][business_a]
                existing["weight"] = max(existing["weight"], weight)
                if shared_entities:
                    existing_entities = set(existing.get("entities", []))
                    new_entities = set(shared_entities)
                    existing["entities"] = list(existing_entities | new_entities)
            else:
                # 创建新反向关系
                self.relations["relations"][business_b][business_a] = {
                    "type": relation_type,
                    "weight": weight,
                    "entities": shared_entities or []
                }
            
            return self._save_relations()
    
    def get_related_businesses(
        self,
        business_id: str,
        min_weight: float = 0.0,
        max_count: int = 5
    ) -> List[str]:
        """
        获取相关业务列表
        
        Args:
            business_id: 业务ID
            min_weight: 最小权重阈值
            max_count: 最大返回数量
            
        Returns:
            相关业务ID列表，按权重排序
        """
        if business_id not in self.relations["relations"]:
            return []
        
        # 获取所有相关业务及其权重
        related = []
        for other_business, relation in self.relations["relations"][business_id].items():
            weight = relation.get("weight", 0.0)
            if weight >= min_weight:
                related.append((other_business, weight))
        
        # 按权重排序
        related.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前max_count个业务ID
        return [business_id for business_id, _ in related[:max_count]]
    
    def _calculate_relation_weight(
        self,
        business_a: str,
        business_b: str,
        shared_entities: List[str]
    ) -> float:
        """
        计算关联权重
        
        Args:
            business_a: 业务A的ID
            business_b: 业务B的ID
            shared_entities: 共享实体列表
            
        Returns:
            关联权重
        """
        if not shared_entities:
            return 0.0
        
        entities_a = self.get_business_entities(business_a)
        entities_b = self.get_business_entities(business_b)
        
        if not entities_a or not entities_b:
            return 0.0
        
        # 使用Jaccard相似度计算权重
        shared_count = len(shared_entities)
        total_count = len(set(entities_a) | set(entities_b))
        
        if total_count == 0:
            return 0.0
        
        return shared_count / total_count
    
    def get_relation_details(self, business_a: str, business_b: str) -> Optional[Dict[str, Any]]:
        """
        获取两个业务间的关系详情
        
        Args:
            business_a: 业务A的ID
            business_b: 业务B的ID
            
        Returns:
            关系详情，如果不存在则返回None
        """
        if business_a not in self.relations["relations"]:
            return None
        
        if business_b not in self.relations["relations"][business_a]:
            return None
        
        return self.relations["relations"][business_a][business_b].copy()


class SimpleEntityExtractor:
    """
    简单的实体提取器
    
    当无法加载复杂的实体提取器时使用的备用方案。
    """
    
    def extract_entities(self, text: str, max_entities: int = 15) -> List[str]:
        """
        简单的实体提取
        
        Args:
            text: 文本内容
            max_entities: 最大实体数量
            
        Returns:
            提取的实体列表
        """
        try:
            # 使用简单的关键词提取
            import re
            
            # 提取中文词汇（2-6个字符）
            chinese_words = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
            
            # 提取英文词汇
            english_words = re.findall(r'[A-Za-z]{3,}', text)
            
            # 合并并去重
            all_words = list(set(chinese_words + english_words))
            
            # 过滤常见停用词
            stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', '而', '了', '也', '就', '都', '要', '可以', '能够', 'the', 'and', 'or', 'but', 'with', 'for', 'to', 'of', 'in', 'on', 'at'}
            filtered_words = [word for word in all_words if word.lower() not in stop_words]
            
            # 返回前max_entities个
            return filtered_words[:max_entities]
            
        except Exception as e:
            logger.error(f"简单实体提取失败: {str(e)}")
            return []
