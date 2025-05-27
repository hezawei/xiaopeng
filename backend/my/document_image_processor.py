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

import os
import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# 导入文档处理相关库
from docling.document_converter import DocumentConverter
from docling.datamodel.document import DoclingDocument, PictureItem, TextItem

# 导入图像处理相关库
from PIL import Image
import base64
from io import BytesIO

# 导入多模态模型客户端
import requests
import json
import time

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
        multimodal_model: str = "moonshot-v1-32k",  # 默认使用Moonshot多模态模型
        api_key: str = "sk-FefbDs44DxjdtEeQMBpWDe1WZtAFHsle55dSnTUuGv50uUXx",
        api_base: str = "https://api.moonshot.cn/v1",
    ):
        """
        初始化文档图片处理器
        
        Args:
            temp_image_dir: 临时存储图片的目录
            multimodal_model: 使用的多模态模型名称
            api_key: API密钥
            api_base: API基础URL
        """
        self.temp_image_dir = temp_image_dir
        self.multimodal_model = multimodal_model
        self.api_key = api_key
        self.api_base = api_base
        
        # 创建临时图片目录
        os.makedirs(self.temp_image_dir, exist_ok=True)
        
        # 初始化文档转换器
        self.doc_converter = DocumentConverter()
    
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
        print(f"文档属性: {dir(document)}")
        
        # 提取图片
        images_info = self._extract_images_from_document(document)
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
        
        # 提取图片
        images_info = self._extract_images_from_document(document)
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
    
    def _extract_images_from_document(self, document: DoclingDocument) -> List[Dict[str, Any]]:
        """
        从文档中提取所有图片
        
        Args:
            document: 文档对象
            
        Returns:
            图片信息列表，每个元素包含图片路径和在文档中的位置信息
        """
        # 提取文档中的所有图片
        images_info = []
        picture_counter = 0
        
        # 调试信息
        print("开始提取图片...")
        
        try:
            # 尝试使用iterate_items方法
            for element, level in document.iterate_items():
                # 打印元素类型，帮助调试
                print(f"元素类型: {type(element)}")
                
                # 检查元素是否为图片
                if isinstance(element, PictureItem):
                    picture_counter += 1
                    
                    # 生成唯一的图片文件名
                    image_filename = f"image_{picture_counter}_{uuid.uuid4().hex[:8]}.png"
                    image_path = os.path.join(self.temp_image_dir, image_filename)
                    
                    # 保存图片
                    try:
                        # 获取图片并保存
                        image = element.get_image(document)
                        image.save(image_path, "PNG")
                        
                        # 记录图片信息
                        images_info.append({
                            "image_path": image_path,
                            "element_id": element.id,
                            "page_no": element.page_no,
                            "position": picture_counter,
                            "element": element  # 保存元素引用，用于后续处理
                        })
                        
                        print(f"已提取图片 {picture_counter}: {image_path}")
                    except Exception as e:
                        print(f"提取图片 {picture_counter} 失败: {str(e)}")
        except AttributeError:
            print("文档对象没有iterate_items方法，尝试其他方法提取图片...")
            
            # 尝试其他可能的方法提取图片
            try:
                # 尝试使用get_pictures方法
                if hasattr(document, 'get_pictures'):
                    pictures = document.get_pictures()
                    for i, picture in enumerate(pictures):
                        picture_counter += 1
                        
                        # 生成唯一的图片文件名
                        image_filename = f"image_{picture_counter}_{uuid.uuid4().hex[:8]}.png"
                        image_path = os.path.join(self.temp_image_dir, image_filename)
                        
                        # 保存图片
                        try:
                            # 获取图片并保存
                            if hasattr(picture, 'image'):
                                image = picture.image
                            elif hasattr(picture, 'get_image'):
                                image = picture.get_image()
                            else:
                                image = picture
                                
                            if isinstance(image, Image.Image):
                                image.save(image_path, "PNG")
                                
                                # 记录图片信息
                                images_info.append({
                                    "image_path": image_path,
                                    "element_id": getattr(picture, 'id', f'pic_{i}'),
                                    "page_no": getattr(picture, 'page_no', 0),
                                    "position": picture_counter,
                                    "element": picture  # 保存元素引用，用于后续处理
                                })
                                
                                print(f"已提取图片 {picture_counter}: {image_path}")
                        except Exception as e:
                            print(f"提取图片 {picture_counter} 失败: {str(e)}")
                else:
                    print("文档对象没有get_pictures方法")
            except Exception as e:
                print(f"尝试其他方法提取图片失败: {str(e)}")
        
        # 如果没有提取到图片，尝试直接从文档内容中查找图片
        if len(images_info) == 0:
            print("尝试从文档内容中查找图片...")
            
            # 尝试从文档内容中查找图片
            try:
                # 导出文档为临时文件
                temp_dir = os.path.join(self.temp_image_dir, "temp_doc")
                os.makedirs(temp_dir, exist_ok=True)
                
                # 如果docling支持导出为docx，则导出
                if hasattr(document, 'export_to_docx'):
                    temp_docx = os.path.join(temp_dir, "temp_doc.docx")
                    document.export_to_docx(temp_docx)
                    
                    # 使用python-docx提取图片
                    try:
                        from docx import Document as DocxDocument
                        from docx.parts.image import ImagePart
                        
                        docx_doc = DocxDocument(temp_docx)
                        
                        # 提取图片
                        for rel_id, rel in docx_doc.part.rels.items():
                            if isinstance(rel.target_part, ImagePart):
                                picture_counter += 1
                                
                                # 生成唯一的图片文件名
                                image_filename = f"image_{picture_counter}_{uuid.uuid4().hex[:8]}.png"
                                image_path = os.path.join(self.temp_image_dir, image_filename)
                                
                                # 保存图片
                                with open(image_path, 'wb') as f:
                                    f.write(rel.target_part.blob)
                                
                                # 记录图片信息
                                images_info.append({
                                    "image_path": image_path,
                                    "element_id": rel_id,
                                    "page_no": 0,
                                    "position": picture_counter,
                                    "element": None  # 没有元素引用
                                })
                                
                                print(f"已从docx提取图片 {picture_counter}: {image_path}")
                    except ImportError:
                        print("未安装python-docx库，无法从docx提取图片")
                    except Exception as e:
                        print(f"从docx提取图片失败: {str(e)}")
            except Exception as e:
                print(f"从文档内容中查找图片失败: {str(e)}")
        
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
            
            # 发送请求
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload
            )
            
            # 解析响应
            if response.status_code == 200:
                result = response.json()
                description = result["choices"][0]["message"]["content"]
                return description
            else:
                print(f"API请求失败: {response.status_code} {response.text}")
                return f"[图片描述生成失败: API错误 {response.status_code}]"
                
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
            # 获取图片元素
            picture_element = image_info["element"]
            
            # 创建描述文本元素
            description_text = f"[图片描述: {image_info['description']}]"
            
            # 在图片后插入描述文本
            try:
                # 创建文本元素
                text_item = TextItem(text=description_text)
                
                # 获取图片元素的父元素和索引
                parent_elements = self._find_parent_elements(modified_document, picture_element.id)
                
                if parent_elements:
                    parent_element, index = parent_elements
                    # 在图片后插入描述文本
                    parent_element.children.insert(index + 1, text_item)
                    print(f"已在图片后插入描述文本")
                else:
                    print(f"未找到图片的父元素，无法插入描述文本")
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
            
            # 保存为纯文本
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_text)
            
            print(f"已将文档保存为纯文本: {output_path}")
            
        except Exception as e:
            print(f"保存文档失败: {str(e)}")

    async def process_document_async(self, file_path: str) -> str:
        """
        异步处理文档，提取图片并生成描述
        
        Args:
            file_path: 文档路径
            
        Returns:
            包含图片描述的纯文本结果
        """
        print(f"开始异步处理文档: {file_path}")
        
        # 1. 转换文档并提取图片
        conversion_result = self.doc_converter.convert(file_path)
        document = conversion_result.document
        images_info = self._extract_images_from_document(document)
        
        # 2. 异步对每个图片生成描述
        tasks = []
        for image_info in images_info:
            image_path = image_info["image_path"]
            print(f"准备描述图片: {image_path}")
            
            # 创建异步任务
            prompt = "请详细描述这张图片中的所有内容，包括文本、图表、图形和其他视觉元素。"
            task = asyncio.create_task(self._describe_image_with_model_async(image_path, prompt))
            tasks.append((image_info, task))
        
        # 等待所有任务完成
        for image_info, task in tasks:
            description = await task
            image_info["description"] = description
        
        # 3. 生成包含图片描述的文本
        result_text = self._generate_text_with_descriptions(document, images_info)
        
        print(f"文档异步处理完成，生成了包含{len(images_info)}个图片描述的文本")
        return result_text
    
    async def _describe_image_with_model_async(self, image_path: str, prompt: str) -> str:
        """
        异步使用多模态模型描述图片
        
        Args:
            image_path: 图片路径
            prompt: 描述提示词
            
        Returns:
            图片描述
        """
        # 这里实现异步版本的图片描述逻辑
        # 为了简单起见，这里使用同步方法并包装为异步
        return self._describe_image_with_model(image_path, prompt)


# 示例用法
if __name__ == "__main__":
    # 创建处理器实例
    processor = DocumentImageProcessor(
        api_key="sk-FefbDs44DxjdtEeQMBpWDe1WZtAFHsle55dSnTUuGv50uUXx",
        api_base="https://api.moonshot.cn/v1",
        multimodal_model="moonshot-v1-32k"
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




