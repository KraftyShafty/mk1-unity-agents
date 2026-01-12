# Orchestrator Quick Reference

## 🚀 Common Commands

### Single Task Execution
```bash
# Run MK1 crew for a character
python main_orchestrator.py --crew mk1 --task Scorpion --check

# Run code crew for a script
python main_orchestrator.py --crew code --task "Create HealthUI.cs"

# Run asset crew with a spec file
python main_orchestrator.py --crew asset --task "workflows/specs/scorpion_idle.yaml"
```

### Batch Execution
```bash
# Default (priority mode, parallel within priorities)
python batch_runner.py

# Sequential (one at a time, safest)
python batch_runner.py --mode sequential

# Full parallel (all at once, fastest)
python batch_runner.py --mode parallel

# More retries
python batch_runner.py --retries 5 --retry-delay 10
```

## 🔍 Status Checks

### Check Services
```bash
python main_orchestrator.py --crew mk1 --task Scorpion --check
```

Expected output:
```
=== Prerequisite Check ===
  ✓ Ollama: online
  ✓ ComfyUI: online
```

### View Logs
```bash
# Task ledger (all tasks ever run)
cat artifacts/task_ledger.jsonl

# Batch log (last batch run)
cat artifacts/batch_log.jsonl

# Real-time batch monitoring
tail -f artifacts/batch_log.jsonl
```

## 📋 Task Queue (batch_runner.py)

Current tasks:
```python
TASKS = [
    # Priority 1 - Core characters
    {"crew": "mk1", "task": "Scorpion", "priority": 1},
    {"crew": "mk1", "task": "SubZero", "priority": 1},

    # Priority 2 - Additional characters
    {"crew": "mk1", "task": "Raiden", "priority": 2},
    {"crew": "mk1", "task": "LiuKang", "priority": 2},

    # Priority 1 - Core systems
    {"crew": "code", "task": "Create NinjaBase.cs", "priority": 1},
    {"crew": "code", "task": "Create RoundManager.cs", "priority": 1},

    # Priority 2 - UI/Input
    {"crew": "code", "task": "Create HealthUI.cs", "priority": 2},
    {"crew": "code", "task": "Create InputManager.cs", "priority": 2},
]
```

## 🛠️ Python API

### Basic Usage
```python
from main_orchestrator import Orchestrator

# Initialize
orch = Orchestrator(max_retries=3, retry_delay=5)

# Check services
services = orch.check_prerequisites()
print(services)  # {"Ollama": ServiceStatus.ONLINE, ...}

# Run a crew
result = orch.run_mk1_crew("Scorpion")
result = orch.run_code_crew("Create HealthUI.cs")
result = orch.run_asset_crew("workflows/specs/idle.yaml")

# Get status
status = orch.get_status_summary()
print(status["total_tasks"])
print(status["status_counts"])
```

### Parallel Execution
```python
from main_orchestrator import Orchestrator

orch = Orchestrator()

tasks = [
    {"crew": "mk1", "task": "Scorpion"},
    {"crew": "mk1", "task": "SubZero"},
    {"crew": "mk1", "task": "Raiden"},
]

results = orch.run_parallel(tasks, max_workers=3)

for r in results:
    print(f"{r['task']}: {r['status']}")
```

### Batch Runner
```python
from batch_runner import BatchRunner

# Initialize
runner = BatchRunner(max_retries=3, retry_delay=5)

# Check services
is_healthy = runner.check_services()

# Run batch
results = runner.run(mode="priority", parallel=True)

# Results is a list of dicts:
# [
#   {
#     "timestamp": "...",
#     "task": {...},
#     "status": "success",
#     "elapsed_sec": 45.2,
#     "result_preview": "..."
#   },
#   ...
# ]
```

## 📊 Status Enums

### TaskStatus
- `PENDING` - Not yet started
- `RUNNING` - Currently executing
- `SUCCESS` - Completed successfully
- `FAILED` - Failed after all retries
- `RETRY` - Failed, retrying

### ServiceStatus
- `ONLINE` - Service is reachable and healthy
- `OFFLINE` - Service is not reachable
- `DEGRADED` - Service responded but with errors

## 🔧 Configuration

### Environment Variables (future)
```bash
export OLLAMA_URL="http://localhost:11434"
export COMFYUI_URL="http://localhost:8000"
export MAX_RETRIES=5
```

### Config File
Edit `project_config.yaml`:
```yaml
llm:
  ollama:
    base_url: "http://localhost:11434"
    model: "ollama/deepseek-r1:32b"

comfyui:
  base_url: "http://127.0.0.1:8000"
  timeout_sec: 120
```

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| `Ollama: offline` | Run `ollama serve` |
| `ComfyUI: offline` | Start ComfyUI on port 8000 |
| Import errors | Run from project root: `python main_orchestrator.py ...` |
| Tasks failing | Use `--check` flag to verify services |
| Too slow | Use `--mode parallel` for batch |

## 📁 File Locations

```
C:\AI\AI_ROBOTS\
├── main_orchestrator.py      # Core orchestrator
├── batch_runner.py            # Batch execution
├── project_config.yaml        # Configuration
├── artifacts/
│   ├── task_ledger.jsonl      # All task history
│   └── batch_log.jsonl        # Last batch run
├── crews/
│   ├── mk1_crew.py            # MK1 character crew
│   ├── code_crew.py           # General code crew
│   └── asset_crew.py          # Asset generation crew
└── tools/
    ├── unity_tools.py         # Unity integration
    ├── comfy_tools.py         # ComfyUI integration
    └── safe_tools.py          # Security boundaries
```

## 🎯 Workflow Examples

### Generate All Core Characters
```bash
# Edit batch_runner.py TASKS to only include:
# - Scorpion (priority 1)
# - SubZero (priority 1)
# - Raiden (priority 1)
# - LiuKang (priority 1)

python batch_runner.py --mode parallel
```

### Test Single Character
```bash
python main_orchestrator.py --crew mk1 --task Scorpion --check --retries 1
```

### Generate Core Systems Sequentially
```bash
# Edit TASKS to only include code crew tasks
python batch_runner.py --mode sequential
```

### Full Production Run
```bash
# All tasks, priority-based, parallel within priorities
python batch_runner.py --mode priority --retries 5
```

## 💡 Tips

1. **Always check services first** with `--check` flag
2. **Use priority mode** for dependency management
3. **Start with sequential mode** when testing new crews
4. **Monitor logs** in real-time with `tail -f`
5. **Adjust retries** based on Ollama stability
6. **Use parallel mode** only for independent tasks

## 📞 Integration Points

### Dashboard (`dashboard.py`)
```python
from main_orchestrator import Orchestrator

orch = Orchestrator()
status = orch.get_status_summary()

# Update dashboard with:
# - status["total_tasks"]
# - status["status_counts"]
# - status["services"]
```

### CI/CD
```bash
# Exit code 0 = success, 1 = failure
python batch_runner.py --mode priority --retries 3

# Check exit code
if [ $? -eq 0 ]; then
  echo "All tasks succeeded"
else
  echo "Some tasks failed"
fi
```

### Monitoring
```bash
# Watch for failures
watch -n 5 'tail -20 artifacts/task_ledger.jsonl | grep failed'

# Count successes
grep success artifacts/task_ledger.jsonl | wc -l
```
