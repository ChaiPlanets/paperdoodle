# core/prompt_loader.py
import os
from functools import lru_cache

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

PERSONA_FOLDER_MAP = {
    "Executive / CTO": "executive",
    "Researcher / Engineer": "researcher",
    "Educator / Student": "educator"
}

@lru_cache(maxsize=16)
def load_prompt_template(persona: str, prompt_type: str = "summary") -> str:
    """Loads prompt markdown template based on persona and type ('summary' or 'analogy')."""
    folder = PERSONA_FOLDER_MAP.get(persona, "executive")
    file_path = os.path.join(PROMPTS_DIR, folder, f"{prompt_type}.md")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Prompt template not found at {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()