"""
Learner Agent
Continuously extracts knowledge from code and past reviews.
"""

from __future__ import annotations

from typing import Optional

from crewai import Agent, Task, Crew
from core.ollama_client import OllamaClient
from core.rag import MemoryStore


class LearnerAgent:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        memory: Optional[MemoryStore] = None,
    ):
        self.ollama = ollama or OllamaClient()
        self.memory = memory or MemoryStore(ollama=self.ollama)

        self.agent = Agent(
            role="Knowledge Curator",
            goal=(
                "Extract useful patterns, conventions, common mistakes and project-specific "
                "knowledge from code and reviews. Store them for future use."
            ),
            backstory=(
                "You maintain the long-term memory of the system. "
                "You are excellent at summarizing technical knowledge into reusable insights."
            ),
            llm=self.ollama.get_crew_llm(),
            verbose=True,
            allow_delegation=False,
        )

    def learn_from_code(self, file_path: str, content: str, repo: str = "unknown") -> str:
        """Extract knowledge from a code file and store it."""

        task = Task(
            description=(
                f"Analyze this code file and extract reusable knowledge:\n"
                f"File: {file_path} (repo: {repo})\n\n"
                f"```\n{content[:6000]}\n```\n\n"
                "Extract:\n"
                "- Project conventions / style patterns\n"
                "- Common helper patterns\n"
                "- Potential recurring issues\n"
                "- Important domain knowledge\n\n"
                "Return a concise knowledge summary (max 300 words)."
            ),
            expected_output="Concise knowledge summary ready to be stored in memory.",
            agent=self.agent,
        )

        crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
        summary = str(crew.kickoff())

        # Store both original code and the learned summary
        self.memory.add_code_file(file_path, content, repo=repo)
        self.memory.add_texts(
            [summary],
            metadatas=[{"source": file_path, "repo": repo, "type": "learned_insight"}],
        )

        return summary

    def learn_from_review(self, review_text: str, file_path: str, repo: str = "unknown") -> None:
        """Store a review result as future knowledge."""
        self.memory.add_texts(
            [review_text],
            metadatas=[{"source": file_path, "repo": repo, "type": "past_review"}],
        )
