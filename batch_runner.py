"""
MK1 Batch Runner - Enhanced Version
====================================
Runs multiple crew tasks autonomously in sequence or parallel.
Now with:
- Support for parallel execution
- Better error handling and retry logic
- Progress tracking
- Service health checks
- Detailed logging
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from main_orchestrator import Orchestrator, TaskStatus, ServiceStatus

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Task queue - Define your tasks here
TASKS = [
    # Character scripts (MK1 Crew)
    {"crew": "mk1", "task": "Scorpion", "priority": 1},
    {"crew": "mk1", "task": "SubZero", "priority": 1},
    {"crew": "mk1", "task": "Raiden", "priority": 2},
    {"crew": "mk1", "task": "LiuKang", "priority": 2},

    # Core systems (Code Crew)
    {
        "crew": "code",
        "task": "Create NinjaBase.cs - abstract base class for Scorpion/SubZero with shared animations",
        "priority": 1
    },
    {
        "crew": "code",
        "task": "Create RoundManager.cs - handles round state, timer, win conditions",
        "priority": 1
    },
    {
        "crew": "code",
        "task": "Create HealthUI.cs - health bar display with damage flash effects",
        "priority": 2
    },
    {
        "crew": "code",
        "task": "Create InputManager.cs - unified input handling for P1/P2",
        "priority": 2
    },
]


class BatchRunner:
    """Enhanced batch runner with parallel execution and monitoring."""

    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        """
        Initialize batch runner.

        Args:
            max_retries: Maximum retry attempts per task
            retry_delay: Seconds to wait between retries
        """
        self.orchestrator = Orchestrator(
            max_retries=max_retries,
            retry_delay=retry_delay
        )
        self.log_file = Path("artifacts/batch_log.jsonl")
        self.log_file.parent.mkdir(exist_ok=True)

    def check_services(self) -> bool:
        """
        Check if required services are running.

        Returns:
            True if all critical services are online, False otherwise
        """
        logger.info("Checking service health...")
        services = self.orchestrator.check_prerequisites()

        all_ok = True
        for service, status in services.items():
            icon = "✓" if status == ServiceStatus.ONLINE else "✗"
            logger.info(f"  {icon} {service}: {status.value}")

            if status == ServiceStatus.OFFLINE:
                all_ok = False
                logger.warning(f"{service} is offline!")

        return all_ok

    def run_sequential(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run tasks one by one in sequence.

        Args:
            tasks: List of task definitions

        Returns:
            List of execution results
        """
        results = []

        for i, task_def in enumerate(tasks, 1):
            logger.info(f"\n[{i}/{len(tasks)}] Processing: {task_def}")
            start = time.time()

            try:
                result = self.orchestrator.run_crew(
                    task_def["crew"],
                    task_def["task"]
                )
                status = TaskStatus.SUCCESS.value

            except Exception as e:
                logger.error(f"Task failed: {e}")
                result = str(e)
                status = TaskStatus.FAILED.value

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
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

            logger.info(f"    Status: {status} ({elapsed:.1f}s)")

        return results

    def run_parallel(self, tasks: List[Dict[str, Any]],
                    max_workers: int = 3) -> List[Dict[str, Any]]:
        """
        Run independent tasks in parallel.

        Args:
            tasks: List of task definitions
            max_workers: Maximum parallel workers

        Returns:
            List of execution results
        """
        logger.info(f"Running {len(tasks)} tasks in parallel (max {max_workers} workers)...")
        start = time.time()

        # Convert task format for orchestrator
        formatted_tasks = [
            {"crew": t["crew"], "task": t["task"]}
            for t in tasks
        ]

        results = self.orchestrator.run_parallel(formatted_tasks, max_workers)
        elapsed = time.time() - start

        # Log results
        for i, result in enumerate(results):
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "task": tasks[i],
                "status": result["status"],
                "elapsed_sec": round(elapsed, 2),
                "result_preview": str(result.get("result", result.get("error", "")))[:500]
            }

            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        logger.info(f"Parallel execution completed in {elapsed:.1f}s")
        return results

    def run_by_priority(self, tasks: List[Dict[str, Any]],
                       parallel: bool = True) -> List[Dict[str, Any]]:
        """
        Run tasks grouped by priority level.
        Priority 1 tasks run first, then priority 2, etc.
        Within each priority level, tasks can run in parallel.

        Args:
            tasks: List of task definitions with 'priority' field
            parallel: Whether to run tasks in parallel within each priority level

        Returns:
            List of all execution results
        """
        # Group tasks by priority
        priority_groups: Dict[int, List[Dict]] = {}
        for task in tasks:
            priority = task.get("priority", 99)
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(task)

        all_results = []

        # Execute each priority group in order
        for priority in sorted(priority_groups.keys()):
            group_tasks = priority_groups[priority]
            logger.info(f"\n{'='*60}")
            logger.info(f"PRIORITY {priority}: {len(group_tasks)} tasks")
            logger.info(f"{'='*60}")

            if parallel and len(group_tasks) > 1:
                results = self.run_parallel(group_tasks)
            else:
                results = self.run_sequential(group_tasks)

            all_results.extend(results)

        return all_results

    def print_summary(self, results: List[Dict[str, Any]]):
        """
        Print execution summary.

        Args:
            results: List of execution results
        """
        print("\n" + "=" * 60)
        print("BATCH EXECUTION COMPLETE")
        print("=" * 60)

        success = sum(1 for r in results if r["status"] == TaskStatus.SUCCESS.value)
        failed = sum(1 for r in results if r["status"] == TaskStatus.FAILED.value)
        total_time = sum(r["elapsed_sec"] for r in results)

        print(f"✓ Success: {success}/{len(results)}")
        print(f"✗ Failed: {failed}/{len(results)}")
        print(f"⏱  Total time: {total_time:.1f}s")
        print(f"📋 Log file: {self.log_file}")
        print("=" * 60)

        # Print failed tasks if any
        if failed > 0:
            print("\nFailed tasks:")
            for r in results:
                if r["status"] == TaskStatus.FAILED.value:
                    task_name = r["task"].get("task", "unknown")
                    print(f"  ✗ {task_name}")
                    print(f"    Error: {r['result_preview']}")

    def run(self, mode: str = "priority", parallel: bool = True) -> List[Dict[str, Any]]:
        """
        Main execution method.

        Args:
            mode: Execution mode ('sequential', 'parallel', 'priority')
            parallel: Whether to use parallel execution (for priority mode)

        Returns:
            List of execution results
        """
        print("=" * 60)
        print("MK1 BATCH RUNNER - ENHANCED VERSION")
        print("=" * 60)
        print(f"Tasks to process: {len(TASKS)}")
        print(f"Execution mode: {mode}")
        if mode == "priority":
            print(f"Parallel within priority: {parallel}")
        print()

        # Check services
        if not self.check_services():
            logger.warning("Some services are offline - tasks may fail!")
            print("\nContinuing in 3 seconds... (Ctrl+C to cancel)")
            time.sleep(3)

        print()
        logger.info("Starting batch execution...")
        start_time = time.time()

        # Execute based on mode
        if mode == "sequential":
            results = self.run_sequential(TASKS)
        elif mode == "parallel":
            results = self.run_parallel(TASKS)
        elif mode == "priority":
            results = self.run_by_priority(TASKS, parallel=parallel)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        total_elapsed = time.time() - start_time
        logger.info(f"Batch execution completed in {total_elapsed:.1f}s")

        # Print summary
        self.print_summary(results)

        return results


def main():
    """Entry point for batch runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="MK1 Batch Runner - Enhanced Version"
    )
    parser.add_argument(
        "--mode",
        choices=["sequential", "parallel", "priority"],
        default="priority",
        help="Execution mode (default: priority)"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel execution within priority levels"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Maximum retry attempts per task (default: 3)"
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=5,
        help="Seconds between retries (default: 5)"
    )

    args = parser.parse_args()

    # Initialize and run
    runner = BatchRunner(
        max_retries=args.retries,
        retry_delay=args.retry_delay
    )

    try:
        results = runner.run(
            mode=args.mode,
            parallel=not args.no_parallel
        )

        # Exit with error code if any tasks failed
        failed = sum(1 for r in results if r["status"] == TaskStatus.FAILED.value)
        if failed > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nBatch execution cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Batch execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
