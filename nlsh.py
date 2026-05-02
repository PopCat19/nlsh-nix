#!/usr/bin/env python3
# nlsh.py
#
# Purpose: Natural language shell interface
#
# This module:
# - Translates plain English to shell commands via OpenAI-compatible API
import signal
import os
import sys
import subprocess
import readline

def exit_handler(sig, frame):
    print()
    raise InterruptedError()

signal.signal(signal.SIGINT, exit_handler)

CONFIG_DIR = os.path.expanduser("~/.config/nlsh")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config")

REQUIRED_KEYS = ["NLSH_BASE_URL", "NLSH_MODEL"]

_loaded_from_config = set()

def load_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = value
                        _loaded_from_config.add(key)

def save_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        f.write("# nlsh configuration\n")
        f.write(f"NLSH_API_KEY={os.environ.get('NLSH_API_KEY', '')}\n")
        for key in REQUIRED_KEYS:
            f.write(f"{key}={os.environ.get(key, '')}\n")

def setup_api_key():
    print(f"\n\033[36mOpenAI-compatible API setup\033[0m")
    if is_configured():
        print("\033[33mConfig already set. Press Enter to keep current values.\033[0m\n")
    else:
        print()

    api_key = input("\033[33mAPI key (enter to skip): \033[0m").strip()
    if api_key:
        os.environ["NLSH_API_KEY"] = api_key

    base_url = input(f"\033[33mBase URL [{os.environ.get('NLSH_BASE_URL', '')}]: \033[0m").strip()
    if base_url:
        os.environ["NLSH_BASE_URL"] = base_url
    elif not os.environ.get("NLSH_BASE_URL"):
        print("Base URL required.")
        sys.exit(1)

    model = input(f"\033[33mModel [{os.environ.get('NLSH_MODEL', '')}]: \033[0m").strip()
    if model:
        os.environ["NLSH_MODEL"] = model
    elif not os.environ.get("NLSH_MODEL"):
        print("Model required.")
        sys.exit(1)

    save_config()
    print("\033[32m✓ Config saved!\033[0m\n")

def show_help():
    print("\033[36m!api\033[0m       - Change API key/config")
    print("\033[36m!config\033[0m   - Show current config")
    print("\033[36m!help\033[0m      - Show this help")
    print("\033[36m!cmd <cmd>\033[0m  - Run shell command directly")
    print("\033[36m!quit, !q\033[0m   - Exit")
    print()

def is_configured():
    return all(os.environ.get(k) for k in REQUIRED_KEYS)

def show_config():
    api_key = os.environ.get("NLSH_API_KEY", "")
    masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "(not set)" if not api_key else api_key
    source = "env" if "NLSH_API_KEY" not in _loaded_from_config else "config"
    print(f"\033[36mNLSH_API_KEY:\033[0m {masked} [{source}]")
    for key in REQUIRED_KEYS:
        val = os.environ.get(key, "(not set)")
        source = "env" if key not in _loaded_from_config else "config"
        print(f"\033[36m{key}:\033[0m {val} [{source}]")
    print()

load_config()

def is_configured():
    return all(os.environ.get(k) for k in REQUIRED_KEYS)

first_run = not is_configured()
if first_run:
    setup_api_key()

print(f"\033[1mnlsh\033[0m - model: \033[36m{os.environ.get('NLSH_MODEL', 'unknown')}\033[0m\n")
show_help()

from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("NLSH_API_KEY", ""),
    base_url=os.environ["NLSH_BASE_URL"],
)

command_history = []
MAX_HISTORY = 10
MAX_CONTEXT_CHARS = 4000

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

def get_command(user_input: str, cwd: str) -> str:
    history_context = format_history()
    prompt = f"""You are a shell command translator. Convert the user's request into a shell command for Linux/bash.
Current directory: {cwd}

Recent command history:
{history_context}

Rules:
- Output ONLY the command, nothing else
- No explanations, no markdown, no backticks
- If unclear, make a reasonable assumption
- Prefer simple, common commands
- Use the command history for context (e.g., "do that again", "delete the file I just created")

User request: {user_input}"""

    response = client.chat.completions.create(
        model=os.environ["NLSH_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
    )
    return response.choices[0].message.content.strip()

def is_natural_language(text: str) -> bool:
    if text.startswith("!"):
        return False
    shell_commands = ["ls", "pwd", "clear", "exit", "quit", "whoami", "date", "cal",
                      "top", "htop", "history", "which", "man", "touch", "head", "tail",
                      "grep", "find", "sort", "wc", "diff", "tar", "zip", "unzip"]
    shell_starters = ["cd ", "ls ", "echo ", "cat ", "mkdir ", "rm ", "cp ", "mv ",
                      "git ", "npm ", "node ", "npx ", "python", "pip ", "brew ", "curl ",
                      "wget ", "chmod ", "chown ", "sudo ", "vi ", "vim ", "nano ", "code ",
                      "open ", "export ", "source ", "docker ", "kubectl ", "aws ", "gcloud ",
                      "nix ", "nixos-", "home-manager ", "./", "/", "~", "$", ">", ">>", "|", "&&"]
    if text in shell_commands:
        return False
    return not any(text.startswith(s) for s in shell_starters)

def main():
    while True:
        try:
            cwd = os.getcwd()
            prompt = f"\033[32m{os.path.basename(cwd)}\033[0m > "
            user_input = input(prompt).strip()

            if not user_input:
                continue

            if user_input.startswith("cd "):
                path = os.path.expanduser(user_input[3:].strip())
                try:
                    os.chdir(path)
                except Exception as e:
                    print(f"cd: {e}")
                continue
            elif user_input == "cd":
                os.chdir(os.path.expanduser("~"))
                continue

            if user_input in ("!quit", "!q"):
                print("\033[36mo7\033[0m")
                sys.exit(0)

            if user_input == "!api":
                setup_api_key()
                global client
                client = OpenAI(
                    api_key=os.environ.get("NLSH_API_KEY", ""),
                    base_url=os.environ["NLSH_BASE_URL"],
                )
                continue

            if user_input == "!config":
                show_config()
                continue

            if user_input == "!help":
                show_help()
                continue

            if user_input.startswith("!"):
                cmd = user_input[1:]
                if not cmd:
                    continue
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                print(result.stdout, end="")
                if result.stderr:
                    print(result.stderr, end="")
                add_to_history(cmd, result.stdout + result.stderr)
                continue

            if not is_natural_language(user_input):
                result = subprocess.run(user_input, shell=True, capture_output=True, text=True)
                print(result.stdout, end="")
                if result.stderr:
                    print(result.stderr, end="")
                add_to_history(user_input, result.stdout + result.stderr)
                continue

            command = get_command(user_input, cwd)
            confirm = input(f"\033[33m→ {command}\033[0m [Enter] ")

            if confirm == "":
                if command.startswith("cd "):
                    path = os.path.expanduser(command[3:].strip())
                    try:
                        os.chdir(path)
                    except Exception as e:
                        print(f"cd: {e}")
                else:
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    print(result.stdout, end="")
                    if result.stderr:
                        print(result.stderr, end="")
                    add_to_history(command, result.stdout + result.stderr)

        except EOFError:
            print("\n\033[36mo7\033[0m")
            sys.exit(0)
        except (InterruptedError, KeyboardInterrupt):
            continue
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                print("\033[31mrate limit hit - wait a moment and try again\033[0m")
            elif "InterruptedError" not in err and "KeyboardInterrupt" not in err:
                print(f"\033[31merror: {err[:100]}\033[0m")

if __name__ == "__main__":
    main()