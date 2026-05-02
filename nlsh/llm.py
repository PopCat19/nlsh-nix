# llm.py
#
# Purpose: LLM API interaction and command generation
#
# This module:
# - Manages OpenAI client
# - Generates shell commands from natural language
# - Gathers shell context (aliases, abbreviations)

import os
import subprocess
from openai import OpenAI
from .ui import AwaitIndicator, TIMEOUT
from .history import format_history

_client = None
_shell_context = None

def init_client():
    global _client
    _client = OpenAI(
        api_key=os.environ.get("NLSH_API_KEY", ""),
        base_url=os.environ["NLSH_BASE_URL"],
    )

def reinit_client():
    global _client
    _client = OpenAI(
        api_key=os.environ.get("NLSH_API_KEY", ""),
        base_url=os.environ["NLSH_BASE_URL"],
    )

def get_shell_context() -> str:
    shell = os.environ.get('SHELL', '/bin/bash')
    lines = [f"Shell: {shell}"]
    
    if 'fish' in shell:
        try:
            result = subprocess.run(['fish', '-c', 'abbr --show'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                abbrs = [l for l in result.stdout.strip().split('\n')[:10] if l]
                if abbrs:
                    lines.append("Fish abbreviations:")
                    lines.extend(abbrs[:10])
        except:
            pass
    else:
        try:
            result = subprocess.run([shell, '-ic', 'alias'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                aliases = [l for l in result.stdout.strip().split('\n')[:10] if l and not l.startswith('#')]
                if aliases:
                    lines.append("Aliases:")
                    lines.extend(aliases[:10])
        except:
            pass
    
    return '\n'.join(lines)

def ensure_shell_context():
    global _shell_context
    if _shell_context is None:
        _shell_context = get_shell_context()
    return _shell_context

def get_command(user_input: str, cwd: str, clarification: str = "") -> tuple:
    history_context = format_history()
    shell_context = ensure_shell_context()
    
    clarification_section = f"\n\nClarification: {clarification}" if clarification else ""
    
    prompt = f"""You are a shell command translator. Convert the user's request into a shell command.

{shell_context}
Current directory: {cwd}

Recent command history:
{history_context}

Rules:
- Output ONLY the command, nothing else
- No explanations, no markdown, no backticks
- If the request is ambiguous or vague, respond with: CLARIFY: <your question>
- Otherwise, make a reasonable assumption
- Prefer simple, common commands
- Prefer using available aliases/abbreviations when they match
- Use the command history for context (e.g., "do that again", "delete the file I just created"){clarification_section}

User request: {user_input}"""

    try:
        with AwaitIndicator():
            response = _client.chat.completions.create(
                model=os.environ["NLSH_MODEL"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                timeout=TIMEOUT,
            )
        result = response.choices[0].message.content.strip()
        
        # Check if model is asking for clarification (may be after command)
        if "\nCLARIFY:" in result or result.startswith("CLARIFY:"):
            clarify_idx = result.find("CLARIFY:")
            clarify_q = result[clarify_idx + 8:].strip()
            return (None, clarify_q)
        return (result, None)
    except Exception as e:
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            raise TimeoutError("Request timed out")
        raise