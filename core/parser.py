# core/parser.py
import os
import time
from typing import Tuple, List
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc import PictureItem

import os

# Also add the compilation bypass lines from earlier if needed:
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["TORCHDYNAMO_DISABLE"] = "1"



# Your original imports follow below...
import torch
from diffusers import AutoPipelineForText2Image

# def extract_text_with_docling(pdf_path: str) -> tuple[str, float]:
#     """Phase 1.1: Extracts and cleans structured text from PDF using Docling."""
#     start_time = time.perf_counter()
#     converter = DocumentConverter()
#     result = converter.convert(pdf_path)
#     raw_markdown = result.document.export_to_markdown()
#     elapsed = time.perf_counter() - start_time
#     return raw_markdown, elapsed

def extract_pdf_content(
    pdf_path: str, 
    extract_figures: bool = False,
    figures_dir: str = "output/figures"
) -> Tuple[str, List[str], float]:
    """
    Parses a PDF using Docling in a single pass.
    Only extracts embedded figures if extract_figures=True.
    """
    start_time = time.perf_counter()
    extracted_figures = []
    
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.generate_picture_images = extract_figures
    if extract_figures:
        pipeline_options.images_scale = 1.5
        os.makedirs(figures_dir, exist_ok=True)
    
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    
    result = converter.convert(pdf_path)
    raw_markdown = result.document.export_to_markdown()
    
    if extract_figures:
        fig_counter = 0
        for element, _level in result.document.iterate_items():
            if isinstance(element, PictureItem):
                try:
                    pil_image = element.get_image(result.document)
                    if pil_image and pil_image.width > 120 and pil_image.height > 120:
                        fig_counter += 1
                        fig_path = os.path.join(figures_dir, f"figure_{fig_counter}.png")
                        pil_image.save(fig_path, format="PNG")
                        extracted_figures.append(fig_path)
                except Exception:
                    continue

    elapsed_time = time.perf_counter() - start_time
    return raw_markdown, extracted_figures, elapsed_time