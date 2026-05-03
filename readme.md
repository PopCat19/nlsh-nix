# nlsh-nix

NixOS-compatible packaging for [nlsh](https://github.com/junaid-mahmoud/nlsh) with OpenAI-compatible API support.

<details open>
<summary>Installation</summary>

```bash
# Run directly
nix run github:PopCat19/nlsh-nix

# Temporary shell
nix shell github:PopCat19/nlsh-nix && nlsh

# Install to profile
nix profile add github:PopCat19/nlsh-nix

# Update
nix profile upgrade nlsh-nix --refresh

# Remove
nix profile remove nlsh-nix
rm -rf ~/.config/nlsh
```

#### Flake input

```nix
inputs.nlsh-nix.url = "github:PopCat19/nlsh-nix";
```

</details>

<details>
<summary>Configuration</summary>

Config file: `~/.config/nlsh/config`

- `NLSH_BASE_URL` **(required)** — API endpoint (e.g. `https://api.openai.com/v1`)
- `NLSH_MODEL` **(required)** — model name (e.g. `gpt-4o`)
- `NLSH_API_KEY` — API key, skip for local services

Env vars take precedence over the config file. Use `!api` from REPL for interactive editing.

#### First run

Prompts for Base URL, Model, and API key (masked `*` echo). Press `Esc` at any prompt to cancel.

#### Provider examples

**OpenAI**

```bash
export NLSH_API_KEY=sk-...
export NLSH_BASE_URL=https://api.openai.com/v1
export NLSH_MODEL=gpt-4o
```

**Ollama**

```bash
export NLSH_BASE_URL=http://localhost:11434/v1
export NLSH_MODEL=llama3.2
```

**vLLM / LM Studio**

```bash
export NLSH_BASE_URL=http://localhost:8000/v1
export NLSH_MODEL=my-model
```

</details>

<details>
<summary>Usage</summary>

#### One-shot

```bash
nlsh list all python files
```

```
nlsh ad56306 (20260502) - model: ministral-3:8b

Generated commands:
  1) Find Python files recursively
  ↳ find . -name "*.py"
  2) Use fd for faster search
  ↳ fd -e py

[Enter=1 2-3=select s=scout r=regen a=ask h=hist Esc=cancel]
```

#### REPL

```bash
nlsh
```

```
popcat19 > nixos rebuild

Generated commands:
  1) Switch to new configuration
  ↳ sudo nixos-rebuild switch

[Enter=1 2-3=select s=scout r=regen a=ask h=hist Esc=cancel]
```

#### Scout mode

Press `s` to let the model explore before proposing. Uses OpenAI tool calling (`bash`, `read` tools). Shows proposed scouts for review with toggle-to-skip:

```
Proposed scout commands:
  1. ⚙ bash $ which nixos-rebuild           [run]
  2. 📄 read /etc/nixos/flake.nix           [run]

[Enter=run-selected r=regen 1-2=toggle Esc=cancel]
```

Each scout runs with approval — shows output inline (first 5 lines).

#### Ask menu

Press `a` to refine requests:

- `1` Clarify the request
- `2` A different command
- `3` Modify this command
- `4` Safer/alternative approach
- `5` Something completely different
- `0` Custom description

#### History sharing

Press `h` to share shell history (tail 50 lines, fish/bass/zsh auto-detected). Preview → edit in `$EDITOR`, copy to clipboard, or paste from clipboard before sending.

#### REPL commands

- `!api` — interactive config menu (masked API key input)
- `!config` — show current config
- `!help` — help screen
- `!cmd <cmd>` — run shell command directly
- `!quit` / `!q` — exit

#### Keybindings

**Command selection**

- `Enter` / `1` — run option 1
- `2`–`9` — select option
- `s` — scout mode
- `r` — regenerate
- `a` — ask menu
- `h` — share shell history
- `Esc` — cancel

**Scout approval**

- `Enter` — run scout command
- `s` — skip
- `r` — alternative scout
- `Esc` — cancel scout

**Confirmation**

- `Enter` — execute
- `c` — copy to clipboard
- `Esc` — cancel

**`!api` menu**

- `1`–`3` — edit field
- `s` — save & exit
- `c` / `Esc` — cancel (reverts changes)

**REPL input**

- `⭠⭢` — move cursor
- `Home` / `End` — jump to ends
- `Delete` — delete at cursor
- `Ctrl+W` — delete word backward
- `Ctrl+U` — clear line
- `Esc` — empty input
- `↑` / `↓` — history recall

</details>

<details>
<summary>Features</summary>

- Commands run through `$SHELL` — aliases and functions work
- Sudo detection with `⚠ sudo:` warning
- Running indicator with elapsed time: `[running] (3s)`
- 30s timeout with progress indicator
- Confirmation before execution with clipboard copy (`c`)
- Multiple command proposals (up to 3) with descriptions
- Model-initiated clarification with choices
- Regen history visible to model for learning
- Shell context (aliases, fish abbreviations) included in prompts
- Native ESC/backspace/arrow/home/end/delete/Ctrl+W/Ctrl+U handling
- History recall (`↑`/`↓`) in REPL
- Masked API key input (`*` echo)
- Config at `~/.config/nlsh/config` (XDG-friendly)

</details>

<details>
<summary>Differences from upstream</summary>

- OpenAI-compatible API (OpenAI, Ollama, vLLM, LM Studio, etc.)
- One-shot mode with command-line args
- Multiple command proposals with descriptions
- Scout mode via OpenAI tool calling (bash + read tools)
- Preview + toggle for scout commands before execution
- Confirmation with clipboard copy
- Sudo detection with warning
- Running indicator with elapsed time
- Ask menu with numbered options and freeform
- Model-initiated clarification with choices
- Shell history sharing with edit/approve consent loop
- Regen history visible to model
- 30s timeout with progress indicator
- Interactive `!api` menu with masked API key
- Full readline-style line editing in REPL input
- Version format: yyyymmdd-&lt;rev&gt;
- Modular codebase (config, history, llm subpackage, ui, types, util)

</details>

<details>
<summary>Credits</summary>

Forked from [nlsh](https://github.com/junaid-mahmoud/nlsh) by [Junaid Mahmoud](https://github.com/junaid-mahmoud).

</details>
