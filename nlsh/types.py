# types.py
#
# Purpose: Shared data types for nlsh
#
# This module:
# - Defines Command and ClarifyData dataclasses

from dataclasses import dataclass


@dataclass
class Command:
    cmd: str
    desc: str = ""


@dataclass
class ClarifyData:
    question: str
    options: dict  # str -> str
