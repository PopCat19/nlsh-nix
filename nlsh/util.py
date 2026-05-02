# util.py
#
# Purpose: Shared utility functions for clipboard and editor integration
#
# This module:
# - Copies text to system clipboard (wl-copy, xclip, xsel)
# - Reads text from system clipboard (wl-paste, xclip, xsel)
# - Opens text in an external editor for user editing

import os
import shutil
import subprocess
import tempfile


def copy_to_clipboard(text: str) -> bool:
    for tool in ["wl-copy", "xclip", "xsel"]:
        if shutil.which(tool):
            args = []
            if tool == "xclip":
                args = ["-selection", "clipboard"]
            elif tool == "xsel":
                args = ["--clipboard", "--input"]
            try:
                p = subprocess.run(
                    [tool] + args, input=text, text=True, capture_output=True,
                )
                if p.returncode == 0:
                    return True
            except Exception:
                continue
    return False


def clipboard_read() -> str:
    for tool in ["wl-paste", "xclip", "xsel"]:
        if shutil.which(tool):
            args = []
            if tool == "xclip":
                args = ["-selection", "clipboard", "-o"]
            elif tool == "xsel":
                args = ["--clipboard", "--output"]
            try:
                result = subprocess.run(
                    [tool] + args, capture_output=True, text=True,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception:
                continue
    return ""


def edit_in_editor(text: str) -> str:
    editor_cmd = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False,
    ) as f:
        f.write(text)
        tmp = f.name
    try:
        subprocess.run([editor_cmd, tmp])
        with open(tmp) as f:
            return f.read().strip()
    except Exception:
        return ""
    finally:
        os.unlink(tmp)
