# main.py
#
# Purpose: Entry point and main application loop
#
# This module:
# - Handles one-shot and REPL modes
# - Processes user input and command execution

import signal
import os
import sys
import subprocess
import threading
import time

from .config import load_config, is_configured, setup_api_key, config_menu, is_loaded_from_config
from .llm import init_client, reinit_client, get_command, get_commands, scout_and_get_commands
from .history import add_to_history, reset_regen_history, add_regen
from .ui import get_single_key, show_help, show_config, raw_input

SHELL = os.environ.get('SHELL', '/bin/sh')

def run_cmd(cmd: str) -> int:
    """Run command through user's shell, show running indicator."""
    print(f"\033[36m[running] (0s)\033[0m", end="\r")
    start = time.time()
    
    def show_time():
        while True:
            elapsed = int(time.time() - start)
            print(f"\033[36m[running] ({elapsed}s)\033[0m", end="\r")
            time.sleep(1)
    
    timer = threading.Thread(target=show_time, daemon=True)
    timer.start()
    
    result = os.system(cmd)
    print(" " * 30, end="\r")  # Clear running indicator
    return result

def exit_handler(sig, frame):
    print()
    raise InterruptedError()

signal.signal(signal.SIGINT, exit_handler)

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

def safe_input(prompt: str) -> str:
    """Input that handles ESC/Ctrl+C gracefully."""
    return raw_input(prompt)

def prompt_clarify(question: str, options: dict) -> str:
    """Show clarification question with options and get user response."""
    print(f"\033[36m{question}\033[0m")
    for key in sorted(options.keys()):
        print(f"  \033[33m{key}\033[0m) {options[key]}")
    print()
    
    answer = safe_input("\033[33mSelect 1-0, or type answer: \033[0m")
    if not answer:
        return ""
    
    if answer in options:
        if answer == '0' and 'custom' in options.get('0', '').lower():
            custom = safe_input("\033[33mDescribe: \033[0m")
            return custom
        return options[answer]
    return answer

def show_ask_options():
    print("\033[36mWhat do you want?\033[0m")
    print("  \033[33m1\033[0m) Clarify the request")
    print("  \033[33m2\033[0m) A different command")
    print("  \033[33m3\033[0m) Modify this command")
    print("  \033[33m4\033[0m) Safer/alternative approach")
    print("  \033[33m5\033[0m) Something completely different")
    print("  \033[33m0\033[0m) Custom description")
    print("  \033[33mEsc\033[0m) Cancel")
    print()

def confirm_run(cmd: str) -> bool:
    """Ask for confirmation before running, warn if sudo."""
    if 'sudo' in cmd:
        print(f"\033[31m⚠ sudo: {cmd}\033[0m")
        print("\033[36m[Enter=run c=copy Esc=cancel]\033[0m")
    else:
        print(f"\033[33m→ {cmd}\033[0m")
        print("\033[36m[Enter=run c=copy Esc=cancel]\033[0m")
    
    key = get_single_key()
    if key == 'c':
        # Try wl-copy first (Wayland), then xclip (X11)
        import shutil
        if shutil.which('wl-copy'):
            os.system(f"echo '{cmd}' | wl-copy")
            print("\033[32m✓ copied to clipboard\033[0m")
        elif shutil.which('xclip'):
            os.system(f"echo '{cmd}' | xclip -selection clipboard")
            print("\033[32m✓ copied to clipboard\033[0m")
        elif shutil.which('xsel'):
            os.system(f"echo '{cmd}' | xsel --clipboard --input")
            print("\033[32m✓ copied to clipboard\033[0m")
        else:
            print("\033[31mno clipboard tool found (wl-copy/xclip/xsel)\033[0m")
        return False
    return key == '\r' or key == '\n'

def get_cmd(item):
    """Extract command from tuple or string."""
    return item[0] if isinstance(item, tuple) else item

