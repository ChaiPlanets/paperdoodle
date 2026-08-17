# api.py
import os
import re
import uuid
import time
import shutil
import asyncio
import tempfile
from typing import Optional

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    UploadFile,
    File,
    Form,
    Request,
    status
)
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from schemas import (
    SynthesisRequest,
    SynthesisResponse,
    TelemetryMetrics,
    PersonaEnum,
    StylePresetEnum
)
from core.fetcher import download_pdf_from_url
from core.parser import extract_pdf_content
from core.compressor import compress_context_lexrank
from core.synthesizer import generate_executive_summary
from core.image_generator import generate_sketch_diagram_hf
from core.postprocessor import assemble_final_markdown
from core.pdf_compiler import compile_markdown_to_pdf
from core.ppt_compiler import create_deck

app = FastAPI(
    title="PaperDoodle API",
    version="2.0.0",
    description="Universal Multimodal Document Intelligence & Research Synthesis API"
)

# Enable CORS for frontend and external client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_OUTPUT_DIR = "output"
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)


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


def run_pipeline_sync(
    job_id: str,
    job_dir: str,
    pdf_path: str,
    source_name: str,
    persona: str,
    style_preset: str,
    model: str,
    compression_ratio: float,
    llm_key: str,
    hf_token: Optional[str]
) -> SynthesisResponse:
    """Executes the complete PaperDoodle workflow synchronously inside a thread."""
    start_total = time.perf_counter()
    
    # 1. Parse Document & Extract Figures
    should_extract_figures = (persona == PersonaEnum.RESEARCHER.value)
    raw_md, extracted_figures, t_parse = extract_pdf_content(
        pdf_path=pdf_path,
        extract_figures=should_extract_figures
    )
    raw_word_count = len(raw_md.split())
    detected_title = extract_title_from_markdown(raw_md, source_name.title())

    # 2. Compress Context
    compressed_txt, comp_metrics = compress_context_lexrank(raw_md, ratio=compression_ratio)
    t_compress = comp_metrics.get("elapsed_sec", 0.0)
    comp_word_count = comp_metrics.get("compressed_words", len(compressed_txt.split()))

    # 3. Synthesize Summary & Analogy
    briefing_summary, analogy_text, synth_metrics = generate_executive_summary(
        context=compressed_txt,
        api_key=llm_key,
        model=model,
        persona=persona
    )
    t_synth = synth_metrics.get("elapsed_sec", 0.0)
    total_tokens = synth_metrics.get("total_tokens", 0)

    # 4. Visual Asset Routing
    img_output_path = os.path.join(job_dir, "visual.png")
    t_img = 0.0
    
    if should_extract_figures and extracted_figures:
        primary_fig = extracted_figures[0]
        shutil.copyfile(primary_fig, img_output_path)
        visual_label = f"Docling Extracted (Figure 1 of {len(extracted_figures)})"
        t_img = 0.01
        is_extracted = True
    else:
        chosen_style = "Technical Blueprint" if should_extract_figures else style_preset
        if not hf_token:
            raise RuntimeError("Hugging Face token is required for generative visual metaphors.")
        
        # Route the clean physical scene description to the doodle generator
        visual_prompt = synth_metrics.get("visual_prompt", analogy_text)


        print("\n" + "#" * 60)
        print(f"[DEBUG API] Sending to Image Generator:")
        print(f"Style: {chosen_style}")
        print(f"Visual Prompt: {visual_prompt}")
        print("#" * 60 + "\n")

        _, img_metrics = generate_sketch_diagram_hf(
            analogy_text=visual_prompt,
            hf_token=hf_token,
            output_path=img_output_path,
            style_preset=chosen_style
        )
        t_img = img_metrics.get("elapsed_sec", 0.0)
        visual_label = f"FLUX generated ({chosen_style})"
        if should_extract_figures:
            visual_label += " [Fallback]"
        is_extracted = False

    # 5. Multi-Artifact Compilation
    md_output_path = os.path.join(job_dir, "briefing.md")
    pdf_output_path = os.path.join(job_dir, "briefing.pdf")
    ppt_output_path = os.path.join(job_dir, "deck.pptx")

    raw_briefing = f"# {detected_title}\n\n{briefing_summary}"
    final_md_content = assemble_final_markdown(
        summary_text=raw_briefing,
        analogy_text=analogy_text,
        image_filename="visual.png",
        is_extracted_figure=is_extracted
    )
    
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(final_md_content)

    compile_markdown_to_pdf(final_md_content, pdf_output_path, base_asset_dir=job_dir)
    create_deck(detected_title, briefing_summary, analogy_text, img_output_path, ppt_output_path)

    total_sec = time.perf_counter() - start_total

    return SynthesisResponse(
        job_id=job_id,
        status="completed",
        detected_title=detected_title,
        persona=persona,
        summary_markdown=briefing_summary,
        analogy_or_mechanism=analogy_text,
        is_extracted_figure=is_extracted,
        visual_source_label=visual_label,
        telemetry=TelemetryMetrics(
            total_sec=round(total_sec, 2),
            docling_parse_sec=round(t_parse, 2),
            lexrank_compress_sec=round(t_compress, 2),
            litellm_synth_sec=round(t_synth, 2),
            visual_asset_sec=round(t_img, 2),
            raw_word_count=raw_word_count,
            compressed_word_count=comp_word_count,
            total_tokens=total_tokens
        ),
        artifacts={
            "markdown": f"/v1/artifacts/{job_id}/md",
            "pdf": f"/v1/artifacts/{job_id}/pdf",
            "pptx": f"/v1/artifacts/{job_id}/pptx",
            "image": f"/v1/artifacts/{job_id}/image"
        }
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "PaperDoodle API"}


