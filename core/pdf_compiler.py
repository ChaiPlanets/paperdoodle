# core/pdf_compiler.py
import os
import time
import markdown
from weasyprint import HTML, CSS
from core.config import CSS_STYLES_PDF

def compile_markdown_to_pdf(full_markdown_text: str, output_pdf_path: str, base_asset_dir: str) -> tuple[str, float]:
    """Compiles styled HTML and images to PDF using WeasyPrint."""
    start_time = time.perf_counter()

    # Always persist the raw markdown briefing alongside the PDF
    md_output_path = output_pdf_path.rsplit(".", 1)[0] + ".md"
    os.makedirs(os.path.dirname(md_output_path), exist_ok=True)
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(full_markdown_text)
    
    raw_html = markdown.markdown(
        full_markdown_text,
        extensions=["extra", "smarty", "toc"]
    )
    
    html_doc = f"<!DOCTYPE html><html><head><meta charset='UTF-8'></head><body>{raw_html}</body></html>"
    
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    HTML(string=html_doc, base_url=base_asset_dir).write_pdf(
        output_pdf_path,
        stylesheets=[CSS(string=CSS_STYLES_PDF)]
    )
    
    elapsed = time.perf_counter() - start_time
    metrics = {
    "pdf_path": output_pdf_path,
    "md_path": md_output_path,
    "elapsed_sec": round(elapsed, 2)
    }
    return output_pdf_path, metrics