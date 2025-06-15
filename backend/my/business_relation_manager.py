"""
业务关联关系管理模块

本模块实现业务知识库之间的关联关系管理，包括：
1. 记录业务之间的关联关系
2. 基于实体和查询历史动态更新关联强度
3. 提供跨业务知识检索支持

使用方法:
```python
# 创建业务关联管理器
relation_manager = BusinessRelationManager(base_dir)

# 添加业务关联
relation_manager.add_relation("business_a", "business_b", weight=0.5)

# 获取相关业务
related = relation_manager.get_related_businesses("business_a")
```
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BusinessRelationManager:
    """业务关联关系管理"""
    
    def __init__(self, base_dir: Path):
        """
        初始化业务关联管理器
        
        Args:
            base_dir: 基础目录，用于存储关联关系文件
        """
        self.base_dir = base_dir
        self.relation_file = base_dir / "business_relations.json"
        self.relations = self._load_relations()
        logger.info(f"业务关联管理器初始化完成，关联文件: {self.relation_file}")
        
    def _load_relations(self) -> Dict[str, Any]:
        """加载关联关系数据"""
        if self.relation_file.exists():
            try:
                with open(self.relation_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载关联关系失败: {str(e)}")
                return {"relations": {}, "entity_map": {}}
        else:
            return {"relations": {}, "entity_map": {}}
    
    def _save_relations(self):
        """保存关联关系数据"""
        try:
            with open(self.relation_file, 'w', encoding='utf-8') as f:
                json.dump(self.relations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存关联关系失败: {str(e)}")
    
    def add_relation(self, business_a: str, business_b: str, relation_type: str = "related", 
                    weight: float = 1.0, entity: str = None):
        """
        添加业务关联关系
        
        Args:
            business_a: 业务A的ID
            business_b: 业务B的ID
            relation_type: 关联类型，如"related"、"shared_entity"、"query_usage"
            weight: 关联权重
            entity: 关联实体（如果有）
        """
        if business_a == business_b:
            return  # 不添加自身关联
            
        # 确保业务A的关系字典存在
        if business_a not in self.relations["relations"]:
            self.relations["relations"][business_a] = {}
            
        # 确保业务B的关系字典存在
        if business_b not in self.relations["relations"]:
            self.relations["relations"][business_b] = {}
            
        # 更新A到B的关系权重
        if business_b in self.relations["relations"][business_a]:
            current_weight = self.relations["relations"][business_a][business_b]["weight"]
            self.relations["relations"][business_a][business_b]["weight"] = current_weight + weight
            # 记录关系类型（如果是新类型）
            if relation_type not in self.relations["relations"][business_a][business_b]["types"]:
                self.relations["relations"][business_a][business_b]["types"].append(relation_type)
        else:
            self.relations["relations"][business_a][business_b] = {
                "types": [relation_type],
                "weight": weight,
                "entities": []
            }
        
        # 更新B到A的关系权重（双向关系）
        if business_a in self.relations["relations"][business_b]:
            current_weight = self.relations["relations"][business_b][business_a]["weight"]
            self.relations["relations"][business_b][business_a]["weight"] = current_weight + weight
            # 记录关系类型（如果是新类型）
            if relation_type not in self.relations["relations"][business_b][business_a]["types"]:
                self.relations["relations"][business_b][business_a]["types"].append(relation_type)
        else:
            self.relations["relations"][business_b][business_a] = {
                "types": [relation_type],
                "weight": weight,
                "entities": []
            }
        
        # 如果提供了实体，添加到关联实体列表
        if entity:
            if entity not in self.relations["relations"][business_a][business_b]["entities"]:
                self.relations["relations"][business_a][business_b]["entities"].append(entity)
            if entity not in self.relations["relations"][business_b][business_a]["entities"]:
                self.relations["relations"][business_b][business_a]["entities"].append(entity)
                
            # 更新实体映射
            if entity not in self.relations["entity_map"]:
                self.relations["entity_map"][entity] = []
            if business_a not in self.relations["entity_map"][entity]:
                self.relations["entity_map"][entity].append(business_a)
            if business_b not in self.relations["entity_map"][entity]:
                self.relations["entity_map"][entity].append(business_b)
        
        # 保存关系
        self._save_relations()
        logger.info(f"添加业务关联: {business_a} <-> {business_b}, 类型: {relation_type}, 权重: {weight}")
    
    def get_related_businesses(self, business_id: str, max_count: int = 3) -> List[str]:
        """
        获取与指定业务相关的业务列表，按权重排序
        
        Args:
            business_id: 业务ID
            max_count: 最大返回数量
            
        Returns:
            相关业务ID列表
        """
        if business_id not in self.relations["relations"]:
            return []
            
        # 按权重排序相关业务
        related = [(b, info["weight"]) for b, info in self.relations["relations"][business_id].items()]
        related.sort(key=lambda x: x[1], reverse=True)
        
        return [b for b, _ in related[:max_count]]
    
    def get_businesses_by_entity(self, entity: str) -> List[str]:
        """
        获取包含指定实体的所有业务
        
        Args:
            entity: 实体名称
            
        Returns:
            业务ID列表
        """
        return self.relations["entity_map"].get(entity, [])
    
    def record_query_usage(self, query_business: str, used_businesses: Dict[str, int]):
        """
        记录查询使用情况，用于动态优化业务关联
        
        Args:
            query_business: 查询的主业务ID
            used_businesses: 使用的业务ID及次数，如 {"business_b": 2, "business_c": 1}
        """
        for business, count in used_businesses.items():
            if business != query_business:
                # 使用次数作为权重增量，但设置上限
                weight_increment = min(count * 0.2, 1.0)
                self.add_relation(
                    business_a=query_business,
                    business_b=business,
                    relation_type="query_usage",
                    weight=weight_increment
                )
                logger.info(f"记录查询使用: {query_business} -> {business}, 权重增量: {weight_increment}")
    
    def extract_entities(self, text: str, max_entities: int = 10) -> List[str]:
        """
        从文本中提取实体（简化实现）
        
        Args:
            text: 文本内容
            max_entities: 最大实体数量
            
        Returns:
            实体列表
        """
        try:
            # 简单的关键词提取（实际项目中应使用更复杂的NER）
            from sklearn.feature_extraction.text import TfidfVectorizer
            vectorizer = TfidfVectorizer(max_features=max_entities)
            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            
            # 获取最重要的词作为实体
            entities = list(feature_names)
            return entities
        except Exception as e:
            logger.error(f"提取实体失败: {str(e)}")
            # 简单分词作为备选
            words = text.split()
            entities = list(set([w for w in words if len(w) > 2]))[:max_entities]
            return entities
    
    def build_relations_from_entities(self, business_id: str, entities: List[str], 
                                     initial_weight: float = 0.5):
        """
        基于实体构建业务关联
        
        Args:
            business_id: 业务ID
            entities: 实体列表
            initial_weight: 初始关联权重
        """
        for entity in entities:
            # 获取包含该实体的其他业务
            businesses = self.get_businesses_by_entity(entity)
            
            # 为每个业务添加关联
            for other_business in businesses:
                if other_business != business_id:
                    self.add_relation(
                        business_a=business_id,
                        business_b=other_business,
                        relation_type="shared_entity",
                        weight=initial_weight,
                        entity=entity
                    )
            
            # 将实体添加到映射
            if entity not in self.relations["entity_map"]:
                self.relations["entity_map"][entity] = []
            if business_id not in self.relations["entity_map"][entity]:
                self.relations["entity_map"][entity].append(business_id)
                self._save_relations()