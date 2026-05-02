# shell.py
#
# Purpose: Shell environment introspection for LLM context
#
# This module:
# - Detects and reads shell aliases, abbreviations, and configuration
# - Reads the user's terminal history file for context sharing

import os
import subprocess

_shell_context = None


def get_shell_context():
    shell = os.environ.get("SHELL", "/bin/bash")
    lines = [f"Shell: {shell}"]

    if "fish" in shell:
        try:
            result = subprocess.run(
                ["fish", "-c", "abbr --show"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                abbrs = [
                    l for l in result.stdout.strip().split("\n")[:10] if l
                ]
                if abbrs:
                    lines.append("Fish abbreviations:")
                    lines.extend(abbrs[:10])
        except Exception:
            pass
    else:
        try:
            result = subprocess.run(
                [shell, "-ic", "alias"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                aliases = [
                    l
                    for l in result.stdout.strip().split("\n")[:10]
                    if l and not l.startswith("#")
                ]
                if aliases:
                    lines.append("Aliases:")
                    lines.extend(aliases[:10])
        except Exception:
            pass

    return "\n".join(lines)


def ensure_shell_context():
    global _shell_context
    if _shell_context is None:
        _shell_context = get_shell_context()
    return _shell_context


def get_shell_history(n=50, max_line=200):
    shell = os.environ.get("SHELL", "/bin/bash")

    if "fish" in shell:
        hist_file = os.path.expanduser("~/.local/share/fish/fish_history")
    elif "zsh" in shell:
        hist_file = os.path.expanduser("~/.zsh_history")
    else:
        hist_file = os.path.expanduser("~/.bash_history")

    if not os.path.exists(hist_file):
        return ""

    try:
        with open(hist_file, "r", errors="replace") as f:
            raw = f.readlines()[-n:]

        history = []
        for line in raw:
            line = line.strip()
            if not line:
                continue

            if "fish" in shell:
                if line.startswith("- cmd: "):
                    cmd = line[7:]
                    history.append(cmd[:max_line] if len(cmd) > max_line else cmd)
            elif "zsh" in shell:
                if line.startswith(": "):
                    parts = line.split(";", 1)
                    if len(parts) > 1:
                        cmd = parts[1]
                        history.append(cmd[:max_line] if len(cmd) > max_line else cmd)
            else:
                history.append(line[:max_line] if len(line) > max_line else line)

        return "\n".join(f"  $ {cmd}" for cmd in history)
    except Exception:
        return ""
