"""
文档处理器 V2 - 重构版本

负责文档内容的提取和预处理，集成现有的文档处理工厂：
1. 使用 DocumentProcessorFactory 自动选择处理方式
2. 自动检测文档是否包含图片
3. 支持多种文档格式的处理
4. 与现有的图片处理和 LlamaIndex 处理器集成
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from llama_index.core import Document

# 设置日志
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    文档处理器

    负责处理各种格式的文档，集成现有的文档处理工厂，
    自动选择合适的处理方式。
    """

    def __init__(self):
        """
        初始化文档处理器
        """
        # 统一文档处理器（延迟加载）
        self._unified_processor = None

        logger.info("文档处理器初始化完成")

    @property
    def unified_processor(self):
        """
        延迟加载统一文档处理器

        Returns:
            统一文档处理器实例
        """
        if self._unified_processor is None:
            try:
                # 添加父目录到路径以导入现有的处理器
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if parent_dir not in sys.path:
                    sys.path.append(parent_dir)

                from document_processing_entry import DocumentProcessingEntry

                # 创建统一处理器
                self._unified_processor = DocumentProcessingEntry.create_processor()
                logger.info("统一文档处理器加载成功")
            except ImportError as e:
                logger.error(f"无法加载统一文档处理器: {str(e)}")
                self._unified_processor = None
            except Exception as e:
                logger.error(f"创建统一文档处理器失败: {str(e)}")
                self._unified_processor = None

        return self._unified_processor
    
    async def process_document(
        self,
        file_path: str,
        process_images: bool = True  # 保留参数以兼容，但实际不使用
    ) -> Optional[Document]:
        """
        处理文档

        Args:
            file_path: 文档路径
            process_images: 兼容参数，实际由工厂类自动判断

        Returns:
            处理后的文档对象
        """
        try:
            logger.info(f"开始处理文档: {file_path}")

            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None

            # 使用统一文档处理器
            if self.unified_processor is None:
                logger.error("统一文档处理器未初始化")
                return None

            # 调用统一处理器处理文档
            result = await self.unified_processor.process_document(file_path)

            if not result or "documents" not in result:
                logger.error(f"无法提取文档内容: {file_path}")
                return None

            # 获取第一个文档（通常只有一个）
            documents = result["documents"]
            if not documents:
                logger.error(f"处理结果中没有文档: {file_path}")
                return None

            document = documents[0]

            # 更新元数据
            document.metadata.update({
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_ext": os.path.splitext(file_path)[1].lower(),
                "processed_with_images": result.get("processed_with_image_handler", False)
            })

            logger.info(f"文档处理完成: {file_path}")
            return document

        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            return None