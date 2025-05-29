"""
文档图片提取方法测试

本脚本用于测试不同的图片提取方法，并比较它们的效果。
"""

import os
import uuid
import time
from pathlib import Path
from typing import List, Dict, Any

# 导入所需的库
from docling.document_converter import DocumentConverter
from docling.datamodel.document import DoclingDocument
from docling_core.types.doc import PictureItem

# 可选导入
try:
    import docx
    from docx.document import Document as DocxDocument
    from docx.parts.image import ImagePart
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

class ImageExtractorTester:
    """测试不同的图片提取方法"""
    
    def __init__(self, temp_dir: str = "./test_images"):
        self.temp_image_dir = temp_dir
        os.makedirs(self.temp_image_dir, exist_ok=True)
        self.doc_converter = DocumentConverter()
    
    def test_all_methods(self, file_path: str):
        """测试所有提取方法"""
        print(f"测试文件: {file_path}")
        
        # 转换文档
        conversion_result = self.doc_converter.convert(file_path)
        document = conversion_result.document
        
        # 测试方法1: DoclingDocument
        start_time = time.time()
        images1 = self._extract_with_docling_document(document)
        time1 = time.time() - start_time
        print(f"方法1 (DoclingDocument): 提取到 {len(images1)} 张图片，耗时 {time1:.2f} 秒")
        
        # 测试方法2: python-docx (仅适用于.docx)
        if file_path.lower().endswith('.docx') and DOCX_AVAILABLE:
            start_time = time.time()
            images2 = self._extract_with_python_docx(file_path)
            time2 = time.time() - start_time
            print(f"方法2 (python-docx): 提取到 {len(images2)} 张图片，耗时 {time2:.2f} 秒")
        else:
            images2 = []
            time2 = 0
            print("方法2 (python-docx): 不适用于此文件类型或库未安装")
        
        # 测试方法3: Docling转换结果
        start_time = time.time()
        images3 = self._extract_with_conversion_result(document)
        time3 = time.time() - start_time
        print(f"方法3 (Docling转换结果): 提取到 {len(images3)} 张图片，耗时 {time3:.2f} 秒")
        
        # 测试方法4: PyMuPDF (仅适用于.pdf)
        if file_path.lower().endswith('.pdf') and PYMUPDF_AVAILABLE:
            start_time = time.time()
            images4 = self._extract_with_pymupdf(file_path)
            time4 = time.time() - start_time
            print(f"方法4 (PyMuPDF): 提取到 {len(images4)} 张图片，耗时 {time4:.2f} 秒")
        else:
            images4 = []
            time4 = 0
            print("方法4 (PyMuPDF): 不适用于此文件类型或库未安装")
        
        # 测试方法5: zipfile (仅适用于.docx)
        if file_path.lower().endswith('.docx'):
            start_time = time.time()
            images5 = self._extract_with_zipfile(file_path)
            time5 = time.time() - start_time
            print(f"方法5 (zipfile): 提取到 {len(images5)} 张图片，耗时 {time5:.2f} 秒")
        else:
            images5 = []
            time5 = 0
            print("方法5 (zipfile): 不适用于此文件类型")
        
        # 比较结果
        self._compare_results(
            file_path,
            [
                ("DoclingDocument", images1, time1),
                ("python-docx", images2, time2),
                ("Docling转换结果", images3, time3),
                ("PyMuPDF", images4, time4),
                ("zipfile", images5, time5)
            ]
        )
    
    def _extract_with_docling_document(self, document: DoclingDocument) -> List[Dict[str, Any]]:
        """使用DoclingDocument对象提取图片"""
        images_info = []
        picture_counter = 0
        
        if hasattr(document, 'pages'):
            for page_idx, page in enumerate(document.pages):
                for item in page.items:
                    if isinstance(item, PictureItem):
                        picture_counter += 1
                        image_filename = f"docling_{page_idx}_{picture_counter}_{uuid.uuid4().hex[:8]}.png"
                        image_path = os.path.join(self.temp_image_dir, image_filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(item.image_data)
                        
                        images_info.append({
                            "method": "docling_document",
                            "image_path": image_path,
                            "page_idx": page_idx,
                            "position": picture_counter
                        })
        
        return images_info
    
    def _extract_with_python_docx(self, file_path: str) -> List[Dict[str, Any]]:
        """使用python-docx库提取图片"""
        images_info = []
        picture_counter = 0
        
        try:
            doc = docx.Document(file_path)
            
            for rel_id, rel in doc.part.rels.items():
                if isinstance(rel.target_part, ImagePart):
                    image_data = rel.target_part.blob
                    
                    picture_counter += 1
                    image_filename = f"docx_{picture_counter}_{uuid.uuid4().hex[:8]}.png"
                    image_path = os.path.join(self.temp_image_dir, image_filename)
                    
                    with open(image_path, "wb") as f:
                        f.write(image_data)
                    
                    images_info.append({
                        "method": "python_docx",
                        "image_path": image_path,
                        "rel_id": rel_id,
                        "position": picture_counter
                    })
        except Exception as e:
            print(f"python-docx提取错误: {str(e)}")
        
        return images_info
    
    def _extract_with_conversion_result(self, document: DoclingDocument) -> List[Dict[str, Any]]:
        """使用Docling的原始转换结果提取图片"""
        images_info = []
        picture_counter = 0
        
        try:
            if hasattr(document, '_conversion_result'):
                conversion_result = document._conversion_result
                if hasattr(conversion_result, 'images') and conversion_result.images:
                    for idx, img_data in enumerate(conversion_result.images):
                        picture_counter += 1
                        image_filename = f"conversion_{picture_counter}_{uuid.uuid4().hex[:8]}.png"
                        image_path = os.path.join(self.temp_image_dir, image_filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(img_data)
                        
                        images_info.append({
                            "method": "conversion_result",
                            "image_path": image_path,
                            "index": idx,
                            "position": picture_counter
                        })
        except Exception as e:
            print(f"转换结果提取错误: {str(e)}")
        
        return images_info
    
    def _extract_with_pymupdf(self, file_path: str) -> List[Dict[str, Any]]:
        """使用PyMuPDF提取图片"""
        images_info = []
        picture_counter = 0
        
        try:
            doc = fitz.open(file_path)
            
            for page_idx, page in enumerate(doc):
                image_list = page.get_images(full=True)
                
                for img_idx, img_info in enumerate(image_list):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_data = base_image["image"]
                    
                    picture_counter += 1
                    image_filename = f"pymupdf_{page_idx}_{img_idx}_{uuid.uuid4().hex[:8]}.png"
                    image_path = os.path.join(self.temp_image_dir, image_filename)
                    
                    with open(image_path, "wb") as f:
                        f.write(image_data)
                    
                    images_info.append({
                        "method": "pymupdf",
                        "image_path": image_path,
                        "page_idx": page_idx,
                        "img_idx": img_idx,
                        "position": picture_counter
                    })
            
            doc.close()
        except Exception as e:
            print(f"PyMuPDF提取错误: {str(e)}")
        
        return images_info
    
    def _extract_with_zipfile(self, file_path: str) -> List[Dict[str, Any]]:
        """使用zipfile直接从docx提取图片"""
        images_info = []
        picture_counter = 0
        
        try:
            import zipfile
            
            with zipfile.ZipFile(file_path) as docx_zip:
                file_list = docx_zip.namelist()
                image_files = [f for f in file_list if f.startswith('word/media/')]
                
                for img_idx, img_file in enumerate(image_files):
                    image_data = docx_zip.read(img_file)
                    
                    picture_counter += 1
                    image_filename = f"zipfile_{img_idx}_{uuid.uuid4().hex[:8]}.png"
                    image_path = os.path.join(self.temp_image_dir, image_filename)
                    
                    with open(image_path, "wb") as f:
                        f.write(image_data)
                    
                    images_info.append({
                        "method": "zipfile",
                        "image_path": image_path,
                        "source_file": img_file,
                        "position": picture_counter
                    })
        except Exception as e:
            print(f"zipfile提取错误: {str(e)}")
        
        return images_info
    
    def _compare_results(self, file_path: str, results: List[tuple]):
        """比较不同方法的结果"""
        print("\n=== 结果比较 ===")
        
        # 找出提取图片最多的方法
        max_images = max([len(images) for _, images, _ in results if images])
        
        # 找出最快的方法
        valid_times = [time for _, images, time in results if images and time > 0]
        min_time = min(valid_times) if valid_times else 0
        
        print(f"文件: {file_path}")
        print(f"最多提取图片数: {max_images}")
        
        # 推荐最佳方法
        best_method = None
        best_score = -1
        
        for method_name, images, time in results:
            if not images:
                continue
                
            # 计算得分: 图片数量占比 * 0.7 + 速度占比 * 0.3
            image_score = len(images) / max_images if max_images > 0 else 0
            speed_score = min_time / time if time > 0 else 0
            score = image_score * 0.7 + speed_score * 0.3
            
            print(f"{method_name}: {len(images)}张图片, {time:.2f}秒, 得分: {score:.2f}")
            
            if score > best_score:
                best_score = score
                best_method = method_name
        
        if best_method:
            print(f"\n推荐方法: {best_method}")
            
            # 针对不同文件类型的建议
            if file_path.lower().endswith('.docx'):
                if best_method == "DoclingDocument":
                    print("对于Word文档，建议使用DoclingDocument方法")
                elif best_method == "python-docx":
                    print("对于Word文档，建议使用python-docx方法")
                elif best_method == "zipfile":
                    print("对于Word文档，建议使用zipfile方法")
            elif file_path.lower().endswith('.pdf'):
                if best_method == "DoclingDocument":
                    print("对于PDF文档，建议使用DoclingDocument方法")
                elif best_method == "PyMuPDF":
                    print("对于PDF文档，建议使用PyMuPDF方法")
        else:
            print("没有找到有效的提取方法")

# 测试代码
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python document_image_extractor_test.py <文档路径>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    tester = ImageExtractorTester()
    tester.test_all_methods(file_path)