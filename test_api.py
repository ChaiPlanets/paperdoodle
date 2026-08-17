# test_api.py
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

# Change to your public ngrok URL when testing over the internet
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Fetch API credentials from local environment
LLM_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

HEADERS = {
    "Content-Type": "application/json",
    "X-LLM-Key": LLM_KEY or "",
    "X-HF-Token": HF_TOKEN or "",
}

TEST_PAYLOAD = {
    "source_url": "https://arxiv.org/pdf/2608.13345",  # Attention Is All You Need
    "persona": "Educator / Student",
    "style_preset": "Whiteboard Sketch",
    "model": "groq/llama-3.3-70b-versatile",
    "compression_ratio": 0.30
}


def test_health():
    print("\n[1/3] Testing /health endpoint...")
    try:
        res = requests.get(f"{BASE_URL}/health", timeout=10)
        res.raise_for_status()
        print(f" Health check passed: {res.json()}")
    except Exception as err:
        print(f" Health check failed: {err}")
        print("  Make sure the FastAPI server is running with: uvicorn api:app --reload --port 8000")
        sys.exit(1)


def test_synthesize():
    print(f"\n[2/3] Testing /v1/synthesize with URL: {TEST_PAYLOAD['source_url']}...")
    print(f"      Persona: {TEST_PAYLOAD['persona']} | Model: {TEST_PAYLOAD['model']}")
    
    try:
        res = requests.post(
            f"{BASE_URL}/v1/synthesize",
            headers=HEADERS,
            json=TEST_PAYLOAD,
            timeout=180
        )
        
        if res.status_code != 200:
            print(f" Synthesis failed with code {res.status_code}: {res.text}")
            sys.exit(1)
            
        data = res.json()
        print(f" Synthesis completed successfully!")
        print(f"   - Job ID: {data.get('job_id')}")
        print(f"   - Title: {data.get('detected_title')}")
        print(f"   - Total Latency: {data.get('telemetry', {}).get('total_sec')}s")
        print(f"   - Figure Source: {data.get('visual_source_label')}")
        print(f"   - Artifacts: {data.get('artifacts')}")
        return data
    except Exception as err:
        print(f" Error connecting to synthesis endpoint: {err}")
        sys.exit(1)


def test_artifacts(job_id: str, artifacts: dict):
    print(f"\n[3/3] Testing /v1/artifacts retrieval for Job ID: {job_id}...")
    download_dir = "test_downloads"
    os.makedirs(download_dir, exist_ok=True)

    for artifact_type, endpoint_path in artifacts.items():
        url = f"{BASE_URL}{endpoint_path}"
        try:
            res = requests.get(url, timeout=30)
            res.raise_for_status()
            
            ext_map = {"markdown": "md", "pdf": "pdf", "pptx": "pptx", "image": "png"}
            ext = ext_map.get(artifact_type, "bin")
            save_path = os.path.join(download_dir, f"{job_id}_{artifact_type}.{ext}")
            
            with open(save_path, "wb") as f:
                f.write(res.content)
                
            file_size_kb = len(res.content) / 1024
            print(f"   Downloaded {artifact_type.upper()} ({file_size_kb:.1f} KB) -> {save_path}")
        except Exception as err:
            print(f"   Failed downloading artifact '{artifact_type}': {err}")


if __name__ == "__main__":
    print(f"--- Starting PaperDoodle API Verification on {BASE_URL} ---")
    test_health()
    synthesis_result = test_synthesize()
    test_artifacts(
        job_id=synthesis_result["job_id"],
        artifacts=synthesis_result["artifacts"]
    )
    print("\n--- All tests completed successfully! ---")