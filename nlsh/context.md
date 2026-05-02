# context.md
#
# - `__init__.py` — package initialization, exposes version info and main entry point
# - `__main__.py` — entry point for running as `python -m nlsh`, invokes `main()` from main module
# - `types.py` — shared data types, defines Command and ClarifyData dataclasses
# - `config.py` — config loading, saving, and management, defines Config dataclass with load/save, provides setup wizard and interactive config menu
# - `history.py` — command history management, provides HistoryStore class for tracking commands and regens, formats history for LLM context
# - `llm.py` — LLM API interaction and command generation, manages OpenAI client, generates shell commands from natural language, gathers shell context (aliases, abbreviations)
# - `ui.py` — terminal UI components and user interaction, handles single keypress reading and line editing, displays help/config/command options, manages await indicator and clarification prompts
# - `main.py` — entry point and main application loop, handles one-shot and REPL modes, processes user input and command execution
