import asyncio
from pathlib import Path
from docling.document_converter import DocumentConverter
from llama_index.core import SimpleDirectoryReader, Document

async def convert_document_with_docling(file_path: str) -> str:
    """
    使用Docling库将文档转换为Markdown格式
    
    :param file_path: 文档文件路径（支持PDF或DOCX格式）
    :return: 转换后的Markdown文本
    """
    try:
        print(f"开始处理文件: {file_path}")
        
        # 创建DocumentConverter实例
        converter = DocumentConverter()
        
        # 转换文档
        result = converter.convert(file_path)
        
        # 将文档导出为Markdown格式
        markdown_content = result.document.export_to_markdown()
        
        # 打印文档的一些基本信息
        print(f"文档转换成功!")
        print(f"文档页数: {len(result.document.pages)}")
        
        # 返回Markdown内容
        return markdown_content
    
    except Exception as e:
        print(f"文档转换失败: {str(e)}")
        return f"错误: {str(e)}"

async def get_document_content(file_path: str) -> str:
    """
    根据文件类型选择合适的方法获取文档内容
    
    :param file_path: 文件路径
    :return: 文档内容
    """
    try:
        # 检查文件是否存在
        if not Path(file_path).exists():
            return f"错误: 文件 '{file_path}' 不存在"
        
        # 如果是PDF文件或Word文档(.docx)，使用DocumentConverter
        if file_path.endswith(('.pdf', '.docx')):
            print(f"使用Docling处理{'PDF' if file_path.endswith('.pdf') else 'Word'}文档")
            content = await convert_document_with_docling(file_path)
        else:
            # 使用LlamaIndex读取其他类型的文件
            print(f"使用LlamaIndex处理文件")
            reader = SimpleDirectoryReader(input_files=[file_path])
            docs = reader.load_data()
            content = "\n\n".join([doc.text for doc in docs])
        
        # 限制文档长度，防止超出模型上下文长度
        max_chars = 30000  # 大约10000个token
        if len(content) > max_chars:
            print(f"文档过长，进行截断处理。原长度: {len(content)} 字符")
            # 提取文档的前半部分和后半部分
            first_part = content[:max_chars//2]
            last_part = content[-max_chars//2:]
            content = first_part + "\n\n...[文档中间部分已省略]...\n\n" + last_part
            print(f"截断后长度: {len(content)} 字符")
        
        return content
    
    except Exception as e:
        import traceback
        print(f"读取文件失败，详细错误: {traceback.format_exc()}")
        return f"读取文件失败: {str(e)}"

async def main():
    """
    主函数，演示如何使用docling处理文档
    """
    # 示例：处理Word文档
    docx_file = "c:/Users/SuperV/Desktop/ai_dev/my/AI接口测试系统建设方案.docx"  # 替换为实际的Word文档路径
    print("\n=== 处理Word文档 ===")
    docx_content = await get_document_content(docx_file)
    print(f"\nWord文档内容预览 (前200字符):\n{docx_content}...\n")
    
    # 示例：处理PDF文档（如果有的话）
    # pdf_file = "example.pdf"  # 替换为实际的PDF文档路径
    # print("\n=== 处理PDF文档 ===")
    # pdf_content = await get_document_content(pdf_file)
    # print(f"\nPDF文档内容预览 (前200字符):\n{pdf_content[:200]}...\n")
    
    # 示例：处理文本文件
    # txt_file = "example.txt"  # 替换为实际的文本文件路径
    # print("\n=== 处理文本文件 ===")
    # txt_content = await get_document_content(txt_file)
    # print(f"\n文本文件内容预览 (前200字符):\n{txt_content[:200]}...\n")

if __name__ == "__main__":
    asyncio.run(main())
