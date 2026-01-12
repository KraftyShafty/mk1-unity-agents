"""
Safe File System Tools
======================
Security-constrained file operations for AI agents.
Prevents path traversal, enforces extension allowlists, and restricts to repo root.
"""

import os
import yaml
from crewai.tools import tool
from pathlib import Path

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / "project_config.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

REPO_ROOT = Path(__file__).parent.parent.resolve()
ALLOWED_EXTS = set(CONFIG['security']['allowed_extensions'])
ALLOWED_DIRS = set(CONFIG['security']['allowed_directories'])


def _validate_path(rel_path: str, check_extension: bool = True) -> tuple[Path, str | None]:
    """
    Validate a relative path is safe.
    Returns (full_path, error_message). If error_message is None, path is valid.
    """
    # Normalize and check for absolute path
    rel_path = rel_path.replace("\\", "/")
    if os.path.isabs(rel_path):
        return None, "ERROR: Absolute paths not allowed."
    
    # Resolve full path
    full_path = (REPO_ROOT / rel_path).resolve()
    
    # Check repo root constraint
    try:
        full_path.relative_to(REPO_ROOT)
    except ValueError:
        return None, "ERROR: Path escapes repo root."
    
    # Check extension allowlist
    if check_extension:
        ext = full_path.suffix.lower()
        if ext not in ALLOWED_EXTS:
            return None, f"ERROR: Extension '{ext}' not allowed. Allowed: {ALLOWED_EXTS}"
    
    return full_path, None


@tool("ReadRepoFile")
def read_repo_file(rel_path: str) -> str:
    """
    Read a text file from within the repo.
    
    Args:
        rel_path: Relative path from repo root (e.g., 'src/main.cpp')
    
    Returns:
        File contents or error message.
    """
    full_path, error = _validate_path(rel_path)
    if error:
        return error
    
    if not full_path.exists():
        return f"ERROR: File not found: {rel_path}"
    
    if not full_path.is_file():
        return f"ERROR: Not a file: {rel_path}"
    
    try:
        return full_path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        return f"ERROR: Could not read file: {e}"


@tool("WriteRepoFile")
def write_repo_file(rel_path: str, content: str) -> str:
    """
    Write a text file within allowed directories.
    
    Args:
        rel_path: Relative path from repo root (e.g., 'artifacts/analysis/report.md')
        content: Text content to write
    
    Returns:
        Success message or error.
    """
    # Check top-level directory is allowed
    top_dir = rel_path.replace("\\", "/").split("/")[0]
    if top_dir not in ALLOWED_DIRS:
        return f"ERROR: Write not allowed to '{top_dir}'. Allowed: {ALLOWED_DIRS}"
    
    full_path, error = _validate_path(rel_path)
    if error:
        return error
    
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')
        return f"OK: Wrote {rel_path} ({len(content)} bytes)"
    except Exception as e:
        return f"ERROR: Could not write file: {e}"


@tool("ListRepoTree")
def list_repo_tree(rel_dir: str = ".", max_depth: int = 3) -> str:
    """
    List repository file tree (repo map builder).
    
    Args:
        rel_dir: Relative directory to list (default: repo root)
        max_depth: Maximum recursion depth
    
    Returns:
        Tree structure as text.
    """
    full_path, error = _validate_path(rel_dir, check_extension=False)
    if error:
        return error
    
    if not full_path.is_dir():
        return f"ERROR: Not a directory: {rel_dir}"
    
    lines = []
    
    def _walk(path: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        
        try:
            entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        except PermissionError:
            return
        
        for i, entry in enumerate(entries):
            # Skip hidden and common noise
            if entry.name.startswith('.') or entry.name in {'__pycache__', 'node_modules', 'venv', 'build'}:
                continue
            
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                next_prefix = prefix + ("    " if is_last else "│   ")
                _walk(entry, next_prefix, depth + 1)
            else:
                size = entry.stat().st_size
                lines.append(f"{prefix}{connector}{entry.name} ({size}B)")
    
    lines.append(f"{rel_dir}/")
    _walk(full_path, "", 1)
    
    return "\n".join(lines[:200])  # Cap output


if __name__ == "__main__":
    # Self-test
    print("=== Safe Tools Self-Test ===")
    print(list_repo_tree(".", max_depth=2))
