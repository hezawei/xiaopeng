"""
混合搜索引擎

负责跨业务的混合搜索功能，包括：
1. 基于关联关系的跨业务搜索
2. 搜索结果的合并和排序
3. 关联强度的动态调整
4. 搜索历史的记录和分析

这是混合搜索功能的核心实现，被独立拆分以提高可维护性和可扩展性。
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    混合搜索引擎
    
    负责实现跨业务的混合搜索功能，这是系统的核心特性之一。
    通过关联关系管理器获取业务间的关联信息，然后进行跨业务搜索。
    """
    
    def __init__(self, index_manager, relation_manager, metadata_manager):
        """
        初始化混合搜索引擎
        
        Args:
            index_manager: 索引管理器
            relation_manager: 关联关系管理器
            metadata_manager: 元数据管理器
        """
        self.index_manager = index_manager
        self.relation_manager = relation_manager
        self.metadata_manager = metadata_manager
        
        # 搜索历史记录
        self.search_history = []
        
        logger.info("混合搜索引擎初始化完成")
    
    async def cross_business_search(
        self,
        primary_business_id: str,
        query: str,
        expand_to_related: bool = True,
        max_related_businesses: int = 2,
        response_mode: str = "compact",
        similarity_top_k: int = 3
    ) -> Dict[str, Any]:
        """
        跨业务搜索
        
        Args:
            primary_business_id: 主业务ID
            query: 查询文本
            expand_to_related: 是否扩展到相关业务
            max_related_businesses: 最大相关业务数量
            response_mode: 响应模式
            similarity_top_k: 每个业务返回的相似结果数量
            
        Returns:
            搜索结果
        """
        try:
            logger.info(f"开始跨业务搜索，主业务: {primary_business_id}, 查询: {query}")
            
            # 记录搜索历史
            self._record_search_history(primary_business_id, query)
            
            # 首先搜索主业务
            primary_results = await self._search_single_business(
                primary_business_id, query, similarity_top_k
            )
            
            # 如果不需要扩展到相关业务，直接返回主业务结果
            if not expand_to_related:
                return self._format_single_business_result(
                    primary_business_id, primary_results, query, response_mode
                )
            
            # 获取相关业务
            related_businesses = self.relation_manager.get_related_businesses(
                primary_business_id, max_count=max_related_businesses
            )
            
            if not related_businesses:
                logger.info(f"业务 '{primary_business_id}' 没有相关业务")
                return self._format_single_business_result(
                    primary_business_id, primary_results, query, response_mode
                )
            
            # 搜索相关业务
            related_results = []
            for related_business_id in related_businesses:
                try:
                    # 检查相关业务是否存在
                    if not self.metadata_manager.business_exists(related_business_id):
                        logger.warning(f"相关业务 '{related_business_id}' 不存在，跳过")
                        continue
                    
                    # 搜索相关业务
                    business_results = await self._search_single_business(
                        related_business_id, query, similarity_top_k
                    )
                    
                    if business_results:
                        # 获取业务信息
                        business_info = self.metadata_manager.get_business_info(related_business_id)
                        business_name = business_info.get("name", related_business_id)
                        
                        # 获取关联详情
                        relation_details = self.relation_manager.get_relation_details(
                            primary_business_id, related_business_id
                        )
                        
                        related_results.append({
                            "business_id": related_business_id,
                            "business_name": business_name,
                            "results": business_results,
                            "relation_weight": relation_details.get("weight", 0.0) if relation_details else 0.0,
                            "shared_entities": relation_details.get("entities", []) if relation_details else []
                        })
                        
                except Exception as e:
                    logger.error(f"搜索相关业务 '{related_business_id}' 失败: {str(e)}")
            
            # 更新关联强度（基于查询历史）
            self._update_relation_weights(primary_business_id, related_businesses, query)
            
            # 合并和格式化结果
            return self._format_cross_business_result(
                primary_business_id, primary_results, related_results, query, response_mode
            )
            
        except Exception as e:
            logger.error(f"跨业务搜索失败: {str(e)}")
            return {
                "response": f"搜索失败: {str(e)}",
                "source_nodes": [],
                "related_businesses": []
            }
    
    async def _search_single_business(
        self,
        business_id: str,
        query: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        搜索单个业务
        
        Args:
            business_id: 业务ID
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        try:
            # 检查业务是否存在
            if not self.metadata_manager.business_exists(business_id):
                logger.warning(f"业务 '{business_id}' 不存在")
                return []
            
            # 检查索引是否存在
            if not self.index_manager.collection_exists(business_id):
                logger.warning(f"业务 '{business_id}' 的索引不存在")
                return []
            
            # 执行搜索
            results = await self.index_manager.search(business_id, query, top_k)
            
            # 添加业务信息到结果中
            for result in results:
                result["business_id"] = business_id
            
            return results
            
        except Exception as e:
            logger.error(f"搜索业务 '{business_id}' 失败: {str(e)}")
            return []
    
    def _format_single_business_result(
        self,
        business_id: str,
        results: List[Dict[str, Any]],
        query: str,
        response_mode: str
    ) -> Dict[str, Any]:
        """
        格式化单业务搜索结果
        
        Args:
            business_id: 业务ID
            results: 搜索结果
            query: 查询文本
            response_mode: 响应模式
            
        Returns:
            格式化后的结果
        """
        if not results:
            return {
                "response": f"在业务 '{business_id}' 中未找到与查询 '{query}' 相关的信息。",
                "source_nodes": []
            }
        
        # 生成响应文本
        if response_mode == "compact":
            response_text = f"根据查询 '{query}'，在业务 '{business_id}' 中找到以下相关信息:\n\n"
            for i, result in enumerate(results):
                response_text += f"{i+1}. {result['text'][:200]}...\n\n"
        else:
            # 详细模式
            response_text = f"查询 '{query}' 的详细结果:\n\n"
            for i, result in enumerate(results):
                response_text += f"结果 {i+1} (相关度: {result.get('score', 0):.4f}):\n{result['text']}\n\n"
        
        return {
            "response": response_text,
            "source_nodes": results
        }
    
    def _format_cross_business_result(
        self,
        primary_business_id: str,
        primary_results: List[Dict[str, Any]],
        related_results: List[Dict[str, Any]],
        query: str,
        response_mode: str
    ) -> Dict[str, Any]:
        """
        格式化跨业务搜索结果
        
        Args:
            primary_business_id: 主业务ID
            primary_results: 主业务搜索结果
            related_results: 相关业务搜索结果
            query: 查询文本
            response_mode: 响应模式
            
        Returns:
            格式化后的结果
        """
        if response_mode == "detailed":
            # 详细模式：分别显示各业务的结果
            return self._format_detailed_cross_business_result(
                primary_business_id, primary_results, related_results, query
            )
        else:
            # 紧凑模式：合并所有结果
            return self._format_compact_cross_business_result(
                primary_business_id, primary_results, related_results, query
            )
    
    def _format_detailed_cross_business_result(
        self,
        primary_business_id: str,
        primary_results: List[Dict[str, Any]],
        related_results: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        格式化详细模式的跨业务搜索结果
        """
        # 获取主业务信息
        primary_business_info = self.metadata_manager.get_business_info(primary_business_id)
        primary_business_name = primary_business_info.get("name", primary_business_id)
        
        # 生成主业务响应
        if primary_results:
            response_text = f"在主业务 '{primary_business_name}' 中找到以下相关信息:\n\n"
            for i, result in enumerate(primary_results):
                response_text += f"{i+1}. {result['text'][:200]}...\n\n"
        else:
            response_text = f"在主业务 '{primary_business_name}' 中未找到相关信息。\n\n"
        
        # 处理相关业务结果
        formatted_related = []
        for related in related_results:
            business_name = related["business_name"]
            business_results = related["results"]
            
            if business_results:
                related_response = f"在相关业务 '{business_name}' 中找到以下信息:\n\n"
                for i, result in enumerate(business_results):
                    related_response += f"{i+1}. {result['text'][:200]}...\n\n"
            else:
                related_response = f"在相关业务 '{business_name}' 中未找到相关信息。"
            
            formatted_related.append({
                "business_id": related["business_id"],
                "business_name": business_name,
                "response": related_response,
                "source_nodes": business_results,
                "relation_weight": related["relation_weight"],
                "shared_entities": related["shared_entities"]
            })
        
        return {
            "response": response_text,
            "source_nodes": primary_results,
            "related_businesses": formatted_related
        }
    
    def _format_compact_cross_business_result(
        self,
        primary_business_id: str,
        primary_results: List[Dict[str, Any]],
        related_results: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        格式化紧凑模式的跨业务搜索结果
        """
        # 合并所有搜索结果
        all_source_nodes = primary_results.copy()
        
        # 收集所有相关业务的结果
        for related in related_results:
            for result in related["results"]:
                # 添加业务信息
                result["business_id"] = related["business_id"]
                result["business_name"] = related["business_name"]
                result["relation_weight"] = related["relation_weight"]
                all_source_nodes.append(result)
        
        # 按相关度和关联权重排序
        all_source_nodes.sort(
            key=lambda x: (x.get("score", 0) * (1 + x.get("relation_weight", 0))), 
            reverse=True
        )
        
        # 生成综合响应
        if all_source_nodes:
            response_text = f"根据查询 '{query}'，在相关业务中找到以下信息:\n\n"
            
            for i, result in enumerate(all_source_nodes[:5]):  # 只显示前5个结果
                business_name = result.get("business_name", "")
                if business_name:
                    response_text += f"{i+1}. [来自 {business_name}] {result['text'][:200]}...\n\n"
                else:
                    response_text += f"{i+1}. {result['text'][:200]}...\n\n"
        else:
            response_text = f"未找到与查询 '{query}' 相关的信息。"
        
        return {
            "response": response_text,
            "source_nodes": all_source_nodes
        }
    
    def _record_search_history(self, business_id: str, query: str):
        """
        记录搜索历史
        
        Args:
            business_id: 业务ID
            query: 查询文本
        """
        try:
            search_record = {
                "business_id": business_id,
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
            
            self.search_history.append(search_record)
            
            # 保持历史记录在合理范围内
            if len(self.search_history) > 1000:
                self.search_history = self.search_history[-500:]
                
        except Exception as e:
            logger.error(f"记录搜索历史失败: {str(e)}")
    
    def _update_relation_weights(
        self,
        primary_business_id: str,
        related_businesses: List[str],
        query: str
    ):
        """
        基于查询历史更新关联权重
        
        Args:
            primary_business_id: 主业务ID
            related_businesses: 相关业务列表
            query: 查询文本
        """
        try:
            # 为每个相关业务增加查询使用权重
            for related_business_id in related_businesses:
                self.relation_manager.add_relation(
                    business_a=primary_business_id,
                    business_b=related_business_id,
                    relation_type="query_usage",
                    weight=0.1  # 每次查询增加0.1的权重
                )
                
        except Exception as e:
            logger.error(f"更新关联权重失败: {str(e)}")
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """
        获取搜索统计信息
        
        Returns:
            搜索统计信息
        """
        try:
            from collections import Counter
            
            # 统计业务查询频率
            business_counts = Counter([record["business_id"] for record in self.search_history])
            
            # 统计查询关键词
            query_counts = Counter([record["query"] for record in self.search_history])
            
            return {
                "total_searches": len(self.search_history),
                "most_searched_businesses": business_counts.most_common(5),
                "most_common_queries": query_counts.most_common(10),
                "recent_searches": self.search_history[-10:] if self.search_history else []
            }
            
        except Exception as e:
            logger.error(f"获取搜索统计失败: {str(e)}")
            return {
                "total_searches": 0,
                "error": str(e)
            }
