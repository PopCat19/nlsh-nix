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

try:
    import readline
except ImportError:
    pass

from .config import Config, setup_wizard, config_menu
from .history import HistoryStore
from .llm import init_client, reinit_client, get_command, get_commands, get_shell_history, scout_and_get_commands
from .ui import get_single_key, raw_input, show_help, show_config, show_gen_options, show_ask_options, prompt_clarify, show_history_approval
from .util import copy_to_clipboard, clipboard_read, edit_in_editor
from .types import Command


# --- Command Execution ---

def run_cmd(cmd, store):
    print(f"\033[36m[running] (0s)\033[0m", end="\r")
    start = time.time()
    stop_event = threading.Event()
    output_parts = []

    def show_time():
        while not stop_event.is_set():
            elapsed = int(time.time() - start)
            print(f"\033[36m[running] ({elapsed}s)\033[0m", end="\r")
            time.sleep(0.5)

    timer = threading.Thread(target=show_time, daemon=True)
    timer.start()

    ret = 1
    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            output_parts.append(line)
        proc.wait()
        ret = proc.returncode
    except Exception as e:
        sys.stdout.write(f"\nerror: {e}\n")

    stop_event.set()
    time.sleep(0.1)
    print(" " * 30, end="\r")

    output = "".join(output_parts)
    store.add_command(cmd, output[:2000])
    return ret


# --- Input Classification ---

def is_natural_language(text: str) -> bool:
    if text.startswith("!"):
        return False
    shell_commands = [
        "ls", "pwd", "clear", "exit", "quit", "whoami", "date", "cal",
        "top", "htop", "history", "which", "man", "touch", "head", "tail",
        "grep", "find", "sort", "wc", "diff", "tar", "zip", "unzip",
    ]
    shell_starters = [
        "cd ", "ls ", "echo ", "cat ", "mkdir ", "rm ", "cp ", "mv ",
        "git ", "npm ", "node ", "npx ", "python", "pip ", "brew ", "curl ",
        "wget ", "chmod ", "chown ", "sudo ", "vi ", "vim ", "nano ", "code ",
        "open ", "export ", "source ", "docker ", "kubectl ", "aws ", "gcloud ",
        "nix ", "nixos-", "home-manager ", "./", "/", "~", "$", ">", ">>", "|", "&&",
    ]
    if text in shell_commands:
        return False
    return not any(text.startswith(s) for s in shell_starters)


# --- Confirmation ---

def confirm_run(cmd: str) -> bool:
    if "sudo" in cmd:
        print(f"\033[31m⚠ sudo: {cmd}\033[0m")
    else:
        print(f"\033[33m→ {cmd}\033[0m")
    print("\033[36m[Enter=run c=copy Esc=cancel]\033[0m")

    key = get_single_key()
    if key == "c":
        if copy_to_clipboard(cmd):
            print("\033[32m✓ copied to clipboard\033[0m")
        else:
            print("\033[31mno clipboard tool found (wl-copy/xclip/xsel)\033[0m")
        return False
        return False
    return key in ("\r", "\n")


# --- Signal Handling ---

def exit_handler(sig, frame):
    print()
    raise InterruptedError()

signal.signal(signal.SIGINT, exit_handler)


# --- Ask Menu Handler ---

def _handle_ask(choice, clarification, user_input):
    if choice == "0":
        custom = raw_input("\033[33mDescribe: \033[0m")
        if not custom:
            return user_input, clarification, False
        clarification = (
            f"{clarification} {custom}".strip() if clarification else custom
        )
        return user_input, clarification, False
    elif choice == "1":
        clarify = raw_input("\033[33mClarify: \033[0m")
        if not clarify:
            return user_input, clarification, False
        clarification = f"{clarification} clarify: {clarify}".strip()
        return user_input, clarification, False
    elif choice == "2":
        clarification = f"{clarification} generate a different command".strip()
        return user_input, clarification, False
    elif choice == "3":
        changes = raw_input("\033[33mDescribe changes: \033[0m")
        if not changes:
            return user_input, clarification, False
        clarification = f"{clarification} modify: {changes}".strip()
        return user_input, clarification, False
    elif choice == "4":
        clarification = f"{clarification} generate a safer alternative".strip()
        return user_input, clarification, False
    elif choice == "5":
        new_req = raw_input("\033[33mNew request: \033[0m")
        if not new_req:
            return user_input, clarification, False
        return new_req, "", True
    return user_input, clarification, False


# --- Shared Command Selection Loop ---

