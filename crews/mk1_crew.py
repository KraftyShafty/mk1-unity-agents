"""
MK1 Unity Crew
==============
Specialized crew for generating MK1 Unity game code.
Uses Unity tools to write directly to the project.
"""

import yaml
from pathlib import Path
from crewai import Agent, Task, Crew, Process, LLM

# Import tools
from tools.safe_tools import read_repo_file
from tools.unity_tools import (
    write_unity_script, 
    read_unity_script, 
    list_unity_scripts,
    list_character_assets
)

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / "project_config.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)


class MK1Crew:
    """Crew specialized for MK1 Unity game development."""
    
    def __init__(self):
        self.llm = LLM(
            model=CONFIG['llm']['nim']['model'],
            base_url=CONFIG['llm']['nim']['base_url'],
            api_key=CONFIG['llm']['nim']['api_key']
        )
        
        # Fighting Game Architect
        self.architect = Agent(
            role="Fighting Game Architect",
            goal="Design precise specifications for 2D fighting game mechanics",
            backstory=(
                "Expert in classic 2D fighting games (MK, SF2, KOF). "
                "Understands frame data, hitboxes, state machines, and input systems. "
                "Creates detailed specs that implementers can follow exactly. "
                "NOTE: The docs folder in Final Assets is REFERENCE ONLY - paths and code "
                "are from a different project. Use for concepts only, not direct copying."
            ),
            tools=[read_unity_script, list_unity_scripts, list_character_assets],
            llm=self.llm,
            verbose=True,
            max_iter=5
        )
        
        # Unity C# Implementer
        self.implementer = Agent(
            role="Unity C# Developer",
            goal="Implement fighting game mechanics in clean, idiomatic Unity C#",
            backstory=(
                "Senior Unity developer specializing in 2D games. "
                "Writes clean C# code using Unity best practices. "
                "Familiar with SpriteRenderer, Animator, Physics2D, and Input System."
            ),
            tools=[write_unity_script, read_unity_script, list_character_assets],
            llm=self.llm,
            verbose=True,
            max_iter=5
        )
        
        # Code Reviewer
        self.reviewer = Agent(
            role="Unity Code Reviewer",
            goal="Ensure code quality, performance, and fighting game accuracy",
            backstory=(
                "Pedantic C# reviewer who ensures code compiles, follows conventions, "
                "and correctly implements fighting game mechanics."
            ),
            tools=[read_unity_script, list_unity_scripts],
            llm=self.llm,
            verbose=True,
            max_iter=3
        )
    
    def generate_character_script(self, character: str, include_specials: bool = True) -> str:
        """
        Generate a complete character controller script.
        
        Args:
            character: Character name (Scorpion or SubZero)
            include_specials: Whether to include special move implementations
        """
        # Define character-specific data
        if character.lower() == "scorpion":
            specials = """
Special Moves:
- Spear (QCF + Punch): Throws spear projectile, pulls opponent on hit
- Teleport Punch (Down, Back + Punch): Teleports behind opponent with punch
- Leg Takedown (Down, Back + Kick): Low sweep attack
            """
        elif character.lower() in ["subzero", "sub-zero", "sub_zero"]:
            character = "SubZero"
            specials = """
Special Moves:
- Ice Ball (QCF + Punch): Freezes opponent on hit, slow projectile
- Ice Slide (Back + Block + LowKick): Slides forward with low attack
- Ice Clone (Down, Back + Punch): Creates ice statue that freezes on contact
            """
        else:
            return f"ERROR: Unknown character '{character}'"
        
        # Spec task
        spec_task = Task(
            description=f"""
Design a detailed specification for {character}Controller.cs.

Base CharacterController already exists with:
- CharacterState enum (Idle, Walk, Crouch, attacks, hits, etc.)
- State machine with SetState(), UpdateAnimation(), UpdatePhysics()
- Input handling framework

{specials}

Your spec must include:
1. Class structure inheriting from CharacterController
2. Special move state additions
3. Input detection for each special (QCF, etc.)
4. Frame data (startup, active, recovery)
5. Hitbox data for each move
6. Animation triggers

Use ListCharacterAssets to see available sprite animations.
            """,
            expected_output="Technical specification for the character controller.",
            agent=self.architect
        )
        
        # Implementation task
        impl_task = Task(
            description=f"""
Implement {character}Controller.cs based on the Architect's specification.

Requirements:
1. Inherit from CharacterController (in MKReturns.Characters namespace)
2. Override necessary methods to add special moves
3. Use InputBuffer.CheckQCF(), CheckQCB(), CheckDP() for motion inputs
4. Use CombatSystem for hitbox registration
5. Use CharacterState enum for states

Use WriteUnityScript to save to Characters category.
File must be valid C# that compiles in Unity.
            """,
            expected_output="Complete C# script written to Unity project.",
            agent=self.implementer
        )
        
        # Review task
        review_task = Task(
            description=f"""
Review the {character}Controller.cs implementation.

Check:
1. Code compiles (no syntax errors)
2. Proper Unity patterns (RequireComponent, SerializeField)
3. Correct namespaces and inheritance
4. Special moves match specification
5. No infinite loops or performance issues

Use ReadUnityScript to review the code.
Output: APPROVED or list specific issues.
            """,
            expected_output="Review verdict with any issues found.",
            agent=self.reviewer
        )
        
        # Run crew
        crew = Crew(
            agents=[self.architect, self.implementer, self.reviewer],
            tasks=[spec_task, impl_task, review_task],
            process=Process.sequential,
            verbose=True
        )
        
        return crew.kickoff()


def run_mk1_character(character: str):
    """CLI entry point for generating character scripts."""
    crew = MK1Crew()
    result = crew.generate_character_script(character)
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        char = sys.argv[1]
    else:
        char = "Scorpion"
    
    print(f"=== Generating {char} Controller ===")
    result = run_mk1_character(char)
    print(result)
