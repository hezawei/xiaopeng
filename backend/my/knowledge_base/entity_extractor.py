"""
实体提取器

负责从文档文本中提取实体，支持多种提取方法：
1. 基于规则的实体提取
2. 基于TF-IDF的关键词提取
3. 基于NLP模型的命名实体识别
4. 基于LLM的智能实体提取

这是关联关系构建的核心组件，被独立拆分以提高可维护性。
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from collections import Counter

# 设置日志
logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    实体提取器
    
    提供多种实体提取方法，可以根据需要选择合适的提取策略。
    """
    
    def __init__(self):
        """
        初始化实体提取器
        """
        # TF-IDF向量化器（延迟加载）
        self._tfidf_vectorizer = None
        
        # NLP模型（延迟加载）
        self._nlp_model = None
        
        # LLM客户端（延迟加载）
        self._llm_client = None
        
        # 停用词集合
        self.stop_words = self._load_stop_words()
        
        logger.info("实体提取器初始化完成")
    
    def _load_stop_words(self) -> Set[str]:
        """
        加载停用词
        
        Returns:
            停用词集合
        """
        # 中文停用词
        chinese_stop_words = {
            '的', '是', '在', '有', '和', '与', '或', '但', '而', '了', '也', '就', '都', '要',
            '可以', '能够', '应该', '必须', '需要', '可能', '或许', '也许', '如果', '因为',
            '所以', '因此', '然后', '接着', '最后', '首先', '其次', '另外', '此外', '同时',
            '不过', '然而', '虽然', '尽管', '除了', '除非', '只要', '只有', '无论', '不管',
            '通过', '根据', '按照', '依据', '基于', '关于', '对于', '针对', '面对', '朝向'
        }
        
        # 英文停用词
        english_stop_words = {
            'the', 'and', 'or', 'but', 'with', 'for', 'to', 'of', 'in', 'on', 'at',
            'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'must', 'shall', 'this', 'that',
            'these', 'those', 'a', 'an', 'some', 'any', 'all', 'each', 'every',
            'no', 'not', 'only', 'just', 'also', 'even', 'still', 'yet', 'already'
        }
        
        return chinese_stop_words | english_stop_words
    
    @property
    def tfidf_vectorizer(self):
        """
        延迟加载TF-IDF向量化器
        
        Returns:
            TF-IDF向量化器实例
        """
        if self._tfidf_vectorizer is None:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                self._tfidf_vectorizer = TfidfVectorizer(
                    max_features=1000,
                    stop_words=None,  # 我们自己处理停用词
                    ngram_range=(1, 2),  # 支持1-2元组
                    min_df=1,  # 最小文档频率
                    max_df=1.0,  # 最大文档频率，避免单文档时的冲突
                    lowercase=True
                )
                logger.info("TF-IDF向量化器加载成功")
            except ImportError as e:
                logger.warning(f"无法加载TF-IDF向量化器: {str(e)}")
                self._tfidf_vectorizer = None
        
        return self._tfidf_vectorizer
    
    def extract_entities(
        self,
        text: str,
        method: str = "hybrid",
        max_entities: int = 15
    ) -> List[str]:
        """
        提取实体
        
        Args:
            text: 文本内容
            method: 提取方法，可选值: rule, tfidf, nlp, llm, hybrid
            max_entities: 最大实体数量
            
        Returns:
            提取的实体列表
        """
        try:
            if method == "rule":
                return self._extract_by_rules(text, max_entities)
            elif method == "tfidf":
                return self._extract_by_tfidf(text, max_entities)
            elif method == "nlp":
                return self._extract_by_nlp(text, max_entities)
            elif method == "llm":
                return self._extract_by_llm(text, max_entities)
            elif method == "hybrid":
                return self._extract_by_hybrid(text, max_entities)
            else:
                logger.warning(f"未知的提取方法: {method}，使用默认方法")
                return self._extract_by_rules(text, max_entities)
                
        except Exception as e:
            logger.error(f"实体提取失败: {str(e)}")
            return []
    
    def _extract_by_rules(self, text: str, max_entities: int) -> List[str]:
        """
        基于规则的实体提取
        
        Args:
            text: 文本内容
            max_entities: 最大实体数量
            
        Returns:
            提取的实体列表
        """
        entities = []
        
        # 提取中文词汇（2-8个字符）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,8}', text)
        entities.extend(chinese_words)
        
        # 提取英文词汇（3个字符以上）
        english_words = re.findall(r'[A-Za-z]{3,}', text)
        entities.extend(english_words)
        
        # 提取数字+单位的组合
        number_units = re.findall(r'\d+[\u4e00-\u9fff]{1,3}', text)
        entities.extend(number_units)
        
        # 提取专业术语（包含英文和中文的组合）
        mixed_terms = re.findall(r'[A-Za-z]+[\u4e00-\u9fff]+|[\u4e00-\u9fff]+[A-Za-z]+', text)
        entities.extend(mixed_terms)
        
        # 去重并过滤停用词
        unique_entities = []
        seen = set()
        for entity in entities:
            entity_lower = entity.lower()
            if (entity_lower not in self.stop_words and 
                entity not in seen and 
                len(entity.strip()) > 1):
                unique_entities.append(entity)
                seen.add(entity)
        
        # 按长度排序，优先选择较长的实体
        unique_entities.sort(key=len, reverse=True)
        
        return unique_entities[:max_entities]
    
    def _extract_by_tfidf(self, text: str, max_entities: int) -> List[str]:
        """
        基于TF-IDF的关键词提取

        Args:
            text: 文本内容
            max_entities: 最大实体数量

        Returns:
            提取的实体列表
        """
        if self.tfidf_vectorizer is None:
            logger.warning("TF-IDF向量化器不可用，使用规则方法")
            return self._extract_by_rules(text, max_entities)

        try:
            # 预处理文本
            processed_text = self._preprocess_text_for_tfidf(text)

            # 将文本分割成句子，增加文档数量以避免TF-IDF参数冲突
            sentences = self._split_text_to_sentences(processed_text)

            # 如果句子太少，使用规则方法
            if len(sentences) < 2:
                logger.info("文本太短，使用规则方法提取实体")
                return self._extract_by_rules(text, max_entities)

            # 创建适合单文档的TF-IDF向量化器
            from sklearn.feature_extraction.text import TfidfVectorizer
            single_doc_vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=None,
                ngram_range=(1, 2),
                min_df=1,  # 最小文档频率为1
                max_df=1.0,  # 最大文档频率为100%，避免冲突
                lowercase=True
            )

            # 使用TF-IDF提取关键词
            tfidf_matrix = single_doc_vectorizer.fit_transform(sentences)
            feature_names = single_doc_vectorizer.get_feature_names_out()

            # 计算所有句子的平均TF-IDF得分
            mean_scores = tfidf_matrix.mean(axis=0).A1

            # 获取得分最高的关键词
            word_scores = list(zip(feature_names, mean_scores))
            word_scores.sort(key=lambda x: x[1], reverse=True)

            # 过滤和清理
            entities = []
            for word, score in word_scores:
                if (score > 0 and
                    word.lower() not in self.stop_words and
                    len(word.strip()) > 1 and
                    not word.isdigit()):  # 排除纯数字
                    entities.append(word)

                if len(entities) >= max_entities:
                    break

            return entities

        except Exception as e:
            logger.error(f"TF-IDF提取失败: {str(e)}")
            return self._extract_by_rules(text, max_entities)
    
    def _extract_by_nlp(self, text: str, max_entities: int) -> List[str]:
        """
        基于NLP模型的命名实体识别
        
        Args:
            text: 文本内容
            max_entities: 最大实体数量
            
        Returns:
            提取的实体列表
        """
        # 这里可以集成spaCy、jieba等NLP库
        # 目前使用规则方法作为备用
        logger.info("NLP模型提取暂未实现，使用规则方法")
        return self._extract_by_rules(text, max_entities)
    
    def _extract_by_llm(self, text: str, max_entities: int) -> List[str]:
        """
        基于LLM的智能实体提取
        
        Args:
            text: 文本内容
            max_entities: 最大实体数量
            
        Returns:
            提取的实体列表
        """
        # 这里可以集成LLM API进行智能实体提取
        # 目前使用规则方法作为备用
        logger.info("LLM实体提取暂未实现，使用规则方法")
        return self._extract_by_rules(text, max_entities)
    
    def _extract_by_hybrid(self, text: str, max_entities: int) -> List[str]:
        """
        混合方法实体提取
        
        Args:
            text: 文本内容
            max_entities: 最大实体数量
            
        Returns:
            提取的实体列表
        """
        # 使用多种方法提取，然后合并结果
        entities_rule = self._extract_by_rules(text, max_entities * 2)
        entities_tfidf = self._extract_by_tfidf(text, max_entities * 2)
        
        # 合并并计算权重
        entity_scores = Counter()
        
        # 规则方法的结果权重
        for i, entity in enumerate(entities_rule):
            score = (len(entities_rule) - i) / len(entities_rule)
            entity_scores[entity] += score * 0.6  # 规则方法权重0.6
        
        # TF-IDF方法的结果权重
        for i, entity in enumerate(entities_tfidf):
            score = (len(entities_tfidf) - i) / len(entities_tfidf)
            entity_scores[entity] += score * 0.4  # TF-IDF方法权重0.4
        
        # 按得分排序
        sorted_entities = sorted(entity_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 返回前max_entities个
        return [entity for entity, _ in sorted_entities[:max_entities]]
    
    def _preprocess_text_for_tfidf(self, text: str) -> str:
        """
        为TF-IDF预处理文本
        
        Args:
            text: 原始文本
            
        Returns:
            预处理后的文本
        """
        # 移除特殊字符，保留中文、英文、数字和空格
        cleaned_text = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', ' ', text)
        
        # 移除多余的空格
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text

    def _split_text_to_sentences(self, text: str) -> List[str]:
        """
        将文本分割成句子

        Args:
            text: 输入文本

        Returns:
            句子列表
        """
        # 使用多种分隔符分割句子
        import re

        # 中文和英文的句子分隔符
        sentence_delimiters = r'[。！？；\n\r]|[.!?;](?=\s|$)'

        # 分割句子
        sentences = re.split(sentence_delimiters, text)

        # 清理和过滤句子
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # 只保留长度大于10的句子
                cleaned_sentences.append(sentence)

        # 如果句子太少，按长度分割
        if len(cleaned_sentences) < 3:
            # 按固定长度分割文本
            chunk_size = max(100, len(text) // 5)  # 至少100字符，最多分成5段
            chunks = []
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size].strip()
                if len(chunk) > 20:
                    chunks.append(chunk)

            if len(chunks) >= 2:
                return chunks

        return cleaned_sentences if len(cleaned_sentences) >= 2 else [text]
    
    def extract_entities_batch(
        self,
        texts: List[str],
        method: str = "hybrid",
        max_entities: int = 15
    ) -> List[List[str]]:
        """
        批量提取实体
        
        Args:
            texts: 文本列表
            method: 提取方法
            max_entities: 每个文本的最大实体数量
            
        Returns:
            每个文本的实体列表
        """
        results = []
        
        for text in texts:
            entities = self.extract_entities(text, method, max_entities)
            results.append(entities)
        
        return results
    
    def get_entity_statistics(self, entities_list: List[List[str]]) -> Dict[str, Any]:
        """
        获取实体统计信息
        
        Args:
            entities_list: 实体列表的列表
            
        Returns:
            统计信息
        """
        all_entities = []
        for entities in entities_list:
            all_entities.extend(entities)
        
        entity_counts = Counter(all_entities)
        
        return {
            "total_entities": len(all_entities),
            "unique_entities": len(entity_counts),
            "most_common": entity_counts.most_common(10),
            "average_entities_per_text": len(all_entities) / len(entities_list) if entities_list else 0
        }
