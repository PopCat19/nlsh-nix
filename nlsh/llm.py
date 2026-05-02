# llm.py
#
# Purpose: LLM API interaction and command generation
#
# This module:
# - Manages OpenAI client
# - Generates shell commands from natural language
# - Gathers shell context (aliases, abbreviations)

import os
import json
import time
import subprocess

from openai import OpenAI

from .ui import get_single_key, AwaitIndicator, TIMEOUT
from .types import Command, ClarifyData

_client = None
_shell_context = None

# --- Prompts ---

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

# --- Client ---

def init_client(config):
    global _client
    _client = OpenAI(api_key=config.api_key, base_url=config.base_url)


def reinit_client(config):
    global _client
    _client = OpenAI(api_key=config.api_key, base_url=config.base_url)


def _call_api(messages, max_tokens=256):
    with AwaitIndicator():
        response = _client.chat.completions.create(
            model=os.environ["NLSH_MODEL"],
            messages=messages,
            max_tokens=max_tokens,
            timeout=TIMEOUT,
        )
    return response.choices[0].message.content.strip()


def _call_api_tools(messages, tools, max_tokens=256):
    with AwaitIndicator():
        response = _client.chat.completions.create(
            model=os.environ["NLSH_MODEL"],
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=max_tokens,
            timeout=TIMEOUT,
        )
    return response.choices[0].message


# --- Response Parsing ---

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


# --- Shell Context ---

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


# --- Command Generation ---

def _build_sections(clarification, store, terminal_history=""):
    """Build shared prompt sections from clarification, history, and terminal context."""
    clarification_section = (
        f"\n\nClarification: {clarification}" if clarification else ""
    )
    regen = store.format_regen_history()
    regen_section = (
        f"\n\nPrevious attempts:\n{regen}"
        if regen != "No previous attempts."
        else ""
    )
    th_sec = (
        f"\n\nRecent terminal activity:\n{terminal_history}"
        if terminal_history
        else ""
    )
    return clarification_section, regen_section, th_sec


def get_command(user_input, cwd, store, clarification="", terminal_history=""):
    history = store.format_history()
    shell_ctx = ensure_shell_context()
    cs, rs, th = _build_sections(clarification, store, terminal_history)

    prompt = PROMPT_SINGLE.format(
        shell_context=shell_ctx,
        cwd=cwd,
        history=history,
        regen_section=rs,
        clarification_section=cs,
        terminal_history=th,
        user_input=user_input,
    )

    try:
        result = _call_api([{"role": "user", "content": prompt}])

        if "\nCLARIFY:" in result or result.startswith("CLARIFY:"):
            idx = result.find("CLARIFY:")
            clarify_text = result[idx + 8:].strip()
            return (None, parse_clarify_response(clarify_text))
        return (clean_cmd(result), None)
    except Exception as e:
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            raise TimeoutError("Request timed out")
        raise


def get_commands(user_input, cwd, store, clarification="", terminal_history=""):
    history = store.format_history()
    shell_ctx = ensure_shell_context()
    cs, rs, th = _build_sections(clarification, store, terminal_history)

    prompt = PROMPT_MULTI.format(
        shell_context=shell_ctx,
        cwd=cwd,
        history=history,
        regen_section=rs,
        clarification_section=cs,
        terminal_history=th,
        user_input=user_input,
    )

    try:
        result = _call_api([{"role": "user", "content": prompt}])
        commands = parse_multi_commands(result)
        if len(commands) >= 3:
            return commands[:3]
        single, _ = get_command(user_input, cwd, store, clarification)
        if single:
            return [Command(cmd=single)]
        return [Command(cmd="echo 'no command generated'")]
    except TimeoutError:
        raise
    except Exception:
        raise


def _show_scout_preview(scout_cmds, skipped):
    print("\033[36mProposed scout commands:\033[0m")
    for i, item in enumerate(scout_cmds, 1):
        status = (
            "\033[31m[skip]\033[0m" if i in skipped else "\033[32m[run]\033[0m"
        )
        if isinstance(item, tuple):
            tool_type, _, value, _ = item
            label = "⚙ bash" if tool_type == "bash" else "📄 read"
            display = f"$ {value}" if tool_type == "bash" else value
        else:
            label = "⚙ bash"
            display = f"$ {item}"
        print(f"  \033[33m{i}\033[0m. {label} {display} {status}")
    print()
    print(
        f"\033[36m[Enter=run-selected r=regen "
        f"1-{len(scout_cmds)}=toggle Esc=cancel]\033[0m"
    )
    return get_single_key()


