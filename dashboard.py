"""
MK1 System Dashboard
=====================
Real-time visual status of all system layers.
Run: python dashboard.py
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from pathlib import Path

# ANSI colors
class C:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def check_ollama():
    """Check Ollama LLM status."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        if r.ok:
            models = r.json().get("models", [])
            loaded = [m["name"] for m in models if m.get("size", 0) > 0]
            return {"status": "running", "models": len(models), "details": loaded[:3]}
    except:
        pass
    return {"status": "offline", "models": 0, "details": []}


def check_comfyui():
    """Check ComfyUI status."""
    try:
        r = requests.get("http://127.0.0.1:8000/system_stats", timeout=2)
        if r.ok:
            data = r.json()
            version = data.get("system", {}).get("comfyui_version", "?")
            gpu = data.get("devices", [{}])[0].get("name", "?")
            vram = data.get("devices", [{}])[0].get("vram_free", 0)
            return {"status": "running", "version": version, "gpu": gpu[:30], "vram_free_gb": round(vram / 1e9, 1)}
    except:
        pass
    return {"status": "offline", "version": "?", "gpu": "?", "vram_free_gb": 0}


def check_unity_project():
    """Check Unity project files."""
    proj_path = Path("C:/dev/Compare/MK1_Project")
    scripts_path = proj_path / "Assets/Scripts"
    
    if not proj_path.exists():
        return {"status": "missing", "scripts": 0, "recent": []}
    
    scripts = list(scripts_path.rglob("*.cs"))
    recent = sorted(scripts, key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    recent_names = [f.name for f in recent]
    
    return {"status": "exists", "scripts": len(scripts), "recent": recent_names}


def check_task_ledger():
    """Check recent crew tasks."""
    ledger = Path("C:/AI/AI_ROBOTS/artifacts/task_ledger.jsonl")
    if not ledger.exists():
        return {"status": "empty", "tasks": 0, "recent": []}
    
    lines = ledger.read_text().strip().split("\n")
    tasks = [json.loads(line) for line in lines[-5:] if line]
    recent = [{"crew": t.get("crew", "?"), "status": t.get("status", "?")} for t in tasks]
    
    return {"status": "active", "tasks": len(lines), "recent": recent}


def check_batch_log():
    """Check batch runner status."""
    log = Path("C:/AI/AI_ROBOTS/artifacts/batch_log.jsonl")
    if not log.exists():
        return {"status": "no_runs", "completed": 0, "recent": []}
    
    lines = log.read_text().strip().split("\n")
    if not lines or not lines[0]:
        return {"status": "no_runs", "completed": 0, "recent": []}
    
    tasks = [json.loads(line) for line in lines[-3:] if line]
    recent = [{"task": str(t.get("task", {}))[:40], "status": t.get("status", "?")} for t in tasks]
    
    return {"status": "has_runs", "completed": len(lines), "recent": recent}


def check_assets():
    """Check Final Assets folder."""
    assets = Path("C:/dev/Compare/Final Assets/Characters")
    if not assets.exists():
        return {"status": "missing", "characters": []}
    
    chars = [d.name for d in assets.iterdir() if d.is_dir()]
    return {"status": "exists", "characters": chars}


def status_icon(status):
    if status in ("running", "exists", "active", "has_runs"):
        return f"{C.GREEN}●{C.RESET}"
    elif status in ("offline", "missing", "empty", "no_runs"):
        return f"{C.RED}●{C.RESET}"
    return f"{C.YELLOW}●{C.RESET}"


def render_dashboard():
    """Render the dashboard."""
    clear_screen()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"{C.BOLD}{C.CYAN}╔══════════════════════════════════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}║           MK1 SYSTEM DASHBOARD                 {now} ║{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
    print()
    
    # Layer 1: LLM Backend
    ollama = check_ollama()
    print(f"{C.BOLD}┌─ LAYER 1: LLM BACKEND ─────────────────────────────────────────────┐{C.RESET}")
    print(f"│ {status_icon(ollama['status'])} Ollama: {ollama['status'].upper():<10} Models: {ollama['models']}")
    if ollama['details']:
        print(f"│   Loaded: {', '.join(ollama['details'][:2])}")
    print(f"{C.BOLD}└──────────────────────────────────────────────────────────────────────┘{C.RESET}")
    print()
    
    # Layer 2: ComfyUI
    comfy = check_comfyui()
    print(f"{C.BOLD}┌─ LAYER 2: COMFYUI (Asset Generation) ──────────────────────────────┐{C.RESET}")
    print(f"│ {status_icon(comfy['status'])} ComfyUI: {comfy['status'].upper():<10} Version: {comfy['version']}")
    if comfy['status'] == 'running':
        print(f"│   GPU: {comfy['gpu']}")
        print(f"│   VRAM Free: {comfy['vram_free_gb']} GB")
    print(f"{C.BOLD}└──────────────────────────────────────────────────────────────────────┘{C.RESET}")
    print()
    
    # Layer 3: AI Crews
    ledger = check_task_ledger()
    batch = check_batch_log()
    print(f"{C.BOLD}┌─ LAYER 3: AI AGENT CREWS ──────────────────────────────────────────┐{C.RESET}")
    print(f"│ {status_icon(ledger['status'])} Task Ledger: {ledger['tasks']} total tasks")
    print(f"│ {status_icon(batch['status'])} Batch Runner: {batch['completed']} completed")
    if ledger['recent']:
        print(f"│   Recent: ", end="")
        for t in ledger['recent'][-3:]:
            color = C.GREEN if t['status'] == 'completed' else C.YELLOW
            print(f"{color}{t['crew']}/{t['status'][:4]}{C.RESET} ", end="")
        print()
    print(f"{C.BOLD}└──────────────────────────────────────────────────────────────────────┘{C.RESET}")
    print()
    
    # Layer 4: Unity Project
    unity = check_unity_project()
    print(f"{C.BOLD}┌─ LAYER 4: UNITY PROJECT (MK1_Project) ─────────────────────────────┐{C.RESET}")
    print(f"│ {status_icon(unity['status'])} Project: {unity['status'].upper():<10} Scripts: {unity['scripts']}")
    if unity['recent']:
        print(f"│   Recent changes: {', '.join(unity['recent'][:3])}")
    print(f"{C.BOLD}└──────────────────────────────────────────────────────────────────────┘{C.RESET}")
    print()
    
    # Layer 5: Assets
    assets = check_assets()
    print(f"{C.BOLD}┌─ LAYER 5: FINAL ASSETS ────────────────────────────────────────────┐{C.RESET}")
    print(f"│ {status_icon(assets['status'])} Assets: {assets['status'].upper()}")
    if assets['characters']:
        print(f"│   Characters: {', '.join(assets['characters'])}")
    print(f"{C.BOLD}└──────────────────────────────────────────────────────────────────────┘{C.RESET}")
    print()
    
    print(f"{C.DIM}Press Ctrl+C to exit. Refreshing every 5 seconds...{C.RESET}")


def main():
    print("Starting MK1 System Dashboard...")
    try:
        while True:
            render_dashboard()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nDashboard closed.")


if __name__ == "__main__":
    main()
