# generate.py
#
# Purpose: Shell command generation from natural language
#
# This module:
# - Builds prompt sections from clarification, history, and terminal context
# - Generates single or multiple command proposals via LLM

from ..types import Command

from .client import _call_api
from .parsing import clean_cmd, parse_multi_commands, parse_clarify_response
from .prompts import PROMPT_SINGLE, PROMPT_MULTI
from .shell import ensure_shell_context


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