def get_scout_cmd(user_input, cwd, rejected=""):
    shell_ctx = ensure_shell_context()
    reject_section = (
        f"\nPrevious scout command was rejected: {rejected}" if rejected else ""
    )

    prompt = PROMPT_SCOUT_SINGLE.format(
        shell_context=shell_ctx,
        cwd=cwd,
        reject_section=reject_section,
        user_input=user_input,
    )

    try:
        result = _call_api([{"role": "user", "content": prompt}], max_tokens=100)
        cmd = clean_cmd(result)
        return cmd if cmd else None
    except Exception:
        return None


def _fallback_from_executed(executed, user_input, cwd, store):
    """Generate commands from executed scout output when tool-call flow fails."""
    shell_ctx = ensure_shell_context()
    output_text = "\n\n".join(o for _, o in executed)

    gen_prompt = (
        f"You are a shell command translator. "
        f"Generate exactly 3 different command options.\n\n"
        f"{shell_ctx}\nCurrent directory: {cwd}\n\n"
        f"Scout results:\n{output_text}\n\n"
        f"Format: 1) <command> // <brief description>\n"
        f"Request: {user_input}"
    )

    try:
        return _call_api([{"role": "user", "content": gen_prompt}])
    except Exception:
        return get_commands(user_input, cwd, store, "")


