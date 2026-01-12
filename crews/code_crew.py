"""
Code Crew
=========
Architect → Implementer → Build Sentinel → Reviewer
"""

import yaml
from pathlib import Path
from crewai import Agent, Task, Crew, Process, LLM

# Import tools
from tools.safe_tools import read_repo_file, write_repo_file, list_repo_tree
from tools.build_sentinel import build_and_test, get_build_status

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / "project_config.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)


class CodeCrew:
    """Code development crew with build verification."""
    
    def __init__(self):
        # Initialize LLM connection to local inference
        self.llm = LLM(
            model=CONFIG['llm']['nim']['model'],
            base_url=CONFIG['llm']['nim']['base_url'],
            api_key=CONFIG['llm']['nim']['api_key']
        )
        
        # Define agents
        self.architect = Agent(
            role="Engine Architect",
            goal="Produce narrow, testable specs and interfaces for engine subsystems",
            backstory=(
                "Veteran C++ engine architect. Prefers stable interfaces, explicit ownership, "
                "and testability. You do NOT write implementation code - only specs and headers."
            ),
            tools=[read_repo_file, list_repo_tree],
            llm=self.llm,
            verbose=True,
            max_iter=5
        )
        
        self.implementer = Agent(
            role="Systems Programmer",
            goal="Implement exactly what the spec requires, nothing else",
            backstory=(
                "Senior C++ engineer. Outputs code changes only, keeps edits minimal. "
                "Uses modern C++ features where applicable."
            ),
            tools=[read_repo_file, write_repo_file],
            llm=self.llm,
            verbose=True,
            max_iter=5
        )
        
        self.sentinel = Agent(
            role="Build Sentinel",
            goal="Run the toolchain and report failures with exact repro + log localization",
            backstory=(
                "CI in human form. Trusts ONLY compiler/test output. "
                "If it doesn't compile, it doesn't exist."
            ),
            tools=[build_and_test, get_build_status],
            llm=self.llm,
            verbose=True,
            max_iter=3
        )
        
        self.reviewer = Agent(
            role="Code Reviewer",
            goal="Find correctness/perf issues and missing edge cases; require fixes",
            backstory=(
                "Paranoid C++ reviewer. Hunts UB, lifetime hazards, threading bugs, perf cliffs. "
                "Only approves code that passes build AND meets spec."
            ),
            tools=[read_repo_file],
            llm=self.llm,
            verbose=True,
            max_iter=3
        )
    
    def run(self, task_description: str) -> str:
        """Run the code crew on a task."""
        
        # Define tasks
        spec_task = Task(
            description=(
                f"Design a spec for: {task_description}\n\n"
                "Include: scope, APIs, files to create/modify, invariants, "
                "and acceptance criteria (must include build command)."
            ),
            expected_output="A technical specification with clear acceptance criteria.",
            agent=self.architect
        )
        
        impl_task = Task(
            description=(
                "Implement the code per the Architect's spec.\n"
                "Use WriteRepoFile to save files. Keep changes minimal."
            ),
            expected_output="Code files written to the repo.",
            agent=self.implementer
        )
        
        verify_task = Task(
            description=(
                "Run BuildAndTest(profile='build') to verify the code compiles.\n"
                "If it fails, pinpoint the exact error and propose a fix."
            ),
            expected_output="Build PASS/FAIL status with log analysis.",
            agent=self.sentinel
        )
        
        review_task = Task(
            description=(
                "Review the implemented code for:\n"
                "1. Spec compliance\n"
                "2. Memory safety\n"
                "3. Performance issues\n"
                "If issues found, list them. If clean, output 'APPROVED'."
            ),
            expected_output="Review report with APPROVED or list of issues.",
            agent=self.reviewer
        )
        
        # Create and run crew
        crew = Crew(
            agents=[self.architect, self.implementer, self.sentinel, self.reviewer],
            tasks=[spec_task, impl_task, verify_task, review_task],
            process=Process.sequential,
            verbose=True
        )
        
        return crew.kickoff()


if __name__ == "__main__":
    crew = CodeCrew()
    result = crew.run("Add a hello_world.cpp file that prints 'Hello, MK Engine!'")
    print(result)
