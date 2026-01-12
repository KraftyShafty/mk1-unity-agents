"""
MK1 Batch Runner
=================
Runs multiple crew tasks autonomously in sequence.
No user intervention required.
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from crews.mk1_crew import MK1Crew
from main_orchestrator import Orchestrator

# Task queue
TASKS = [
    # Character scripts
    {"crew": "mk1", "character": "Scorpion"},
    {"crew": "mk1", "character": "SubZero"},
    
    # Core systems via code crew
    {"crew": "code", "task": "Create NinjaBase.cs - abstract base class for Scorpion/SubZero with shared animations"},
    {"crew": "code", "task": "Create RoundManager.cs - handles round state, timer, win conditions"},
    {"crew": "code", "task": "Create HealthUI.cs - health bar display with damage flash effects"},
    {"crew": "code", "task": "Create InputManager.cs - unified input handling for P1/P2"},
]


def run_batch():
    """Run all tasks without user intervention."""
    log_file = Path("artifacts/batch_log.jsonl")
    log_file.parent.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("MK1 BATCH RUNNER - AUTONOMOUS MODE")
    print("=" * 60)
    print(f"Tasks to process: {len(TASKS)}")
    print("Starting in 3 seconds... (Ctrl+C to cancel)")
    time.sleep(3)
    
    results = []
    
    for i, task_def in enumerate(TASKS, 1):
        print(f"\n[{i}/{len(TASKS)}] Processing: {task_def}")
        start = time.time()
        
        try:
            if task_def.get("crew") == "mk1":
                # Character generation
                crew = MK1Crew()
                result = crew.generate_character_script(task_def["character"])
                status = "success"
            else:
                # General code crew
                orch = Orchestrator()
                result = orch.run_crew(task_def["crew"], task_def["task"])
                status = "success"
                
        except Exception as e:
            result = str(e)
            status = "error"
        
        elapsed = time.time() - start
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task_def,
            "status": status,
            "elapsed_sec": round(elapsed, 2),
            "result_preview": str(result)[:500]
        }
        
        results.append(log_entry)
        
        # Append to log file
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        print(f"    Status: {status} ({elapsed:.1f}s)")
    
    # Summary
    print("\n" + "=" * 60)
    print("BATCH COMPLETE")
    print("=" * 60)
    success = sum(1 for r in results if r["status"] == "success")
    print(f"Success: {success}/{len(results)}")
    print(f"Log: {log_file}")
    
    return results


if __name__ == "__main__":
    run_batch()
