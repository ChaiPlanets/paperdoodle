# core/config.py

DEFAULT_EXTRACTION_RATIO = 0.28
DEFAULT_GROQ_MODEL = "groq/llama-3.3-70b-versatile"
DEFAULT_HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
HF_INFERENCE_BASE_URL = "https://api-inference.huggingface.co/models"

# Visual Style Presets
STYLE_PROMPTS = {
    "Line Art Doodle": (
        "Minimalist continuous black line-art drawing, whimsical sketch doodle style, "
        "clean pure white background, vector line simplicity, no shading, no solid dark fills, no text."
    ),
    "Whiteboard Sketch": (
        "Hand-drawn dry-erase marker whiteboard illustration, clean colorful marker outlines "
        "on pure white background, presentation sketch, no text."
    ),
    "Technical Blueprint": (
        "Technical cyan schematic drawing, precise blueprint style, clean geometric drafting lines, "
        "minimal engineering diagram, no text."
    )
}

CSS_STYLES_PDF = """
@page {
    size: A4;
    margin: 20mm;
    @bottom-center {
        content: counter(page);
        font-family: Arial, sans-serif;
        font-size: 0.9em;
        color: #777;
    }
}
body { font-family: 'Georgia', serif; color: #333; line-height: 1.6; }
h1, h2, h3 { font-family: 'Arial', sans-serif; color: #111; }
h1 { font-size: 2em; border-bottom: 2px solid #222; padding-bottom: 8px; }
h2 { font-size: 1.5em; margin-top: 1.3em; border-bottom: 1px solid #eee; padding-bottom: 4px; }
ul { margin: 10px 0 15px 25px; }
li { margin-bottom: 6px; }
p { margin-bottom: 1em; }
"""