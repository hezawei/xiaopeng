"""
文档处理统一入口模块

本模块提供统一的文档处理入口，根据文档类型自动选择合适的处理器：
1. 对于带图片的文档，使用MultimodalDocumentProcessor先处理图片
2. 对于纯文本文档，直接使用TextDocumentProcessor处理

使用方法:
```python
processor = DocumentProcessingEntry.create_processor()
result = await processor.process_document("path/to/document.docx")
```
"""
import os.path
import os
import uuid
from typing import Union, Dict, Any, List, Optional
import asyncio
from pathlib import Path

from multimodal_document_processor import MultimodalDocumentProcessor
from text_document_processor import TextDocumentProcessor
from llama_index.core import SimpleDirectoryReader, Document

class DocumentProcessingEntry:
    """文档处理统一入口类，根据文档类型自动选择合适的处理器"""
    
    @staticmethod
    def create_processor(config: Optional[Dict[str, Any]] = None) -> "UnifiedDocumentProcessor":
        """
        创建统一的文档处理器
        
        Args:
            config: 配置字典，包含embedding和llm的配置
            
        Returns:
            UnifiedDocumentProcessor实例
        """
        if config is None:
            config = {}
        
        # 设置默认配置
        default_config = {
            "embedding": {
                "model_type": "huggingface",
                "model_name": "BAAI/bge-small-zh-v1.5"
            },
            "llm": {
                "use_deepseek": True
            }
        }
        
        # 合并配置
        embedding_config = {**default_config["embedding"], **(config.get("embedding", {}))}
        llm_config = {**default_config["llm"], **(config.get("llm", {}))}
        
        try:
            # 创建多模态处理器
            multimodal_processor = MultimodalDocumentProcessor()
            
            # 创建文本处理器
            text_processor = TextDocumentProcessor(
                embedding_model_type=embedding_config["model_type"],
                embedding_model_name=embedding_config["model_name"],
                use_deepseek_llm=llm_config["use_deepseek"]
            )
            
            # 创建并返回统一处理器
            return UnifiedDocumentProcessor(multimodal_processor, text_processor)
        except ImportError as e:
            print(f"创建处理器时导入错误: {str(e)}")
            raise
        except Exception as e:
            print(f"创建处理器时出错: {str(e)}")
            raise


