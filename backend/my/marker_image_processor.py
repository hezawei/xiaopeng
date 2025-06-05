"""
使用Marker库处理文档中的图片

本模块演示如何使用Marker库从PDF文档中提取图片，并使用多模态大模型对图片进行描述，
然后将描述替换回文档中的相应位置。对于Word文档，先将其转换为PDF再处理。
"""

import asyncio
import aiohttp
import base64
import os
import time
import uuid
import json
import tempfile
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# 导入Marker库
import marker
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

# 用于Word转PDF的库
import docx2pdf


class MarkerImageProcessor:
    """使用Marker库处理文档中的图片"""
    
    def __init__(self, 
                 api_keys: List[str] = [
                    "sk-fCgBeG8ETu8MMCIaAmdOI4JpOKKagF7qXNIE4kIhu2q8zEU3",
                    "sk-n9Kb2lFGyV3LJ0GEwg3NBjy5ZrJk3qTlNJJt4Kfkro7T8Fct",
                    "sk-GwCmhwrrhicbkbishgUhYmVg6IrAJkg4mwWPNIMpdkQBe8tr",
                    "sk-3vO3Ku08wFZBRREAWGxPWKYtEcUE8pZ1ResjWOa0RvBLz2aM",
                ],
                 api_base: str = "https://api.moonshot.cn/v1",
                 multimodal_model: str = "moonshot-v1-32k-vision-preview",
                 max_concurrent_requests: int = 3,
                 temp_dir: str = None):
        """
        初始化处理器
        
        Args:
            api_keys: API密钥列表，用于多模态大模型
            api_base: API基础URL
            multimodal_model: 多模态模型名称
            max_concurrent_requests: 最大并发请求数
            temp_dir: 临时文件目录
        """
        # 初始化API密钥
        self.api_keys = api_keys or []
        if not self.api_keys:
            # 尝试从环境变量获取API密钥
            env_api_key = os.environ.get("MOONSHOT_API_KEY")
            if env_api_key:
                self.api_keys = [env_api_key]
        
        # API配置
        self.api_base = api_base
        self.multimodal_model = multimodal_model
        
        # 并发控制
        self.max_concurrent_requests = max_concurrent_requests
        self.api_key_semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # API密钥状态跟踪
        self.api_key_in_use = {key: False for key in self.api_keys}
        self.api_key_last_used = {key: 0 for key in self.api_keys}
        
        # 临时目录设置
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(tempfile.gettempdir()) / "marker_images"
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化Marker模型字典
        self.artifact_dict = create_model_dict()
        print(f"Marker模型字典已初始化")
    
    def _convert_docx_to_pdf(self, docx_path: str) -> str:
        """将Word文档转换为PDF"""
        print(f"开始将Word文档转换为PDF: {docx_path}")
        
        # 创建输出PDF路径
        pdf_path = str(self.temp_dir / f"{Path(docx_path).stem}_{uuid.uuid4().hex[:8]}.pdf")
        
        try:
            # 使用docx2pdf库转换
            docx2pdf.convert(docx_path, pdf_path)
            print(f"使用docx2pdf转换成功: {pdf_path}")
            return pdf_path
        
        except Exception as e:
            print(f"Word转PDF失败: {e}")
            raise
    
    async def _get_available_api_key(self) -> str:
        """获取当前可用的API密钥"""
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
        """发送图片描述请求"""
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
    
    async def _process_single_image(self, image_info: Dict[str, Any], image_path: str, prompt: str) -> None:
        """处理单个图片的描述任务"""
        try:
            description = await self._describe_image_with_api_key_pool(image_path, prompt)
            image_info["description"] = description
            print(f"成功获取图片描述: {image_path}")
        except Exception as e:
            print(f"描述图片失败: {str(e)}")
            image_info["description"] = f"[图片描述生成失败: {str(e)}]"
    
    def _extract_images_from_marker_result(self, rendered_result) -> List[Dict[str, Any]]:
        """从Marker结果中提取图片信息"""
        images_info = []
        
        # 从marker结果中提取图片
        if hasattr(rendered_result, 'images') and rendered_result.images:
            for idx, (image_id, image_data) in enumerate(rendered_result.images.items()):
                # 保存图片到临时文件
                image_filename = f"marker_image_{idx}_{uuid.uuid4().hex[:8]}.png"
                image_path = self.temp_dir / image_filename
                
                # 保存图片数据
                try:
                    # 检查图片数据格式
                    if isinstance(image_data, str) and image_data.startswith("data:"):
                        # 处理base64编码的图片
                        image_content = image_data.split(",", 1)[1]
                        image_bytes = base64.b64decode(image_content)
                    elif isinstance(image_data, bytes):
                        # 直接使用字节数据
                        image_bytes = image_data
                    else:
                        print(f"警告: 不支持的图片数据格式，跳过图片 {idx}")
                        continue
                    
                    # 保存图片
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    
                    # 记录图片信息
                    images_info.append({
                        "image_path": str(image_path),
                        "position": idx,
                        "location_info": f"文档中的第{idx+1}张图片",
                        "marker_id": image_id  # 保存图片ID，用于后续替换
                    })
                except Exception as e:
                    print(f"保存图片失败: {e}")
        
        return images_info
    
    def _replace_images_with_descriptions(self, markdown_text: str, images_info: List[Dict[str, Any]]) -> str:
        """将Markdown文本中的图片标记替换为图片描述"""
        result_text = markdown_text
        
        # 按照图片在文档中的位置排序
        sorted_images = sorted(images_info, key=lambda x: x.get("position", 0))
        
        # 替换图片标记
        for image_info in sorted_images:
            marker_id = image_info.get("marker_id")
            description = image_info.get("description", "[图片描述生成失败]")
            
            # 使用特殊标记包围图片描述
            replacement = f"\n\n[IMAGE_DESC]{description}[/IMAGE_DESC]\n\n"
            
            # 尝试替换图片标记
            # Marker生成的markdown中图片格式通常是 ![](image_id)
            image_marker = f"![]({marker_id})"
            if image_marker in result_text:
                result_text = result_text.replace(image_marker, replacement)
            else:
                # 尝试其他可能的格式
                import re
                pattern = rf"!\[.*?\]\({marker_id}\)"
                result_text = re.sub(pattern, replacement, result_text)
        
        return result_text
    
    async def process_document_to_text(self, file_path: str) -> str:
        """处理文档，提取图片并生成描述，输出纯文本结果"""
        print(f"开始处理文档: {file_path}")
        
        # 检查文件类型
        file_ext = os.path.splitext(file_path.lower())[1]
        
        # 如果是Word文档，先转换为PDF
        pdf_path = file_path
        if file_ext == '.docx':
            print("检测到Word文档，先转换为PDF")
            try:
                pdf_path = self._convert_docx_to_pdf(file_path)
            except Exception as e:
                print(f"Word转PDF失败: {e}")
                return f"处理失败: 无法将Word文档转换为PDF: {str(e)}"
        elif file_ext != '.pdf':
            print(f"不支持的文件类型: {file_ext}")
            return f"处理失败: 不支持的文件类型 {file_ext}，仅支持 .pdf 和 .docx"
        
        # 使用Marker处理PDF文档
        try:
            print(f"使用Marker处理PDF文档: {pdf_path}")
            
            # 创建PdfConverter实例
            converter = PdfConverter(artifact_dict=self.artifact_dict)
            
            # 转换PDF文件
            rendered = converter(pdf_path)
            
            # 获取Markdown文本和图片
            markdown_text = rendered.markdown
            print(f"成功转换为Markdown，长度: {len(markdown_text)}")
            
            # 提取图片
            images_info = self._extract_images_from_marker_result(rendered)
            print(f"提取到 {len(images_info)} 张图片")
            
            if len(images_info) == 0:
                print("警告: 未从文档中提取到任何图片，返回原始文档内容")
                return markdown_text
            
            # 创建图片描述任务
            prompt = """请分析这张图片并提供详细描述。根据图片类型给出适当的描述:
            
            - 如果是流程图或架构图: 详细描述各个组件、流程步骤、数据流向和逻辑关系
            - 如果是表格: 描述表格结构、列名和主要数据内容
            - 如果是图表(如柱状图、饼图等): 解释图表表达的数据关系、趋势和关键数据点
            - 如果是界面截图: 描述界面布局、功能区域和主要控件
            - 如果是其他类型图片: 描述图片中的主要视觉元素和内容
            
            请确保描述全面、准确，覆盖图片中的所有重要信息，包括任何文本内容。"""
            
            # 创建任务列表
            tasks = []
            for image_info in images_info:
                image_path = image_info["image_path"]
                tasks.append(self._process_single_image(image_info, image_path, prompt))
            
            # 并发处理所有图片
            await asyncio.gather(*tasks)
            
            # 替换图片标记为描述
            result_text = self._replace_images_with_descriptions(markdown_text, images_info)
            
            print(f"处理完成，生成的文本长度: {len(result_text)}")
            return result_text
            
        except Exception as e:
            print(f"处理PDF文档失败: {str(e)}")
            return f"处理失败: {str(e)}"
    
    async def process_document_to_file(self, file_path: str, output_path: str) -> str:
        """处理文档并将结果保存到文件"""
        result_text = await self.process_document_to_text(file_path)
        
        # 保存结果到文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result_text)
        
        print(f"处理结果已保存到: {output_path}")
        return output_path


# 示例用法
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # 创建处理器实例
        processor = MarkerImageProcessor(
            api_base="https://api.moonshot.cn/v1",
            multimodal_model="moonshot-v1-32k-vision-preview",
            max_concurrent_requests=4
        )
        
        # 处理文档并输出文本
        document_path = "海外三方地图分享地址到车.docx"  # 替换为实际的文档路径
        output_text_path = "example_with_image_descriptions.txt"
        
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


