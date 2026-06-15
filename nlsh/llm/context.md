# context.md
#
# - `__init__.py`, re-exports narrow public surface used by main.py
# - `prompts.py`, LLM prompt templates for single, multi, and scout command generation plus scout safety blocklist
# - `client.py`, OpenAI client initialization and API calling with timeout and await indicator
# - `parsing.py`, response parsing: strips markdown, extracts numbered commands, parses clarification prompts
# - `shell.py`, shell environment introspection: aliases, fish abbreviations, terminal history reading
# - `tools.py`, tool definitions for bash and read function calling, safe tool execution with output truncation
# - `generate.py`, command generation from natural language: builds prompt sections, calls LLM, returns typed results
# - `scout.py`, model-driven scouting: tool-call proposal, preview with toggle, execution, and context-aware regeneration
