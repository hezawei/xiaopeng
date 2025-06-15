"""
查询引擎

负责查询逻辑的处理和结果合并，包括：
1. 单业务查询处理
2. 查询结果的格式化
3. 不同响应模式的支持
4. 查询性能优化
"""

import logging
from typing import Dict, Any, List, Optional

# 设置日志
logger = logging.getLogger(__name__)


class QueryEngine:
    """
    查询引擎
    
    负责处理各种查询请求，包括单业务查询和跨业务查询。
    提供统一的查询接口和结果格式化功能。
    """
    
    def __init__(self, index_manager, hybrid_search_engine):
        """
        初始化查询引擎
        
        Args:
            index_manager: 索引管理器
            hybrid_search_engine: 混合搜索引擎
        """
        self.index_manager = index_manager
        self.hybrid_search_engine = hybrid_search_engine
        
        logger.info("查询引擎初始化完成")
    
    async def query_single_business(
        self,
        business_id: str,
        query: str,
        similarity_top_k: int = 3,
        response_mode: str = "compact"
    ) -> Dict[str, Any]:
        """
        查询单个业务知识库
        
        Args:
            business_id: 业务ID
            query: 查询文本
            similarity_top_k: 返回的相似结果数量
            response_mode: 响应模式
            
        Returns:
            查询结果
        """
        try:
            logger.info(f"查询单业务: {business_id}, 查询: {query}")
            
            # 检查索引是否存在
            if not self.index_manager.collection_exists(business_id):
                logger.warning(f"业务 '{business_id}' 的索引不存在")
                return {
                    "response": f"业务 '{business_id}' 的索引不存在，请先添加文档并创建索引。",
                    "source_nodes": []
                }
            
            # 检查集合中是否有数据
            stats = self.index_manager.get_collection_stats(business_id)
            if stats.get("row_count", 0) == 0:
                return {
                    "response": f"业务 '{business_id}' 中没有数据，请先添加文档。",
                    "source_nodes": []
                }
            
            # 执行搜索
            search_results = await self.index_manager.search(
                business_id, query, similarity_top_k
            )
            
            # 构建响应
            return self._build_response(query, search_results, response_mode)
            
        except Exception as e:
            logger.error(f"查询单业务失败: {str(e)}")
            return {
                "response": f"查询失败: {str(e)}",
                "source_nodes": []
            }
    
    async def query_cross_business(
        self,
        primary_business_id: str,
        query: str,
        expand_to_related: bool = True,
        max_related_businesses: int = 2,
        response_mode: str = "compact",
        similarity_top_k: int = 3
    ) -> Dict[str, Any]:
        """
        跨业务查询
        
        Args:
            primary_business_id: 主业务ID
            query: 查询文本
            expand_to_related: 是否扩展到相关业务
            max_related_businesses: 最大相关业务数量
            response_mode: 响应模式
            similarity_top_k: 每个业务返回的相似结果数量
            
        Returns:
            查询结果
        """
        return await self.hybrid_search_engine.cross_business_search(
            primary_business_id=primary_business_id,
            query=query,
            expand_to_related=expand_to_related,
            max_related_businesses=max_related_businesses,
            response_mode=response_mode,
            similarity_top_k=similarity_top_k
        )
    
    def _build_response(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        response_mode: str
    ) -> Dict[str, Any]:
        """
        构建查询响应
        
        Args:
            query: 查询文本
            search_results: 搜索结果
            response_mode: 响应模式
            
        Returns:
            构建的响应
        """
        if response_mode == "compact":
            return self._build_compact_response(query, search_results)
        elif response_mode == "tree_summarize":
            return self._build_tree_summarize_response(query, search_results)
        elif response_mode == "refine":
            return self._build_refine_response(query, search_results)
        elif response_mode == "detailed":
            return self._build_detailed_response(query, search_results)
        else:
            logger.warning(f"未知的响应模式: {response_mode}，使用compact模式")
            return self._build_compact_response(query, search_results)
    
    def _build_compact_response(
        self,
        query: str,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建紧凑模式的响应
        
        Args:
            query: 查询文本
            search_results: 搜索结果
            
        Returns:
            紧凑模式的响应
        """
        if not search_results:
            return {
                "response": f"未找到与查询 '{query}' 相关的信息。",
                "source_nodes": []
            }
        
        response_text = f"根据查询 '{query}'，找到以下相关信息:\n\n"
        for i, result in enumerate(search_results):
            # 截取文本的前200个字符
            text_preview = result.get("text", "")[:200]
            if len(result.get("text", "")) > 200:
                text_preview += "..."
            
            response_text += f"{i+1}. {text_preview}\n\n"
        
        return {
            "response": response_text,
            "source_nodes": search_results
        }
    
    def _build_detailed_response(
        self,
        query: str,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建详细模式的响应
        
        Args:
            query: 查询文本
            search_results: 搜索结果
            
        Returns:
            详细模式的响应
        """
        if not search_results:
            return {
                "response": f"未找到与查询 '{query}' 相关的信息。",
                "source_nodes": []
            }
        
        response_text = f"查询 '{query}' 的详细结果:\n\n"
        for i, result in enumerate(search_results):
            score = result.get("score", 0)
            text = result.get("text", "")
            
            response_text += f"结果 {i+1} (相关度: {score:.4f}):\n"
            response_text += f"{text}\n"
            response_text += "-" * 50 + "\n\n"
        
        return {
            "response": response_text,
            "source_nodes": search_results
        }
    
    def _build_tree_summarize_response(
        self,
        query: str,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建树状总结模式的响应
        
        Args:
            query: 查询文本
            search_results: 搜索结果
            
        Returns:
            树状总结模式的响应
        """
        # 这里可以实现更复杂的树状总结逻辑
        # 目前使用紧凑模式的响应作为备用
        logger.info("树状总结模式暂未完全实现，使用紧凑模式")
        return self._build_compact_response(query, search_results)
    
    def _build_refine_response(
        self,
        query: str,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建细化模式的响应
        
        Args:
            query: 查询文本
            search_results: 搜索结果
            
        Returns:
            细化模式的响应
        """
        # 这里可以实现更复杂的细化逻辑
        # 目前使用详细模式的响应作为备用
        logger.info("细化模式暂未完全实现，使用详细模式")
        return self._build_detailed_response(query, search_results)
    
    async def batch_query(
        self,
        queries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量查询
        
        Args:
            queries: 查询列表，每个查询包含business_id, query, 和其他参数
            
        Returns:
            查询结果列表
        """
        results = []
        
        for query_info in queries:
            try:
                business_id = query_info.get("business_id")
                query_text = query_info.get("query")
                similarity_top_k = query_info.get("similarity_top_k", 3)
                response_mode = query_info.get("response_mode", "compact")
                
                if not business_id or not query_text:
                    results.append({
                        "error": "缺少必要参数 business_id 或 query",
                        "query_info": query_info
                    })
                    continue
                
                # 执行查询
                result = await self.query_single_business(
                    business_id, query_text, similarity_top_k, response_mode
                )
                
                # 添加查询信息到结果中
                result["query_info"] = query_info
                results.append(result)
                
            except Exception as e:
                logger.error(f"批量查询中的单个查询失败: {str(e)}")
                results.append({
                    "error": str(e),
                    "query_info": query_info
                })
        
        return results
    
    def get_query_suggestions(
        self,
        business_id: str,
        partial_query: str,
        max_suggestions: int = 5
    ) -> List[str]:
        """
        获取查询建议
        
        Args:
            business_id: 业务ID
            partial_query: 部分查询文本
            max_suggestions: 最大建议数量
            
        Returns:
            查询建议列表
        """
        try:
            # 这里可以实现基于历史查询、实体等的查询建议
            # 目前返回简单的建议
            suggestions = []
            
            # 基于部分查询生成建议
            if len(partial_query) >= 2:
                # 可以从搜索历史中查找相似查询
                # 可以从业务实体中查找匹配的实体
                # 目前返回一些通用建议
                common_queries = [
                    f"{partial_query}的功能",
                    f"{partial_query}的特点",
                    f"{partial_query}的应用",
                    f"{partial_query}的优势",
                    f"{partial_query}的原理"
                ]
                
                suggestions.extend(common_queries[:max_suggestions])
            
            return suggestions
            
        except Exception as e:
            logger.error(f"获取查询建议失败: {str(e)}")
            return []
    
    def analyze_query_performance(
        self,
        business_id: str,
        query: str
    ) -> Dict[str, Any]:
        """
        分析查询性能
        
        Args:
            business_id: 业务ID
            query: 查询文本
            
        Returns:
            性能分析结果
        """
        try:
            import time
            
            start_time = time.time()
            
            # 获取集合统计信息
            stats = self.index_manager.get_collection_stats(business_id)
            
            # 模拟查询（不返回结果，只测试性能）
            # 这里可以添加更详细的性能分析逻辑
            
            end_time = time.time()
            query_time = end_time - start_time
            
            return {
                "business_id": business_id,
                "query": query,
                "collection_exists": stats.get("exists", False),
                "document_count": stats.get("row_count", 0),
                "query_time": query_time,
                "estimated_complexity": "low" if len(query) < 20 else "medium" if len(query) < 50 else "high"
            }
            
        except Exception as e:
            logger.error(f"分析查询性能失败: {str(e)}")
            return {
                "business_id": business_id,
                "query": query,
                "error": str(e)
            }
