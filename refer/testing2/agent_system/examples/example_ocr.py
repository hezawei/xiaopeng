from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TesseractCliOcrOptions,
    TesseractOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
def main():
    input_doc = Path("./05-ucmp_V1.1.8.pdf")
    # 在调用 docling 前添加以下配置
    from docling.models.tesseract_ocr_cli_model import TesseractOcrCliModel

    TesseractOcrCliModel.DEFAULT_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # 替换为你的实际路径
    # Set lang=["auto"] with a tesseract OCR engine: TesseractOcrOptions, TesseractCliOcrOptions
    # ocr_options = TesseractOcrOptions(lang=["auto"])
    ocr_options = TesseractCliOcrOptions(lang=["auto"], tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe")

    pipeline_options = PdfPipelineOptions(
        do_ocr=True, force_full_page_ocr=False, ocr_options=ocr_options
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
            )
        }
    )

    doc = converter.convert(input_doc).document
    md = doc.export_to_markdown()
    print(md)


main()