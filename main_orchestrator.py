"""
Main Orchestrator
=================
Deterministic Python runner that coordinates crews.
NO LLM here - LLMs belong INSIDE the crews, not above them.
"""

import yaml
import argparse
from pathlib import Path
from datetime import datetime
import json


# Load configuration
CONFIG_PATH = Path(__file__).parent / "project_config.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

REPO_ROOT = Path(__file__).parent.resolve()
TASK_LEDGER = REPO_ROOT / CONFIG['artifacts']['task_ledger']


def log_task(crew_name: str, task_name: str, status: str, details: str = ""):
    """Append task execution to the ledger."""
    TASK_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    
    record = {
        "crew": crew_name,
        "task": task_name,
        "status": status,
        "details": details[:500],
        "timestamp": datetime.now().isoformat()
    }
    
    with open(TASK_LEDGER, 'a') as f:
        f.write(json.dumps(record) + "\n")


def run_code_crew(task_description: str):
    """
    Execute the Code Crew pipeline.
    Architect → Implementer → Build Sentinel → Reviewer
    """
    from crews.code_crew import CodeCrew
    
    log_task("code_crew", "start", "RUNNING", task_description)
    
    try:
        crew = CodeCrew()
        result = crew.run(task_description)
        log_task("code_crew", "complete", "DONE", str(result)[:500])
        return result
    except Exception as e:
        log_task("code_crew", "error", "FAILED", str(e))
        raise


def run_asset_crew(spec_path: str):
    """
    Execute the Asset Crew pipeline.
    Art Director → ComfyUI Generator → QC → Cataloger
    """
    from crews.asset_crew import AssetCrew
    
    log_task("asset_crew", "start", "RUNNING", spec_path)
    
    try:
        crew = AssetCrew()
        result = crew.run(spec_path)
        log_task("asset_crew", "complete", "DONE", str(result)[:500])
        return result
    except Exception as e:
        log_task("asset_crew", "error", "FAILED", str(e))
        raise


def check_prerequisites():
    """Verify required services are running."""
    import requests
    
    checks = []
    
    # Check NIM
    try:
        resp = requests.get(f"{CONFIG['llm']['nim']['base_url']}/models", timeout=5)
        checks.append(("NIM", "OK" if resp.status_code == 200 else "FAIL"))
    except Exception:
        checks.append(("NIM", "OFFLINE"))
    
    # Check ComfyUI
    try:
        resp = requests.get(f"{CONFIG['comfyui']['base_url']}/system_stats", timeout=5)
        checks.append(("ComfyUI", "OK" if resp.status_code == 200 else "FAIL"))
    except Exception:
        checks.append(("ComfyUI", "OFFLINE"))
    
    return checks


def main():
    parser = argparse.ArgumentParser(description="AI Robot Agent Orchestrator")
    parser.add_argument("--crew", choices=["code", "asset"], required=True,
                        help="Which crew to run")
    parser.add_argument("--task", type=str, required=True,
                        help="For code crew: task description. For asset crew: spec file path.")
    parser.add_argument("--check", action="store_true",
                        help="Check prerequisites before running")
    
    args = parser.parse_args()
    
    if args.check:
        print("=== Prerequisite Check ===")
        for service, status in check_prerequisites():
            print(f"  {service}: {status}")
        print()
    
    print(f"=== Running {args.crew} Crew ===")
    print(f"Task: {args.task}")
    print()
    
    if args.crew == "code":
        result = run_code_crew(args.task)
    elif args.crew == "asset":
        result = run_asset_crew(args.task)
    
    print("\n=== Result ===")
    print(result)


if __name__ == "__main__":
    main()
