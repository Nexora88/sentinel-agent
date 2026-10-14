"""
Reporter Agent
Produces clean, prioritized reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from crewai import Agent, Task, Crew
from core.ollama_client import OllamaClient


class ReporterAgent:
    def __init__(self, ollama: Optional[OllamaClient] = None):
        self.ollama = ollama or OllamaClient()

        self.agent = Agent(
            role="Clear Technical Reporter",
            goal="Turn raw findings into clear, prioritized and actionable reports for the human.",
            backstory=(
                "You are excellent at communication. You write concise reports that busy developers "
                "actually read. You always put the most important issues first."
            ),
            llm=self.ollama.get_crew_llm(),
            verbose=False,
            allow_delegation=False,
        )

    def create_report(
        self,
        code_reviews: List[str],
        security_findings: List[str],
        repo: str = "unknown",
    ) -> str:
        """Generate a final human-readable report."""

        combined = "\n\n".join(
            ["=== CODE REVIEWS ==="] + code_reviews +
            ["\n=== SECURITY FINDINGS ==="] + security_findings
        )

        task = Task(
            description=(
                f"Create a clear nightly report for repository: {repo}\n\n"
                f"Raw findings:\n{combined[:12000]}\n\n"
                "Structure the report as:\n"
                "# Sentinel Nightly Report\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                "Repository: ...\n\n"
                "## Critical Issues\n"
                "## High Priority\n"
                "## Medium / Low\n"
                "## Summary & Recommended Actions\n\n"
                "Keep it concise and actionable."
            ),
            expected_output="Clean markdown report ready to send to the human.",
            agent=self.agent,
        )

        crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
        return str(crew.kickoff())
