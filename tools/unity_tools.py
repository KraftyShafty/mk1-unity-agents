"""
Unity Tools
============
Tools for AI agents to write Unity C# scripts.
Writes directly to the MK1_Project.
"""

import os
import yaml
from crewai.tools import tool
from pathlib import Path

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / "project_config.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

UNITY_ROOT = Path(CONFIG['unity_project']['root'])
UNITY_SCRIPTS = Path(CONFIG['unity_project']['scripts'])
UNITY_EDITOR = Path(CONFIG['unity_project']['editor'])

ALLOWED_SCRIPT_DIRS = {
    "Characters": UNITY_SCRIPTS / "Characters",
    "Combat": UNITY_SCRIPTS / "Combat",
    "Core": UNITY_SCRIPTS / "Core",
    "UI": UNITY_SCRIPTS / "UI",
    "Editor": UNITY_EDITOR,
}


@tool("WriteUnityScript")
def write_unity_script(script_name: str, category: str, content: str) -> str:
    """
    Write a C# script to the Unity project.
    
    Args:
        script_name: Name of the script file (e.g., 'ScorpionController.cs')
        category: Category folder - one of: Characters, Combat, Core, UI, Editor
        content: The C# code content
    
    Returns:
        Success message or error.
    """
    if category not in ALLOWED_SCRIPT_DIRS:
        return f"ERROR: Invalid category '{category}'. Use one of: {list(ALLOWED_SCRIPT_DIRS.keys())}"
    
    if not script_name.endswith(".cs"):
        script_name += ".cs"
    
    target_dir = ALLOWED_SCRIPT_DIRS[category]
    target_file = target_dir / script_name
    
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content, encoding='utf-8')
        return f"OK: Wrote {script_name} to {category}/ ({len(content)} bytes)"
    except Exception as e:
        return f"ERROR: {e}"


@tool("ReadUnityScript")
def read_unity_script(script_path: str) -> str:
    """
    Read a C# script from the Unity project.
    
    Args:
        script_path: Relative path from Assets/Scripts (e.g., 'Characters/CharacterController.cs')
    
    Returns:
        File contents or error.
    """
    full_path = UNITY_SCRIPTS / script_path
    
    # Security check
    try:
        full_path.resolve().relative_to(UNITY_ROOT.resolve())
    except ValueError:
        return "ERROR: Path outside Unity project"
    
    if not full_path.exists():
        return f"ERROR: File not found: {script_path}"
    
    try:
        return full_path.read_text(encoding='utf-8')
    except Exception as e:
        return f"ERROR: {e}"


@tool("ListUnityScripts")
def list_unity_scripts(category: str = None) -> str:
    """
    List C# scripts in the Unity project.
    
    Args:
        category: Optional category to list (Characters, Combat, Core, UI, Editor)
    
    Returns:
        List of script files.
    """
    if category and category in ALLOWED_SCRIPT_DIRS:
        dirs = {category: ALLOWED_SCRIPT_DIRS[category]}
    else:
        dirs = ALLOWED_SCRIPT_DIRS
    
    result = []
    for cat_name, cat_path in dirs.items():
        if cat_path.exists():
            scripts = list(cat_path.glob("*.cs"))
            if scripts:
                result.append(f"\n{cat_name}/")
                for script in scripts:
                    size = script.stat().st_size
                    result.append(f"  - {script.name} ({size}B)")
    
    if not result:
        return "No scripts found."
    
    return "\n".join(result)


@tool("ListCharacterAssets") 
def list_character_assets(character: str) -> str:
    """
    List available sprite animations for a character.
    
    Args:
        character: Character name (Scorpion, SubZero, Shared)
    
    Returns:
        List of animation folders.
    """
    assets_source = Path(CONFIG['unity_project']['assets_source'])
    char_path = assets_source / "Characters" / character
    
    if not char_path.exists():
        return f"ERROR: Character folder not found: {character}"
    
    folders = [f.name for f in char_path.iterdir() if f.is_dir()]
    
    if not folders:
        return f"No animation folders found for {character}"
    
    return f"{character} animations ({len(folders)}):\n" + "\n".join(f"  - {f}" for f in sorted(folders)[:30])


if __name__ == "__main__":
    print("=== Unity Tools Self-Test ===")
    print(list_unity_scripts())
    print()
    print(list_character_assets("Scorpion"))
