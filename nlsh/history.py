# history.py
#
# Purpose: Command history management
#
# This module:
# - Provides HistoryStore class for tracking commands and regens
# - Formats history for LLM context


class HistoryStore:
    def __init__(self, max_entries=10, max_chars=4000):
        self._commands = []
        self._regens = []
        self.max_entries = max_entries
        self.max_chars = max_chars

    def add_command(self, command, output=""):
        self._commands.append(
            {
                "command": command,
                "output": output[:500] if output else "",
            }
        )
        while len(self._commands) > self.max_entries:
            self._commands.pop(0)
        while self._context_size > self.max_chars and len(self._commands) > 1:
            self._commands.pop(0)

    def add_regen(self, command, clarification=""):
        self._regens.append(
            {
                "attempt": len(self._regens) + 1,
                "command": command,
                "clarification": clarification,
            }
        )

    def reset_regen(self):
        self._regens.clear()

    @property
    def _context_size(self):
        return sum(len(e["command"]) + len(e["output"]) for e in self._commands)

    def format_history(self):
        if not self._commands:
            return "No previous commands."
        lines = []
        for i, entry in enumerate(self._commands[-5:], 1):
            lines.append(f"{i}. $ {entry['command']}")
            if entry["output"]:
                output_lines = entry["output"].strip().split("\n")[:2]
                for line in output_lines:
                    lines.append(f"   {line}")
        return "\n".join(lines)

    def format_regen_history(self):
        if not self._regens:
            return "No previous attempts."
        lines = []
        for entry in self._regens:
            lines.append(f"Attempt {entry['attempt']}: {entry['command']}")
            if entry["clarification"]:
                lines.append(f"  Clarification: {entry['clarification']}")
        return "\n".join(lines)
