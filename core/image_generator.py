# core/image_generator.py
import io
import os
import sys
import time
import requests
import urllib.parse
from typing import Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageStat
from huggingface_hub import InferenceClient

PRIMARY_HF_MODEL = "black-forest-labs/FLUX.1-schnell"


def is_image_blank_or_corrupt(image_path: str) -> bool:
    """Checks if the file is readable and not purely blank/black."""
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            stat = ImageStat.Stat(img)
            avg_brightness = sum(stat.mean) / len(stat.mean)
            return avg_brightness < 2.0
    except Exception:
        return True


def create_fallback_image(output_path: str, analogy_text: str):
    """Draws a clean canvas fallback if both remote engines fail."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img = Image.new("RGB", (1024, 768), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(20, 20), (1004, 748)], outline=(203, 213, 225), width=3)
    draw.text((60, 60), "CONCEPT DIAGRAM", fill=(37, 99, 235))

    cleaned = " ".join(analogy_text.strip().split())
    if len(cleaned) > 280:
        cleaned = cleaned[:277] + "..."

    text_content = f"Visual Illustration:\n\n{cleaned}"
    draw.text((60, 110), text_content, fill=(51, 65, 85))
    img.save(output_path)


def build_doodle_prompt(analogy_text: str, style_preset: str = "Line Art Doodle") -> str:
    """Builds a minimalist visual doodle prompt with negative constraints."""
    cleaned_analogy = " ".join(analogy_text.strip().split())

    if style_preset == "Whiteboard Sketch":
        style_desc = (
            "colorful marker whiteboard drawing, simple conceptual diagram sketch, "
            "clean arrows and flowchart symbols, high contrast whiteboard"
        )
    elif style_preset == "Technical Blueprint":
        style_desc = (
            "architectural blueprint diagram, crisp white technical outlines on deep blue grid background, "
            "schematic layout, engineering symbols, isometric wireframe"
        )
    else:  # Default: Line Art Doodle
        style_desc = (
            "A whimsical, minimalist black and white line art doodle, "
            "elegant clean pen sketch style on pure white background, hand-drawn aesthetic, conceptual diagram"
        )

    return (
        f"{style_desc} illustrating: {cleaned_analogy}. "
        "Visual metaphor, no words, no letters, no typography, no labels, no handwriting, no numbers, no text."
    )


def generate_with_hf_flux(
    prompt: str,
    output_path: str,
    hf_token: str,
    model_name: str = PRIMARY_HF_MODEL
) -> bool:
    """Primary: Attempts generation via native Hugging Face FLUX."""
    if not hf_token:
        return False
    try:
        print(f"[Image Gen] 1️⃣ Trying Hugging Face FLUX ({model_name})...", flush=True)
        client = InferenceClient(api_key=hf_token.strip())
        image = client.text_to_image(prompt=prompt, model=model_name)
        image.save(output_path)
        return not is_image_blank_or_corrupt(output_path)
    except Exception as exc:
        print(f"[Image Gen] ⚠️ Hugging Face failed: {exc}", flush=True)
        return False


def generate_with_pollinations_flux(prompt: str, output_path: str) -> bool:
    """Secondary: Attempts generation via Pollinations FLUX engine."""
    try:
        print("[Image Gen] 2️⃣ Failing over to Pollinations FLUX...", flush=True)
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Primary Pollinations GET URL specifying model=flux
        endpoints = [
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=768&model=flux&nologo=true&seed=42",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=768&nologo=true&seed=42"
        ]
        
        headers = {"User-Agent": "PaperDoodle-Pipeline/1.0 (Windows NT 10.0; Win64; x64)"}
        for url in endpoints:
            try:
                resp = requests.get(url, headers=headers, timeout=25)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    if not is_image_blank_or_corrupt(output_path):
                        return True
            except Exception:
                continue
    except Exception as exc:
        print(f"[Image Gen] ⚠️ Pollinations error: {exc}", flush=True)
    return False


def generate_sketch_diagram_hf(
    analogy_text: str,
    hf_token: str = None,
    output_path: str = "output/5_doodle_diagram.png",
    style_preset: str = "Line Art Doodle",
    model_name: str = PRIMARY_HF_MODEL
) -> Tuple[str, Dict[str, Any]]:
    """
    Tiered Generation:
      1. Hugging Face FLUX.1-schnell (Primary)
      2. Pollinations.ai FLUX (Secondary Failover)
      3. PIL Local Canvas (Hard Offline Fallback)
    """
    start_time = time.perf_counter()
    image_prompt = build_doodle_prompt(analogy_text, style_preset)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 1. Primary: Hugging Face
    if generate_with_hf_flux(image_prompt, output_path, hf_token, model_name):
        elapsed = time.perf_counter() - start_time
        print(f"[Image Gen] ✅ Generated via Hugging Face FLUX in {elapsed:.2f}s", flush=True)
        return output_path, {
            "elapsed_sec": round(elapsed, 2),
            "style": style_preset,
            "status": "success",
            "provider": "huggingface",
            "model_used": model_name,
            "prompt_used": image_prompt
        }

    # 2. Secondary: Pollinations FLUX
    if generate_with_pollinations_flux(image_prompt, output_path):
        elapsed = time.perf_counter() - start_time
        print(f"[Image Gen] ✅ Generated via Pollinations FLUX in {elapsed:.2f}s", flush=True)
        return output_path, {
            "elapsed_sec": round(elapsed, 2),
            "style": style_preset,
            "status": "success (failover)",
            "provider": "pollinations",
            "model_used": "pollinations-flux",
            "prompt_used": image_prompt
        }

    # 3. Final Fallback: Local Canvas
    print("[Image Gen] 3️⃣ Remote engines unavailable. Rendering local placeholder...", flush=True)
    create_fallback_image(output_path, analogy_text)
    elapsed = time.perf_counter() - start_time
    return output_path, {
        "elapsed_sec": round(elapsed, 2),
        "style": style_preset,
        "status": "local_fallback",
        "provider": "local",
        "model_used": "pillow_placeholder",
        "prompt_used": image_prompt
    }