def show_gen_options(commands: list):
    print("\033[36mGenerated commands:\033[0m")
    for i, item in enumerate(commands, 1):
        if isinstance(item, tuple):
            cmd, desc = item
            if desc:
                print(f"  \033[33m{i}\033[0m) \033[90m{desc}\033[0m")
                print(f"  ↳ {cmd}")
            else:
                print(f"  \033[33m{i}\033[0m) {cmd}")
        else:
            print(f"  \033[33m{i}\033[0m) {item}")
    print()

def run_oneshot(args: str):
    cwd = os.getcwd()
    reset_regen_history()
    
    try:
        commands = get_commands(args, cwd)
    except TimeoutError:
        print("\033[31mtimed out\033[0m")
        sys.exit(1)
    except Exception as e:
        print(f"\033[31merror: {e}\033[0m")
        sys.exit(1)
    
    command = get_cmd(commands[0])  # Default to first
    add_regen(command)
    
    regen_count = 0
    clarification = ""
    
    while True:
        show_gen_options(commands)
        regen_str = f" (regen {regen_count})" if regen_count > 0 else ""
        print(f"\033[36m[Enter=1 2-3=select s=scout r=regen a=ask Esc=cancel]{regen_str}\033[0m")
        key = get_single_key()
        
        if key == '\r' or key == '\n' or key == '1':
            if confirm_run(get_cmd(commands[0])):
                run_cmd(get_cmd(commands[0]))
            sys.exit(0)
        elif key == '2':
            if confirm_run(get_cmd(commands[1])):
                run_cmd(get_cmd(commands[1]))
            sys.exit(0)
        elif key == '3':
            if confirm_run(get_cmd(commands[2])):
                run_cmd(get_cmd(commands[2]))
            sys.exit(0)
        elif key == 's':
            try:
                print()
                commands = scout_and_get_commands(args, cwd)
                command = get_cmd(commands[0])
                clarification = ""
                regen_count = 0
            except TimeoutError:
                print("\033[31mtimed out\033[0m")
            except Exception as e:
                print(f"\033[31merror: {e}\033[0m")
        elif key == 'r':
            try:
                commands = get_commands(args, cwd, clarification)
                command = get_cmd(commands[0])
                add_regen(command, clarification)
                regen_count += 1
            except TimeoutError:
                print("\033[31mtimed out\033[0m")
            except Exception as e:
                print(f"\033[31merror: {e}\033[0m")
        elif key == 'a':
            show_ask_options()
            choice = get_single_key()
            if choice == '\x1b':
                continue
            elif choice == '0':
                custom = safe_input("\033[33mDescribe: \033[0m")
                if custom:
                    clarification = f"{clarification} {custom}".strip() if clarification else custom
                else:
                    continue
            elif choice == '1':
                clarify = safe_input("\033[33mClarify: \033[0m")
                if clarify:
                    clarification = f"{clarification} clarify: {clarify}".strip()
                else:
                    continue
            elif choice == '2':
                clarification = f"{clarification} generate a different command".strip()
            elif choice == '3':
                changes = safe_input("\033[33mDescribe changes: \033[0m")
                if changes:
                    clarification = f"{clarification} modify: {changes}".strip()
                else:
                    continue
            elif choice == '4':
                clarification = f"{clarification} generate a safer alternative".strip()
            elif choice == '5':
                new_req = safe_input("\033[33mNew request: \033[0m")
                if new_req:
                    args = new_req
                    reset_regen_history()
                    clarification = ""
                else:
                    continue
            else:
                continue
            try:
                commands = get_commands(args, cwd, clarification)
                command = get_cmd(commands[0])
                add_regen(command, clarification)
                regen_count += 1
            except TimeoutError:
                print("\033[31mtimed out\033[0m")
            except Exception as e:
                print(f"\033[31merror: {e}\033[0m")
        elif key == '\x1b':
            sys.exit(0)
        else:
            sys.exit(0)

