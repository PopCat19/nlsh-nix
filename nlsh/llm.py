# llm.py
#
# Purpose: LLM API interaction and command generation
#
# This module:
# - Manages OpenAI client
# - Generates shell commands from natural language
# - Gathers shell context (aliases, abbreviations)

import os
import time
import subprocess
import threading

from .ui import get_single_key, AwaitIndicator
import subprocess
from openai import OpenAI
from .ui import AwaitIndicator, TIMEOUT
from .history import format_history, format_regen_history

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

def parse_clarify_response(text: str) -> tuple:
    """Parse CLARIFY response into question and options."""
    lines = text.strip().split('\n')
    question = lines[0].strip() if lines else ""
    options = {}
    
    for line in lines[1:]:
        line = line.strip()
        if line and len(line) > 2 and line[1] == ')':
            key = line[0]
            if key.isdigit():
                options[key] = line[3:].strip()
    
    return (question, options)

def scout_and_get_commands(user_input: str, cwd: str) -> list:
    """Let model scout the environment first, then generate commands."""
    history_context = format_history()
    shell_context = ensure_shell_context()
    
    # Step 1: Ask model what to scout
    scout_prompt = f"""You are scouting a shell environment. What commands should you run to understand the context for this request?

{shell_context}
Current directory: {cwd}

Rules:
- Output ONLY the commands to run, one per line
- NO sudo allowed - skip if needed
- Keep it minimal (2-5 commands max)
- Common scouts: ls, cat, which, find, grep

Request: {user_input}

Output only the scout commands, nothing else:"""
    
    try:
        with AwaitIndicator():
            response = _client.chat.completions.create(
                model=os.environ["NLSH_MODEL"],
                messages=[{"role": "user", "content": scout_prompt}],
                max_tokens=256,
                timeout=TIMEOUT,
            )
        scout_cmds = response.choices[0].message.content.strip().split('\n')
        scout_cmds = [c.strip() for c in scout_cmds if c.strip() and 'sudo' not in c]
        scout_cmds = [c for c in scout_cmds if not c.startswith('```') and not c == '']
        scout_cmds = scout_cmds[:5]  # Max 5
    except:
        scout_cmds = ['ls -la', 'pwd']
    
    # Step 2: Run scout commands with approval
    print(f"\033[36mScouting...\033[0m")
    scout_results = []
    safe_cmds = ['ls', 'cat', 'which', 'pwd', 'grep', 'head', 'tail', 'find .', 'du']
    
    for i, cmd in enumerate(scout_cmds, 1):
        # Block slow/dangerous patterns
        if any(x in cmd for x in ['find /', 'rm', 'dd', 'mkfs', 'sudo', '>']):
            print(f"  {i}. $ {cmd} \033[31m[blocked]\033[0m")
            continue
        
        # Ask for approval
        print(f"  {i}. $ {cmd}")
        print(f"  \033[36m[Enter=run s=skip Esc=cancel]\033[0m")
        key = get_single_key()
        
        if key == '\x1b':  # Esc - cancel scout
            print("\033[33mScout cancelled\033[0m")
            break
        elif key == 's' or key == 'S':  # Skip
            print(f"  {i}. $ {cmd} \033[90m[skipped]\033[0m")
            continue
        elif key == '\r' or key == '\n':  # Run
            print(f"  \033[36m[running] (0s/10s)\033[0m", end='\r')
            start = time.time()
            
            def show_time():
                while True:
                    elapsed = int(time.time() - start)
                    print(f"  \033[36m[running] ({elapsed}s/10s)\033[0m", end='\r')
                    time.sleep(1)
            
            timer = threading.Thread(target=show_time, daemon=True)
            timer.start()
            
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                elapsed = int(time.time() - start)
                print(f"  {i}. $ {cmd} \033[32m({elapsed}s/10s)\033[0m")
                output = (result.stdout + result.stderr)
                if output.strip():
                    print(f"  \033[36m[output]\033[0m")
                    # Show max 20 lines
                    for line in output.strip().split('\n')[:20]:
                        print(f"     {line}")
                # Keep full output for LLM
                scout_results.append(f"$ {cmd}\n{output[:500]}")
            except subprocess.TimeoutExpired:
                print(f"  {i}. $ {cmd} \033[31m[timeout]\033[0m")
        else:
            print(f"  {i}. $ {cmd} \033[90m[skipped]\033[0m")
            continue
    
    # Step 3: Generate commands with scout context
    scout_context = "\n\n".join(scout_results)
    
    prompt = f"""You are a shell command translator. Generate exactly 3 different command options for the user's request.

{shell_context}
Current directory: {cwd}

Scout results:
{scout_context}

Rules:
- Output exactly 3 commands, one per line, numbered 1-3
- Include a very brief description after // (max 5 words)
- Each command should be a different approach
- No markdown, no backticks
- Format: 1) <command> // <5 word max>
- Prefer simple, common commands

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
        
        commands = []
        for line in result.split('\n'):
            line = line.strip()
            if line and len(line) > 2:
                if line[0].isdigit() and line[1] in ') .':
                    rest = line[2:].strip()
                    if '//' in rest:
                        cmd, desc = rest.split('//', 1)
                        commands.append((cmd.strip(), desc.strip()))
                    else:
                        commands.append((rest.strip(), ""))
        
        if len(commands) >= 3:
            return commands[:3]
        
        # Fallback
        single = get_command(user_input, cwd, "")
        if single and single[0]:
            return [(single[0], "")]
        return [("echo 'no command generated'", "")]
        
    except TimeoutError:
        raise
    except Exception as e:
        raise

def get_commands(user_input: str, cwd: str, clarification: str = "") -> list:
    """Generate 3 command options with descriptions for the user request."""
    history_context = format_history()
    shell_context = ensure_shell_context()
    regen_context = format_regen_history()
    
    clarification_section = f"\n\nClarification: {clarification}" if clarification else ""
    regen_section = f"\n\nPrevious attempts:\n{regen_context}" if regen_context != "No previous attempts." else ""
    
    prompt = f"""You are a shell command translator. Generate exactly 3 different command options for the user's request.

