"""
Main Orchestrator - Enhanced Version
====================================
Deterministic Python runner that coordinates crews with:
- Retry logic and error handling
- Progress tracking
- Environment health checks
- Parallel execution support
- Dashboard integration ready

NO LLM here - LLMs belong INSIDE the crews, not above them.
"""

import yaml
import argparse
from pathlib import Path
from datetime import datetime
import json
import time
import requests
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
CONFIG_PATH = Path(__file__).parent / "project_config.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

REPO_ROOT = Path(__file__).parent.resolve()
TASK_LEDGER = REPO_ROOT / CONFIG['artifacts']['task_ledger']


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


class ServiceStatus(Enum):
    """Service health status."""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class Orchestrator:
    """Enhanced orchestrator with retry, parallel execution, and monitoring."""

    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        """
        Initialize orchestrator.

        Args:
            max_retries: Maximum retry attempts for failed tasks
            retry_delay: Seconds to wait between retries
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.task_history: List[Dict] = []

    def log_task(self, crew_name: str, task_name: str, status: str,
                 details: str = "", metadata: Dict = None):
        """
        Append task execution to the ledger with enhanced metadata.

        Args:
            crew_name: Name of the crew executing the task
            task_name: Task identifier
            status: Task status (pending/running/success/failed)
            details: Additional details (truncated to 500 chars)
            metadata: Optional additional metadata
        """
        TASK_LEDGER.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "crew": crew_name,
            "task": task_name,
            "status": status,
            "details": details[:500] if details else "",
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.task_history.append(record)

        with open(TASK_LEDGER, 'a') as f:
            f.write(json.dumps(record) + "\n")

        logger.info(f"[{crew_name}] {task_name}: {status}")

    def check_prerequisites(self) -> Dict[str, ServiceStatus]:
        """
        Verify required services are running.

        Returns:
            Dictionary mapping service names to their status
        """
        checks = {}

        # Check Ollama
        try:
            resp = requests.get(
                f"{CONFIG['llm']['ollama']['base_url']}/api/tags",
                timeout=5
            )
            if resp.status_code == 200:
                checks["Ollama"] = ServiceStatus.ONLINE
            else:
                checks["Ollama"] = ServiceStatus.DEGRADED
        except Exception as e:
            logger.warning(f"Ollama check failed: {e}")
            checks["Ollama"] = ServiceStatus.OFFLINE

        # Check ComfyUI
        try:
            resp = requests.get(
                f"{CONFIG['comfyui']['base_url']}/system_stats",
                timeout=5
            )
            if resp.status_code == 200:
                checks["ComfyUI"] = ServiceStatus.ONLINE
            else:
                checks["ComfyUI"] = ServiceStatus.DEGRADED
        except Exception as e:
            logger.warning(f"ComfyUI check failed: {e}")
            checks["ComfyUI"] = ServiceStatus.OFFLINE

        return checks

    def run_code_crew(self, task_description: str) -> Any:
        """
        Execute the Code Crew pipeline with retry logic.
        Architect → Implementer → Build Sentinel → Reviewer

        Args:
            task_description: What code to generate

        Returns:
            Crew execution result
        """
        from crews.code_crew import CodeCrew

        self.log_task("code_crew", task_description, TaskStatus.RUNNING.value)

        for attempt in range(1, self.max_retries + 1):
            try:
                crew = CodeCrew()
                result = crew.run(task_description)

                self.log_task(
                    "code_crew",
                    task_description,
                    TaskStatus.SUCCESS.value,
                    str(result)[:500],
                    {"attempts": attempt}
                )
                return result

            except Exception as e:
                logger.error(f"Code crew attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    self.log_task(
                        "code_crew",
                        task_description,
                        TaskStatus.RETRY.value,
                        str(e),
                        {"attempt": attempt, "max_retries": self.max_retries}
                    )
                    time.sleep(self.retry_delay)
                else:
                    self.log_task(
                        "code_crew",
                        task_description,
                        TaskStatus.FAILED.value,
                        str(e),
                        {"attempts": attempt}
                    )
                    raise

    def run_mk1_crew(self, character_name: str) -> Any:
        """
        Execute the MK1 Character Crew pipeline with retry logic.
        Generates character-specific Unity scripts.

        Args:
            character_name: Character to generate (e.g., "Scorpion", "SubZero")

        Returns:
            Crew execution result
        """
        from crews.mk1_crew import MK1Crew

        task_name = f"Generate {character_name}"
        self.log_task("mk1_crew", task_name, TaskStatus.RUNNING.value)

        for attempt in range(1, self.max_retries + 1):
            try:
                crew = MK1Crew()
                result = crew.generate_character_script(character_name)

                self.log_task(
                    "mk1_crew",
                    task_name,
                    TaskStatus.SUCCESS.value,
                    str(result)[:500],
                    {"character": character_name, "attempts": attempt}
                )
                return result

            except Exception as e:
                logger.error(f"MK1 crew attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    self.log_task(
                        "mk1_crew",
                        task_name,
                        TaskStatus.RETRY.value,
                        str(e),
                        {"attempt": attempt, "max_retries": self.max_retries}
                    )
                    time.sleep(self.retry_delay)
                else:
                    self.log_task(
                        "mk1_crew",
                        task_name,
                        TaskStatus.FAILED.value,
                        str(e),
                        {"attempts": attempt}
                    )
                    raise

    def run_asset_crew(self, spec_path: str) -> Any:
        """
        Execute the Asset Crew pipeline with retry logic.
        Art Director → ComfyUI Generator → QC → Cataloger

        Args:
            spec_path: Path to asset specification file

        Returns:
            Crew execution result
        """
        from crews.asset_crew import AssetCrew

        self.log_task("asset_crew", spec_path, TaskStatus.RUNNING.value)

        for attempt in range(1, self.max_retries + 1):
            try:
                crew = AssetCrew()
                result = crew.run(spec_path)

                self.log_task(
                    "asset_crew",
                    spec_path,
                    TaskStatus.SUCCESS.value,
                    str(result)[:500],
                    {"attempts": attempt}
                )
                return result

            except Exception as e:
                logger.error(f"Asset crew attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    self.log_task(
                        "asset_crew",
                        spec_path,
                        TaskStatus.RETRY.value,
                        str(e),
                        {"attempt": attempt, "max_retries": self.max_retries}
                    )
                    time.sleep(self.retry_delay)
                else:
                    self.log_task(
                        "asset_crew",
                        spec_path,
                        TaskStatus.FAILED.value,
                        str(e),
                        {"attempts": attempt}
                    )
                    raise

    def run_crew(self, crew_name: str, task_input: str) -> Any:
        """
        Universal crew runner - dispatches to appropriate crew.

        Args:
            crew_name: Name of crew to run (code/mk1/asset)
            task_input: Task description or input path

        Returns:
            Crew execution result
        """
        if crew_name == "code":
            return self.run_code_crew(task_input)
        elif crew_name == "mk1":
            return self.run_mk1_crew(task_input)
        elif crew_name == "asset":
            return self.run_asset_crew(task_input)
        else:
            raise ValueError(f"Unknown crew: {crew_name}")

    def run_parallel(self, tasks: List[Dict[str, str]],
                    max_workers: int = 3) -> List[Dict[str, Any]]:
        """
        Execute multiple independent tasks in parallel.

        Args:
            tasks: List of task dicts with 'crew' and 'task' keys
            max_workers: Maximum parallel workers

        Returns:
            List of results with status and output
        """
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(
                    self.run_crew,
                    task['crew'],
                    task['task']
                ): task
                for task in tasks
            }

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append({
                        "task": task,
                        "status": TaskStatus.SUCCESS.value,
                        "result": result
                    })
                except Exception as e:
                    logger.error(f"Parallel task failed: {task} - {e}")
                    results.append({
                        "task": task,
                        "status": TaskStatus.FAILED.value,
                        "error": str(e)
                    })

        return results

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get summary of orchestrator state for dashboard.

        Returns:
            Status dictionary with task counts and service health
        """
        status_counts = {}
        for record in self.task_history:
            status = record.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_tasks": len(self.task_history),
            "status_counts": status_counts,
            "services": self.check_prerequisites(),
            "last_updated": datetime.now().isoformat()
        }


