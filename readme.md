# nlsh-nix

NixOS-compatible packaging for [nlsh](https://github.com/junaid-mahmoud/nlsh) with OpenAI-compatible API support.

<details open>
<summary>Usage</summary>

#### One-shot

```bash
nlsh list all python files
```

```
nlsh fc5434b (20260502) - model: ministral-3:8b

Generated commands:
  1) Find Python files recursively
  ↳ find . -name "*.py"
  2) Use fd for faster search
  ↳ fd -e py

[Enter=1 2-3=select s=scout r=regen a=ask Esc=cancel]
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

[Enter=1 2-3=select s=scout r=regen a=ask Esc=cancel]
```

</details>

<details>
<summary>Keybindings</summary>

| Context | Key | Action |
|---|---|---|
| Command selection | `Enter` | Run option 1 |
| | `1`–`9` | Select option |
| | `s` | Scout mode |
| | `r` | Regenerate |
| | `a` | Ask menu |
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
| REPL commands | `!api` | Config menu |
| | `!config` | Show config |
| | `!help` | Help screen |
| | `!cmd <cmd>` | Run shell cmd |
| | `!quit` / `!q` | Exit |
| | `↑` / `↓` | History recall |

</details>

<details>
<summary>Scout mode</summary>

Press `s` from the command selection to let the model explore your environment first:

```
s
Scouting...
  1. $ which nixos-rebuild
  [Enter=run s=skip r=regen Esc=cancel]
  ✓ 0s
  
  2. $ ls -la /etc/nixos
  ✓ 0s
```

Per scout command: `Enter` run, `s` skip, `r` alternative, `Esc` cancel.

On failure, the prompt shows `[r=regen s=skip]`. Commands are blocked if dangerous (`find /`, `rm`, `sudo`, etc.).

</details>

<details>
<summary>Ask menu</summary>

Press `a` from the command selection:

```
What do you want?
  1) Clarify the request
  2) A different command
  3) Modify this command
  4) Safer/alternative approach
  5) Something completely different
  0) Custom description
  Esc) Cancel
```

The model may also initiate clarification (shows choices you can select or type a freeform answer).

</details>

<details>
<summary>Confirmation</summary>

```
→ sudo nixos-rebuild switch
[Enter=run c=copy Esc=cancel]
```

- **Sudo commands** show `⚠ sudo:` in red
- **c** copies to clipboard (wl-copy / xclip / xsel)
- Commands run through `$SHELL` so aliases and functions work
- Elapsed time shown inline: `[running] (3s)`
- 30s timeout with progress indicator

</details>

<details>
<summary>First run</summary>

Prompts for:

1. **Base URL** — e.g. `https://api.openai.com/v1`
2. **Model** — e.g. `gpt-4o`
3. **API key** — masked input (`*` echoed), skip for local services

Press `Esc` at any prompt to cancel (exits if setup incomplete).

</details>

<details>
<summary>Configuration</summary>

Config file: `~/.config/nlsh/config`

| Variable | Required | Description |
|---|---|---|
| `NLSH_BASE_URL` | yes | API endpoint |
| `NLSH_MODEL` | yes | Model name |
| `NLSH_API_KEY` | no | API key (skip for local) |

Env vars take precedence over the config file. Use `!api` from REPL for interactive editing.

<details>
<summary>Provider examples</summary>

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
</details>

<details>
<summary>Nix</summary>

```bash
# Run directly
nix run github:PopCat19/nlsh-nix

# Temporary shell
nix shell github:PopCat19/nlsh-nix && nlsh

# Install
nix profile add github:PopCat19/nlsh-nix

# Update
nix profile upgrade nlsh-nix --refresh

# Flake input
# inputs.nlsh-nix.url = "github:PopCat19/nlsh-nix";
```

</details>

<details>
<summary>Differences from upstream</summary>

- OpenAI-compatible API (OpenAI, Ollama, vLLM, LM Studio, etc.)
- One-shot mode with command-line args
- Multiple command proposals (up to 3) with descriptions
- Scout mode — model explores environment before proposing
- Confirmation with clipboard copy
- Sudo detection with warning
- Running indicator with elapsed time
- Ask menu with numbered options (1–0) and freeform
- Model-initiated clarification with choices
- Regen history visible to model for learning
- 30s timeout with progress indicator
- Interactive `!api` menu with masked API key input
- ESC/backspace/arrow/home/end/delete/Ctrl+W/Ctrl+U in REPL input
- History recall (↑/↓) in REPL
- Config at `~/.config/nlsh/config` (XDG-friendly)
- Commands run through `$SHELL` (aliases/functions work)
- Shell context (fish abbr) included in prompts
- Version format: yyyymmdd-&lt;rev&gt;

</details>