def scout_and_get_commands(user_input, cwd, store):
    shell_ctx = ensure_shell_context()

    system_prompt = (
        f"You are scouting a shell environment.\n"
        f"{shell_ctx}\nCurrent directory: {cwd}\n\n"
        f"Use the available tools to gather context for this request.\n"
        f"All commands must be purely observational / readonly — never change\n"
        f"files, permissions, processes, or system state.\n\n"
        f"Request: {user_input}"
    )
    messages = [{"role": "system", "content": system_prompt}]

    # Step 1: Get model to propose tool calls
    try:
        msg = _call_api_tools(messages, SCOUT_TOOLS)
    except Exception:
        return [Command(cmd="echo 'scout error')")]

    tool_calls = msg.tool_calls or []
    if not tool_calls:
        # Fallback: model returned text instead of tool calls
        if msg.content:
            scout_cmds = [
                c.strip()
                for c in msg.content.strip().split("\n")
                if c.strip() and "sudo" not in c.strip()
            ]
            scout_cmds = [
                c for c in scout_cmds
                if not c.startswith("```") and c != ""
            ][:5]
        else:
            scout_cmds = ["ls -la", "pwd"]
        scout_cmds = [
            ("bash", "bash", c, f"fb_{i}") for i, c in enumerate(scout_cmds)
        ]
    else:
        scout_cmds = []
        for tc in tool_calls:
            fn = tc.function
            if fn.name == "bash":
                try:
                    args = json.loads(fn.arguments)
                    cmd = args.get("command", "").strip()
                except Exception:
                    continue
                if cmd and not _is_blocked_scout(cmd) and "sudo" not in cmd:
                    scout_cmds.append(("bash", fn.name, cmd, tc.id))
            elif fn.name == "read":
                try:
                    args = json.loads(fn.arguments)
                    path = args.get("path", "").strip()
                except Exception:
                    continue
                if path:
                    scout_cmds.append(("read", fn.name, path, tc.id))

    if not scout_cmds:
        return [Command(cmd="echo 'no scout commands'")]

    # Step 1.5: Preview and review
    skipped = set()
    while True:
        key = _show_scout_preview(scout_cmds, skipped)
        if key in ("\r", "\n"):
            break
        elif key == "r":
            try:
                msg = _call_api_tools(messages, SCOUT_TOOLS)
                # Re-parse tool calls... (same logic as above, simplified)
                tcs = msg.tool_calls or []
                if tcs:
                    new_cmds = []
                    for tc in tcs:
                        fn = tc.function
                        if fn.name in ("bash", "read"):
                            try:
                                args = json.loads(fn.arguments)
                                val = args.get(
                                    "command" if fn.name == "bash" else "path",
                                    "",
                                ).strip()
                                if val:
                                    new_cmds.append(
                                        (fn.name, fn.name, val, tc.id)
                                    )
                            except Exception:
                                pass
                    if new_cmds:
                        scout_cmds = new_cmds
                        skipped = set()
            except Exception:
                pass
        elif key == "\x1b":
            print("\033[31mScout cancelled\033[0m")
            return [Command(cmd="echo 'scout cancelled'")]
        elif key.isdigit():
            idx = int(key)
            if 1 <= idx <= len(scout_cmds):
                if idx in skipped:
                    skipped.discard(idx)
                else:
                    skipped.add(idx)

    # Step 2: Execute approved scouts
    executed = []

    for i, (tool_type, tool_name, value, tc_id) in enumerate(scout_cmds, 1):
        label = "⚙ bash" if tool_type == "bash" else "📄 read"
        display = f"$ {value}" if tool_type == "bash" else value

        if i in skipped:
            print(f"  {i}. {label} {display} \033[90m[skipped]\033[0m")
            continue

        if tool_type == "bash" and _is_blocked_scout(value):
            print(f"  {i}. {label} {display} \033[31m[blocked]\033[0m")
            continue

        print(f"  {i}. {label} {display}")
        print(
            "  \033[36m[Enter=run s=skip r=regen Esc=cancel]\033[0m",
            end="", flush=True,
        )
        key = get_single_key()
        print()

        if key == "\x1b":
            print("\033[31mScout cancelled\033[0m")
            break
        elif key in ("s", "S"):
            print("  \033[90m[skipped]\033[0m")
            continue
        elif key in ("r", "R"):
            print("  \033[90m[regenerating...]\033[0m")
            if tool_type == "bash":
                new_cmd = get_scout_cmd(user_input, cwd, value)
                if new_cmd and not _is_blocked_scout(new_cmd):
                    scout_cmds.insert(i, ("bash", "bash", new_cmd, tc_id))
            continue
        elif key in ("\r", "\n"):
            start = time.time()
            args = (
                {"command": value}
                if tool_type == "bash"
                else {"path": value}
            )
            output = _execute_tool(tool_type, args, cwd)
            elapsed = int(time.time() - start)

            # Display result
            status = "\033[32m✓\033[0m" if not output.startswith(
                "[blocked]"
            ) and not output.startswith("(error") and not output.startswith(
                "(timeout"
            ) and not output.startswith(
                "(permission"
            ) and not output.startswith(
                "(file not found"
            ) else "\033[31m✗\033[0m"
            line_count = output.count("\n") + 1 if output else 0
            print(f"  {status} \033[90m{elapsed}s\033[0m", end="")
            if line_count:
                print(f"  \033[90m({line_count} lines)\033[0m")
            else:
                print()
            if output:
                for line in output.split("\n")[:5]:
                    print(f"     \033[90m{line[:100]}\033[0m")

            executed.append((tc_id, output))
        else:
            print("  \033[90m[skipped]\033[0m")
            continue

    if not executed:
        return [Command(cmd="echo 'no scouts executed'")]

    # Step 3: Feed results back and generate final commands
    if tool_calls:
        messages.append(msg)
        for tc_id, output in executed:
            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": output,
            })
        messages.append({
            "role": "user",
            "content": (
                f"Now generate exactly 3 different shell commands for: {user_input}\n"
                f"Format: 1) <command> // <brief description>"
            ),
        })
        try:
            result = _call_api(messages, max_tokens=256)
        except Exception:
            return _fallback_from_executed(executed, user_input, cwd, store)
    else:
        # Fallback: generate from collected output without tool messages
        result = _fallback_from_executed(executed, user_input, cwd, store)
        if isinstance(result, list):
            return result
        # result is string, parse below

    commands = parse_multi_commands(result)
    if len(commands) >= 3:
        return commands[:3]
    single, _ = get_command(user_input, cwd, store, "")
    if single:
        return [Command(cmd=single)]
    return [Command(cmd="echo 'no command generated'")]