class UnifiedDocumentProcessor:
    """统一文档处理器，整合多模态处理和纯文本处理功能"""
    
    def __init__(
        self, 
        multimodal_processor: MultimodalDocumentProcessor,
        text_processor: TextDocumentProcessor
    ):
        """
        初始化统一文档处理器
        
        Args:
            multimodal_processor: 多模态处理器实例
            text_processor: 文本处理器实例
        """
        self.multimodal_processor = multimodal_processor
        self.text_processor = text_processor
        
        # 获取脚本所在目录的绝对路径
        script_dir = Path(__file__).parent.absolute()
        
        # 创建临时文件目录
        self.temp_dir = script_dir / "temp_processed_docs"
        self.temp_dir.mkdir(exist_ok=True, parents=True)
    
    async def process_document(
        self, 
        file_path: str,
        chunk_method: str = "sentence"
    ) -> Dict[str, Any]:
        """
        处理文档，返回处理结果
        
        Args:
            file_path: 文档路径
            chunk_method: 分块方法
        
        Returns:
            处理结果，包含文档内容、节点和索引
        """
        print(f"开始处理文档: {file_path}")
        
        # 获取文件扩展名
        file_ext = os.path.splitext(file_path.lower())[1]
        
        # 检查文档是否包含图片
        has_images = await self._check_document_has_images(file_path)
        
        if has_images:
            print("检测到文档包含图片，使用多模态处理器先处理...")
            # 处理图片并生成带图片描述的文本
            processed_text = await self.multimodal_processor.process_document_to_text(file_path)
            
            # 根据文件类型和处理成熟度选择处理方式
            if file_ext in ('.pdf', '.docx'):
                # 成熟处理方法的文件类型，直接使用处理后的文本
                print(f"使用直接方法处理{file_ext}文件")
                doc = Document(text=processed_text, metadata={"source": file_path})
                documents = [doc]
            else:
                # 其他文件类型，可能需要额外处理
                print(f"使用SimpleDirectoryReader处理{file_ext}文件")
                temp_file_path = self.temp_dir / f"processed_{os.path.basename(file_path)}_{uuid.uuid4().hex[:8]}.txt"
                
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    f.write(processed_text)
                
                # 使用SimpleDirectoryReader加载处理后的文本文件
                reader = SimpleDirectoryReader(input_files=[str(temp_file_path)])
                documents = reader.load_data()
            
            # 分块处理
            nodes = self.text_processor.chunk_document(documents, chunk_method)
            
            # 创建索引
            index = self.text_processor.create_index(nodes)
            
            return {
                "processed_text": processed_text,
                "documents": documents,
                "nodes": nodes,
                "index": index,
                "processed_with_image_handler": True,
                "original_file": file_path
            }
        else:
            # 文档不包含图片，直接使用文本处理器
            print("文档不包含图片，直接使用文本处理器...")
            
            # 加载文档
            documents = self.text_processor.load_document(file_path)
            
            # 分块处理
            nodes = self.text_processor.chunk_document(documents, chunk_method)
            
            # 创建索引
            index = self.text_processor.create_index(nodes)
            
            # 获取文档文本
            processed_text = "\n\n".join([doc.text for doc in documents])
            
            return {
                "processed_text": processed_text,
                "documents": documents,
                "nodes": nodes,
                "index": index,
                "processed_with_image_handler": False,
                "original_file": file_path
            }
    
    def query_index(
        self, 
        index_or_result: Union[Dict[str, Any], Any],
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        查询索引
        
        Args:
            index_or_result: 索引对象或包含索引的处理结果
            query: 查询文本
            top_k: 返回的最相关结果数量
        
        Returns:
            查询结果
        """
        # 从处理结果中提取索引（如果传入的是处理结果）
        index = index_or_result.get("index") if isinstance(index_or_result, dict) else index_or_result
        
        # 执行查询
        result = self.text_processor.query_index(index, query, top_k)
        
        return result
    
    async def process_and_query(
        self, 
        file_path: str, 
        query: str,
        chunk_method: str = "sentence",
        use_existing_index: bool = False,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        处理文档并执行查询（兼容旧接口）
        
        Args:
            file_path: 文档路径
            query: 查询文本
            chunk_method: 分块方法
            use_existing_index: 是否使用现有索引
            top_k: 返回的最相关结果数量
        
        Returns:
            查询结果
        """
        # 处理文档
        process_result = await self.process_document(file_path, chunk_method)
        
        # 查询索引
        query_result = self.query_index(process_result["index"], query, top_k)
        
        # 合并结果
        result = {**process_result, **query_result}
        
        return result
    
    async def _check_document_has_images(self, file_path: str) -> bool:
        """
        检查文档是否包含图片
        
        Args:
            file_path: 文档路径
            
        Returns:
            是否包含图片
        """
        # 只对Word文档和PDF进行检查
        if not file_path.lower().endswith(('.docx', '.pdf')):
            return False
            
        try:
            # 使用多模态处理器的提取图片方法
            from docling.document_converter import DocumentConverter
            
            # 转换文档
            converter = DocumentConverter()
            conversion_result = converter.convert(file_path)
            document = conversion_result.document
            
            # 提取图片信息
            images_info = self.multimodal_processor._extract_images_from_document(
                document, 
                original_file_path=file_path
            )
            
            # 如果提取到图片，返回True
            return len(images_info) > 0
        except Exception as e:
            print(f"检查文档图片时出错: {str(e)}")
            # 出错时保守返回False
            return False


# 为了保持向后兼容性，创建一个别名
DocumentProcessorFactory = DocumentProcessingEntry
