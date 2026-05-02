# context.md
#
# - `__init__.py` — package initialization, exposes version info and main entry point
# - `__main__.py` — entry point for running as `python -m nlsh`, invokes `main()` from main module
# - `main.py` — entry point and main application loop, handles one-shot and REPL modes, processes user input and command execution
# - `ui.py` — terminal UI components and user interaction, handles single keypress reading, displays help and config info, manages await indicator
# - `config.py` — config loading, saving, and management, loads and saves config from `~/.config/nlsh/config`, provides setup wizard and interactive config menu
# - `history.py` — command history management, tracks recent commands and their output, tracks regeneration attempts for current query, formats history for LLM context
# - `llm.py` — LLM API interaction and command generation, manages OpenAI client, generates shell commands from natural language, gathers shell context (aliases, abbreviations)