def _command_selection(
    user_input, cwd, commands, store, config,
    clarification="", regen_count=0,
):
    while True:
        show_gen_options(commands)
        regen_str = f" (regen {regen_count})" if regen_count > 0 else ""
        print(
            f"\033[36m[Enter=1 2-3=select s=scout r=regen a=ask h=hist Esc=cancel]"
            f"{regen_str}\033[0m"
        )
        key = get_single_key()

        if key in ("\r", "\n", "1"):
            if confirm_run(commands[0].cmd):
                run_cmd(commands[0].cmd, store)
            return

        elif key == "2":
            if len(commands) > 1 and confirm_run(commands[1].cmd):
                run_cmd(commands[1].cmd, store)
            return

        elif key == "3":
            if len(commands) > 2 and confirm_run(commands[2].cmd):
                run_cmd(commands[2].cmd, store)
            return

        elif key == "s":
            try:
                print()
                commands = scout_and_get_commands(user_input, cwd, store)
                clarification = ""
                regen_count = 0
            except TimeoutError:
                print("\033[31mtimed out\033[0m")
            except Exception as e:
                print(f"\033[31merror: {e}\033[0m")

        elif key == "r":
            try:
                commands = get_commands(user_input, cwd, store, clarification)
                store.add_regen(commands[0].cmd, clarification)
                regen_count += 1
            except TimeoutError:
                print("\033[31mtimed out\033[0m")
            except Exception as e:
                print(f"\033[31merror: {e}\033[0m")

        elif key == "a":
            show_ask_options()
            choice = get_single_key()
            if choice == "\x1b":
                continue
            user_input, clarification, reset = _handle_ask(
                choice, clarification, user_input,
            )
            if reset:
                store.reset_regen()
                regen_count = 0
            if not clarification and not reset:
                continue
            try:
                commands = get_commands(user_input, cwd, store, clarification)
                store.add_regen(commands[0].cmd, clarification)
                regen_count += 1
            except TimeoutError:
                print("\033[31mtimed out\033[0m")
            except Exception as e:
                print(f"\033[31merror: {e}\033[0m")

        elif key == "h":
            term_hist = get_shell_history()
            if not term_hist:
                print("\033[90m(no shell history found)\033[0m")
                continue

            while True:
                action = show_history_approval(term_hist)

                if action == "esc":
                    break
                elif action == "e":
                    edited = edit_in_editor(term_hist)
                    if edited:
                        term_hist = edited
                    else:
                        print("\033[31meditor returned empty, cancelled\033[0m")
                        break
                elif action == "c":
                    if copy_to_clipboard(term_hist):
                        print("\033[32m✓ copied to clipboard\033[0m")
                    else:
                        print("\033[31mno clipboard tool\033[0m")
                elif action == "p":
                    from_clip = clipboard_read()
                    if from_clip:
                        term_hist = from_clip
                        print("\033[36m(pasted from clipboard)\033[0m")
                    else:
                        print("\033[90mclipboard empty\033[0m")
                elif action == "send":
                    count = term_hist.count("\n") + 1
                    print(
                        f"\033[36msharing {count} history entries...\033[0m"
                    )
                    try:
                        commands = get_commands(
                            user_input, cwd, store, clarification, term_hist,
                        )
                        store.add_regen(commands[0].cmd, clarification)
                        regen_count += 1
                    except TimeoutError:
                        print("\033[31mtimed out\033[0m")
                    except Exception as e:
                        print(f"\033[31merror: {e}\033[0m")
                    break

            continue

        elif key == "\x1b":
            return

        else:
            return


# --- One-shot Mode ---

def run_oneshot(args, store, config):
    cwd = os.getcwd()
    store.reset_regen()

    try:
        commands = get_commands(args, cwd, store)
    except TimeoutError:
        print("\033[31mtimed out\033[0m")
        sys.exit(1)
    except Exception as e:
        print(f"\033[31merror: {e}\033[0m")
        sys.exit(1)

    store.add_regen(commands[0].cmd)
    _command_selection(args, cwd, commands, store, config)
    sys.exit(0)


# --- REPL Mode ---

def run_repl(store, config):
    while True:
        try:
            cwd = os.getcwd()
            prompt = f"\033[32m{os.path.basename(cwd)}\033[0m > "
            user_input = input(prompt).strip()

            if not user_input:
                continue

            if "readline" in sys.modules:
                readline.add_history(user_input)

            # Built-in cd
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

            # Escape commands
            if user_input in ("!quit", "!q"):
                print("\033[36mo7\033[0m")
                sys.exit(0)
            elif user_input == "!api":
                config_menu(config)
                config.apply_to_env()
                reinit_client(config)
                continue
            elif user_input == "!config":
                show_config(config)
                continue
            elif user_input == "!help":
                show_help()
                continue
            elif user_input.startswith("!"):
                if user_input.startswith("!cmd "):
                    cmd = user_input[5:]
                else:
                    cmd = user_input[1:]
                if not cmd:
                    continue
                if confirm_run(cmd):
                    run_cmd(cmd, store)
                continue

            # Direct shell command
            if not is_natural_language(user_input):
                if confirm_run(user_input):
                    run_cmd(user_input, store)
                continue

            # LLM command generation
            try:
                store.reset_regen()
                cmd, clarify = get_command(user_input, cwd, store)
                if clarify:
                    clarification = prompt_clarify(clarify)
                    cmd, _ = get_command(user_input, cwd, store, clarification)

                if not cmd:
                    print("\033[31mNo command generated\033[0m")
                    continue

                commands = [Command(cmd=cmd)]
                store.add_regen(cmd)
                _command_selection(user_input, cwd, commands, store, config)
                print()
            except TimeoutError:
                print("\033[31mtimed out\033[0m")
            except Exception as e:
                print(f"\033[31merror: {e}\033[0m")

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


# --- Entry Point ---

def main():
    config = Config.load()

    if not config.is_configured:
        setup_wizard(config)
    if not config.is_configured:
        print("\033[31mSetup incomplete, exiting.\033[0m")
        sys.exit(1)
    config.apply_to_env()

    from . import VERSION, DATE
    print(
        f"\033[1mnlsh\033[0m {VERSION} ({DATE}) - "
        f"model: \033[36m{config.model or 'unknown'}\033[0m"
    )

    init_client(config)
    store = HistoryStore()

    args = " ".join(sys.argv[1:])
    if args:
        print()
        run_oneshot(args, store, config)
    else:
        print("\n")
        show_help()
        run_repl(store, config)
