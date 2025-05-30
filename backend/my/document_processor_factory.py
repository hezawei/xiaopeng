"""
文档处理器工厂模块

本模块提供统一的文档处理入口，根据文档类型自动选择合适的处理器：
1. 对于带图片的文档，使用DocumentImageProcessor先处理图片
2. 对于纯文本文档，直接使用LlamaIndexDocumentProcessor处理

使用方法:
```python
processor = DocumentProcessorFactory.create_processor()
result = await processor.process_document("path/to/document.docx", "分析这个文档的主要内容")
```
"""

import os
import uuid
from typing import Union, Dict, Any, List, Optional
import asyncio

from my.document_image_processor import DocumentImageProcessor
from my.llamaindex_document_processor import LlamaIndexDocumentProcessor
from llama_index.core import SimpleDirectoryReader, Document

class DocumentProcessorFactory:
    """文档处理器工厂类，根据文档类型创建合适的处理器"""
    
    @staticmethod
    def create_processor(config: Optional[Dict[str, Any]] = None) -> "UnifiedDocumentProcessor":
        """
        创建统一的文档处理器
        
        Args:
            config: 配置字典，包含embedding、llm和multimodal的配置
            
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
            },
            "multimodal": {
                "api_base": "https://api.moonshot.cn/v1",
                "model": "moonshot-v1-32k-vision-preview",
                "max_concurrent": 4
            }
        }
        
        # 合并配置
        embedding_config = {**default_config["embedding"], **(config.get("embedding", {}))}
        llm_config = {**default_config["llm"], **(config.get("llm", {}))}
        multimodal_config = {**default_config["multimodal"], **(config.get("multimodal", {}))}
        
        try:
            # 创建图片处理器
            from my.document_image_processor import DocumentImageProcessor
            image_processor = DocumentImageProcessor(
                api_base=multimodal_config["api_base"],
                multimodal_model=multimodal_config["model"],
                max_concurrent_requests=multimodal_config["max_concurrent"]
            )
            
            # 创建LlamaIndex处理器
            from my.llamaindex_document_processor import LlamaIndexDocumentProcessor
            llamaindex_processor = LlamaIndexDocumentProcessor(
                embedding_model_type=embedding_config["model_type"],
                embedding_model_name=embedding_config["model_name"],
                use_deepseek_llm=llm_config["use_deepseek"]
            )
            
            # 创建并返回统一处理器
            return UnifiedDocumentProcessor(image_processor, llamaindex_processor)
        except ImportError as e:
            print(f"创建处理器时导入错误: {str(e)}")
            raise
        except Exception as e:
            print(f"创建处理器时出错: {str(e)}")
            raise
    



class UnifiedDocumentProcessor:
    """统一文档处理器，整合图片处理和向量检索功能"""
    
    def __init__(
        self, 
        image_processor: DocumentImageProcessor,
        llamaindex_processor: LlamaIndexDocumentProcessor
    ):
        """
        初始化统一文档处理器
        
        Args:
            image_processor: 图片处理器实例
            llamaindex_processor: LlamaIndex处理器实例
        """
        self.image_processor = image_processor
        self.llamaindex_processor = llamaindex_processor
        # 创建临时文件目录
        self.temp_dir = os.path.join(os.getcwd(), "temp_processed_docs")
        os.makedirs(self.temp_dir, exist_ok=True)
    
    # 重命名为process_and_query以保持一致性
    async def process_and_query(
        self, 
        file_path: str, 
        query: str,
        chunk_method: str = "sentence",
        use_existing_index: bool = False,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        处理文档并执行查询的统一入口
        
        Args:
            file_path: 文档路径
            query: 查询文本
            chunk_method: 分块方法
            use_existing_index: 是否使用现有索引
            top_k: 返回的最相关结果数量
        
        Returns:
            查询结果
        """
        print(f"开始处理文档: {file_path}")
        
        # 获取文件扩展名
        file_ext = os.path.splitext(file_path.lower())[1]
        
        # 检查文档是否包含图片
        has_images = await self._check_document_has_images(file_path)
        
        if has_images:
            print("检测到文档包含图片，使用图片处理器先处理...")
            # 处理图片并生成带图片描述的文本
            processed_text = await self.image_processor.process_document_to_text(file_path)
            
            # 根据文件类型和处理成熟度选择处理方式
            if file_ext in ('.pdf', '.docx'):
                # 成熟处理方法的文件类型，直接使用处理后的文本
                print(f"使用直接方法处理{file_ext}文件")
                doc = Document(text=processed_text, metadata={"source": file_path})
                documents = [doc]
            else:
                # 其他文件类型，可能需要额外处理
                print(f"使用SimpleDirectoryReader处理{file_ext}文件")
                temp_file_path = os.path.join(
                    self.temp_dir, 
                    f"processed_{os.path.basename(file_path)}_{uuid.uuid4().hex[:8]}.txt"
                )
                
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    f.write(processed_text)
                
                # 使用SimpleDirectoryReader加载处理后的文本文件
                reader = SimpleDirectoryReader(input_files=[temp_file_path])
                documents = reader.load_data()
            
            # 分块处理
            nodes = self.llamaindex_processor.chunk_document(documents, chunk_method)
            
            # 创建索引
            index = self.llamaindex_processor.create_index(nodes)
            
            # 执行查询
            result = self.llamaindex_processor.query_index(index, query, top_k)
            
            # 在结果中添加处理信息
            result["processed_with_image_handler"] = True
            result["original_file"] = file_path
            
            return result
        else:
            # 文档不包含图片，直接使用LlamaIndex处理器
            print("文档不包含图片，直接使用LlamaIndex处理器...")
            result = self.llamaindex_processor.process_and_query(
                file_path=file_path,
                query=query,
                chunk_method=chunk_method,
                use_existing_index=use_existing_index,
                top_k=top_k
            )
            
            result["processed_with_image_handler"] = False
            
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
            # 使用DocumentImageProcessor的提取图片方法
            from docling.document_converter import DocumentConverter
            
            # 转换文档
            converter = DocumentConverter()
            conversion_result = converter.convert(file_path)
            document = conversion_result.document
            
            # 提取图片信息
            images_info = self.image_processor._extract_images_from_document(
                document, 
                original_file_path=file_path
            )
            
            # 如果提取到图片，返回True
            return len(images_info) > 0
        except Exception as e:
            print(f"检查文档图片时出错: {str(e)}")
            # 出错时保守返回False
            return False









