"""
Asset Crew
==========
Art Director → ComfyUI Generator → QC → Cataloger
"""

import yaml
import json
from pathlib import Path
from crewai import Agent, Task, Crew, Process, LLM
from PIL import Image

# Import tools
from tools.safe_tools import read_repo_file, write_repo_file
from tools.comfy_tools import comfy_queue, comfy_wait, comfy_download, comfy_status

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / "project_config.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

REPO_ROOT = Path(__file__).parent.parent.resolve()


class AssetCrew:
    """Asset generation crew with ComfyUI integration."""
    
    def __init__(self):
        # Initialize LLM connection to local inference
        self.llm = LLM(
            model=CONFIG['llm']['nim']['model'],
            base_url=CONFIG['llm']['nim']['base_url'],
            api_key=CONFIG['llm']['nim']['api_key']
        )
        
        # Define agents
        self.art_director = Agent(
            role="Art Director",
            goal="Translate game design requirements into precise ComfyUI workflow parameters",
            backstory=(
                "Expert in game art pipelines. Understands sprite sheets, UI elements, "
                "and fighting game aesthetics. Creates asset specs with exact dimensions, "
                "style references, and acceptance criteria."
            ),
            tools=[read_repo_file],
            llm=self.llm,
            verbose=True,
            max_iter=3
        )
        
        self.generator = Agent(
            role="ComfyUI Operator",
            goal="Execute ComfyUI workflows with correct parameters and capture outputs",
            backstory=(
                "Expert in Stable Diffusion and ComfyUI. Knows how to queue workflows, "
                "set seeds for reproducibility, and poll for completion."
            ),
            tools=[comfy_status, comfy_queue, comfy_wait, comfy_download],
            llm=self.llm,
            verbose=True,
            max_iter=5
        )
        
        self.qc_agent = Agent(
            role="Asset QC",
            goal="Validate generated assets meet specifications",
            backstory=(
                "Quality control specialist. Verifies image dimensions, format, "
                "and naming conventions. Rejects assets that don't meet spec."
            ),
            tools=[read_repo_file],
            llm=self.llm,
            verbose=True,
            max_iter=3
        )
        
        self.cataloger = Agent(
            role="Asset Cataloger",
            goal="Organize and catalog approved assets for project integration",
            backstory=(
                "Asset management expert. Moves validated assets to correct folders, "
                "updates indexes, and maintains the asset registry."
            ),
            tools=[read_repo_file, write_repo_file],
            llm=self.llm,
            verbose=True,
            max_iter=3
        )
    
    def _validate_image(self, image_path: str, spec: dict) -> tuple[bool, str]:
        """Validate image against spec requirements."""
        try:
            img = Image.open(image_path)
            
            errors = []
            
            # Check dimensions
            if 'size' in spec:
                expected = tuple(spec['size'])
                if img.size != expected:
                    errors.append(f"Dimensions: expected {expected}, got {img.size}")
            
            # Check alpha
            if spec.get('alpha'):
                if img.mode not in ('RGBA', 'LA', 'PA'):
                    errors.append(f"Alpha required but mode is {img.mode}")
            
            # Check format
            if 'format' in spec:
                expected_format = spec['format'].upper()
                if img.format and img.format != expected_format:
                    errors.append(f"Format: expected {expected_format}, got {img.format}")
            
            if errors:
                return False, "; ".join(errors)
            return True, "All checks passed"
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def run(self, spec_path: str) -> str:
        """Run the asset crew on a spec file."""
        
        # Load and validate spec
        spec_file = REPO_ROOT / spec_path
        if not spec_file.exists():
            return f"ERROR: Spec file not found: {spec_path}"
        
        try:
            spec = yaml.safe_load(spec_file.read_text())
        except Exception as e:
            return f"ERROR: Invalid spec YAML: {e}"
        
        # Define tasks
        design_task = Task(
            description=(
                f"Review asset spec: {spec_path}\n"
                f"Spec contents:\n{json.dumps(spec, indent=2)}\n\n"
                "Confirm the workflow exists and parameters are valid."
            ),
            expected_output="Confirmation that spec is valid and ready for generation.",
            agent=self.art_director
        )
        
        generate_task = Task(
            description=(
                f"Generate the asset using workflow: {spec.get('workflow', 'N/A')}\n"
                f"Apply overrides: {spec.get('overrides', {})}\n\n"
                "Steps:\n"
                "1. Check ComfyUIStatus\n"
                "2. Queue the workflow with ComfyUIQueue\n"
                "3. Wait for completion with ComfyUIWait\n"
                "4. Download outputs with ComfyUIDownload"
            ),
            expected_output="Path to downloaded asset files.",
            agent=self.generator
        )
        
        qc_task = Task(
            description=(
                f"Validate generated assets against spec requirements:\n"
                f"- Size: {spec.get('size', 'N/A')}\n"
                f"- Format: {spec.get('format', 'N/A')}\n"
                f"- Alpha: {spec.get('alpha', False)}\n\n"
                "Report PASS or FAIL with details."
            ),
            expected_output="QC PASS/FAIL report.",
            agent=self.qc_agent
        )
        
        catalog_task = Task(
            description=(
                f"If QC passed, move asset to assets/ue_ready/{spec.get('asset_id', 'unknown')}/\n"
                "Update the asset index with metadata."
            ),
            expected_output="Asset cataloged and ready for Unreal import.",
            agent=self.cataloger
        )
        
        # Create and run crew
        crew = Crew(
            agents=[self.art_director, self.generator, self.qc_agent, self.cataloger],
            tasks=[design_task, generate_task, qc_task, catalog_task],
            process=Process.sequential,
            verbose=True
        )
        
        return crew.kickoff()


if __name__ == "__main__":
    # Test with a sample spec
    crew = AssetCrew()
    result = crew.run("workflows/specs/test_sprite.yaml")
    print(result)
