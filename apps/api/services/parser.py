import json
import hashlib
from pathlib import Path
from typing import AsyncIterator
from datetime import datetime


class Conversation:
    """Represents a Claude Code conversation."""

    def __init__(
        self,
        messages: list[dict],
        file_path: str,
        timestamp: datetime | None = None,
    ):
        self.messages = messages
        self.file_path = file_path
        self.timestamp = timestamp or datetime.utcnow()

    def get_full_text(self) -> str:
        """Get the full conversation as text."""
        return "\n\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in self.messages
        )


class ClaudeLogParser:
    """Parser for Claude Code JSONL log files."""

    def __init__(self, logs_path: str):
        self.logs_path = Path(logs_path).expanduser()
        self.processed_hashes: set[str] = set()

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute a hash of the file contents."""
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _parse_jsonl_file(self, file_path: Path) -> list[Conversation]:
        """Parse a single JSONL file into conversations."""
        conversations = []
        current_messages = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)

                        # Extract message based on entry type
                        if "message" in entry:
                            msg = entry["message"]
                            role = msg.get("role", "unknown")
                            content = ""

                            # Handle different content formats
                            if "content" in msg:
                                if isinstance(msg["content"], str):
                                    content = msg["content"]
                                elif isinstance(msg["content"], list):
                                    # Extract text from content blocks
                                    for block in msg["content"]:
                                        if isinstance(block, dict):
                                            if block.get("type") == "text":
                                                content += block.get("text", "")
                                            elif block.get("type") == "tool_use":
                                                content += f"[Tool: {block.get('name', 'unknown')}]"
                                        elif isinstance(block, str):
                                            content += block

                            if content:
                                current_messages.append(
                                    {
                                        "role": role,
                                        "content": content,
                                        "timestamp": entry.get("timestamp"),
                                    }
                                )

                        # Check for conversation boundaries
                        if entry.get("type") == "conversation_end" and current_messages:
                            conversations.append(
                                Conversation(
                                    messages=current_messages.copy(),
                                    file_path=str(file_path),
                                )
                            )
                            current_messages = []

                    except json.JSONDecodeError:
                        continue

            # Add remaining messages as a conversation
            if current_messages:
                conversations.append(
                    Conversation(
                        messages=current_messages,
                        file_path=str(file_path),
                    )
                )

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        return conversations

    async def parse_all_logs(self) -> AsyncIterator[tuple[Path, list[Conversation]]]:
        """Parse all JSONL files in the logs directory."""
        if not self.logs_path.exists():
            print(f"Logs path does not exist: {self.logs_path}")
            return

        # Find all JSONL files - Claude Code stores them directly in project folders
        pattern = "**/*.jsonl"
        files_found = list(self.logs_path.glob(pattern))
        print(f"Found {len(files_found)} JSONL files in {self.logs_path}")

        for file_path in files_found:
            # Skip subagent files (they're fragments)
            if "subagents" in str(file_path):
                continue
            # Check if already processed
            file_hash = self._compute_file_hash(file_path)
            if file_hash in self.processed_hashes:
                continue

            # Parse the file
            conversations = self._parse_jsonl_file(file_path)

            if conversations:
                self.processed_hashes.add(file_hash)
                yield file_path, conversations

    async def watch_for_changes(self) -> AsyncIterator[tuple[Path, list[Conversation]]]:
        """Watch for new or modified log files."""
        # This would use watchdog or similar for real implementation
        # For now, just yield new files
        async for result in self.parse_all_logs():
            yield result
