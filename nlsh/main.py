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

from .config import load_config, is_configured, setup_api_key, config_menu, is_loaded_from_config
from .llm import init_client, reinit_client, get_command
from .history import add_to_history
from .ui import get_single_key, show_help, show_config

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

def prompt_clarify(question: str, options: dict) -> str:
    """Show clarification question with options and get user response."""
    print(f"\033[36m{question}\033[0m")
    for key, desc in options.items():
        print(f"  \033[33m{key}\033[0m) {desc}")
    print()
    
    answer = input("\033[33mSelect or type answer: \033[0m").strip().lower()
    
    if len(answer) == 1 and answer in options:
        if answer == 'z' and 'custom' in options.get('z', '').lower():
            custom = input("\033[33mDescribe: \033[0m").strip()
            return custom
        return options[answer]
    return answer

def run_oneshot(args: str):
    cwd = os.getcwd()
    result, clarify_data = get_command(args, cwd)
    if clarify_data:
        question, options = clarify_data
        clarification = prompt_clarify(question, options)
        result, _ = get_command(args, cwd, clarification)
    command = result
    
    regen_count = 0
    clarification = ""
    
    while True:
        print(f"\033[33m→ {command}\033[0m")
        regen_str = f" (regen {regen_count})" if regen_count > 0 else ""
        print(f"\033[36m[Enter=run r=regen c=clarify Esc=cancel]{regen_str}\033[0m")
        key = get_single_key()
        
        if key == '\r' or key == '\n':
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="")
            sys.exit(0)
        elif key == 'r':
            result, clarify_data = get_command(args, cwd, clarification)
            if clarify_data:
                question, options = clarify_data
                answer = prompt_clarify(question, options)
                if answer:
                    clarification = f"{clarification} {answer}".strip() if clarification else answer
                result, _ = get_command(args, cwd, clarification)
            command = result
            regen_count += 1
        elif key == 'c':
            clarification = input("\033[33mClarify: \033[0m").strip()
            result, _ = get_command(args, cwd, clarification)
            command = result
            regen_count += 1
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
                result, clarify_data = get_command(user_input, cwd)
                if clarify_data:
                    question, options = clarify_data
                    clarification = prompt_clarify(question, options)
                    result, _ = get_command(user_input, cwd, clarification)
                command = result
            except TimeoutError:
                print("\033[31mtimed out\033[0m")
                continue
            except Exception as e:
                print(f"\033[31merror: {e}\033[0m")
                continue

            regen_count = 0
            clarification = ""
            while True:
                print(f"\033[33m→ {command}\033[0m")
                regen_str = f" (regen {regen_count})" if regen_count > 0 else ""
                print(f"\033[36m[Enter=run r=regen c=clarify Esc=cancel]{regen_str}\033[0m")
                key = get_single_key()
                
                if key == '\r' or key == '\n':
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
                        regen_count += 1
                    except TimeoutError:
                        print("\033[31mtimed out - press r to retry\033[0m")
                    except Exception as e:
                        print(f"\033[31merror: {e}\033[0m")
                elif key == 'c':
                    clarification = input("\033[33mClarify: \033[0m").strip()
                    try:
                        result, _ = get_command(user_input, cwd, clarification)
                        command = result
                        regen_count += 1
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
    print(f"\033[1mnlsh\033[0m {VERSION} ({DATE}) - model: \033[36m{os.environ.get('NLSH_MODEL', 'unknown')}\033[0m\n")
    show_help()
    
    init_client()
    
    args = ' '.join(sys.argv[1:])
    if args:
        run_oneshot(args)
    else:
        run_repl()