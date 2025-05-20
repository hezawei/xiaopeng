"""
文档分块策略示例

本模块演示不同的文档分块策略，以及它们如何影响需求文档的处理效果。
包括以下分块策略：
1. 基于句子的分块
2. 基于Token的分块
3. 滑动窗口分块
4. 层次化分块
5. 语义分块

使用方法:
```python
python document_chunking_strategies.py --file "需求文档.docx" --query "系统需要哪些功能?"
```
"""

import argparse
import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# LlamaIndex相关导入
from llama_index.core import (
    SimpleDirectoryReader,
    Document,
    VectorStoreIndex,
    Settings
)
from llama_index.core.node_parser import (
    SentenceSplitter,
    TokenTextSplitter,
    SentenceWindowNodeParser,
    HierarchicalNodeParser
)

# 嵌入模型相关导入
try:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

try:
    from llama_index.embeddings.openai import OpenAIEmbedding
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# 文档处理相关导入
from docling.document_converter import DocumentConverter

# 导入大模型客户端
from llms import model_client

class DocumentChunkingDemo:
    """
    文档分块策略演示类

    该类演示了不同的文档分块策略，并比较它们在需求文档处理中的效果。
    """

    def __init__(
        self,
        file_path: str,
        embedding_model_type: str = "huggingface",
        embedding_model_name: Optional[str] = "BAAI/bge-small-zh-v1.5",
        openai_api_key: Optional[str] = None
    ):
        """
        初始化演示类

        Args:
            file_path: 文档路径
            embedding_model_type: 嵌入模型类型，可选值：
                - "huggingface": 使用HuggingFace嵌入模型
                - "openai": 使用OpenAI嵌入模型
            embedding_model_name: 嵌入模型名称
            openai_api_key: OpenAI API密钥（仅当embedding_model_type为"openai"时需要）
        """
        self.file_path = file_path
        self.documents = self._load_document()

        # 设置嵌入模型
        self._setup_embedding_model(
            embedding_model_type=embedding_model_type,
            embedding_model_name=embedding_model_name,
            openai_api_key=openai_api_key
        )

    def _setup_embedding_model(
        self,
        embedding_model_type: str,
        embedding_model_name: Optional[str],
        openai_api_key: Optional[str]
    ):
        """
        设置嵌入模型

        Args:
            embedding_model_type: 嵌入模型类型
            embedding_model_name: 嵌入模型名称
            openai_api_key: OpenAI API密钥
        """
        if embedding_model_type == "huggingface" and HUGGINGFACE_AVAILABLE and embedding_model_name:
            try:
                self.embed_model = HuggingFaceEmbedding(model_name=embedding_model_name)
                Settings.embed_model = self.embed_model
                print(f"使用HuggingFace嵌入模型: {embedding_model_name}")
            except Exception as e:
                print(f"加载HuggingFace嵌入模型失败: {str(e)}")
        elif embedding_model_type == "openai" and OPENAI_AVAILABLE:
            try:
                # 默认使用text-embedding-3-small模型，如果指定了其他模型名称则使用指定的模型
                model_name = embedding_model_name if embedding_model_name else "text-embedding-3-small"
                self.embed_model = OpenAIEmbedding(
                    model=model_name,
                    api_key=openai_api_key
                )
                Settings.embed_model = self.embed_model
                print(f"使用OpenAI嵌入模型: {model_name}")
            except Exception as e:
                print(f"加载OpenAI嵌入模型失败: {str(e)}")
        else:
            print("未配置嵌入模型或所需库不可用，将使用默认嵌入模型")

    def _load_document(self) -> List[Document]:
        """
        加载文档

        Returns:
            Document对象列表
        """
        print(f"加载文档: {self.file_path}")

        # 检查文件是否存在
        if not Path(self.file_path).exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

        # 根据文件类型选择不同的处理方法
        if self.file_path.endswith(('.pdf', '.docx')):
            # 使用Docling处理PDF或DOCX文件
            print(f"使用Docling处理{'PDF' if self.file_path.endswith('.pdf') else 'Word'}文档")
            converter = DocumentConverter()
            result = converter.convert(self.file_path)
            content = result.document.export_to_markdown()

            # 创建Document对象
            doc = Document(text=content, metadata={"source": self.file_path})
            return [doc]
        else:
            # 使用LlamaIndex的SimpleDirectoryReader处理其他类型文件
            print(f"使用LlamaIndex处理文件")
            reader = SimpleDirectoryReader(input_files=[self.file_path])
            return reader.load_data()

    def chunk_with_sentence_splitter(self, chunk_size: int = 1024, chunk_overlap: int = 20) -> List[Document]:
        """
        使用句子分块器

        Args:
            chunk_size: 块大小
            chunk_overlap: 块重叠大小

        Returns:
            分块后的文档节点
        """
        print(f"使用句子分块器 (chunk_size={chunk_size}, chunk_overlap={chunk_overlap})")

        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        nodes = splitter.get_nodes_from_documents(self.documents)
        print(f"生成了 {len(nodes)} 个文本块")

        return nodes

    def chunk_with_token_splitter(self, chunk_size: int = 1024, chunk_overlap: int = 20) -> List[Document]:
        """
        使用Token分块器

        Args:
            chunk_size: 块大小
            chunk_overlap: 块重叠大小

        Returns:
            分块后的文档节点
        """
        print(f"使用Token分块器 (chunk_size={chunk_size}, chunk_overlap={chunk_overlap})")

        splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        nodes = splitter.get_nodes_from_documents(self.documents)
        print(f"生成了 {len(nodes)} 个文本块")

        return nodes

    def chunk_with_window_splitter(self, window_size: int = 5) -> List[Document]:
        """
        使用滑动窗口分块器

        Args:
            window_size: 窗口大小

        Returns:
            分块后的文档节点
        """
        print(f"使用滑动窗口分块器 (window_size={window_size})")

        splitter = SentenceWindowNodeParser.from_defaults(
            window_size=window_size,
            window_metadata_key="window",
            original_text_metadata_key="original_text"
        )

        nodes = splitter.get_nodes_from_documents(self.documents)
        print(f"生成了 {len(nodes)} 个文本块")

        return nodes

    def chunk_with_hierarchical_splitter(self) -> List[Document]:
        """
        使用层次化分块器

        Returns:
            分块后的文档节点
        """
        print("使用层次化分块器")

        splitter = HierarchicalNodeParser.from_defaults()

        nodes = splitter.get_nodes_from_documents(self.documents)
        print(f"生成了 {len(nodes)} 个文本块")

        return nodes

    def create_index_and_query(self, nodes: List[Document], query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        创建索引并执行查询

        Args:
            nodes: 文档节点
            query: 查询文本
            top_k: 返回的最相关结果数量

        Returns:
            查询结果
        """
        # 创建索引
        index = VectorStoreIndex(nodes)

        # 创建检索器
        retriever = index.as_retriever(similarity_top_k=top_k)

        # 检索相关节点
        retrieved_nodes = retriever.retrieve(query)

        # 创建查询引擎
        query_engine = index.as_query_engine()

        # 执行查询
        response = query_engine.query(query)

        # 构建结果
        result = {
            "query": query,
            "response": str(response),
            "source_nodes": [
                {
                    "text": node.node.text,
                    "score": node.score,
                    "metadata": node.node.metadata
                }
                for node in retrieved_nodes
            ]
        }

        return result

    async def compare_chunking_strategies(self, query: str) -> Dict[str, Dict[str, Any]]:
        """
        比较不同的分块策略

        Args:
            query: 查询文本

        Returns:
            不同分块策略的查询结果
        """
        results = {}

        # 1. 句子分块
        nodes = self.chunk_with_sentence_splitter(chunk_size=1024, chunk_overlap=20)
        results["sentence"] = self.create_index_and_query(nodes, query)

        # 2. Token分块
        nodes = self.chunk_with_token_splitter(chunk_size=1024, chunk_overlap=20)
        results["token"] = self.create_index_and_query(nodes, query)

        # 3. 滑动窗口分块
        nodes = self.chunk_with_window_splitter(window_size=5)
        results["window"] = self.create_index_and_query(nodes, query)

        # 4. 层次化分块
        nodes = self.chunk_with_hierarchical_splitter()
        results["hierarchical"] = self.create_index_and_query(nodes, query)

        return results

    async def analyze_results(self, results: Dict[str, Dict[str, Any]]) -> str:
        """
        分析不同分块策略的结果

        Args:
            results: 不同分块策略的查询结果

        Returns:
            分析结果
        """
        # 构建提示词
        prompt = """
        请分析以下不同文档分块策略在处理需求文档时的效果。

        查询问题: {query}

        各策略的回答:
        """.format(query=results["sentence"]["query"])

        # 添加各策略的回答
        for strategy, result in results.items():
            prompt += f"\n## {strategy} 策略的回答:\n{result['response']}\n"

        # 添加分析要求
        prompt += """
        请分析各策略的优缺点，并推荐最适合处理需求文档的分块策略。
        分析应包括:
        1. 各策略在回答准确性上的表现
        2. 各策略在上下文保留上的表现
        3. 各策略在处理结构化内容上的表现
        4. 最适合需求文档处理的策略推荐及理由
        """

        # 调用大模型进行分析
        print("\n正在使用大模型分析不同分块策略的效果...")
        response = await model_client.create(
            messages=[{"role": "user", "content": prompt}]
        )

        # 返回分析结果
        return response.choices[0].message.content


async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='文档分块策略演示')
    parser.add_argument('--file', type=str, required=True, help='文档路径')
    parser.add_argument('--query', type=str, default="系统需要哪些功能?", help='查询问题')
    parser.add_argument('--embedding-model', type=str, default="huggingface",
                        choices=["huggingface", "openai"], help='嵌入模型类型')
    parser.add_argument('--model-name', type=str,
                        help='嵌入模型名称，默认为huggingface使用BAAI/bge-small-zh-v1.5，openai使用text-embedding-3-small')
    parser.add_argument('--openai-api-key', type=str, help='OpenAI API密钥（仅当使用OpenAI嵌入模型时需要）')
    args = parser.parse_args()

    # 设置模型名称
    model_name = args.model_name
    if model_name is None:
        if args.embedding_model == "huggingface":
            model_name = "BAAI/bge-small-zh-v1.5"
        else:
            model_name = "text-embedding-3-small"

    # 创建演示对象
    demo = DocumentChunkingDemo(
        file_path=args.file,
        embedding_model_type=args.embedding_model,
        embedding_model_name=model_name,
        openai_api_key=args.openai_api_key
    )

    # 比较不同的分块策略
    print(f"\n开始比较不同分块策略在处理文档 '{args.file}' 时的效果")
    print(f"使用嵌入模型类型: {args.embedding_model}")
    print(f"使用嵌入模型名称: {model_name}")
    print(f"查询问题: {args.query}")
    results = await demo.compare_chunking_strategies(query=args.query)

    # 分析结果
    analysis = await demo.analyze_results(results)

    # 打印分析结果
    print("\n分析结果:")
    print(analysis)

    print("\n演示完成")


if __name__ == "__main__":
    asyncio.run(main())
