"""
LlamaIndex文档处理器示例
本模块演示如何使用LlamaIndex处理需求文档，包括：1. 加载文档
2. 文档分块处理
3. 创建向量索引
4. 查询文档内容

使用方法:
```python
processor = LlamaIndexDocumentProcessor()
results = processor.process_and_query("path/to/document.docx", "需求中有哪些功能点?")
print(results)
```
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

# LlamaIndex相关导入
from llama_index.core import (
    SimpleDirectoryReader,
    Document,
    VectorStoreIndex,
    StorageContext,
    Settings,
    load_index_from_storage
)
from llama_index.core.node_parser import (
    SentenceSplitter,
    TokenTextSplitter,
    SentenceWindowNodeParser,
    HierarchicalNodeParser
)

# 文档处理相关导入
from docling.document_converter import DocumentConverter

# 嵌入模型相关导入
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
# 使用旧版本的导入路径
from llama_index.embeddings.openai import OpenAIEmbedding

# LLM模型相关导入
from llama_index.llms.openai import OpenAI
from llama_index.llms.openai.utils import ALL_AVAILABLE_MODELS, CHAT_MODELS

# 注册DeepSeek模型
DEEPSEEK_MODELS = {
    "deepseek-chat": 128000,
}
ALL_AVAILABLE_MODELS.update(DEEPSEEK_MODELS)
CHAT_MODELS.update(DEEPSEEK_MODELS)


class LlamaIndexDocumentProcessor:
    """
    使用LlamaIndex处理文档的类

    该类提供了一套完整的文档处理流程，包括：
    1. 加载不同格式的文档（PDF、DOCX、TXT等）
    2. 使用不同的分块策略对文档进行分块
    3. 创建向量索引用于高效检索
    4. 基于用户查询返回相关内容
    """

    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 20,
        persist_dir: str = "./document_index",
        embedding_model_name: Optional[str] = "BAAI/bge-small-zh-v1.5",
        embedding_model_type: str = "huggingface",
        use_deepseek_llm: bool = True,
        deepseek_api_key: str = "sk-cdb5b06b8ebd4a44a546371052d72f96",
        deepseek_api_base: str = "https://api.deepseek.com/v1"
    ):
        """
        初始化文档处理器

        Args:
            chunk_size: 文本块大小（以字符为单位）
            chunk_overlap: 文本块重叠大小（以字符为单位）
            persist_dir: 索引持久化目录
            embedding_model_name: 嵌入模型名称
            embedding_model_type: 嵌入模型类型，可选值：
                - "huggingface": 使用HuggingFace嵌入模型
                - "openai": 使用OpenAI嵌入模型
            openai_api_key: OpenAI API密钥（仅当embedding_model_type为"openai"时需要）
            use_deepseek_llm: 是否使用DeepSeek LLM
            deepseek_api_key: DeepSeek API密钥
            deepseek_api_base: DeepSeek API基础URL
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.persist_dir = persist_dir
        self.embedding_model_name = embedding_model_name
        self.embedding_model_type = embedding_model_type
        self.use_deepseek_llm = use_deepseek_llm
        self.deepseek_api_key = deepseek_api_key
        self.deepseek_api_base = deepseek_api_base
        
        # 设置嵌入模型
        self._setup_embedding_model()
        
        # 设置LLM模型
        self._setup_llm()
        
    def _setup_embedding_model(self):
        """设置嵌入模型"""
        if self.embedding_model_type == "huggingface":
            # 使用HuggingFace嵌入模型
            print(f"使用HuggingFace嵌入模型: {self.embedding_model_name}")
            embed_model = HuggingFaceEmbedding(
                model_name=self.embedding_model_name
            )
        elif self.embedding_model_type == "openai":
            # 使用OpenAI嵌入模型
            print(f"使用OpenAI嵌入模型: {self.embedding_model_name}")
            embed_model = OpenAIEmbedding(
                model=self.embedding_model_name,
                api_key=self.deepseek_api_key,
                api_base=self.deepseek_api_base
            )
        else:
            raise ValueError(f"不支持的嵌入模型类型: {self.embedding_model_type}")
            
        # 设置全局嵌入模型
        Settings.embed_model = embed_model
        
    def _setup_llm(self):
        """设置LLM模型"""
        if self.use_deepseek_llm:
            # 使用DeepSeek LLM
            print("使用DeepSeek LLM")
            llm = OpenAI(
                model="deepseek-chat",
                api_key=self.deepseek_api_key,
                api_base=self.deepseek_api_base
            )
        else:
            # 使用默认LLM
            print("使用默认LLM")
            llm = None
            
        # 设置全局LLM
        if llm is not None:
            try:
                Settings.llm = llm
                print(f"使用DeepSeek LLM模型: deepseek-chat")
            except Exception as e:
                print(f"加载DeepSeek LLM模型失败: {str(e)}")
                # 禁用LLM
                Settings.llm = None
                print("已禁用LLM，将只使用检索功能")
        else:
            # 禁用LLM
            Settings.llm = None
            print("已禁用LLM，将只使用检索功能")

    def load_document(self, file_path: str) -> List[Document]:
        """
        加载文档


        支持多种文档格式，包括PDF、DOCX、TXT等

        
        支持多种文档格式，包括PDF、DOCX、TXT等

        Args:
            file_path: 文档路径
            
        Returns:
            文档列表
        """
        print(f"加载文档: {file_path}")
        
        # 根据文件类型选择不同的处理方式
        if file_path.endswith(('.pdf', '.docx')):
            # 使用Docling处理PDF或DOCX文件
            print(f"使用Docling处理{'PDF' if file_path.endswith('.pdf') else 'Word'}文档")
            converter = DocumentConverter()
            result = converter.convert(file_path)
            content = result.document.export_to_markdown()

            # 创建Document对象
            doc = Document(text=content, metadata={"source": file_path})
            return [doc]
        else:
            # 使用LlamaIndex的SimpleDirectoryReader处理其他类型文件
            print(f"使用LlamaIndex处理文件")
            reader = SimpleDirectoryReader(input_files=[file_path])
            return reader.load_data()

    def chunk_document(self, documents: List[Document], chunk_method: str = "sentence") -> List[Document]:
        """
        对文档进行分块处理

        Args:
            documents: 文档列表
            chunk_method: 分块方法，可选值：
                - "sentence": 按句子分块
                - "token": 按token分块
                - "window": 滑动窗口分块
                - "hierarchical": 层次化分块

        Returns:
            分块后的文档列表
        """
        print(f"使用 {chunk_method} 方法对文档进行分块")

        if chunk_method == "sentence":
            # 使用句子分块器
            splitter = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
        elif chunk_method == "token":
            # 使用token分块器
            splitter = TokenTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
        elif chunk_method == "window":
            # 使用滑动窗口分块器
            splitter = SentenceWindowNodeParser.from_defaults(
                window_size=5,
                window_metadata_key="window",
                original_text_metadata_key="original_text"
            )
        elif chunk_method == "hierarchical":
            # 使用层次化分块器
            splitter = HierarchicalNodeParser.from_defaults()
        else:
            raise ValueError(f"不支持的分块方法: {chunk_method}")
            
        # 分块处理
        nodes = splitter.get_nodes_from_documents(documents)
        print(f"生成了 {len(nodes)} 个文本块")
        
        return nodes

    def create_index(self, nodes: List[Document]) -> VectorStoreIndex:
        """
        创建向量索引
        
        Args:
            nodes: 文档节点
            
        Returns:
            向量索引对象
        """
        print("开始创建向量索引...")

        # 创建向量索引
        index = VectorStoreIndex(nodes, show_progress=True)

        # 持久化索引
        os.makedirs(self.persist_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=self.persist_dir)
        print(f"索引已持久化到 {self.persist_dir}")

        return index

    def load_index(self) -> Optional[VectorStoreIndex]:
        """
        加载持久化的索引

        Returns:
            向量索引对象，如果索引不存在则返回None
        """
        if not os.path.exists(self.persist_dir):
            print(f"索引目录不存在: {self.persist_dir}")
            return None

        try:
            print(f"加载索引: {self.persist_dir}")
            storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
            index = load_index_from_storage(storage_context)
            return index
        except Exception as e:
            print(f"加载索引失败: {str(e)}")
            return None

    def query_index(self, index: VectorStoreIndex, query: str, top_k: int = 5, language: str = "中文") -> Dict[str, Any]:
        """
        查询索引，在官方提示词基础上添加语言指令
    
        Args:
            index: 向量索引对象
            query: 查询文本
            top_k: 返回的最相关结果数量
            language: 输出语言，默认为"中文"
        
        Returns:
            查询结果
        """
        print(f"执行查询: {query}")

        # 创建检索器
        retriever = index.as_retriever(similarity_top_k=top_k)

        # 检索相关节点
        nodes = retriever.retrieve(query)
        
        # 获取默认查询引擎
        default_query_engine = index.as_query_engine()
        
        # 获取默认提示词模板
        from llama_index.core.prompts import PromptTemplate
        from llama_index.core.prompts.default_prompts import DEFAULT_TEXT_QA_PROMPT
        
        # 获取默认提示词模板的内容
        default_template = DEFAULT_TEXT_QA_PROMPT.template
        
        # 在默认提示词基础上添加语言指令
        # 在"answer the query"后添加语言指令
        modified_template = default_template.replace(
            "answer the query.",
            f"answer the query. Please respond in {language}."
        )
        
        # 创建修改后的提示词模板
        modified_prompt = PromptTemplate(modified_template)
        
        # 创建使用修改后提示词的查询引擎
        query_engine = index.as_query_engine(
            text_qa_template=modified_prompt,
            similarity_top_k=top_k
        )

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
                for node in nodes
            ]
        }

        return result

    def process_and_query(
        self,
        file_path: str,
        query: str,
        chunk_method: str = "sentence",
        use_existing_index: bool = False,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        处理文档并执行查询的完整流程

        Args:
            file_path: 文档路径
            query: 查询文本
            chunk_method: 分块方法
            use_existing_index: 是否使用现有索引
            top_k: 返回的最相关结果数量

        Returns:
            查询结果
        """
        # 尝试加载现有索引
        index = None
        if use_existing_index:
            index = self.load_index()

        # 如果索引不存在，则创建新索引
        if index is None:
            # 加载文档
            documents = self.load_document(file_path)

            # 分块处理
            nodes = self.chunk_document(documents, chunk_method)

            # 创建索引
            index = self.create_index(nodes)

        # 执行查询
        result = self.query_index(index, query, top_k)

        return result


# 示例用法
if __name__ == "__main__":
    # 使用HuggingFace嵌入模型和DeepSeek LLM
    print("\n示例: 使用HuggingFace嵌入模型和DeepSeek LLM")
    processor = LlamaIndexDocumentProcessor(
        embedding_model_type="huggingface",
        embedding_model_name="BAAI/bge-small-zh-v1.5",
        use_deepseek_llm=True,
        deepseek_api_key="sk-cdb5b06b8ebd4a44a546371052d72f96",  # 替换为实际的API密钥
        deepseek_api_base="https://api.deepseek.com/v1"
    )

    # 处理文档并执行查询
    result = processor.process_and_query(
        file_path="AI接口测试系统建设方案.docx",  # 替换为实际文档路径
        query="目标 技术选型 计划",
        chunk_method="sentence"
    )

    # 打印查询结果
    print("\n查询结果:")
    print(result["response"])

    # 打印相关文本块
    print("\n相关文本块:")
    for i, node in enumerate(result["source_nodes"]):
        print(f"\n--- 文本块 {i+1} (相关度: {node['score']:.4f}) ---")
        print(node["text"] + "...")















