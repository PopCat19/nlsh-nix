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
import tty
import termios
import threading
import time

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
    """First-run setup - requires base URL and model."""
    print(f"\n\033[36mOpenAI-compatible API setup\033[0m\n")

    while not os.environ.get("NLSH_BASE_URL"):
        base_url = input("\033[33mBase URL: \033[0m").strip()
        if base_url:
            os.environ["NLSH_BASE_URL"] = base_url
        else:
            print("Base URL required.")

    while not os.environ.get("NLSH_MODEL"):
        model = input("\033[33mModel: \033[0m").strip()
        if model:
            os.environ["NLSH_MODEL"] = model
        else:
            print("Model required.")

    api_key = input("\033[33mAPI key (enter to skip): \033[0m").strip()
    if api_key:
        os.environ["NLSH_API_KEY"] = api_key

    save_config()
    print("\033[32m✓ Config saved!\033[0m\n")

def config_menu():
    """Interactive menu to set individual config options."""
    # Save original values for cancel
    original = {
        'NLSH_BASE_URL': os.environ.get('NLSH_BASE_URL', ''),
        'NLSH_MODEL': os.environ.get('NLSH_MODEL', ''),
        'NLSH_API_KEY': os.environ.get('NLSH_API_KEY', ''),
    }
    
    while True:
        print("\033[36m!api menu\033[0m")
        print(f"  \033[33m1\033[0m Base URL: {os.environ.get('NLSH_BASE_URL', '(not set)')}")
        print(f"  \033[33m2\033[0m Model: {os.environ.get('NLSH_MODEL', '(not set)')}")
        api_key = os.environ.get('NLSH_API_KEY', '')
        masked = api_key[:8] + '...' + api_key[-4:] if len(api_key) > 12 else api_key or '(not set)'
        print(f"  \033[33m3\033[0m API key: {masked}")
        print("  \033[33ms\033[0m Save & exit")
        print("  \033[33mc\033[0m Cancel")
        print()
        
        choice = input("\033[33mSelect: \033[0m").strip().lower()
        
        if choice == "1":
            current = os.environ.get('NLSH_BASE_URL', '')
            val = input(f"\033[33mBase URL [{current}]: \033[0m").strip()
            if val:
                os.environ['NLSH_BASE_URL'] = val
                print("\033[36m(staged)\033[0m")
        elif choice == "2":
            current = os.environ.get('NLSH_MODEL', '')
            val = input(f"\033[33mModel [{current}]: \033[0m").strip()
            if val:
                os.environ['NLSH_MODEL'] = val
                print("\033[36m(staged)\033[0m")
        elif choice == "3":
            val = input("\033[33mAPI key: \033[0m").strip()
            if val:
                os.environ['NLSH_API_KEY'] = val
                print("\033[36m(staged)\033[0m")
            elif input("\033[33mClear API key? [y/N] \033[0m").strip().lower() == "y":
                os.environ['NLSH_API_KEY'] = ''
                print("\033[36m(staged - cleared)\033[0m")
        elif choice == "s":
            save_config()
            print("\033[32m✓ Saved\033[0m\n")
            break
        elif choice == "c":
            # Restore original values
            for key, val in original.items():
                if val:
                    os.environ[key] = val
                else:
                    os.environ.pop(key, None)
            print("\033[33m✗ Cancelled\033[0m\n")
            break
        else:
            print("\033[31mInvalid option\033[0m")

TIMEOUT = 30

def get_single_key():
    """Read a single keypress without requiring Enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        # Handle escape sequences (arrow keys, etc)
        if ch == '\x1b':
            ch += sys.stdin.read(2)  # Read rest of escape sequence
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

class AwaitIndicator:
    """Show elapsed time while awaiting response."""
    def __init__(self, timeout: int = TIMEOUT):
        self.timeout = timeout
        self.start_time = None
        self.stop_event = None
        self.thread = None

    def __enter__(self):
        self.start_time = time.time()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._tick)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop_event.set()
        self.thread.join()
        # Clear the line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _tick(self):
        while not self.stop_event.is_set():
            elapsed = int(time.time() - self.start_time)
            sys.stdout.write(f"\r\033[33m[awaiting API response...] ({elapsed}s/{self.timeout}s)\033[0m")
            sys.stdout.flush()
            time.sleep(0.1)
            if elapsed >= self.timeout:
                break

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

_version = "@VERSION@"
_date = "@DATE@"[:8]  # YYYYMMDD
print(f"\033[1mnlsh\033[0m {_version} ({_date}) - model: \033[36m{os.environ.get('NLSH_MODEL', 'unknown')}\033[0m\n")
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

    try:
        with AwaitIndicator():
            response = client.chat.completions.create(
                model=os.environ["NLSH_MODEL"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                timeout=TIMEOUT,
            )
        return response.choices[0].message.content.strip()
    except Exception as e:
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            raise TimeoutError("Request timed out")
        raise

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
    # Handle command-line args (one-shot mode)
    args = ' '.join(sys.argv[1:])
    if args:
        cwd = os.getcwd()
        command = get_command(args, cwd)
        print(f"\033[33m→ {command}\033[0m")
        print("\033[36m[Enter=run r=regen Esc=cancel]\033[0m")
        key = get_single_key()
        if key == '\r' or key == '\n':  # Enter
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="")
        elif key == 'r':
            command = get_command(args, cwd)
            print(f"\033[33m→ {command}\033[0m")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="")
        # ESC or anything else: cancel (exit silently)
        sys.exit(0)

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
                config_menu()
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

            try:
                command = get_command(user_input, cwd)
            except TimeoutError:
                print("\033[31mtimed out\033[0m")
                continue
            except Exception as e:
                print(f"\033[31merror: {e}\033[0m")
                continue

            while True:
                print(f"\033[33m→ {command}\033[0m \033[36m[Enter=run r=regen Esc=cancel]\033[0m")
                key = get_single_key()
                
                if key == '\r' or key == '\n':  # Enter
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
                    print()  # Newline after output
                    break
                elif key == 'r':
                    try:
                        command = get_command(user_input, cwd)
                    except TimeoutError:
                        print("\033[31mtimed out - press r to retry\033[0m")
                    except Exception as e:
                        print(f"\033[31merror: {e}\033[0m")
                elif key == '\x1b':  # ESC
                    print()  # Newline for clean exit
                    break
                else:
                    print()  # Newline for unknown key
                    break

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