def main():
    """CLI entry point for orchestrator."""
    parser = argparse.ArgumentParser(
        description="AI Robot Agent Orchestrator - Enhanced Version"
    )
    parser.add_argument(
        "--crew",
        choices=["code", "mk1", "asset"],
        required=True,
        help="Which crew to run"
    )
    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="For code/mk1 crew: task description. For asset crew: spec file path."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check prerequisites before running"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Maximum retry attempts (default: 3)"
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=5,
        help="Seconds between retries (default: 5)"
    )

    args = parser.parse_args()

    # Initialize orchestrator
    orch = Orchestrator(max_retries=args.retries, retry_delay=args.retry_delay)

    # Check prerequisites if requested
    if args.check:
        print("\n=== Prerequisite Check ===")
        services = orch.check_prerequisites()
        for service, status in services.items():
            icon = "✓" if status == ServiceStatus.ONLINE else "✗"
            print(f"  {icon} {service}: {status.value}")
        print()

        # Warn if critical services are offline
        if services.get("Ollama") == ServiceStatus.OFFLINE:
            logger.warning("Ollama is offline - LLM tasks will fail!")
        if args.crew == "asset" and services.get("ComfyUI") == ServiceStatus.OFFLINE:
            logger.warning("ComfyUI is offline - asset generation will fail!")

    print(f"\n=== Running {args.crew.upper()} Crew ===")
    print(f"Task: {args.task}")
    print(f"Max Retries: {args.retries}")
    print()

    try:
        result = orch.run_crew(args.crew, args.task)

        print("\n=== Result ===")
        print(result)
        print(f"\n✓ Task completed successfully")

    except Exception as e:
        logger.error(f"Task failed after all retries: {e}")
        print(f"\n✗ Task failed: {e}")
        exit(1)

    # Print summary
    print("\n=== Summary ===")
    summary = orch.get_status_summary()
    print(f"Total tasks executed: {summary['total_tasks']}")
    print(f"Status breakdown: {summary['status_counts']}")


if __name__ == "__main__":
    main()
