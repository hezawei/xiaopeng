"""
文档图片处理器示例

本模块演示如何处理Word文档中的图片，包括：
1. 提取文档中的所有图片
2. 使用多模态大模型(Moonshot)对图片进行详细描述
3. 将图片描述替换到文档中的相应位置
4. 输出包含图片描述的纯文本结果或新的Word文档

使用方法:
```python
processor = DocumentImageProcessor()
# 处理文档并输出纯文本
text_with_image_descriptions = processor.process_document("path/to/document.docx")
print(text_with_image_descriptions)

# 或处理文档并输出新的Word文档
processor.process_document_to_word("path/to/document.docx", "path/to/output.docx")
```
"""

import asyncio
import aiohttp
import base64
import os
import time
import uuid
import requests
import docx
from typing import List, Dict, Any, Optional, Tuple

# 确保导入所需的库
try:
    from docling_core.types.doc.document import DoclingDocument
    from docling_core.types.doc import TextItem
    from docling.document_converter import DocumentConverter
except ImportError:
    print("警告: docling库未安装，某些功能可能不可用")
    DoclingDocument = object
    TextItem = object
    DocumentConverter = object

class DocumentImageProcessor:
    """
    处理文档中图片的类
    
    该类提供了一套完整的文档图片处理流程，包括：
    1. 从Word文档中提取文本和图片
    2. 使用多模态大模型对图片进行详细描述
    3. 将图片描述替换到文档中的相应位置
    4. 输出包含图片描述的纯文本结果或新的Word文档
    """
    
    def __init__(
        self,
        temp_image_dir: str = "./temp_images",
        multimodal_model: str = "moonshot-v1-32k-vision-preview",  # 使用正确的视觉模型名称
        api_key: str = "sk-FefbDs44DxjdtEeQMBpWDe1WZtAFHsle55dSnTUuGv50uUXx",
        api_base: str = "https://api.moonshot.cn/v1",
        max_concurrent_requests: int = 2  # 限制并发请求数量
    ):
        """
        初始化文档图片处理器
        
        Args:
            temp_image_dir: 临时存储图片的目录
            multimodal_model: 使用的多模态模型名称
            api_key: API密钥
            api_base: API基础URL
            max_concurrent_requests: 最大并发请求数
        """
        self.temp_image_dir = temp_image_dir
        self.multimodal_model = multimodal_model
        self.api_key = api_key
        self.api_base = api_base
        self.max_concurrent_requests = max_concurrent_requests
        
        # 创建临时图片目录
        os.makedirs(self.temp_image_dir, exist_ok=True)
        
        # 初始化文档转换器
        self.doc_converter = DocumentConverter()
        
        # 创建信号量以限制并发请求
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
    
    def process_document(self, file_path: str) -> str:
        """
        处理文档，提取图片并生成描述，输出纯文本结果
        
        Args:
            file_path: 文档路径
            
        Returns:
            包含图片描述的纯文本结果
        """
        print(f"开始处理文档: {file_path}")
        
        # 1. 转换文档并提取图片
        conversion_result = self.doc_converter.convert(file_path)
        document = conversion_result.document
        
        # 打印文档结构，帮助调试
        print(f"文档结构: {type(document)}")
        
        # 提取图片，传入原始文件路径
        images_info = self._extract_images_from_document(document, original_file_path=file_path)
        print(f"提取到 {len(images_info)} 张图片")
        
        if len(images_info) == 0:
            print("警告: 未从文档中提取到任何图片，请检查文档格式或docling库的兼容性")
            return document.export_to_markdown()
        
        # 2. 对每个图片生成描述
        for image_info in images_info:
            image_path = image_info["image_path"]
            print(f"正在描述图片: {image_path}")
            
            # 使用智能提示词让模型自行判断图片类型并给出相应描述
            description = self._describe_image_with_model(
                image_path,
                """请分析这张图片并提供详细描述。根据图片类型给出适当的描述:
                
                - 如果是流程图或架构图: 详细描述各个组件、流程步骤、数据流向和逻辑关系
                - 如果是表格: 描述表格结构、列名和主要数据内容
                - 如果是图表(如柱状图、饼图等): 解释图表表达的数据关系、趋势和关键数据点
                - 如果是界面截图: 描述界面布局、功能区域和主要控件
                - 如果是其他类型图片: 描述图片中的主要视觉元素和内容
                
                请确保描述全面、准确，覆盖图片中的所有重要信息，包括任何文本内容。"""
            )
            
            # 保存描述到图片信息中
            image_info["description"] = description
        
        # 3. 生成包含图片描述的文本
        result_text = self._generate_text_with_descriptions(document, images_info)
        
        print(f"文档处理完成，生成了包含{len(images_info)}个图片描述的文本")
        return result_text
    
    def process_document_to_word(self, file_path: str, output_path: str) -> str:
        """
        处理文档，提取图片并生成描述，输出新的Word文档
        
        Args:
            file_path: 输入文档路径
            output_path: 输出文档路径
            
        Returns:
            输出文档路径
        """
        print(f"开始处理文档: {file_path}")
        
        # 1. 转换文档并提取图片
        conversion_result = self.doc_converter.convert(file_path)
        document = conversion_result.document
        
        # 打印文档结构，帮助调试
        print(f"文档结构: {type(document)}")
        
        # 提取图片，传入原始文件路径
        images_info = self._extract_images_from_document(document, original_file_path=file_path)
        print(f"提取到 {len(images_info)} 张图片")
        
        if len(images_info) == 0:
            print("警告: 未从文档中提取到任何图片，请检查文档格式或docling库的兼容性")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(document.export_to_markdown())
            return output_path
        
        # 2. 对每个图片生成描述
        for image_info in images_info:
            image_path = image_info["image_path"]
            print(f"正在描述图片: {image_path}")
            
            # 使用智能提示词让模型自行判断图片类型并给出相应描述
            description = self._describe_image_with_model(
                image_path,
                """请分析这张图片并提供详细描述。根据图片类型给出适当的描述:
                
                - 如果是流程图或架构图: 详细描述各个组件、流程步骤、数据流向和逻辑关系
                - 如果是表格: 描述表格结构、列名和主要数据内容
                - 如果是图表(如柱状图、饼图等): 解释图表表达的数据关系、趋势和关键数据点
                - 如果是界面截图: 描述界面布局、功能区域和主要控件
                - 如果是其他类型图片: 描述图片中的主要视觉元素和内容
                
                请确保描述全面、准确，覆盖图片中的所有重要信息，包括任何文本内容。"""
            )
            
            # 保存描述到图片信息中
            image_info["description"] = description
        
        # 3. 修改文档，将图片描述添加到文档中
        modified_document = self._modify_document_with_descriptions(document, images_info)
        
        # 4. 保存修改后的文档
        self._save_document_as_word(modified_document, output_path)
        
        print(f"文档处理完成，生成了包含{len(images_info)}个图片描述的Word文档: {output_path}")
        return output_path
    
    def _extract_images_from_document(self, document: DoclingDocument, original_file_path: str = None) -> List[Dict[str, Any]]:
        """
        从文档中提取所有图片
        
        Args:
            document: 文档对象
            original_file_path: 原始文件路径
            
        Returns:
            图片信息列表，每个元素包含图片路径和在文档中的位置信息
        """
        # 提取文档中的所有图片
        images_info = []
        picture_counter = 0
        
        # 调试信息
        print("开始提取图片...")
        
        # 方法1: 尝试直接从DoclingDocument对象中提取图片
        if hasattr(document, 'pages'):
            print("尝试从document.pages提取图片...")
            for page_idx, page in enumerate(document.pages):
                for item in page.items:
                    if isinstance(item, PictureItem):
                        picture_counter += 1
                        # 保存图片到临时文件
                        image_filename = f"image_{page_idx}_{picture_counter}_{uuid.uuid4().hex[:8]}.png"
                        image_path = os.path.join(self.temp_image_dir, image_filename)
                        
                        # 保存图片数据
                        with open(image_path, "wb") as f:
                            f.write(item.image_data)
                        
                        # 记录图片信息
                        images_info.append({
                            "image_path": image_path,
                            "page_idx": page_idx,
                            "item": item,
                            "position": picture_counter
                        })
    
        # 方法2: 尝试使用python-docx库直接从原始文档提取
        if len(images_info) == 0 and original_file_path and original_file_path.lower().endswith('.docx'):
            print("尝试使用python-docx库提取图片...")
            try:
                import docx
                from docx.document import Document as DocxDocument
                from docx.parts.image import ImagePart
                
                # 使用传入的原始文件路径
                doc = docx.Document(original_file_path)
                
                # 提取所有图片
                for rel_id, rel in doc.part.rels.items():
                    if isinstance(rel.target_part, ImagePart):
                        # 获取图片数据
                        image_data = rel.target_part.blob
                        
                        # 保存图片到临时文件
                        picture_counter += 1
                        image_filename = f"docx_image_{picture_counter}_{uuid.uuid4().hex[:8]}.png"
                        image_path = os.path.join(self.temp_image_dir, image_filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(image_data)
                        
                        # 记录图片信息
                        images_info.append({
                            "image_path": image_path,
                            "rel_id": rel_id,
                            "position": picture_counter
                        })
            except Exception as e:
                print(f"使用python-docx提取图片时出错: {str(e)}")
    
        # 方法3: 尝试使用docling的原始转换结果
        if len(images_info) == 0 and hasattr(document, '_conversion_result'):
            print("尝试从conversion_result提取图片...")
            try:
                conversion_result = document._conversion_result
                if hasattr(conversion_result, 'images') and conversion_result.images:
                    for idx, img_data in enumerate(conversion_result.images):
                        picture_counter += 1
                        image_filename = f"conversion_image_{picture_counter}_{uuid.uuid4().hex[:8]}.png"
                        image_path = os.path.join(self.temp_image_dir, image_filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(img_data)
                        
                        images_info.append({
                            "image_path": image_path,
                            "index": idx,
                            "position": picture_counter
                        })
            except Exception as e:
                print(f"从conversion_result提取图片时出错: {str(e)}")
    
        # 方法4: 如果文档是PDF，尝试使用PyMuPDF提取图片
        if len(images_info) == 0 and original_file_path and original_file_path.lower().endswith('.pdf'):
            print("尝试使用PyMuPDF提取图片...")
            try:
                import fitz  # PyMuPDF
                
                doc = fitz.open(original_file_path)
                
                for page_idx, page in enumerate(doc):
                    image_list = page.get_images(full=True)
                    
                    for img_idx, img_info in enumerate(image_list):
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)
                        image_data = base_image["image"]
                        
                        picture_counter += 1
                        image_filename = f"pdf_image_{page_idx}_{img_idx}_{uuid.uuid4().hex[:8]}.png"
                        image_path = os.path.join(self.temp_image_dir, image_filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(image_data)
                        
                        images_info.append({
                            "image_path": image_path,
                            "page_idx": page_idx,
                            "img_idx": img_idx,
                            "position": picture_counter
                        })
                
                doc.close()
            except Exception as e:
                print(f"使用PyMuPDF提取图片时出错: {str(e)}")
    
        # 方法5: 尝试直接从docx文件中提取图片（使用zipfile）
        if len(images_info) == 0 and original_file_path and original_file_path.lower().endswith('.docx'):
            print("尝试使用zipfile直接从docx文件中提取图片...")
            try:
                import zipfile
                from xml.etree import ElementTree as ET
                
                # 打开docx文件（实际上是一个zip文件）
                with zipfile.ZipFile(original_file_path) as docx_zip:
                    # 获取所有文件列表
                    file_list = docx_zip.namelist()
                    
                    # 查找所有图片文件（通常在word/media/目录下）
                    image_files = [f for f in file_list if f.startswith('word/media/')]
                    
                    for img_idx, img_file in enumerate(image_files):
                        # 提取图片数据
                        image_data = docx_zip.read(img_file)
                        
                        picture_counter += 1
                        image_filename = f"zip_image_{img_idx}_{uuid.uuid4().hex[:8]}.png"
                        image_path = os.path.join(self.temp_image_dir, image_filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(image_data)
                        
                        images_info.append({
                            "image_path": image_path,
                            "source_file": img_file,
                            "position": picture_counter
                        })
            except Exception as e:
                print(f"使用zipfile提取图片时出错: {str(e)}")
    
        print(f"总共提取到 {len(images_info)} 张图片")
        return images_info



    def _describe_image_with_model(self, image_path: str, prompt: str) -> str:
        """
        使用多模态模型描述图片
        
        Args:
            image_path: 图片路径
            prompt: 描述提示词
            
        Returns:
            图片描述
        """
        try:
            # 读取图片并转换为base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")
            
            # 构建API请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 使用Moonshot多模态API
            payload = {
                "model": self.multimodal_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000
            }
            
            # 发送请求，使用循环而不是递归来处理重试
            max_retries = 5
            retry_count = 0
            retry_delay = 2  # 初始重试延迟（秒）
            
            while retry_count < max_retries:
                # 发送请求
                response = requests.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60  # 设置较长的超时时间
                )
                
                # 解析响应
                if response.status_code == 200:
                    result = response.json()
                    description = result["choices"][0]["message"]["content"]
                    return description
                elif response.status_code == 429:
                    # 遇到速率限制，等待后重试
                    print(f"API请求受到速率限制，等待{retry_delay}秒后重试... ({retry_count+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # 增加重试延迟
                    retry_count += 1
                else:
                    print(f"API请求失败: {response.status_code} {response.text}")
                    return f"[图片描述生成失败: API错误 {response.status_code}]"
            
            return "[图片描述生成失败: 超过最大重试次数]"
                
        except Exception as e:
            print(f"图片描述生成失败: {str(e)}")
            return f"[图片描述生成失败: {str(e)}]"
    
    def _generate_text_with_descriptions(self, document: DoclingDocument, images_info: List[Dict[str, Any]]) -> str:
        """
        生成包含图片描述的文本
        
        Args:
            document: 文档对象
            images_info: 图片信息列表
            
        Returns:
            包含图片描述的纯文本
        """
        # 获取文档的Markdown文本
        markdown_text = document.export_to_markdown()
        
        # 在Markdown文本中查找并替换图片标记
        result_text = markdown_text
        
        # 按照图片在文档中的位置排序
        sorted_images = sorted(images_info, key=lambda x: x["position"])
        
        # 替换图片标记
        for image_info in sorted_images:
            # 在Markdown中，图片通常表示为 ![alt text](image_url)
            # 在docling生成的Markdown中，可能是 <image> 或其他标记
            # 这里需要根据实际情况调整替换逻辑
            
            # 尝试多种可能的图片标记
            image_markers = ["<image>", "![", "<img"]
            replaced = False
            
            for marker in image_markers:
                if marker in result_text:
                    # 找到标记的位置
                    marker_pos = result_text.find(marker)
                    
                    # 如果是![或<img，需要找到标记的结束位置
                    if marker == "![":
                        # 查找下一个)，这是Markdown图片语法的结束
                        end_pos = result_text.find(")", marker_pos)
                        if end_pos > marker_pos:
                            # 替换整个图片标记
                            old_text = result_text[marker_pos:end_pos+1]
                            new_text = f"\n[图片描述: {image_info['description']}]\n"
                            result_text = result_text.replace(old_text, new_text, 1)
                            replaced = True
                            break
                    elif marker == "<img":
                        # 查找下一个>，这是HTML图片标签的结束
                        end_pos = result_text.find(">", marker_pos)
                        if end_pos > marker_pos:
                            # 替换整个图片标记
                            old_text = result_text[marker_pos:end_pos+1]
                            new_text = f"\n[图片描述: {image_info['description']}]\n"
                            result_text = result_text.replace(old_text, new_text, 1)
                            replaced = True
                            break
                    else:
                        # 直接替换标记
                        result_text = result_text.replace(
                            marker, 
                            f"\n[图片描述: {image_info['description']}]\n", 
                            1  # 只替换第一次出现的标记
                        )
                        replaced = True
                        break
            
            # 如果没有找到任何标记，则在文档末尾添加图片描述
            if not replaced:
                result_text += f"\n\n[图片 {image_info['position']} 描述: {image_info['description']}]\n"
        
        return result_text
    
    def _modify_document_with_descriptions(self, document: DoclingDocument, images_info: List[Dict[str, Any]]) -> DoclingDocument:
        """
        修改文档，将图片描述添加到文档中
        
        Args:
            document: 原始文档对象
            images_info: 图片信息列表
            
        Returns:
            修改后的文档对象
        """
        # 创建文档的副本
        modified_document = document
        
        # 按照图片在文档中的位置排序
        sorted_images = sorted(images_info, key=lambda x: x["position"])
        
        # 为每个图片添加描述
        for image_info in sorted_images:
            # 获取图片描述
            description = image_info.get("description", "[图片描述未生成]")
            
            # 创建描述文本元素
            description_text = f"[图片描述: {description}]"
            
            try:
                # 创建文本元素
                text_item = TextItem(text=description_text)
                
                # 尝试找到图片元素的位置并插入描述
                # 由于我们可能没有直接的图片元素引用，我们将尝试在文档中查找图片标记
                # 并在其后插入描述文本
                
                # 这里简化处理，直接将描述添加到文档末尾
                # 实际应用中可能需要更复杂的逻辑来定位图片位置
                print(f"将图片描述添加到文档中: {description[:50]}...")
                
                # 如果有页面，尝试添加到最后一个页面
                if hasattr(modified_document, 'pages') and modified_document.pages:
                    last_page = modified_document.pages[-1]
                    if hasattr(last_page, 'items'):
                        last_page.items.append(text_item)
                        print("已将描述添加到最后一页")
            
            except Exception as e:
                print(f"插入图片描述失败: {str(e)}")
        
        return modified_document
    
    def _find_parent_elements(self, document: DoclingDocument, element_id: str) -> Optional[Tuple[Any, int]]:
        """
        查找元素的父元素和索引
        
        Args:
            document: 文档对象
            element_id: 元素ID
            
        Returns:
            父元素和索引的元组，如果未找到则返回None
        """
        # 遍历文档中的所有元素
        for parent in document.iterate_containers():
            for i, child in enumerate(parent.children):
                if hasattr(child, 'id') and child.id == element_id:
                    return parent, i
        return None
    
    def _save_document_as_word(self, document: DoclingDocument, output_path: str) -> None:
        """
        将文档保存为Word文档
        
        Args:
            document: 文档对象
            output_path: 输出文档路径
        """
        try:
            # 导出为Markdown
            markdown_text = document.export_to_markdown()
            
            # 获取文件扩展名
            ext = os.path.splitext(output_path)[1].lower()
            
            if ext == '.docx':
                try:
                    # 尝试使用python-docx创建Word文档
                    from docx import Document
                    from docx.shared import Pt
                    
                    doc = Document()
                    
                    # 添加文本内容
                    for paragraph_text in markdown_text.split('\n\n'):
                        if paragraph_text.strip():
                            p = doc.add_paragraph(paragraph_text)
                    
                    # 保存文档
                    doc.save(output_path)
                    print(f"已将文档保存为Word文档: {output_path}")
                    return
                except Exception as e:
                    print(f"保存为Word文档失败，将保存为纯文本: {str(e)}")
            
            # 如果无法保存为Word或者输出路径不是.docx，则保存为纯文本
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_text)
            
            print(f"已将文档保存为纯文本: {output_path}")
            
        except Exception as e:
            print(f"保存文档失败: {str(e)}")
            
            # 尝试至少保存文本内容
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("文档保存失败，但以下是提取的文本内容:\n\n")
                    f.write(document.export_to_markdown())
                print(f"已将文本内容保存到: {output_path}")
            except Exception as inner_e:
                print(f"保存文本内容也失败了: {str(inner_e)}")

    async def process_document_async(self, file_path: str) -> str:
        """
        异步处理文档，提取图片并生成描述，输出纯文本结果
        
        Args:
            file_path: 文档路径
            
        Returns:
            包含图片描述的纯文本结果
        """
        print(f"开始异步处理文档: {file_path}")
        
        # 1. 转换文档并提取图片
        conversion_result = self.doc_converter.convert(file_path)
        document = conversion_result.document
        
        # 打印文档结构，帮助调试
        print(f"文档结构: {type(document)}")
        
        # 提取图片，传入原始文件路径
        images_info = self._extract_images_from_document(document, original_file_path=file_path)
        print(f"提取到 {len(images_info)} 张图片")
        
        if len(images_info) == 0:
            print("警告: 未从文档中提取到任何图片，请检查文档格式或docling库的兼容性")
            return document.export_to_markdown()
        
        # 2. 异步对每个图片生成描述
        tasks = []
        for image_info in images_info:
            image_path = image_info["image_path"]
            print(f"准备描述图片: {image_path}")
            
            # 使用智能提示词让模型自行判断图片类型并给出相应描述
            prompt = """请分析这张图片并提供详细描述。根据图片类型给出适当的描述:
            
            - 如果是流程图或架构图: 详细描述各个组件、流程步骤、数据流向和逻辑关系
            - 如果是表格: 描述表格结构、列名和主要数据内容
            - 如果是图表(如柱状图、饼图等): 解释图表表达的数据关系、趋势和关键数据点
            - 如果是界面截图: 描述界面布局、功能区域和主要控件
            - 如果是其他类型图片: 描述图片中的主要视觉元素和内容
            
            请确保描述全面、准确，覆盖图片中的所有重要信息，包括任何文本内容。"""
            
            # 创建异步任务
            task = asyncio.create_task(self._describe_image_with_model_async(image_path, prompt))
            tasks.append((image_info, task))
        
        # 等待所有任务完成
        for image_info, task in tasks:
            try:
                description = await task
                image_info["description"] = description
            except Exception as e:
                print(f"描述图片失败: {str(e)}")
                image_info["description"] = f"[图片描述生成失败: {str(e)}]"
        
        # 3. 生成包含图片描述的文本
        result_text = self._generate_text_with_descriptions(document, images_info)
        
        print(f"文档处理完成，生成了包含{len(images_info)}个图片描述的文本")
        return result_text

    async def process_document_to_word_async(self, file_path: str, output_path: str) -> str:
        """
        异步处理文档，提取图片并生成描述，输出新的Word文档
        
        Args:
            file_path: 输入文档路径
            output_path: 输出文档路径
            
        Returns:
            输出文档路径
        """
        print(f"开始异步处理文档: {file_path}")
        
        # 1. 转换文档并提取图片
        conversion_result = self.doc_converter.convert(file_path)
        document = conversion_result.document
        
        # 打印文档结构，帮助调试
        print(f"文档结构: {type(document)}")
        
        # 提取图片，传入原始文件路径
        images_info = self._extract_images_from_document(document, original_file_path=file_path)
        print(f"提取到 {len(images_info)} 张图片")
        
        if len(images_info) == 0:
            print("警告: 未从文档中提取到任何图片，请检查文档格式或docling库的兼容性")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(document.export_to_markdown())
            return output_path
        
        # 2. 异步对每个图片生成描述
        tasks = []
        for image_info in images_info:
            image_path = image_info["image_path"]
            print(f"准备描述图片: {image_path}")
            
            # 使用智能提示词让模型自行判断图片类型并给出相应描述
            prompt = """请分析这张图片并提供详细描述。根据图片类型给出适当的描述:
            
            - 如果是流程图或架构图: 详细描述各个组件、流程步骤、数据流向和逻辑关系
            - 如果是表格: 描述表格结构、列名和主要数据内容
            - 如果是图表(如柱状图、饼图等): 解释图表表达的数据关系、趋势和关键数据点
            - 如果是界面截图: 描述界面布局、功能区域和主要控件
            - 如果是其他类型图片: 描述图片中的主要视觉元素和内容
            
            请确保描述全面、准确，覆盖图片中的所有重要信息，包括任何文本内容。"""
            
            # 创建异步任务
            task = asyncio.create_task(self._describe_image_with_model_async(image_path, prompt))
            tasks.append((image_info, task))
        
        # 等待所有任务完成
        for image_info, task in tasks:
            try:
                description = await task
                image_info["description"] = description
            except Exception as e:
                print(f"描述图片失败: {str(e)}")
                image_info["description"] = f"[图片描述生成失败: {str(e)}]"
        
        # 3. 修改文档，将图片描述添加到文档中
        modified_document = self._modify_document_with_descriptions(document, images_info)
        
        # 4. 保存修改后的文档
        self._save_document_as_word(modified_document, output_path)
        
        print(f"文档处理完成，生成了包含{len(images_info)}个图片描述的Word文档: {output_path}")
        return output_path

    async def _describe_image_with_model_async(self, image_path: str, prompt: str) -> str:
        """
        异步使用多模态模型描述图片
        
        Args:
            image_path: 图片路径
            prompt: 描述提示词
            
        Returns:
            图片描述
        """
        print(f"准备描述图片: {image_path}")
        
        try:
            # 读取图片并转换为base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")
            
            # 构建API请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 使用Moonshot多模态API
            payload = {
                "model": self.multimodal_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000
            }
            
            # 使用aiohttp发送异步请求
            async with aiohttp.ClientSession() as session:
                max_retries = 5
                retry_count = 0
                retry_delay = 2  # 初始重试延迟（秒）
                
                while retry_count < max_retries:
                    try:
                        print(f"发送API请求: {image_path}")
                        async with session.post(
                            f"{self.api_base}/chat/completions",
                            headers=headers,
                            json=payload,
                            timeout=60  # 设置较长的超时时间
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                description = result["choices"][0]["message"]["content"]
                                print(f"成功获取图片描述: {image_path}")
                                return description
                            elif response.status == 429:
                                # 遇到速率限制，等待后重试
                                response_text = await response.text()
                                print(f"API请求受到速率限制，等待{retry_delay}秒后重试... ({retry_count+1}/{max_retries})")
                                
                                # 指数退避策略
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 1.5  # 增加重试延迟
                                retry_count += 1
                            else:
                                response_text = await response.text()
                                print(f"API请求失败: {response.status} {response_text}")
                                return f"[图片描述生成失败: API错误 {response.status}]"
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        print(f"请求出错: {str(e)}，等待{retry_delay}秒后重试... ({retry_count+1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5
                        retry_count += 1
                
                return "[图片描述生成失败: 超过最大重试次数]"
                
        except Exception as e:
            print(f"图片描述生成失败: {str(e)}")
            return f"[图片描述生成失败: {str(e)}]"


# 示例用法
if __name__ == "__main__":
    # 创建处理器实例
    processor = DocumentImageProcessor(
        api_key="sk-FefbDs44DxjdtEeQMBpWDe1WZtAFHsle55dSnTUuGv50uUXx",
        api_base="https://api.moonshot.cn/v1",
        multimodal_model="moonshot-v1-32k-vision-preview",
        max_concurrent_requests=2  # 限制并发请求数
    )
    
    # 处理文档并输出纯文本
    document_path = "AI接口测试系统建设方案.docx"  # 替换为实际的文档路径
    result = processor.process_document(document_path)
    
    # 打印结果
    print("\n处理结果:")
    print(result)
    
    # 保存结果到文件
    output_text_path = "example_with_image_descriptions.txt"
    with open(output_text_path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"\n文本结果已保存到: {output_text_path}")
    
    # 处理文档并输出Word文档
    output_word_path = "example_with_image_descriptions.docx"
    processor.process_document_to_word(document_path, output_word_path)


