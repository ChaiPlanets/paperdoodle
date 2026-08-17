# app.py
import os
import re
import time
import shutil
import tempfile
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

from core.fetcher import download_pdf_from_url
from core.parser import extract_pdf_content
from core.compressor import compress_context_lexrank
from core.synthesizer import generate_executive_summary
from core.image_generator import generate_sketch_diagram_hf
from core.postprocessor import assemble_final_markdown
from core.pdf_compiler import compile_markdown_to_pdf
from core.ppt_compiler import create_deck
from core.config import DEFAULT_EXTRACTION_RATIO, DEFAULT_GROQ_MODEL

st.set_page_config(
    page_title="PaperDoodle | Research to Executive Briefings",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

def extract_title_from_markdown(raw_markdown: str, fallback_title: str) -> str:
    lines = [line.strip() for line in raw_markdown.splitlines() if line.strip()]
    if not lines:
        return fallback_title
    for line in lines[:8]:
        if line.startswith("#"):
            cleaned = re.sub(r"^#+\s*", "", line).strip()
            if len(cleaned) > 5:
                return cleaned
    candidate = lines[0]
    if len(lines) > 1 and len(candidate) < 60 and not lines[1].lower().startswith(("abstract", "author", "by ")):
        candidate = f"{candidate}: {lines[1]}"
    return candidate.replace("\n", " ").strip() if candidate else fallback_title

# --- Sidebar: Configuration & Pre-Flight ---
with st.sidebar:
    st.title("⚙️ Engine Configuration")
    
    llm_provider = st.selectbox(
        "LLM Provider (BYOK)",
        options=["Groq", "OpenAI", "Google Gemini", "Anthropic"],
        index=0
    )
    
    model_defaults = {
        "Groq": DEFAULT_GROQ_MODEL,
        "OpenAI": "gpt-4o-mini",
        "Google Gemini": "gemini/gemini-1.5-flash",
        "Anthropic": "claude-3-5-haiku-20241022"
    }
    
    model_string = st.text_input("LiteLLM Model ID", value=model_defaults[llm_provider])
    
    env_keys = {
        "Groq": os.getenv("GROQ_API_KEY", "").strip(),
        "OpenAI": os.getenv("OPENAI_API_KEY", "").strip(),
        "Google Gemini": os.getenv("GEMINI_API_KEY", "").strip(),
        "Anthropic": os.getenv("ANTHROPIC_API_KEY", "").strip()
    }
    
    default_key = env_keys.get(llm_provider, "")
    if default_key:
        st.text_input(f"{llm_provider} Key", value="•••••••• [From .env]", disabled=True)
        active_llm_key = default_key
    else:
        active_llm_key = st.text_input(f"{llm_provider} API Key", type="password", placeholder="Enter key")

    env_hf = os.getenv("HF_TOKEN", "").strip()
    if env_hf:
        st.text_input("Hugging Face Token", value="•••••••• [From .env]", disabled=True)
        active_hf_token = env_hf
    else:
        active_hf_token = st.text_input("Hugging Face Token", type="password", placeholder="Enter HF token")
    
    st.divider()
    
    st.subheader("Synthesis Presets")
    selected_persona = st.selectbox(
        "Target Persona",
        options=["Executive / CTO", "Researcher / Engineer", "Educator / Student"],
        index=0
    )
    
    if selected_persona != "Researcher / Engineer":
        selected_style = st.selectbox(
            "Visual Metaphor Style",
            options=["Line Art Doodle", "Whiteboard Sketch"],
            index=0
        )
    else:
        selected_style = "Technical Blueprint"
        st.caption("Default: Extracts paper figures. Falls back to Technical Blueprint if no figures found.")
    
    compression_ratio = st.slider("Context Compression Ratio", 0.15, 0.45, DEFAULT_EXTRACTION_RATIO, 0.01)

# --- Main Interface ---
st.title("🎨 PaperDoodle")
st.caption("Universal multimodal document intelligence pipeline.")

tab_upload, tab_url = st.tabs(["📁 Upload PDF", "🔗 arXiv / Web URL"])

input_pdf_path = None
paper_source_name = "document"

with tab_upload:
    uploaded_file = st.file_uploader("Upload an Academic Research PDF", type=["pdf"])
    if uploaded_file:
        paper_source_name = os.path.splitext(uploaded_file.name)[0]

with tab_url:
    url_input = st.text_input("Enter arXiv ID, arXiv URL, or Direct PDF Link", placeholder="e.g. 1706.03762 or https://arxiv.org/abs/1706.03762")

col_btn, _ = st.columns([1, 4])
with col_btn:
    start_processing = st.button("🚀 Synthesize Research", type="primary", use_container_width=True)

# Define Output Paths
os.makedirs("output", exist_ok=True)
output_img_path = os.path.join("output", "5_final_visual.png")
output_md_path = os.path.join("output", "4_executive_briefing.md")
output_pdf_path = os.path.join("output", "final_briefing.pdf")
output_ppt_path = os.path.join("output", "executive_deck.pptx")

if start_processing:
    if not active_llm_key:
        st.error(f"Please configure your {llm_provider} Key in the sidebar.")
        st.stop()
        
    if selected_persona != "Researcher / Engineer" and not active_hf_token:
        st.error("Doodle generation requires a Hugging Face Token. Please provide one in the sidebar or switch to Researcher persona.")
        st.stop()
        
    status_box = st.status("Initializing PaperDoodle pipeline...", expanded=True)
    total_start = time.perf_counter()
    
    try:
        # Step 1: Ingestion
        status_box.update(label="[1/6] Ingesting document source...")
        if uploaded_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                input_pdf_path = tmp_file.name
        elif url_input.strip():
            input_pdf_path = download_pdf_from_url(url_input.strip())
            paper_source_name = url_input.strip().split("/")[-1]
        else:
            status_box.update(label="❌ No input provided", state="error")
            st.warning("Please upload a file or enter an arXiv/PDF URL.")
            st.stop()

        # Step 2: Parse & Extract Figures
        should_extract_figures = (selected_persona == "Researcher / Engineer")
        status_box.update(label=f"[2/6] Parsing document (Extract Figures: {should_extract_figures})...")
        
        raw_md, extracted_figures, t_parse = extract_pdf_content(
            pdf_path=input_pdf_path,
            extract_figures=should_extract_figures
        )
        raw_word_count = len(raw_md.split())
        detected_paper_title = extract_title_from_markdown(raw_md, paper_source_name.title())

        # Step 3: Compress
        status_box.update(label="[3/6] Compressing context with LexRank...")
        compressed_txt, comp_metrics = compress_context_lexrank(raw_md, ratio=compression_ratio)
        t_compress = comp_metrics.get("elapsed_sec", 0.0)

        # Step 4: Synthesize (LiteLLM)
        status_box.update(label=f"[4/6] Synthesizing briefing via {model_string}...")
        briefing_summary, analogy_metaphor, synth_metrics = generate_executive_summary(
            context=compressed_txt,
            api_key=active_llm_key,
            model=model_string,
            persona=selected_persona
        )
        t_synth = synth_metrics.get("elapsed_sec", 0.0)

        # Step 5: Adaptive Visual Routing
        status_box.update(label="[5/6] Finalizing visual asset...")
        visual_mode_label = ""
        t_img = 0.0
        
        if should_extract_figures and extracted_figures:
            primary_fig_path = extracted_figures[0]
            shutil.copyfile(primary_fig_path, output_img_path)
            visual_mode_label = f"Docling Extracted (Figure 1 of {len(extracted_figures)})"
            t_img = 0.01
            is_extracted = True
        else:
            final_style = "Technical Blueprint" if should_extract_figures else selected_style
            if not active_hf_token:
                raise RuntimeError("Hugging Face token required for doodle generation fallback.")
                
            status_box.update(label=f"[5/6] Generating {final_style} doodle with FLUX...")
            _, img_metrics = generate_sketch_diagram_hf(
                analogy_text=analogy_metaphor,
                hf_token=active_hf_token,
                output_path=output_img_path,
                style_preset=final_style
            )
            t_img = img_metrics.get("elapsed_sec", 0.0)
            visual_mode_label = f"FLUX generated ({final_style})"
            if should_extract_figures:
                visual_mode_label += " [Fallback]"
            is_extracted = False

        # Step 6: Multi-Artifact Compilation
        status_box.update(label="[6/6] Compiling Markdown, PDF, and PowerPoint...")
        
        raw_briefing = f"# {detected_paper_title}\n\n{briefing_summary}"
        final_md_content = assemble_final_markdown(
            summary_text=raw_briefing, 
            analogy_text=analogy_metaphor, 
            image_filename=os.path.basename(output_img_path),
            is_extracted_figure=is_extracted
        )
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(final_md_content)
            
        compile_markdown_to_pdf(final_md_content, output_pdf_path, base_asset_dir="output")
        create_deck(detected_paper_title, briefing_summary, analogy_metaphor, output_img_path, output_ppt_path)
        
        total_elapsed = time.perf_counter() - total_start
        status_box.update(label=f"🎉 Processed in {total_elapsed:.1f}s!", state="complete", expanded=False)
        
        if input_pdf_path and os.path.exists(input_pdf_path) and "tmp" in input_pdf_path:
            os.remove(input_pdf_path)

        # Persist session state
        st.session_state["pipeline_finalized"] = True
        st.session_state["p_title"] = detected_paper_title
        st.session_state["p_summary"] = briefing_summary
        st.session_state["p_analogy"] = analogy_metaphor
        st.session_state["is_extracted_figure"] = is_extracted
        st.session_state["visual_mode_label"] = visual_mode_label
        
        st.session_state["perf_telemetry"] = {
            "Total": f"{total_elapsed:.1f}s",
            "Docling (Parse/Fig)": f"{t_parse:.1f}s | {raw_word_count} raw words | Figs: {len(extracted_figures)}",
            "LexRank (Compress)": f"{t_compress:.2f}s | {comp_metrics.get('compressed_words', 0)} words",
            "LiteLLM (Synth)": f"{t_synth:.1f}s | {synth_metrics.get('total_tokens', 0)} tokens",
            "Visual Asset": f"{t_img:.1f}s | Source: {visual_mode_label}"
        }

    except Exception as e:
        status_box.update(label="❌ Pipeline failed!", state="error")
        st.error(f"Error during processing: {str(e)}")
        if input_pdf_path and os.path.exists(input_pdf_path) and "tmp" in input_pdf_path:
            os.remove(input_pdf_path)

# --- Results Presentation ---
if st.session_state.get("pipeline_finalized", False):
    st.divider()
    
    st.subheader("⚡ Performance Telemetry")
    t = st.session_state["perf_telemetry"]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Latency", t["Total"])
    m2.metric("LLM Latency", t["LiteLLM (Synth)"].split('|')[0].strip())
    m3.metric("Parsing Latency", t["Docling (Parse/Fig)"].split('|')[0].strip())
    m4.metric("Image Latency", t["Visual Asset"].split('|')[0].strip())
    
    with st.expander("View detailed token and word counts", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Parser:** {t['Docling (Parse/Fig)'].split('|', 1)[1].strip()}")
        c2.write(f"**Compression:** {t['LexRank (Compress)'].split('|', 1)[1].strip()}")
        c3.write(f"**LLM Tokens:** {t['LiteLLM (Synth)'].split('|', 1)[1].strip()}")
    
    st.divider()
    
    col_left, col_right = st.columns([3, 2], gap="large")
    
    with col_left:
        st.subheader("📄 Generated Research Briefing")
        st.markdown(f"### 📑 {st.session_state['p_title']}")
        st.markdown(st.session_state["p_summary"])
        
    with col_right:
        is_extracted = st.session_state.get("is_extracted_figure", False)
        active_label = st.session_state.get("visual_mode_label", "Generated Visual")

        if is_extracted:
            st.subheader("📐 Architecture & Extracted Figures")
        else:
            st.subheader("💡 Visual Metaphor & Intuition")

        if os.path.exists(output_img_path):
            try:
                verify_img = Image.open(output_img_path)
                st.image(
                    verify_img, 
                    caption=f"Visual Asset ({active_label})", 
                    use_container_width=True
                )
            except Exception as img_err:
                st.warning(f"Unable to display image preview: {img_err}")

        if is_extracted:
            st.success(f"**Technical Mechanism & Intuition:**\n\n{st.session_state.get('p_analogy', '')}")
        else:
            st.info(f"**Conceptual Metaphor:**\n\n{st.session_state.get('p_analogy', '')}")
        
        st.subheader("📥 Export Final Deliverables")
        safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', st.session_state.get('p_title', 'paper_briefing')[:30]).lower()
        
        if os.path.exists(output_md_path):
            with open(output_md_path, "r", encoding="utf-8") as f:
                st.download_button("📄 Download Markdown (.md)", f.read(), f"{safe_title}_briefing.md", "text/markdown", use_container_width=True)
                
        if os.path.exists(output_pdf_path):
            with open(output_pdf_path, "rb") as f:
                st.download_button("📕 Download PDF Briefing (.pdf)", f.read(), f"{safe_title}_briefing.pdf", "application/pdf", use_container_width=True)
                
        if os.path.exists(output_ppt_path):
            with open(output_ppt_path, "rb") as f:
                st.download_button("📊 Download Presentation (.pptx)", f.read(), f"{safe_title}_deck.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)