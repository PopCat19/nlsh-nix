# prompts.py
#
# Purpose: LLM prompt templates and scouting safety rules
#
# This module:
# - Defines prompt templates for command generation
# - Maintains the scout command blocklist

SCOUT_BLOCKED = [
    "rm ", "mv ", "touch ", "mkdir ", "rmdir ",
    "chmod ", "chown ", "chgrp ",
    "dd ", "mkfs",
    "kill ", "pkill", "killall",
    "reboot", "shutdown", "poweroff", "halt",
    "mount ", "umount",
    "systemctl start", "systemctl stop", "systemctl restart",
    "systemctl enable", "systemctl disable",
    "systemctl mask", "systemctl unmask",
    "sudo",
    " > ", " >> ",
    "| tee ",
    "git commit", "git push", "git add ", "git rm ",
    "git checkout ", "git merge", "git rebase",
    "git reset ",
    "nixos-rebuild switch", "nixos-rebuild boot",
    "nix build ", "nix shell ", "nix run ",
    "nix develop", "nix profile install",
    "ln -",
    "pip install", "pip uninstall",
    "npm install -g", "cargo install",
    "make install",
    "cp ", "scp ",
]


def _is_blocked_scout(cmd):
    for p in SCOUT_BLOCKED:
        if cmd.startswith(p) or f" {p}" in cmd:
            return True
    return False


PROMPT_SINGLE = """You are a shell command translator. Convert the user's request into a shell command.

{shell_context}
Current directory: {cwd}

Recent command history:
{history}{regen_section}{clarification_section}{terminal_history}

Rules:
- Output ONLY the command, nothing else
- No explanations, no markdown, no backticks
- If the request is ambiguous or vague, respond with: CLARIFY: <question>
  1) <option 1>
  2) <option 2>
  ...
  0) custom (describe what you want)
- Learn from previous attempts - if a similar command was rejected, try a different approach
- Otherwise, make a reasonable assumption
- Prefer simple, common commands
- Prefer using available aliases/abbreviations when they match

User request: {user_input}"""

PROMPT_MULTI = """You are a shell command translator. Generate exactly 3 different command options for the user's request.

{shell_context}
Current directory: {cwd}

Recent command history:
{history}{regen_section}{clarification_section}{terminal_history}

Rules:
- Output exactly 3 commands, one per line, numbered 1-3
- Include a very brief description after // (max 5 words)
- Each command should be a different approach
- No markdown, no backticks
- Format: 1) <command> // <5 word max>
- Learn from previous attempts
- Prefer simple, common commands

User request: {user_input}"""

PROMPT_SCOUT_SINGLE = """Generate ONE scout command to gather context for this request.

{shell_context}
Current directory: {cwd}{reject_section}

Rules:
- Output ONLY the command, nothing else
- Scout MUST be purely observational / readonly
- Never change files, permissions, processes, or system state
- NO sudo allowed
- Keep it minimal and fast
- Safe scouts: ls, cat, head, tail, file, stat, which, find (not /), grep, rg,
  ps, df, du, free, echo, git log, git diff, systemctl status, journalctl

Request: {user_input}

Output only the single scout command:"""
