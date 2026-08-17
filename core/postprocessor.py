# core/postprocessor.py
import re

def clean_markdown_bullets(text: str) -> str:
    """Normalizes bullet points and ensures clean formatting."""
    # Normalize varied bullet styles (e.g., *, +, -) to standard '-'
    cleaned = re.sub(r'^[ \t]*[\*\+][ \t]+', '- ', text, flags=re.MULTILINE)
    # Ensure double newlines between major markdown headers for clean rendering
    cleaned = re.sub(r'\n(#{1,4}\s+)', r'\n\n\1', cleaned)
    return cleaned.strip()

def assemble_final_markdown(
    summary_text: str,
    analogy_text: str,
    image_filename: str = "5_final_visual.png",
    is_extracted_figure: bool = False
) -> str:
    """Stitches clean summary and HTML Figure Card with persona-adaptive framing."""
    clean_summary = clean_markdown_bullets(summary_text)

    # Adaptive header and figure caption based on visual source
    if is_extracted_figure:
        section_title = "📐 Key Architectural Diagram"
        caption_title = "Figure 1: Technical Model Architecture"
    else:
        section_title = "🎨 Core Concept Visualization"
        caption_title = "💡 Figure 1: Core Concept Metaphor"

    figure_card_html = f"""

---
## {section_title}

<div align="center" style="margin-top: 15px; border: 1px solid #e0e0e0; padding: 18px; border-radius: 12px; background-color: #fafafa; text-align: center; width: 75%; margin-left: auto; margin-right: auto;">
  <img src="{image_filename}" alt="{caption_title}" style="max-width: 100%; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.12);" />
  <p style="font-weight: bold; font-size: 1.1em; color: #222; margin-top: 15px; margin-bottom: 5px;">{caption_title}</p>
  <p style="font-size: 0.95em; color: #555; font-style: italic; margin-top: 0;">{analogy_text}</p>
</div>
"""
    return clean_summary + figure_card_html