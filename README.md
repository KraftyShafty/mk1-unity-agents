# MK1 Unity Agent Orchestration

AI-powered game development for Mortal Kombat Returns Unity rebuild.

## Quick Start

1. **Dashboard** - Visual monitoring of all system layers
2. **Batch Runner** - Autonomous task execution
3. **JupyterLab** - Interactive development

## Crews

- **Code Crew**: Generates Unity C# scripts (CharacterController, Combat, etc.)
- **Asset Crew**: Creates sprites via ComfyUI (requires running ComfyUI)
- **MK1 Crew**: Specialized character script generation

## Usage

```bash
# Run dashboard
python dashboard.py

# Run autonomous batch
python batch_runner.py

# Run single crew task
python main_orchestrator.py --crew code --task "Create HealthBar.cs UI component"
```

## Configuration

See `project_config.yaml` for LLM endpoints, paths, and settings.
