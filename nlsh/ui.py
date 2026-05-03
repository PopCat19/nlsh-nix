# ui.py
#
# Purpose: Terminal UI components and user interaction
#
# This module:
# - Handles single keypress reading and line editing
# - Displays help, config, command options
# - Manages await indicator and clarification prompts

import sys
import os
import tty
import termios
import threading
import time
import select

TIMEOUT = 30


def get_single_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            while select.select([sys.stdin], [], [], 0.05)[0]:
                ch += sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def raw_input(prompt: str) -> str:
    sys.stdout.write(prompt)
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    buffer = []
    pos = 0

    def redraw():
        sys.stdout.write("\r" + prompt + "".join(buffer) + "\033[K")
        sys.stdout.write("\r" + prompt + "".join(buffer[:pos]))
        sys.stdout.flush()

    def delete_word_backward():
        nonlocal pos
        while pos > 0 and buffer[pos - 1] == " ":
            pos -= 1
            buffer.pop(pos)
        while pos > 0 and buffer[pos - 1] != " ":
            pos -= 1
            buffer.pop(pos)

    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)

            if ch == "\x1b":
                while select.select([sys.stdin], [], [], 0.03)[0]:
                    ch += sys.stdin.read(1)
                seq = ch
                if seq == "\x1b":
                    sys.stdout.write("\r\n")
                    sys.stdout.flush()
                    return ""
                elif seq in ("\x1b[C", "\x1bOC"):
                    if pos < len(buffer):
                        pos += 1
                        redraw()
                elif seq in ("\x1b[D", "\x1bOD"):
                    if pos > 0:
                        pos -= 1
                        redraw()
                elif seq in ("\x1b[H", "\x1b[1~", "\x1bOH"):
                    pos = 0
                    redraw()
                elif seq in ("\x1b[F", "\x1b[4~", "\x1bOF"):
                    pos = len(buffer)
                    redraw()
                elif seq == "\x1b[3~":
                    if pos < len(buffer):
                        buffer.pop(pos)
                        redraw()
            elif ch in ("\r", "\n"):
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                return "".join(buffer)
            elif ch in ("\x7f", "\x08"):
                if pos > 0:
                    pos -= 1
                    buffer.pop(pos)
                    redraw()
            elif ch == "\x17":
                delete_word_backward()
                redraw()
            elif ch == "\x15":
                buffer = buffer[pos:]
                pos = 0
                redraw()
            elif ch == "\x03":
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                return ""
            elif ch.isprintable():
                buffer.insert(pos, ch)
                pos += 1
                redraw()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def secret_input(prompt: str) -> str:
    sys.stdout.write(prompt)
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    buffer = []

    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)

            if ch == "\x1b":
                while select.select([sys.stdin], [], [], 0.03)[0]:
                    ch += sys.stdin.read(1)
                if ch == "\x1b":
                    sys.stdout.write("\r\n")
                    sys.stdout.flush()
                    return ""
            elif ch in ("\r", "\n"):
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                return "".join(buffer)
            elif ch in ("\x7f", "\x08"):
                if buffer:
                    buffer.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch == "\x03":
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                return ""
            elif ch.isprintable():
                buffer.append(ch)
                sys.stdout.write("*")
                sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class AwaitIndicator:
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
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _tick(self):
        while not self.stop_event.is_set():
            elapsed = int(time.time() - self.start_time)
            sys.stdout.write(
                f"\r\033[33m[awaiting API response...] "
                f"({elapsed}s/{self.timeout}s)\033[0m"
            )
            sys.stdout.flush()
            time.sleep(0.1)
            if elapsed >= self.timeout:
                break


# --- Display Functions ---


def show_help():
    print("\033[36mType plain English to generate shell commands\033[0m")
    print("\033[36m!api\033[0m       - Change API key/config")
    print("\033[36m!config\033[0m   - Show current config")
    print("\033[36m!help\033[0m      - Show this help")
    print("\033[36m!cmd <cmd>\033[0m  - Run shell command directly")
    print("\033[36m!quit, !q\033[0m   - Exit")
    print()


def show_config(config):
    api_key = config.api_key
    masked = (
        api_key[:8] + "..." + api_key[-4:]
        if len(api_key) > 12
        else "(not set)" if not api_key else api_key
    )
    print(f"\033[36mNLSH_API_KEY:\033[0m {masked}")
    print(f"\033[36mNLSH_BASE_URL:\033[0m {config.base_url or '(not set)'}")
    print(f"\033[36mNLSH_MODEL:\033[0m {config.model or '(not set)'}")
    print()


def show_gen_options(commands):
    print("\033[36mGenerated commands:\033[0m")
    for i, cmd in enumerate(commands, 1):
        if cmd.desc:
            print(f"  \033[33m{i}\033[0m) \033[35m{cmd.desc}\033[0m")
            print(f"  ↳ \033[33m{cmd.cmd}\033[0m")
        else:
            print(f"  \033[33m{i}\033[0m) \033[33m{cmd.cmd}\033[0m")
    print()


def show_ask_options():
    print("\033[36mWhat do you want?\033[0m")
    print("  \033[33m0\033[0m) Custom description")
    print("  \033[33m1\033[0m) Clarify the request")
    print("  \033[33m2\033[0m) A different command")
    print("  \033[33m3\033[0m) Modify this command")
    print("  \033[33m4\033[0m) Safer/alternative approach")
    print("  \033[33m5\033[0m) Something completely different")
    print("  \033[33mEsc\033[0m) Cancel")
    print()


# --- Interactive Prompts ---


def prompt_clarify(clarify):
    print(f"\033[36m{clarify.question}\033[0m")
    for key in sorted(clarify.options.keys()):
        print(f"  \033[33m{key}\033[0m) {clarify.options[key]}")
    print("  \033[33mEsc\033[0m) Cancel")
    print()

    answer = raw_input("\033[33mSelect 0-9, or type answer: \033[0m")
    if not answer:
        return ""

    if answer in clarify.options:
        if answer == "0" and "custom" in clarify.options.get("0", "").lower():
            custom = raw_input("\033[33mDescribe: \033[0m")
            return custom
        return clarify.options[answer]
    return answer


def show_history_approval(history):
    lines = history.split("\n")
    preview_n = 12
    if len(lines) > preview_n + 3:
        preview = lines[:preview_n]
        preview.append(f"\033[90m  ... and {len(lines) - preview_n} more lines\033[0m")
    else:
        preview = lines

    print("\033[36mShell history preview:\033[0m")
    print("\033[90m" + "\n".join(preview) + "\033[0m")
    print()
    print("\033[36m[Enter=send e=edit c=copy p=paste Esc=cancel]\033[0m")

    key = get_single_key()
    if key in ("\r", "\n"):
        return "send"
    elif key == "e":
        return "e"
    elif key == "c":
        return "c"
    elif key == "p":
        return "p"
    return "esc"
