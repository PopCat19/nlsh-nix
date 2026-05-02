# history.py
#
# Purpose: Command history management
#
# This module:
# - Tracks recent commands and their output
# - Tracks regeneration attempts for current query
# - Formats history for LLM context

command_history = []
regen_history = []  # [(attempt, command, clarification)]
MAX_HISTORY = 10
MAX_CONTEXT_CHARS = 4000

def reset_regen_history():
    regen_history.clear()

def add_regen(command: str, clarification: str = ""):
    regen_history.append({
        "attempt": len(regen_history) + 1,
        "command": command,
        "clarification": clarification
    })

def format_regen_history() -> str:
    if not regen_history:
        return "No previous attempts."
    
    lines = []
    for entry in regen_history:
        lines.append(f"Attempt {entry['attempt']}: {entry['command']}")
        if entry['clarification']:
            lines.append(f"  Clarification: {entry['clarification']}")
    return "\n".join(lines)

def get_context_size() -> int:
    return sum(len(e["command"]) + len(e["output"]) for e in command_history)

def add_to_history(command: str, output: str = ""):
    command_history.append({
        "command": command,
        "output": output[:500] if output else ""
    })
    while len(command_history) > MAX_HISTORY:
        command_history.pop(0)
    while get_context_size() > MAX_CONTEXT_CHARS and len(command_history) > 1:
        command_history.pop(0)

def format_history() -> str:
    if not command_history:
        return "No previous commands."

    lines = []
    for i, entry in enumerate(command_history[-5:], 1):
        lines.append(f"{i}. $ {entry['command']}")
        if entry['output']:
            output_lines = entry['output'].strip().split('\n')[:2]
            for line in output_lines:
                lines.append(f"   {line}")
    return "\n".join(lines)