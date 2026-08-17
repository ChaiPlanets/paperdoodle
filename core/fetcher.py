# core/fetcher.py
import re
import requests
import tempfile

def resolve_arxiv_url(url_or_id: str) -> str:
    """Normalizes arXiv IDs or abstract URLs to direct PDF download links."""
    clean_input = url_or_id.strip()
    
    # Check if raw arXiv ID (e.g. 2401.12345 or 2401.12345v1)
    if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", clean_input):
        return f"https://arxiv.org/pdf/{clean_input}.pdf"
    
    # Check if arXiv abstract page URL
    abs_match = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5}(v\d+)?)", clean_input)
    if abs_match:
        arxiv_id = abs_match.group(1)
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
    return clean_input

def download_pdf_from_url(url: str) -> str:
    """Downloads a PDF from a URL/arXiv into a temporary file and returns local path."""
    target_url = resolve_arxiv_url(url)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(target_url, headers=headers, stream=True, timeout=30)
    response.raise_for_status()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                tmp.write(chunk)
        return tmp.name