def run_repl():
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
                reinit_client()
                continue

            if user_input == "!config":
                show_config(is_loaded_from_config)
                continue

            if user_input == "!help":
                show_help()
                continue

            if user_input.startswith("!"):
                cmd = user_input[1:]
                if not cmd:
                    continue
                if confirm_run(cmd):
                    run_cmd(cmd)
                    add_to_history(cmd, "")
                continue

            if not is_natural_language(user_input):
                if confirm_run(user_input):
                    run_cmd(user_input)
                    add_to_history(user_input, "")
                continue

            try:
                reset_regen_history()
                result, clarify_data = get_command(user_input, cwd)
                if clarify_data:
                    question, options = clarify_data
                    clarification = prompt_clarify(question, options)
                    result, _ = get_command(user_input, cwd, clarification)
                command = result
                add_regen(command)
            except TimeoutError:
                print("\033[31mtimed out\033[0m")
                continue
            except Exception as e:
                print(f"\033[31merror: {e}\033[0m")
                continue

            regen_count = 0
            clarification = ""
            while True:
                if 'sudo' in command:
                    print(f"\033[31m⚠ sudo: {command}\033[0m")
                else:
                    print(f"\033[33m→ {command}\033[0m")
                regen_str = f" (regen {regen_count})" if regen_count > 0 else ""
                print(f"\033[36m[Enter=run r=regen a=ask Esc=cancel]{regen_str}\033[0m")
                key = get_single_key()
                
                if key == '\r' or key == '\n':
                    if command.startswith("cd "):
                        path = os.path.expanduser(command[3:].strip())
                        try:
                            os.chdir(path)
                        except Exception as e:
                            print(f"cd: {e}")
                    else:
                        run_cmd(command)
                        add_to_history(command, "")
                    print()
                    break
                elif key == 'r':
                    try:
                        result, clarify_data = get_command(user_input, cwd, clarification)
                        if clarify_data:
                            question, options = clarify_data
                            answer = prompt_clarify(question, options)
                            if answer:
                                clarification = f"{clarification} {answer}".strip() if clarification else answer
                            result, _ = get_command(user_input, cwd, clarification)
                        command = result
                        add_regen(command, clarification)
                        regen_count += 1
                    except TimeoutError:
                        print("\033[31mtimed out - press r to retry\033[0m")
                    except Exception as e:
                        print(f"\033[31merror: {e}\033[0m")
                elif key == 'a':
                    show_ask_options()
                    choice = get_single_key()
                    if choice == '\x1b':
                        continue
                    elif choice == '0':
                        custom = safe_input("\033[33mDescribe: \033[0m")
                        if custom:
                            clarification = f"{clarification} {custom}".strip() if clarification else custom
                        else:
                            continue
                    elif choice == '1':
                        clarify = safe_input("\033[33mClarify: \033[0m")
                        if clarify:
                            clarification = f"{clarification} clarify: {clarify}".strip()
                        else:
                            continue
                    elif choice == '2':
                        clarification = f"{clarification} generate a different command".strip()
                    elif choice == '3':
                        changes = safe_input("\033[33mDescribe changes: \033[0m")
                        if changes:
                            clarification = f"{clarification} modify: {changes}".strip()
                        else:
                            continue
                    elif choice == '4':
                        clarification = f"{clarification} generate a safer alternative".strip()
                    elif choice == '5':
                        new_req = safe_input("\033[33mNew request: \033[0m")
                        if new_req:
                            user_input = new_req
                            reset_regen_history()
                            clarification = ""
                        else:
                            continue
                    else:
                        continue
                    try:
                        result, _ = get_command(user_input, cwd, clarification)
                        if result:
                            command = result
                            add_regen(command, clarification)
                            regen_count += 1
                        else:
                            print("\033[31mNo command generated\033[0m")
                    except TimeoutError:
                        print("\033[31mtimed out\033[0m")
                    except Exception as e:
                        print(f"\033[31merror: {e}\033[0m")
                elif key == '\x1b':
                    print()
                    break
                else:
                    print()
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

def main():
    load_config()
    
    first_run = not is_configured()
    if first_run:
        setup_api_key()
    
    from . import VERSION, DATE
    print(f"\033[1mnlsh\033[0m {VERSION} ({DATE}) - model: \033[36m{os.environ.get('NLSH_MODEL', 'unknown')}\033[0m")
    
    init_client()
    
    args = ' '.join(sys.argv[1:])
    if args:
        print()
        run_oneshot(args)
    else:
        print("\n")
        show_help()
        run_repl()