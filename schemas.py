# schemas.py
from enum import Enum
from typing import Optional, Dict
from pydantic import BaseModel, Field


class PersonaEnum(str, Enum):
    EXECUTIVE = "Executive / CTO"
    RESEARCHER = "Researcher / Engineer"
    EDUCATOR = "Educator / Student"


class StylePresetEnum(str, Enum):
    LINE_ART = "Line Art Doodle"
    WHITEBOARD = "Whiteboard Sketch"
    BLUEPRINT = "Technical Blueprint"


class SynthesisRequest(BaseModel):
    source_url: str = Field(
        ...,
        description="Direct PDF URL, arXiv URL, or arXiv ID (e.g. '1706.03762')",
        examples=["https://arxiv.org/abs/1706.03762"]
    )
    persona: PersonaEnum = Field(
        default=PersonaEnum.EXECUTIVE,
        description="Target persona controlling tone and visual selection"
    )
    style_preset: StylePresetEnum = Field(
        default=StylePresetEnum.LINE_ART,
        description="Visual style when generative FLUX is triggered"
    )
    model: str = Field(
        default="groq/llama-3.3-70b-versatile",
        description="LiteLLM model string identifier"
    )
    compression_ratio: float = Field(
        default=0.30,
        ge=0.10,
        le=0.60,
        description="LexRank text extraction ratio"
    )


class TelemetryMetrics(BaseModel):
    total_sec: float
    docling_parse_sec: float
    lexrank_compress_sec: float
    litellm_synth_sec: float
    visual_asset_sec: float
    raw_word_count: int
    compressed_word_count: int
    total_tokens: int


class SynthesisResponse(BaseModel):
    job_id: str
    status: str
    detected_title: str
    persona: str
    summary_markdown: str
    analogy_or_mechanism: str
    is_extracted_figure: bool
    visual_source_label: str
    telemetry: TelemetryMetrics
    artifacts: Dict[str, str] = Field(
        description="Relative endpoint paths to download generated artifacts"
    )