# core/compressor.py
import re
import time
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

def strip_references_and_appendix(raw_markdown: str) -> str:
    """Discards References, Bibliography, and Appendix sections to avoid scoring citation noise."""
    pattern = r"\n#{1,3}\s*(References|Bibliography|Works Cited|Appendix)"
    parts = re.split(pattern, raw_markdown, maxsplit=1, flags=re.IGNORECASE)
    return parts[0]

def compress_context_lexrank(raw_text: str, ratio: float = 0.28) -> tuple[str, float]:
    """Phase 1.2: Strips references and performs graph-based centrality sentence filtering."""
    start_time = time.perf_counter()
    
    # 1. Strip bibliography/references
    cleaned_text = strip_references_and_appendix(raw_text)
    
    # 2. Tokenize and rank sentences
    parser = PlaintextParser.from_string(cleaned_text, Tokenizer("english"))
    sentences = parser.document.sentences
    target_count = max(5, int(len(sentences) * ratio))
    
    summarizer = LexRankSummarizer()
    selected_sentences = summarizer(parser.document, target_count)
    
    compressed_text = " ".join([str(s) for s in selected_sentences])
    elapsed = time.perf_counter() - start_time
        
    metrics = {
        "original_words": len(raw_text.split()),
        "compressed_words": len(compressed_text.split()),
        "elapsed_sec": round(elapsed, 2)
    }
    return compressed_text, metrics