\"\"\"
Sentinel Agent - Main Runner
"\"\"

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from core.ollama_client import OllamaClient
from core.rag import MemoryStore
from agents.code_reviewer import CodeReviewerAgent
from agents.security_scanner import SecurityScannerAgent


def review_local_file(file_path: str):
    """Quick test: review a single local file."""
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return

    content = path.read_text(encoding="utf-8", errors="ignore")
    language = path.suffix.lstrip(".") or "text"

    print(f"\n🔍 Reviewing: {file_path}\n")

    ollama = OllamaClient()
    memory = MemoryStore(ollama=ollama)

    reviewer = CodeReviewerAgent(ollama=ollama, memory=memory)
    result = reviewer.review_file(str(path), content, language=language)

    print("\n" + "=" * 60)
    print("CODE REVIEW RESULT")
    print("=" * 60)
    print(result)


def security_scan_file(file_path: str):
    """Quick test: defensive security scan."""
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return

    content = path.read_text(encoding="utf-8", errors="ignore")
    language = path.suffix.lstrip(".") or "text"

    print(f"\n🛡️  Security scanning: {file_path}\n")

    ollama = OllamaClient()
    memory = MemoryStore(ollama=ollama)

    scanner = SecurityScannerAgent(ollama=ollama, memory=memory)
    result = scanner.scan_code(str(path), content, language=language)

    print("\n" + "=" * 60)
    print("SECURITY SCAN RESULT")
    print("=" * 60)
    print(result)


def main():
    parser = argparse.ArgumentParser(description="Sentinel Agent")
    parser.add_argument("--review", type=str, help="Review a local file")
    parser.add_argument("--security", type=str, help="Run defensive security scan on a file")
    parser.add_argument("--test", action="store_true", help="Run a quick self-test")

    args = parser.parse_args()

    if args.review:
        review_local_file(args.review)
    elif args.security:
        security_scan_file(args.security)
    elif args.test:
        print("Sentinel Agent is alive.")
        print(f"Ollama URL : {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
        print(f"Model      : {os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:32b')}")
    else:
        print("Sentinel Agent")
        print("Usage:")
        print("  python -m scripts.run --review path/to/file.py")
        print("  python -m scripts.run --security path/to/file.py")
        print("  python -m scripts.run --test")


if __name__ == "__main__":
    main()
