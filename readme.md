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

| Variable | Required | Description |
|---|---|---|
| `NLSH_BASE_URL` | yes | API endpoint |
| `NLSH_MODEL` | yes | Model name |
| `NLSH_API_KEY` | no | API key (skip for local) |

Env vars take precedence. Use `!api` from REPL for interactive editing.

#### First run

Prompts for Base URL, Model, and API key (masked `*` echo). Press `Esc` to cancel.

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

<details open>
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

Press `s` to let the model explore before proposing. Uses OpenAI tool calling (`bash`, `read` tools). Shows proposed scouts for review with toggle-to-skip.

```
Proposed scout commands:
  1. ⚙ bash $ which nixos-rebuild           [run]
  2. 📄 read /etc/nixos/flake.nix           [run]

[Enter=run-selected r=regen 1-2=toggle Esc=cancel]
```

Each scout runs with approval — shows output inline (first 5 lines).

#### Ask menu

Press `a` to refine: clarify, different command, modify, safer approach, or custom.

#### History sharing

Press `h` to share shell history (tail 50 lines, fish/bass/zsh auto-detected). Preview → edit in `$EDITOR`, copy to clipboard, or paste from clipboard before sending.

#### REPL commands

| Command | Action |
|---|---|
| `!api` | Interactive config menu |
| `!config` | Show current config |
| `!help` | Help screen |
| `!cmd <cmd>` | Run shell command directly |
| `!quit` / `!q` | Exit |

#### Keybindings

| Context | Key | Action |
|---|---|---|
| Command selection | `Enter` / `1` | Run option 1 |
| | `2`–`9` | Select option |
| | `s` | Scout mode |
| | `r` | Regenerate |
| | `a` | Ask menu |
| | `h` | Share shell history |
| | `Esc` | Cancel |
| Scout approval | `Enter` | Run scout cmd |
| | `s` | Skip |
| | `r` | Alternative scout |
| | `Esc` | Cancel scout |
| Confirmation | `Enter` | Execute |
| | `c` | Copy to clipboard |
| | `Esc` | Cancel |
| Ask menu | `1`–`5`,`0` | Select request |
| | `Esc` | Back |
| `!api` menu | `1`–`3` | Edit field |
| | `s` | Save & exit |
| | `c` / `Esc` | Cancel |
| REPL input | `⭠⭢` | Move cursor |
| | `Home` / `End` | Jump ends |
| | `Delete` | Delete at cursor |
| | `Ctrl+W` | Delete word |
| | `Ctrl+U` | Clear line |
| | `Esc` | Empty input |
| | `↑` / `↓` | History recall |

</details>

<details>
<summary>Features</summary>

- Commands run through `$SHELL` (aliases and functions work)
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
