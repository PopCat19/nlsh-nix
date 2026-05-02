# ui.py
#
# Purpose: Terminal UI components and user interaction
#
# This module:
# - Handles single keypress reading
# - Displays help and config info
# - Manages await indicator

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
        if ch == '\x1b':
            if select.select([sys.stdin], [], [], 0.1)[0]:
                ch += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def raw_input(prompt: str) -> str:
    """Read line with ESC=cancel, Backspace=delete, Enter=submit."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    buffer = []
    
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            
            if ch == '\x1b':  # ESC
                print()
                return ""
            elif ch == '\r' or ch == '\n':  # Enter
                print()
                return ''.join(buffer)
            elif ch == '\x7f' or ch == '\x08':  # Backspace
                if buffer:
                    buffer.pop()
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            elif ch == '\x03':  # Ctrl+C
                print()
                return ""
            elif ch.isprintable():
                buffer.append(ch)
                sys.stdout.write(ch)
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

def show_config(is_loaded_from_config):
    from .config import REQUIRED_KEYS
    api_key = os.environ.get("NLSH_API_KEY", "")
    masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "(not set)" if not api_key else api_key
    source = "env" if not is_loaded_from_config("NLSH_API_KEY") else "config"
    print(f"\033[36mNLSH_API_KEY:\033[0m {masked} [{source}]")
    for key in REQUIRED_KEYS:
        val = os.environ.get(key, "(not set)")
        source = "env" if not is_loaded_from_config(key) else "config"
        print(f"\033[36m{key}:\033[0m {val} [{source}]")
    print()