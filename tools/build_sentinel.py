"""
Build Sentinel Tools
====================
Profile-based build/test execution with NO arbitrary shell commands.
All commands are predefined in project_config.yaml.
"""

import subprocess
import yaml
from crewai.tools import tool
from pathlib import Path
from datetime import datetime
import json

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / "project_config.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

REPO_ROOT = Path(__file__).parent.parent.resolve()
BUILD_PROFILES = CONFIG['build_profiles']
BUILD_LOG_DIR = REPO_ROOT / CONFIG['artifacts']['build_logs']


def _log_build(profile: str, status: str, output: str) -> Path:
    """Log build result to artifacts."""
    BUILD_LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = BUILD_LOG_DIR / f"{profile}_{timestamp}.log"
    
    log_data = {
        "profile": profile,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "output": output[-5000:]  # Last 5k chars
    }
    
    log_file.write_text(json.dumps(log_data, indent=2))
    return log_file


@tool("BuildAndTest")
def build_and_test(profile: str) -> str:
    """
    Run a predefined build/test profile.
    
    Args:
        profile: One of 'configure', 'build', 'test', 'format'
    
    Returns:
        PASS/FAIL status with log tail.
    """
    if profile not in BUILD_PROFILES:
        valid = list(BUILD_PROFILES.keys())
        return f"ERROR: Invalid profile '{profile}'. Valid options: {valid}"
    
    profile_config = BUILD_PROFILES[profile]
    command = profile_config['command']
    timeout = profile_config.get('timeout_sec', 300)
    
    try:
        # Run command (NO shell=True - fixed argv array only)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT)
        )
        
        output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        status = "PASS" if result.returncode == 0 else "FAIL"
        
        # Log the build
        log_file = _log_build(profile, status, output)
        
        # Return summary
        return (
            f"{status} (exit={result.returncode})\n"
            f"Command: {' '.join(command)}\n"
            f"Log: {log_file.relative_to(REPO_ROOT)}\n"
            f"---OUTPUT TAIL---\n"
            f"{output[-2000:]}"
        )
        
    except subprocess.TimeoutExpired:
        return f"FAIL: Command timed out after {timeout}s"
    except FileNotFoundError as e:
        return f"FAIL: Command not found: {e}"
    except Exception as e:
        return f"FAIL: Exception: {e}"


@tool("GetBuildStatus")
def get_build_status() -> str:
    """
    Get the status of recent builds.
    
    Returns:
        Summary of last 5 build logs.
    """
    if not BUILD_LOG_DIR.exists():
        return "No build logs found."
    
    logs = sorted(BUILD_LOG_DIR.glob("*.log"), reverse=True)[:5]
    
    if not logs:
        return "No build logs found."
    
    summaries = []
    for log_file in logs:
        try:
            data = json.loads(log_file.read_text())
            summaries.append(
                f"- {data['profile']}: {data['status']} @ {data['timestamp']}"
            )
        except Exception:
            summaries.append(f"- {log_file.name}: (parse error)")
    
    return "Recent Builds:\n" + "\n".join(summaries)


if __name__ == "__main__":
    print("=== Build Sentinel Self-Test ===")
    print(f"Available profiles: {list(BUILD_PROFILES.keys())}")
    print(get_build_status())
