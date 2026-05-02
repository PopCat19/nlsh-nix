# tools.py
#
# Purpose: Structured tool definitions and execution for model-driven scouting
#
# This module:
# - Defines bash and read tool schemas for OpenAI function calling
# - Executes tool calls safely with output truncation and error handling

import os
import subprocess

from .prompts import _is_blocked_scout

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Execute a bash command in the current working directory. "
            "Returns stdout and stderr. Use for scouting and gathering "
            "information about the environment. "
            "Commands must be purely observational/readonly — never "
            "change files, permissions, processes, or system state."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Bash command to execute",
                },
            },
            "required": ["command"],
        },
    },
}

READ_TOOL = {
    "type": "function",
    "function": {
        "name": "read",
        "description": (
            "Read the contents of a file at the given path. "
            "Returns the file contents truncated to 2000 lines or 50KB."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read",
                },
            },
            "required": ["path"],
        },
    },
}

SCOUT_TOOLS = [BASH_TOOL, READ_TOOL]


def _execute_tool(tool_name, args, cwd):
    if tool_name == "bash":
        cmd = args.get("command", "")
        if not cmd:
            return "(no command provided)"
        if _is_blocked_scout(cmd) or "sudo" in cmd:
            return f"[blocked] {cmd}"
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10,
            )
            output = (result.stdout + result.stderr).strip()
            return output[:2000] if output else "(no output)"
        except subprocess.TimeoutExpired:
            return "(timeout)"
        except Exception as e:
            return f"(error: {e})"

    elif tool_name == "read":
        path = os.path.expanduser(args.get("path", ""))
        if not path:
            return "(no path provided)"
        try:
            with open(path, "r", errors="replace") as f:
                lines = f.readlines()[:2000]
            content = "".join(lines)
            size = len(content.encode("utf-8"))
            if size > 50000:
                content = content[:50000] + "\n... (truncated)"
            return content if content.strip() else "(empty file)"
        except FileNotFoundError:
            return "(file not found)"
        except PermissionError:
            return "(permission denied)"
        except Exception as e:
            return f"(error: {e})"

    return "(unknown tool)"
