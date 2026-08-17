# core/synthesizer.py
import os
import re
import time
from typing import Tuple, Dict
from litellm import completion

PERSONA_FOLDER_MAP = {
    "Executive / CTO": "executive",
    "Researcher / Engineer": "researcher",
    "Educator / Student": "educator"
}

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")


def load_prompt_template(persona: str, template_type: str) -> str:
    """Loads markdown prompt template from prompts/{persona_folder}/{template_type}.md."""
    folder_name = PERSONA_FOLDER_MAP.get(persona, "educator")
    template_path = os.path.join(PROMPTS_DIR, folder_name, f"{template_type}.md")
    
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read().strip()
            
    # Generic fallback if template file is missing
    return f"Summarize the following paper context for a {persona} audience using structured markdown."


def generate_research_briefing(
    context: str,
    api_key: str,
    model: str = "groq/llama-3.3-70b-versatile",
    persona: str = "Educator / Student"
) -> Tuple[str, str, Dict]:
    """Generic synthesizer that dynamically drives prompts from markdown templates."""
    start_time = time.perf_counter()
    
    summary_sys_prompt = load_prompt_template(persona, "summary")
    analogy_sys_prompt = load_prompt_template(persona, "analogy")

    combined_system_prompt = f"""{summary_sys_prompt}

---

{analogy_sys_prompt}
"""

    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": combined_system_prompt},
            {"role": "user", "content": f"Research Context:\n\n{context}"}
        ],
        api_key=api_key,
        temperature=0.2
    )

    elapsed_sec = time.perf_counter() - start_time
    content = response.choices[0].message.content.strip()
    total_tokens = getattr(response.usage, "total_tokens", 0) if hasattr(response, "usage") else 0

    # Extract Analogy
    analogy_match = re.search(
        r"(?:##\s*(?:\d+\.)?\s*Human Analogy|##\s*(?:\d+\.)?\s*Real-World Analogy)\s*([\s\S]*?)(?=##\s*(?:\d+\.)?\s*Visual Scene Prompt|##\s*(?:\d+\.)?\s*Visual Prompt|$)",
        content,
        re.IGNORECASE
    )
    analogy_text = analogy_match.group(1).strip() if analogy_match else "Intuitive conceptual analogy."

    # Extract Visual Scene Prompt
    visual_match = re.search(
        r"(?:##\s*(?:\d+\.)?\s*Visual Scene Prompt|##\s*(?:\d+\.)?\s*Visual Prompt)\s*([\s\S]*)$",
        content,
        re.IGNORECASE
    )
    visual_prompt = visual_match.group(1).strip() if visual_match else analogy_text

    # Extract Summary content (everything prior to the Analogy/Visual section)
    summary_match = re.search(
        r"([\s\S]*?)(?=##\s*(?:\d+\.)?\s*(?:Human|Real-World)?\s*Analogy|$)",
        content,
        re.IGNORECASE
    )
    summary_text = summary_match.group(1).strip() if summary_match else content

    metrics = {
        "elapsed_sec": elapsed_sec,
        "total_tokens": total_tokens,
        "visual_prompt": visual_prompt
    }

    return summary_text, analogy_text, metrics

# Compatibility alias
generate_executive_summary = generate_research_briefing