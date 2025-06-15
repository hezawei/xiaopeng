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

from docling.datamodel.document import DoclingDocument
from docling_core.types.doc import PictureItem
from docling.document_converter import DocumentConverter

class MultimodalDocumentProcessor:
    """
    处理文档中图片的类
    
    该类提供了一套完整的文档图片处理流程，包括：
    1. 从Word文档中提取文本和图片
    2. 使用多模态大模型对图片进行详细描述
    3. 将图片描述替换到文档中的相应位置
    4. 输出包含图片描述的纯文本结果或Markdown文本
    """
    
    def __init__(self):
        """
        初始化文档图片处理器
        """
        # 直接定义API密钥列表
        self.api_keys = [
            "sk-fCgBeG8ETu8MMCIaAmdOI4JpOKKagF7qXNIE4kIhu2q8zEU3",
            "sk-n9Kb2lFGyV3LJ0GEwg3NBjy5ZrJk3qTlNJJt4Kfkro7T8Fct",
            "sk-GwCmhwrrhicbkbishgUhYmVg6IrAJkg4mwWPNIMpdkQBe8tr",
            "sk-3vO3Ku08wFZBRREAWGxPWKYtEcUE8pZ1ResjWOa0RvBLz2aM",
        ]
            
        # 直接定义API基础URL和模型名称
        self.api_base = "https://api.moonshot.cn/v1"
        self.multimodal_model = "moonshot-v1-32k-vision-preview"
        
        # 确保并发数不超过API密钥数量
        self.max_concurrent_requests = len(self.api_keys)
        
        # 获取脚本所在目录的绝对路径
        from pathlib import Path
        script_dir = Path(__file__).parent.absolute()
        
        # 直接定义临时目录为脚本目录下的temp_images
        self.temp_image_dir = str(script_dir / "temp_images")
        
        # 确保临时目录存在
        os.makedirs(self.temp_image_dir, exist_ok=True)
        
        # 初始化文档转换器
        self.doc_converter = DocumentConverter()
        
        # API密钥管理 - 使用锁和状态跟踪
        self.api_key_in_use = {key: False for key in self.api_keys}
        self.api_key_last_used = {key: 0 for key in self.api_keys}
        
        # 创建API密钥池信号量 - 限制总并发数
        self.api_key_semaphore = asyncio.Semaphore(len(self.api_keys))
    
    def _extract_images_from_document(self, document: DoclingDocument, original_file_path: str = None) -> List[Dict[str, Any]]:
        """
        从文档中提取主要图片（与Markdown标记对应的图片）
        
        Args:
            document: 文档对象
            original_file_path: 原始文件路径
            
        Returns:
            图片信息列表，每个元素包含图片路径和在文档中的位置信息
        """
        # 获取文档的Markdown文本，用于计算图片标记数量
        markdown_text = document.export_to_markdown()
        image_marker_count = markdown_text.count("<!-- image -->")
        print(f"Markdown中包含 {image_marker_count} 个图片标记")
        
        # 提取文档中的所有图片
        images_info = []
        picture_counter = 0
        
        # 根据文档类型选择最佳提取方法
        if original_file_path:
            file_ext = os.path.splitext(original_file_path.lower())[1]
            
            # 对于Word文档，使用python-docx方法
            if file_ext == '.docx':
                print("使用python-docx库提取Word文档图片...")
                try:
                    import docx
                    from docx.parts.image import ImagePart
                    
                    doc = docx.Document(original_file_path)
                    
                    # 存储所有图片关系
                    image_rels = {}
                    for rel_id, rel in doc.part.rels.items():
                        if isinstance(rel.target_part, ImagePart):
                            image_rels[rel_id] = rel
                    
                    # 遍历文档中的所有段落，查找主要图片引用（不在表格中的图片）
                    ordered_rel_ids = []
                    
                    # 检查文档主体中的图片（不在表格中的图片）
                    for paragraph in doc.paragraphs:
                        for run in paragraph.runs:
                            # 检查run的XML内容中的图片引用
                            xml = run._element.xml
                            for rel_id in image_rels.keys():
                                # 在XML中查找图片关系ID
                                if rel_id in xml and rel_id not in ordered_rel_ids:
                                    # 检查这个图片是否在表格中
                                    is_in_table = False
                                    parent = run._element
                                    while parent is not None:
                                        if parent.tag.endswith('tbl'):
                                            is_in_table = True
                                            break
                                        parent = parent.getparent()
                                    
                                    # 只添加不在表格中的图片
                                    if not is_in_table:
                                        ordered_rel_ids.append(rel_id)
                    
                    # 按照找到的顺序提取图片
                    for doc_idx, rel_id in enumerate(ordered_rel_ids):
                        rel = image_rels[rel_id]
                        # 获取图片数据
                        image_data = rel.target_part.blob
                        
                        # 保存图片到临时文件
                        picture_counter += 1
                        image_filename = f"docx_image_{doc_idx}_{uuid.uuid4().hex[:8]}.png"
                        image_path = os.path.join(self.temp_image_dir, image_filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(image_data)
                        
                        # 记录图片信息
                        images_info.append({
                            "image_path": image_path,
                            "position": picture_counter,
                            "location_info": f"Word文档中的第{doc_idx+1}张主图片(ID:{rel_id})"
                        })
                except Exception as e:
                    print(f"使用python-docx提取图片时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # 对于PDF文档，使用PyMuPDF方法
            elif file_ext == '.pdf':
                try:
                    import fitz  # PyMuPDF
                    print("使用PyMuPDF提取PDF图片...")
                    
                    doc = fitz.open(original_file_path)
                    all_images = []
                    
                    for page_idx, page in enumerate(doc):
                        # 获取页面上的图片
                        image_list = page.get_images(full=True)
                        
                        # 处理页面上的每个图片
                        for img_idx, img_info in enumerate(image_list):
                            xref = img_info[0]
                            base_image = doc.extract_image(xref)
                            image_data = base_image["image"]
                            
                            # 记录图片信息
                            all_images.append({
                                "page_idx": page_idx,
                                "img_idx": img_idx,
                                "xref": xref,
                                "image_data": image_data
                            })
                    
                    # 保存选定的图片
                    for idx, img_info in enumerate(all_images):
                        picture_counter += 1
                        image_filename = f"pdf_image_{img_info['page_idx']}_{img_info['img_idx']}_{uuid.uuid4().hex[:8]}.png"
                        image_path = os.path.join(self.temp_image_dir, image_filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(img_info["image_data"])
                        
                        images_info.append({
                            "image_path": image_path,
                            "position": picture_counter,
                            "location_info": f"PDF第{img_info['page_idx']+1}页的第{img_info['img_idx']+1}张图片"
                        })
                    
                    doc.close()
                except Exception as e:
                    print(f"使用PyMuPDF提取图片时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"不支持的文件类型: {file_ext}，无法提取图片")
        else:
            print("未提供原始文件路径，无法提取图片")
        
        print(f"总共提取到 {len(images_info)} 张主要图片")
        return images_info

    async def _process_single_image(self, image_info: Dict[str, Any], image_path: str, prompt: str) -> None:
        """
        处理单个图片的描述任务
        
        Args:
            image_info: 图片信息字典，将被原地修改添加描述
            image_path: 图片路径
            prompt: 描述提示词
        """
        try:
            description = await self._describe_image_with_api_key_pool(image_path, prompt)
            image_info["description"] = description
            print(f"成功获取图片描述: {image_path}")
        except Exception as e:
            print(f"描述图片失败: {str(e)}")
            image_info["description"] = f"[图片描述生成失败: {str(e)}]"

    async def _describe_image_with_api_key_pool(self, image_path: str, prompt: str) -> str:
        """使用API密钥池异步描述图片"""
        # 从API密钥池获取可用的API密钥
        try:
            async with self.api_key_semaphore:
                # 获取可用的API密钥
                api_key = await self._get_available_api_key()
                
                try:
                    # 标记API密钥为使用中
                    self.api_key_in_use[api_key] = True
                    
                    # 使用选中的API密钥发送请求
                    return await self._send_image_description_request(image_path, prompt, api_key)
                except Exception as e:
                    # 记录特定API密钥的错误
                    print(f"API密钥 {api_key[:8]}... 请求失败: {str(e)}")
                    raise
                finally:
                    # 无论成功失败，都标记API密钥为可用
                    self.api_key_in_use[api_key] = False
                    # 更新最后使用时间
                    self.api_key_last_used[api_key] = time.time()
        except Exception as e:
            # 所有API密钥都失败的情况
            print(f"所有API密钥请求都失败: {str(e)}")
            return f"[无法获取图片描述: {str(e)}]"

    async def _get_available_api_key(self) -> str:
        """
        获取当前可用的API密钥，优先选择未被使用的密钥
        
        Returns:
            API密钥
        """
        # 首先尝试获取未被使用的密钥
        available_keys = [key for key, in_use in self.api_key_in_use.items() if not in_use]
        
        if available_keys:
            # 如果有未使用的密钥，按最后使用时间排序
            sorted_keys = sorted([(key, self.api_key_last_used[key]) for key in available_keys], 
                                key=lambda x: x[1])
            return sorted_keys[0][0]
        else:
            # 如果所有密钥都在使用中，等待任意一个密钥变为可用
            while True:
                await asyncio.sleep(0.1)  # 短暂等待
                available_keys = [key for key, in_use in self.api_key_in_use.items() if not in_use]
                if available_keys:
                    sorted_keys = sorted([(key, self.api_key_last_used[key]) for key in available_keys], 
                                        key=lambda x: x[1])
                    return sorted_keys[0][0]

    async def _send_image_description_request(self, image_path: str, prompt: str, api_key: str) -> str:
        """
        发送图片描述请求

        Args:
            image_path: 图片路径
            prompt: 描述提示词
            api_key: API密钥

        Returns:
            图片描述
        """
        print(f"使用API密钥 {api_key[:8]}... 处理图片: {image_path}")

        try:
            # 读取图片并转换为base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")

            # 构建API请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
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
                max_retries = 3
                retry_count = 0
                retry_delay = 2

                while retry_count < max_retries:
                    try:
                        async with session.post(
                            f"{self.api_base}/chat/completions",
                            headers=headers,
                            json=payload,
                            timeout=100
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                description = result["choices"][0]["message"]["content"]
                                print(f"成功获取图片描述: {image_path}")
                                return description
                            elif response.status == 429:
                                # 速率限制，检查响应头中的Retry-After
                                retry_after = response.headers.get('Retry-After')
                                wait_time = int(retry_after) if retry_after and retry_after.isdigit() else retry_delay

                                response_text = await response.text()
                                print(f"API密钥 {api_key[:8]}... 请求受到速率限制，等待{wait_time}秒后重试")
                                await asyncio.sleep(wait_time)
                                retry_delay = max(retry_delay * 1.5, wait_time * 1.2)  # 动态调整重试延迟
                                retry_count += 1
                            else:
                                response_text = await response.text()
                                raise Exception(f"API错误 {response.status}: {response_text}")
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        print(f"请求出错: {str(e)}，等待{retry_delay}秒后重试")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5
                        retry_count += 1

                raise Exception("超过最大重试次数")

        except Exception as e:
            raise Exception(f"描述图片失败: {str(e)}")

    async def process_document_to_text(self, file_path: str) -> str:
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

        # 获取文档的Markdown文本
        markdown_text = document.export_to_markdown()
        print(f"导出的Markdown文本长度: {len(markdown_text)}")

        # 检查文档中是否包含图片标记
        image_marker_count = markdown_text.count("<!-- image -->")
        print(f"在Markdown中找到 {image_marker_count} 个图片标记")

        if len(images_info) == 0:
            print("警告: 未从文档中提取到任何图片，返回原始文档内容")
            return markdown_text

        # 检查图片数量与标记数量是否匹配
        if image_marker_count != len(images_info):
            print(f"警告: 图片标记数量({image_marker_count})与提取的图片数量({len(images_info)})不匹配")
            print("返回原始文档内容，不进行图片描述替换")
            return markdown_text

        # 2. 创建所有图片描述任务
        prompt = """请分析这张图片并提供详细描述。根据图片类型给出适当的描述:

        - 如果是流程图或架构图: 详细描述各个组件、流程步骤、数据流向和逻辑关系
        - 如果是表格: 描述表格结构、列名和主要数据内容
        - 如果是图表(如柱状图、饼图等): 解释图表表达的数据关系、趋势和关键数据点
        - 如果是界面截图: 描述界面布局、功能区域和主要控件
        - 如果是其他类型图片: 描述图片中的主要视觉元素和内容

        请确保描述全面、准确，覆盖图片中的所有重要信息，包括任何文本内容。"""

        # 创建任务列表
        tasks = []
        for i, image_info in enumerate(images_info):
            image_path = image_info["image_path"]
            print(f"创建图片描述任务 {i+1}/{len(images_info)}: {image_path}")
            task = self._process_single_image(image_info, image_path, prompt)
            tasks.append(task)

        # 并发执行所有任务
        print(f"开始并发处理 {len(tasks)} 个图片描述任务")
        await asyncio.gather(*tasks)

        # 打印每个图片的描述结果（调试用）
        for i, image_info in enumerate(images_info):
            desc = image_info.get("description", "[无描述]")
            print(f"图片 {i+1} 描述: {desc[:50]}...")

        try:
            # 3. 将图片标记替换为图片描述
            result_text = self._replace_images_with_descriptions(markdown_text, images_info)
            print(f"文档处理完成，生成了包含{len(images_info)}个图片描述的文本")
            return result_text
        except ValueError as e:
            # 如果替换过程中出错，返回原始文档
            print(f"替换图片描述时出错: {str(e)}")
            print("返回原始文档内容，不进行图片描述替换")
            return markdown_text

    def _replace_images_with_descriptions(self, text: str, images_info: List[Dict[str, Any]]) -> str:
        """
        将文本中的图片标记替换为图片描述

        Args:
            text: 原始文本
            images_info: 图片信息列表

        Returns:
            替换后的文本
        """
        result_text = text

        # 查找所有 <!-- image --> 标记的位置
        image_markers = []
        marker = "<!-- image -->"
        start_pos = 0

        while True:
            pos = result_text.find(marker, start_pos)
            if pos == -1:
                break
            image_markers.append(pos)
            start_pos = pos + len(marker)

        print(f"在文档中找到 {len(image_markers)} 个图片标记")

        # 如果标记数量与图片数量不匹配，抛出错误
        if len(image_markers) != len(images_info):
            error_msg = f"错误: 图片标记数量({len(image_markers)})与图片数量({len(images_info)})不匹配，无法继续处理"
            print(error_msg)
            raise ValueError(error_msg)

        # 从后往前替换，避免位置偏移问题
        for i in range(len(image_markers) - 1, -1, -1):
            marker_pos = image_markers[i]
            image_info = images_info[i]
            description = image_info.get("description", "[图片描述不可用]")

            # 构建替换文本
            replacement = f"\n\n**图片 {i+1} 描述:**\n{description}\n\n"

            # 替换标记
            result_text = (result_text[:marker_pos] +
                          replacement +
                          result_text[marker_pos + len(marker):])

        return result_text


# 为了保持向后兼容性，创建一个别名
DocumentImageProcessor = MultimodalDocumentProcessor


# 示例用法
if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    
    async def main():
        # 获取脚本所在目录的绝对路径
        script_dir = Path(__file__).parent.absolute()
        
        # 创建处理器实例 - 使用默认配置
        processor = MultimodalDocumentProcessor()
        
        # 处理文档并输出文本
        document_path = "海外三方地图分享地址到车.docx"  # 替换为实际的文档路径
        output_text_path = str(script_dir / "example_with_image_descriptions.txt")
        
        print(f"开始处理文档: {document_path}")
        
        # 使用异步方法处理文档
        result_text = await processor.process_document_to_text(document_path)
        
        # 保存结果到文件
        try:
            with open(output_text_path, "w", encoding="utf-8") as f:
                f.write(result_text)
            print(f"\n处理结果已保存到: {output_text_path}")
        except Exception as e:
            print(f"保存结果失败: {str(e)}")
            print("\n处理结果预览:")
            print(result_text[:500] + "...")

    # 运行异步主函数
    asyncio.run(main())



























