"""
Code Reviewer Agent
Finds bugs, code smells, performance issues and suggests safe improvements.
"""

from __future__ import annotations

from typing import Optional

from crewai import Agent, Task, Crew
from core.ollama_client import OllamaClient
from core.rag import MemoryStore


class CodeReviewerAgent:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        memory: Optional[MemoryStore] = None,
    ):
        self.ollama = ollama or OllamaClient()
        self.memory = memory or MemoryStore(ollama=self.ollama)

        self.agent = Agent(
            role="Senior Code Reviewer",
            goal=(
                "Carefully review code for bugs, logic errors, code smells, "
                "performance issues and maintainability problems. "
                "Suggest minimal, safe and clear improvements. Never break working code."
            ),
            backstory=(
                "You are a highly experienced senior software engineer who performs "
                "nightly code reviews. You are strict about quality but always prefer "
                "small, safe changes over large refactors. You explain every issue clearly."
            ),
            llm=self.ollama.get_crew_llm(),
            verbose=True,
            allow_delegation=False,
        )

    def review_file(self, file_path: str, content: str, language: str = "python") -> str:
        """Review a single file and return structured findings."""

        # Retrieve relevant past knowledge
        context = self.memory.get_context(
            f"code review {language} {file_path} common issues",
            k=4,
        )

        task = Task(
            description=(
                f"Review the following {language} code file: `{file_path}`\n\n"
                f"Relevant past knowledge from memory:\n{context}\n\n"
                f"Code to review:\n```{language}\n{content}\n```\n\n"
                "Provide a clear review with:\n"
                "1. Critical issues (bugs / crashes / security)
"
                "2. Important improvements
"
                "3. Minor suggestions
"
                "4. Positive notes (what is good)\n\n"
                "Be specific. Show line references when possible. "
                "Only suggest changes that are safe."
            ),
            expected_output=(
                "A structured code review report with severity levels and concrete suggestions."
            ),
            agent=self.agent,
        )

        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=True,
        )

        result = crew.kickoff()
        return str(result)

    def review_diff(self, diff: str, repo: str = "unknown") -> str:
        """Review a git diff."""

        context = self.memory.get_context(f"code review diff {repo}", k=3)

        task = Task(
            description=(
                f"Review the following git diff from repository `{repo}`:\n\n"
                f"Past knowledge:\n{context}\n\n"
                f"Diff:\n```diff\n{diff}\n```\n\n"
                "Focus on newly introduced issues. Be strict but fair."
            ),
            expected_output="Structured review of the diff with clear action items.",
            agent=self.agent,
        )

        crew = Crew(agents=[self.agent], tasks=[task], verbose=True)
        return str(crew.kickoff())
