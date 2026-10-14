"""
Permission-controlled code writing and fixing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from core.permission_manager import PermissionManager, Action
from core.ollama_client import OllamaClient

logger = logging.getLogger("sentinel.code_writer")


class CodeWriter:
    """Writes or fixes code only after permission is granted."""

    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        permissions: Optional[PermissionManager] = None,
    ):
        self.ollama = ollama or OllamaClient()
        self.permissions = permissions or PermissionManager()

    def propose_fix(self, file_path: str, content: str, issue_description: str) -> str:
        """Generate a fixed version of the code (does not write to disk yet)."""

        prompt = f"""
You are a careful senior developer. Fix the following issue in the code.
Only change what is necessary. Keep the rest of the code intact.
Return ONLY the complete fixed file content, nothing else.

Issue:
{issue_description}

Current code ({file_path}):
```
{content}
```
"""
        fixed = self.ollama.chat(prompt, system="You are a precise code fixer. Output only the full corrected file.")
        return fixed.strip()

    def write_file(self, file_path: str, new_content: str, reason: str) -> str:
        """Write content to disk only if permission allows."""

        if not self.permissions.can_perform(Action.MODIFY_FILES):
            return self.permissions.request_approval(
                Action.MODIFY_FILES,
                f"Write/fix file: {file_path}\nReason: {reason}",
                context={"file": file_path, "preview": new_content[:500]},
            )

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_content, encoding="utf-8")
        logger.info(f"File written: {file_path}")
        return f"✅ File written successfully: {file_path}"

    def apply_fix(self, file_path: str, content: str, issue: str) -> str:
        """Propose + write (with permission check)."""
        fixed = self.propose_fix(file_path, content, issue)
        return self.write_file(file_path, fixed, reason=issue)
