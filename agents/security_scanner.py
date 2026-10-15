"""
Defensive Security Scanner Agent
Only finds and reports vulnerabilities. Never generates exploits.
"""

from __future__ import annotations

from typing import Optional

from crewai import Agent, Task, Crew
from core.ollama_client import OllamaClient
from core.rag import MemoryStore


class SecurityScannerAgent:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        memory: Optional[MemoryStore] = None,
    ):
        self.ollama = ollama or OllamaClient()
        self.memory = memory or MemoryStore(ollama=self.ollama)

        self.agent = Agent(
            role="Defensive Security Analyst",
            goal=(
                "Identify security vulnerabilities, insecure coding patterns, "
                "secrets, and misconfigurations. Only report findings and "
                "suggest safe fixes. Never create or describe exploits."
            ),
            backstory=(
                "You are a defensive security engineer focused solely on protection. "
                "You use knowledge of OWASP Top 10, common CVEs and secure coding "
                "practices. You never help with offensive techniques."
            ),
            llm=self.ollama.get_crew_llm(),
            verbose=True,
            allow_delegation=False,
        )

    def scan_code(self, file_path: str, content: str, language: str = "python") -> str:
        """Perform defensive security review of a file."""

        context = self.memory.get_context(
            f"security vulnerabilities {language} {file_path}",
            k=4,
        )

        task = Task(
            description=(
                f"Perform a **defensive** security analysis of this {language} file: `{file_path}`\n\n"
                f"Relevant memory:\n{context}\n\n"
                f"Code:\n```{language}\n{content}\n```\n\n"
                "Look for:\n"
                "- Injection risks\n"
                "- Hardcoded secrets / credentials\n"
                "- Insecure deserialization\n"
                "- Path traversal\n"
                "- Weak cryptography\n"
                "- Authentication / authorization issues\n"
                "- Any OWASP Top 10 related problems\n\n"
                "Output format:\n"
                "- Severity (Critical / High / Medium / Low)\n"
                "- Issue description\n"
                "- Location\n"
                "- Safe remediation suggestion\n\n"
                "Important: Do NOT provide any exploit code or attack instructions."
            ),
            expected_output="Structured defensive security report with severity and safe fixes only.",
            agent=self.agent,
        )

        crew = Crew(agents=[self.agent], tasks=[task], verbose=True)
        return str(crew.kickoff())
