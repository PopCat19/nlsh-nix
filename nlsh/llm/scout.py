# scout.py
#
# Purpose: Model-driven environment scouting before command generation
#
# This module:
# - Uses tool calling to let the model propose exploratory commands
# - Shows preview with toggle/regen before execution
# - Feeds scout results back to generate context-aware commands

import json
import time

from ..types import Command
from ..ui import get_single_key

from .client import _call_api, _call_api_tools
from .generate import get_command, get_commands
from .parsing import clean_cmd, parse_multi_commands
from .prompts import PROMPT_SCOUT_SINGLE, _is_blocked_scout
from .shell import ensure_shell_context
from .tools import SCOUT_TOOLS, _execute_tool

try:
    InterruptedError
except NameError:
    InterruptedError = KeyboardInterrupt  # Python < 3.5 compat


def _show_scout_preview(scout_cmds, skipped):
    print("\033[36mProposed scout commands:\033[0m")
    for i, item in enumerate(scout_cmds, 1):
        status = "\033[31m[skip]\033[0m" if i in skipped else "\033[32m[run]\033[0m"
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
    """Generate commands from executed scout output when tool-call flow fails.

    Always returns List[Command] — never a raw string.
    """
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
        result = _call_api([{"role": "user", "content": gen_prompt}])
        commands = parse_multi_commands(result)
        if commands:
            return commands[:3]
        single, _ = get_command(user_input, cwd, store, "")
        if single:
            return [Command(cmd=single)]
        return [Command(cmd="echo 'no command generated'")]
    except (KeyboardInterrupt, InterruptedError):
        return [Command(cmd="echo 'scout interrupted'")]
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
    except (KeyboardInterrupt, InterruptedError):
        print("\n\033[31mInterrupted\033[0m")
        return [Command(cmd="echo 'scout interrupted'")]
    except Exception:
        return _fallback_from_executed([], user_input, cwd, store)

    tool_calls = msg.tool_calls or []
    if not tool_calls:
        # Fallback: model returned text instead of tool calls
        if msg.content:
            scout_cmds = [
                c.strip()
                for c in msg.content.strip().split("\n")
                if c.strip() and "sudo" not in c.strip()
            ]
            scout_cmds = [c for c in scout_cmds if not c.startswith("```") and c != ""][
                :5
            ]
        else:
            scout_cmds = ["ls -la", "pwd"]
        scout_cmds = [("bash", "bash", c, f"fb_{i}") for i, c in enumerate(scout_cmds)]
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
                                    new_cmds.append((fn.name, fn.name, val, tc.id))
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
            end="",
            flush=True,
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
            args = {"command": value} if tool_type == "bash" else {"path": value}
            output = _execute_tool(tool_type, args, cwd)
            elapsed = int(time.time() - start)

            # Display result
            status = (
                "\033[32m✓\033[0m"
                if not output.startswith("[blocked]")
                and not output.startswith("(error")
                and not output.startswith("(timeout")
                and not output.startswith("(permission")
                and not output.startswith("(file not found")
                else "\033[31m✗\033[0m"
            )
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

    # Step 3: Feed results back and let model decide — more scouting or final commands
    if tool_calls:
        messages.append(msg)
        for tc_id, output in executed:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": output,
                }
            )

        max_scout_rounds = 3
        for _ in range(max_scout_rounds):
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Do you have enough information to generate commands "
                        f"for: {user_input}?\n\n"
                        f"If YES — generate exactly 3 different shell commands:\n"
                        f"Format: 1) <command> // <brief description>\n\n"
                        f"If NO — use the bash or read tools to gather more "
                        f"information (readonly only)."
                    ),
                }
            )
            try:
                msg2 = _call_api_tools(messages, SCOUT_TOOLS, max_tokens=512)
            except (KeyboardInterrupt, InterruptedError):
                print("\n\033[31mInterrupted\033[0m")
                return _fallback_from_executed(executed, user_input, cwd, store)
            except Exception:
                return _fallback_from_executed(executed, user_input, cwd, store)

            more_calls = msg2.tool_calls or []

            if not more_calls:
                # Model has enough info — parse text response
                if msg2 and msg2.content:
                    commands = parse_multi_commands(msg2.content)
                    if len(commands) >= 3:
                        return commands[:3]
                return _fallback_from_executed(executed, user_input, cwd, store)

            # Model wants more scouting — collect proposed commands
            new_scout_cmds = []
            for tc in more_calls:
                fn = tc.function
                if fn.name == "bash":
                    try:
                        args = json.loads(fn.arguments)
                        cmd = args.get("command", "").strip()
                    except Exception:
                        continue
                    if cmd and not _is_blocked_scout(cmd) and "sudo" not in cmd:
                        new_scout_cmds.append(("bash", fn.name, cmd, tc.id))
                elif fn.name == "read":
                    try:
                        args = json.loads(fn.arguments)
                        path = args.get("path", "").strip()
                    except Exception:
                        continue
                    if path:
                        new_scout_cmds.append(("read", fn.name, path, tc.id))

            if not new_scout_cmds:
                return _fallback_from_executed(executed, user_input, cwd, store)

            # Preview and execute with user approval
            print(f"\n\033[36mAdditional scouting:\033[0m")
            skipped = set()
            while True:
                key = _show_scout_preview(new_scout_cmds, skipped)
                if key in ("\r", "\n"):
                    break
                elif key == "r":
                    messages.pop()  # remove the last user message, re-ask model
                    break
                elif key == "\x1b":
                    return _fallback_from_executed(executed, user_input, cwd, store)
                elif key.isdigit():
                    idx = int(key)
                    if 1 <= idx <= len(new_scout_cmds):
                        if idx in skipped:
                            skipped.discard(idx)
                        else:
                            skipped.add(idx)

            if key == "r":
                continue  # re-ask model for better scouts

            # Execute approved scouts
            messages.append(msg2)
            for i, (tool_type, _, value, tc_id) in enumerate(new_scout_cmds, 1):
                if i in skipped:
                    continue
                args = {"command": value} if tool_type == "bash" else {"path": value}
                output = _execute_tool(tool_type, args, cwd)
                label = "⚙ bash" if tool_type == "bash" else "📄 read"
                display = f"$ {value}" if tool_type == "bash" else value
                line_count = output.count("\n") + 1 if output else 0
                status = "\033[32m✓\033[0m" if not output.startswith(("(", "[blocked]")) else "\033[31m✗\033[0m"
                print(f"  {i}. {label} {display} {status} \033[90m({line_count} lines)\033[0m")
                messages.append({"role": "tool", "tool_call_id": tc_id, "content": output})
                executed.append((tc_id, output))
            # Loop back to ask model: enough info or scout more?

    # If no tool_calls from Step 1, or we exhausted scout rounds
    result = _fallback_from_executed(executed, user_input, cwd, store)
    if isinstance(result, list):
        return result

    commands = parse_multi_commands(result)
    if len(commands) >= 3:
        return commands[:3]
    single, _ = get_command(user_input, cwd, store, "")
    if single:
        return [Command(cmd=single)]
    return [Command(cmd="echo 'no command generated'")]
