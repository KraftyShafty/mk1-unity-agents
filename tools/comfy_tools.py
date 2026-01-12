"""
ComfyUI Integration Tools
=========================
Queue → Wait → Download pipeline with provenance tracking.
"""

import requests
import time
import json
import hashlib
import yaml
from crewai.tools import tool
from pathlib import Path
from datetime import datetime

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / "project_config.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

REPO_ROOT = Path(__file__).parent.parent.resolve()
COMFY_URL = CONFIG['comfyui']['base_url']
TIMEOUT_SEC = CONFIG['comfyui']['timeout_sec']
POLL_INTERVAL = CONFIG['comfyui']['poll_interval_sec']

ASSET_INDEX = REPO_ROOT / CONFIG['artifacts']['asset_index']
RAW_ASSETS = REPO_ROOT / CONFIG['assets']['raw']


def _record_provenance(prompt_id: str, workflow_hash: str, overrides: dict, output_files: list):
    """Append asset provenance to the index ledger."""
    ASSET_INDEX.parent.mkdir(parents=True, exist_ok=True)
    
    record = {
        "prompt_id": prompt_id,
        "workflow_hash": workflow_hash,
        "overrides": overrides,
        "output_files": output_files,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(ASSET_INDEX, 'a') as f:
        f.write(json.dumps(record) + "\n")


@tool("ComfyUIQueue")
def comfy_queue(workflow_path: str, overrides: dict = None) -> str:
    """
    Queue a ComfyUI workflow for execution.
    
    Args:
        workflow_path: Relative path to workflow JSON (e.g., 'workflows/sprite_gen.json')
        overrides: Dict of node_id -> {input_name: value} to override
    
    Returns:
        Prompt ID for tracking, or error message.
    """
    overrides = overrides or {}
    
    workflow_file = REPO_ROOT / workflow_path
    if not workflow_file.exists():
        return f"ERROR: Workflow not found: {workflow_path}"
    
    try:
        workflow = json.loads(workflow_file.read_text())
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid workflow JSON: {e}"
    
    # Calculate workflow hash for provenance
    workflow_hash = hashlib.sha256(workflow_file.read_bytes()).hexdigest()[:12]
    
    # Apply overrides
    for node_id, params in overrides.items():
        if node_id in workflow:
            workflow[node_id].setdefault('inputs', {}).update(params)
    
    # Queue the prompt
    try:
        resp = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}, timeout=10)
        resp.raise_for_status()
        prompt_id = resp.json().get('prompt_id')
        
        if not prompt_id:
            return f"ERROR: No prompt_id returned. Response: {resp.text[:500]}"
        
        return f"QUEUED: prompt_id={prompt_id}, workflow_hash={workflow_hash}"
        
    except requests.exceptions.ConnectionError:
        return f"ERROR: Cannot connect to ComfyUI at {COMFY_URL}"
    except Exception as e:
        return f"ERROR: {e}"


@tool("ComfyUIWait")
def comfy_wait(prompt_id: str, timeout_sec: int = None) -> str:
    """
    Wait for a ComfyUI job to complete.
    
    Args:
        prompt_id: The prompt ID from ComfyUIQueue
        timeout_sec: Max seconds to wait (default: from config)
    
    Returns:
        DONE/TIMEOUT status with output info.
    """
    timeout_sec = timeout_sec or TIMEOUT_SEC
    start = time.time()
    
    while time.time() - start < timeout_sec:
        try:
            resp = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=5)
            history = resp.json()
            
            if prompt_id in history:
                outputs = history[prompt_id].get('outputs', {})
                if outputs:
                    # Count output images
                    image_count = sum(
                        len(node_data.get('images', []))
                        for node_data in outputs.values()
                    )
                    return f"DONE: prompt_id={prompt_id}, outputs={image_count} images"
            
            time.sleep(POLL_INTERVAL)
            
        except Exception as e:
            return f"ERROR: Polling failed: {e}"
    
    return f"TIMEOUT: Job {prompt_id} not complete after {timeout_sec}s"


@tool("ComfyUIDownload")
def comfy_download(prompt_id: str, output_subdir: str = None) -> str:
    """
    Download completed outputs from ComfyUI.
    
    Args:
        prompt_id: The prompt ID from ComfyUIQueue
        output_subdir: Subdirectory under assets/raw/ (default: prompt_id)
    
    Returns:
        List of downloaded file paths or error.
    """
    output_subdir = output_subdir or prompt_id
    output_dir = RAW_ASSETS / output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        resp = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=5)
        history = resp.json()
        
        if prompt_id not in history:
            return f"ERROR: No history found for {prompt_id}"
        
        outputs = history[prompt_id].get('outputs', {})
        downloaded = []
        
        for node_id, node_data in outputs.items():
            for img in node_data.get('images', []):
                filename = img['filename']
                subfolder = img.get('subfolder', '')
                
                # Download image
                view_url = f"{COMFY_URL}/view?filename={filename}"
                if subfolder:
                    view_url += f"&subfolder={subfolder}"
                
                img_resp = requests.get(view_url, timeout=30)
                if img_resp.status_code == 200:
                    save_path = output_dir / filename
                    save_path.write_bytes(img_resp.content)
                    downloaded.append(str(save_path.relative_to(REPO_ROOT)))
        
        if downloaded:
            # Record provenance
            _record_provenance(prompt_id, "unknown", {}, downloaded)
            return f"DOWNLOADED: {len(downloaded)} files to {output_dir.relative_to(REPO_ROOT)}\n" + "\n".join(downloaded)
        else:
            return f"ERROR: No images found in outputs for {prompt_id}"
            
    except Exception as e:
        return f"ERROR: Download failed: {e}"


@tool("ComfyUIStatus")
def comfy_status() -> str:
    """
    Check ComfyUI server status.
    
    Returns:
        Server status info or error.
    """
    try:
        resp = requests.get(f"{COMFY_URL}/system_stats", timeout=5)
        stats = resp.json()
        
        return (
            f"ComfyUI Status: ONLINE\n"
            f"URL: {COMFY_URL}\n"
            f"Stats: {json.dumps(stats, indent=2)[:500]}"
        )
    except requests.exceptions.ConnectionError:
        return f"ERROR: Cannot connect to ComfyUI at {COMFY_URL}"
    except Exception as e:
        return f"ERROR: {e}"


if __name__ == "__main__":
    print("=== ComfyUI Tools Self-Test ===")
    print(comfy_status())
