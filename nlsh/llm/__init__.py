# __init__.py
#
# Purpose: LLM subpackage — public API for command generation and scouting
#
# This module:
# - Re-exports the narrow public surface used by main.py

from .client import init_client, reinit_client
from .generate import get_command, get_commands
from .scout import scout_and_get_commands
from .shell import get_shell_history
