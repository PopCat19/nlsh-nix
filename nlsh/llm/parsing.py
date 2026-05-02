# parsing.py
#
# Purpose: LLM response parsing and normalization
#
# This module:
# - Strips markdown formatting from LLM output
# - Parses numbered command lists into Command objects
# - Extracts clarification prompts from LLM responses

from ..types import Command, ClarifyData


def clean_cmd(text):
    """Strip markdown and backticks from LLM output."""
    cmd = text.strip()
    if cmd.startswith("```"):
        cmd = cmd.split("\n", 1)[1] if "\n" in cmd else ""
    if cmd.endswith("```"):
        cmd = cmd.rsplit("```", 1)[0]
    return cmd.strip("`").strip()


def parse_multi_commands(text):
    """Parse numbered command list into list of Commands."""
    commands = []
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line) > 2 and line[0].isdigit() and line[1] in ") .":
            rest = line[2:].strip()
            if "//" in rest:
                cmd, desc = rest.split("//", 1)
                commands.append(Command(cmd=cmd.strip(), desc=desc.strip()))
            else:
                commands.append(Command(cmd=rest.strip()))
    return commands


def parse_clarify_response(text):
    """Parse CLARIFY response into ClarifyData."""
    lines = text.strip().split("\n")
    question = lines[0].strip() if lines else ""
    options = {}
    for line in lines[1:]:
        line = line.strip()
        if line and len(line) > 2 and line[1] == ")":
            key = line[0]
            if key.isdigit():
                options[key] = line[3:].strip()
    return ClarifyData(question=question, options=options)
