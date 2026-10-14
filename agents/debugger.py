"""
Debugger Agent
Helps find and explain root causes of errors / bugs.
"""

from __future__ import annotations

from typing import Optional

from crewai import Agent, Task, Crew
from core.ollama_client import OllamaClient
from core.rag import MemoryStore


class DebuggerAgent:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        memory: Optional[MemoryStore] = None,
    ):
        self.ollama = ollama or OllamaClient()
        self.memory = memory or MemoryStore(ollama=self.ollama)

        self.agent = Agent(
            role="Expert Debugger",
            goal=(
                "Analyze error messages, stack traces and code to find the root cause "
                "and propose the smallest safe fix."
            ),
            backstory=(
                "You are a patient and methodical debugger. You never guess. "
                "You look at the evidence (error + code) and explain clearly what is wrong "
                "and how to fix it with minimal changes."
            ),
            llm=self.ollama.get_crew_llm(),
            verbose=True,
            allow_delegation=False,
        )

    def debug(self, error_message: str, code: str = "", file_path: str = "unknown") -> str:
        context = self.memory.get_context(f"debug error {error_message[:200]}", k=4)

        task = Task(
            description=(
                f"Debug the following error.\n\n"
                f"Error / Stack trace:\n{error_message}\n\n"
                f"Related code ({file_path}):\n```\n{code[:8000]}\n```\n\n"
                f"Past knowledge:\n{context}\n\n"
                "Provide:\n"
                "1. Root cause explanation\n"
                "2. Exact location of the problem\n"
                "3. Smallest safe fix (show the corrected snippet)\n"
                "4. How to prevent similar issues in the future"
            ),
            expected_output="Clear root-cause analysis and minimal fix suggestion.",
            agent=self.agent,
        )

        crew = Crew(agents=[self.agent], tasks=[task], verbose=True)
        return str(crew.kickoff())
