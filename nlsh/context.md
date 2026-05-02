# context.md
#
# - `__init__.py` — package initialization, exposes version info and main entry point
# - `__main__.py` — entry point for running as `python -m nlsh`, invokes `main()` from main module
# - `types.py` — shared data types, defines Command and ClarifyData dataclasses
# - `config.py` — config loading, saving, and management, defines Config dataclass with load/save, provides setup wizard and interactive config menu
# - `history.py` — command history management, provides HistoryStore class for tracking commands and regens, formats history for LLM context
# - `ui.py` — terminal UI components and user interaction, handles keypress reading, masked input, line editing, display functions, clarification prompts
# - `util.py` — shared utilities for clipboard integration and external editor support
# - `main.py` — entry point and main application loop, handles one-shot and REPL modes, command execution
# - `llm/` — LLM subpackage for prompt templates, API client, response parsing, shell introspection, tool definitions, command generation, and scouting
