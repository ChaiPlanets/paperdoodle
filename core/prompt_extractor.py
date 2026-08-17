# core/prompt_extractor.py
import re
import time
from core.config import DOODLE_STYLE_PREFIX, DOODLE_STYLE_SUFFIX

def extract_doodle_prompt(summary_text: str) -> tuple[str, str, float]:
    """Phase 2: Extracts analogy via regex and constructs text-free prompt."""
    start_time = time.perf_counter()
    pattern = r"\[Analogy Start\](.*?)\[Analogy End\]"
    match = re.search(pattern, summary_text, re.DOTALL | re.IGNORECASE)
    
    if match:
        analogy = match.group(1).strip()
        analogy = re.sub(r"\s+", " ", analogy)
    else:
        analogy = "A simple system showing inputs interacting with a central processing mechanism to generate outputs."
        
    full_prompt = f"{DOODLE_STYLE_PREFIX}{analogy}{DOODLE_STYLE_SUFFIX}"
    elapsed = time.perf_counter() - start_time
    return analogy, full_prompt, elapsed