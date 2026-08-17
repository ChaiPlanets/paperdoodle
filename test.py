# test.py
import os
import time
import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# Imports from core
from core.fetcher import download_pdf_from_url, resolve_arxiv_url
from core.prompt_loader import load_prompt_template, PERSONA_FOLDER_MAP
from core.synthesizer import generate_executive_summary
from core.image_generator import generate_sketch_diagram_hf, is_image_black
from core.config import DEFAULT_GROQ_MODEL, STYLE_PROMPTS

# Pre-flight attempt for optional hf_transfer installation
try: install_hf_transfer() 
except: pass

load_dotenv()


def run_preflight_diagnostics():
    print("="*60)
    print("🎨 PaperDoodle Day 1: Final Pre-Flight Diagnostics")
    print("="*60)
    
    overall_status = True

    # --- 1. Test Key Configurations ---
    print("\n[1/5] Checking API Keys...")
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    hf_token = os.getenv("HF_TOKEN", "").strip()
    
    if not groq_key:
        print("❌ CRITICAL: GROQ_API_KEY missing from .env.")
        overall_status = False
    else:
        print(f"✅ GROQ_API_KEY found (Starts with: {groq_key[:6]}...)")
        
    if not hf_token:
        print("⚠️ WARNING: HF_TOKEN missing from .env. Doodle generation will fail.")
    else:
        print(f"✅ HF_TOKEN found (Starts with: {hf_token[:6]}...)")

    # --- 2. Test Prompt Template Loading ---
    print("\n[2/5] Checking External Prompt Templates...")
    required_prompt_types = ["summary", "analogy"]
    
    prompts_found = 0
    for persona in PERSONA_FOLDER_MAP.keys():
        try:
            for p_type in required_prompt_types:
                template = load_prompt_template(persona, p_type)
                prompts_found += 1
            print(f"✅ Loaded templates for: {persona} (Length check: Passed)")
        except FileNotFoundError as e:
            print(f"❌ Error loading prompts for {persona}: {e}")
            overall_status = False
        except Exception as e:
            print(f"❌ Unexpected error loading prompts: {e}")
            overall_status = False
            
    if prompts_found == len(PERSONA_FOLDER_MAP) * len(required_prompt_types):
        print(f"✅ All {prompts_found} Markdown prompt templates verified.")

    # --- 3. Test arXiv Ingestion (Networking) ---
    print("\n[3/5] Testing arXiv Resolver & PDF Download...")
    sample_arxiv_id = "1706.03762" # Attention is All You Need
    
    try:
        resolved_url = resolve_arxiv_url(sample_arxiv_id)
        if "arxiv.org/pdf/1706.03762.pdf" in resolved_url:
            print(f"✅ arXiv ID '{sample_arxiv_id}' resolved correctly to direct PDF.")
            
        print("...attempting sample PDF download (timeout 15s)...")
        # Download, get path, immediately delete to keep things clean
        tmp_pdf_path = download_pdf_from_url(sample_arxiv_id)
        
        if os.path.exists(tmp_pdf_path) and os.path.getsize(tmp_pdf_path) > 10000:
            print(f"✅ Download successful! Size: {os.path.getsize(tmp_pdf_path)} bytes.")
            os.remove(tmp_pdf_path) # Clean up
        else:
            print(f"❌ Downloaded file appears invalid or missing.")
            overall_status = False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Networking error resolving/downloading arXiv (DNS issue?): {e}")
        overall_status = False
    except Exception as e:
        print(f"❌ Ingestion pipeline failure: {e}")
        overall_status = False

    # --- 4. Test LiteLLM Synthesis & BYOK Routing ---
    if groq_key:
        print("\n[4/5] Testing LiteLLM routing via Groq (BYOK)...")
        sample_context = (
            "The Transformer model relies entirely on self-attention mechanisms, "
            "allowing for parallelization across sequence dimensions, enabling "
            "significant throughput gains over traditional RNN architectures."
        )
        try:
            start_synth = time.perf_counter()
            summary, analogy, metrics = generate_executive_summary(
                context=sample_context,
                api_key=groq_key,
                model=DEFAULT_GROQ_MODEL, # Uses groq/ prefix via LiteLLM
                persona="Executive / CTO"
            )
            elapsed = time.perf_counter() - start_synth
            
            print(f"✅ LiteLLM Execution successful via {metrics['model']}.")
            print(f"Latency: {elapsed:.2f}s | Tokens used: {metrics['total_tokens']}")
            print(f"Sample Metaphor generated: \"{analogy[:100]}...\"")
            
        except Exception as e:
            print(f"❌ LiteLLM execution failed: {e}")
            overall_status = False
    else:
        print("\n[4/5] Skipped LiteLLM test (No Key).")

    # --- 5. Test Hugging Face InferenceClient (Image Gen) ---
    if hf_token:
        print("\n[5/5] Testing HF InferenceClient for visual generation...")
        test_analogy = "A high-performance clutch engaging a dual-gear transmission smoothly."
        test_output_img = "output/diagnostic_test_image.png"
        
        try:
            # Ensure output directory exists
            os.makedirs("output", exist_ok=True)
            if os.path.exists(test_output_img): os.remove(test_output_img)
            
            # Using the modernized InferenceClient approach from core
            start_img = time.perf_counter()
            out_path, img_metrics = generate_sketch_diagram_hf(
                analogy_text=test_analogy,
                hf_token=hf_token,
                output_path=test_output_img,
                style_preset="Line Art Doodle"
            )
            elapsed = time.perf_counter() - start_img
            
            # Diagnostic verification of output file
            if os.path.exists(test_output_img) and os.path.getsize(test_output_img) > 20000:
                print(f"✅ Image file successfully generated via FLUX.1 SDK.")
                
                # Check for blank/black tensors (false positives)
                with open(test_output_img, "rb") as f:
                    if is_image_black(f.read()):
                        print(f"❌ Image generated but is completely black (safety filter blank).")
                        overall_status = False
                    else:
                        try:
                            pil_img = Image.open(test_output_img)
                            print(f"✅ Image validated. Latency: {elapsed:.1f}s | Size: {pil_img.size}")
                        except Exception:
                            print(f"❌ Image file is corrupt.")
                            overall_status = False
            else:
                print(f"❌ Image generation failed (status reported as success but file missing or tiny).")
                print(f"Metrics: {img_metrics}")
                overall_status = False
                
        except Exception as e:
            print(f"❌ Visual generation pipeline failure: {e}")
            overall_status = False
    else:
        print("\n[5/5] Skipped Visual generation test (No Token).")

    # --- Final Conclusion ---
    print("\n"+"="*60)
    if overall_status:
        print("🎉 Result: All core pipelines passed! You are ready for app.py testing.")
    else:
        print("⚠️ Result: Some checks failed. Review the errors (❌) above before launching app.py.")
    print("="*60)

if __name__ == "__main__":
    run_preflight_diagnostics()