@app.post("/v1/synthesize", response_model=SynthesisResponse, status_code=status.HTTP_200_OK)
async def synthesize_url(
    payload: SynthesisRequest,
    x_llm_key: Optional[str] = Header(None, alias="X-LLM-Key"),
    x_hf_token: Optional[str] = Header(None, alias="X-HF-Token")
):
    """Synthesize a paper from an arXiv ID, arXiv URL, or direct PDF link."""
    active_llm_key = x_llm_key or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    active_hf_token = x_hf_token or os.getenv("HF_TOKEN")

    if not active_llm_key:
        raise HTTPException(
            status_code=400,
            detail="Missing LLM API Key. Provide via 'X-LLM-Key' header or server .env."
        )

    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(BASE_OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        downloaded_path = await asyncio.to_thread(download_pdf_from_url, payload.source_url)
        pdf_path = os.path.join(job_dir, "input.pdf")
        if downloaded_path != pdf_path:
            shutil.copyfile(downloaded_path, pdf_path)
            
        source_name = payload.source_url.rstrip("/").split("/")[-1]

        result = await asyncio.to_thread(
            run_pipeline_sync,
            job_id=job_id,
            job_dir=job_dir,
            pdf_path=pdf_path,
            source_name=source_name,
            persona=payload.persona.value,
            style_preset=payload.style_preset.value,
            model=payload.model,
            compression_ratio=payload.compression_ratio,
            llm_key=active_llm_key,
            hf_token=active_hf_token
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(exc)}")


@app.post("/v1/synthesize/file", response_model=SynthesisResponse, status_code=status.HTTP_200_OK)
async def synthesize_uploaded_file(
    file: UploadFile = File(...),
    persona: PersonaEnum = Form(PersonaEnum.EXECUTIVE),
    style_preset: StylePresetEnum = Form(StylePresetEnum.LINE_ART),
    model: str = Form("groq/llama-3.3-70b-versatile"),
    compression_ratio: float = Form(0.30),
    x_llm_key: Optional[str] = Header(None, alias="X-LLM-Key"),
    x_hf_token: Optional[str] = Header(None, alias="X-HF-Token")
):
    """Synthesize a paper by directly uploading a PDF file."""
    active_llm_key = x_llm_key or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    active_hf_token = x_hf_token or os.getenv("HF_TOKEN")

    if not active_llm_key:
        raise HTTPException(
            status_code=400,
            detail="Missing LLM API Key. Provide via 'X-LLM-Key' header or server .env."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(BASE_OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        pdf_path = os.path.join(job_dir, "input.pdf")
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        source_name = os.path.splitext(file.filename)[0]

        result = await asyncio.to_thread(
            run_pipeline_sync,
            job_id=job_id,
            job_dir=job_dir,
            pdf_path=pdf_path,
            source_name=source_name,
            persona=persona.value,
            style_preset=style_preset.value,
            model=model,
            compression_ratio=compression_ratio,
            llm_key=active_llm_key,
            hf_token=active_hf_token
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(exc)}")


@app.get("/v1/artifacts/{job_id}/{artifact_type}")
async def download_artifact(job_id: str, artifact_type: str):
    """Stream generated artifacts: 'pdf', 'pptx', 'md', or 'image'."""
    job_dir = os.path.join(BASE_OUTPUT_DIR, job_id)
    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Job ID not found.")

    artifact_map = {
        "pdf": ("briefing.pdf", "application/pdf"),
        "pptx": ("deck.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        "md": ("briefing.md", "text/markdown"),
        "image": ("visual.png", "image/png")
    }

    if artifact_type not in artifact_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid artifact type. Allowed: {list(artifact_map.keys())}"
        )

    file_name, media_type = artifact_map[artifact_type]
    file_path = os.path.join(job_dir, file_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_type}' was not found for job {job_id}.")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=f"{job_id}_{file_name}"
    )