{shell_context}
Current directory: {cwd}

Recent command history:
{history_context}{regen_section}{clarification_section}

Rules:
- Output exactly 3 commands, one per line, numbered 1-3
- Include a very brief description after // (max 5 words)
- Each command should be a different approach
- No markdown, no backticks
- Format: 1) <command> // <5 word max>
- Learn from previous attempts
- Prefer simple, common commands

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
        
        # Parse numbered commands with descriptions
        commands = []
        for line in result.split('\n'):
            line = line.strip()
            if line and len(line) > 2:
                if line[0].isdigit() and line[1] in ') .':
                    rest = line[2:].strip()
                    # Split on // for description
                    if '//' in rest:
                        cmd, desc = rest.split('//', 1)
                        commands.append((cmd.strip(), desc.strip()))
                    else:
                        commands.append((rest.strip(), ""))
        
        if len(commands) >= 3:
            return commands[:3]
        
        # Fallback
        single = get_command(user_input, cwd, clarification)
        if single and single[0]:
            return [(single[0], "")]
        return [("echo 'no command generated'", "")]
        
    except TimeoutError:
        raise
    except Exception as e:
        raise

def get_command(user_input: str, cwd: str, clarification: str = "") -> tuple:
    history_context = format_history()
    shell_context = ensure_shell_context()
    regen_context = format_regen_history()
    
    clarification_section = f"\n\nClarification: {clarification}" if clarification else ""
    regen_section = f"\n\nPrevious attempts:\n{regen_context}" if regen_context != "No previous attempts." else ""
    
    prompt = f"""You are a shell command translator. Convert the user's request into a shell command.

{shell_context}
Current directory: {cwd}

Recent command history:
{history_context}{regen_section}{clarification_section}

Rules:
- Output ONLY the command, nothing else
- No explanations, no markdown, no backticks
- If the request is ambiguous or vague, respond with: CLARIFY: <question>\n  1) <option 1>\n  2) <option 2>\n  ...\n  0) custom (describe what you want)
- Learn from previous attempts - if a similar command was rejected, try a different approach
- Otherwise, make a reasonable assumption
- Prefer simple, common commands
- Prefer using available aliases/abbreviations when they match

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
            clarify_text = result[clarify_idx + 8:].strip()
            question, options = parse_clarify_response(clarify_text)
            return (None, (question, options))
        return (result, None)
        return (result, None)
    except Exception as e:
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            raise TimeoutError("Request timed out")
        raise