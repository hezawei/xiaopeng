import asyncio

from docling.document_converter import DocumentConverter


async def get_file_content():
    """获取需求文件内容"""
    source = "api_doc.pdf"  # document per local path or URL
    converter = DocumentConverter()
    result = converter.convert(source)
    print(result.document.export_to_markdown())

asyncio.run(get_file_content())