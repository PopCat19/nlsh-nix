# nlsh-nix

NixOS-compatible packaging for [nlsh](https://github.com/junaid-mahmood/nlsh) with OpenAI-compatible API support.

## Usage

### One-shot mode

```bash
nlsh list all python files
[awaiting API response...] (1s/30s)
→ find . -name "*.py"
[Enter=run r=regen a=ask Esc=cancel]
```

Press `Enter` to run, `r` to regenerate, `a` to ask for changes, `Esc` to cancel.

### REPL mode

```bash
nlsh
nlsh 7abc282 (20260502) - model: ministral-3:8b

!api       - Change API key/config
!config   - Show current config
!help      - Show this help
!cmd <cmd>  - Run shell command directly
!quit, !q   - Exit

popcat19 > nixos rebuild
[awaiting API response...] (2s/30s)
→ nixos-rebuild switch
[Enter=run r=regen a=ask Esc=cancel]
```

### Ask menu

Press `a` to request changes:

```
→ nixos-rebuild switch
[Enter=run r=regen a=ask Esc=cancel]
a
What do you want?
  1) Clarify the request
  2) A different command
  3) Modify this command
  4) Safer/alternative approach
  5) Something completely different
  0) Custom description
  Esc) Cancel
```

Press `Esc` to cancel without changes.

### Model-initiated clarification

If your request is vague, the model may ask for clarification:

```
popcat19 > delete the file
[awaiting API response...] (1s/30s)
Which file do you want to delete?
  1) config.json
  2) *.log files
  3) Everything in ./tmp
  0) Custom (describe what you want)

Select 1-0, or type answer: 1
[awaiting API response...] (1s/30s)
→ rm config.json
[Enter=run r=regen a=ask Esc=cancel]
```

### Commands

| Command | Description |
|--------|-------------|
| `!api` | Interactive menu for API config |
| `!config` | Show current configuration |
| `!help` | Show available commands |
| `!cmd <shell>` | Run shell command directly |
| `!quit`, `!q` | Exit |
| `Ctrl+D` | Exit |

### Confirmation keys

| Key | Action |
|-----|--------|
| `Enter` | Run the suggested command |
| `r` | Regenerate suggestion (model sees history) |
| `a` | Ask menu for changes |
| `Esc` | Cancel |

The `(regen N)` counter shows regeneration attempts.

### Behavior

- Type naturally → suggests a shell command
- Shell commands (`ls`, `git`, `nix`, etc.) run directly without LLM
- `cd` works natively for directory navigation
- Shell-aware: uses your aliases (bash/zsh) and abbreviations (fish)
- Model sees previous regeneration attempts
- 30s timeout with progress indicator

### First run

Prompts for:

1. Base URL (required)
2. Model (required)
3. API key (optional - skip for local services)

## Configuration

Config stored at `~/.config/nlsh/config`:

| Variable | Required | Description |
|----------|----------|-------------|
| `NLSH_BASE_URL` | yes | API endpoint |
| `NLSH_MODEL` | yes | Model to use |
| `NLSH_API_KEY` | no | API key (skip for local services) |

**Env vars take precedence over config file.**

### Examples

**OpenAI:**

```bash
export NLSH_API_KEY=<api-key>
export NLSH_BASE_URL=https://api.openai.com/v1
export NLSH_MODEL=<model-name>
```

**Ollama:**

```bash
export NLSH_BASE_URL=http://localhost:11434/v1
export NLSH_MODEL=<model-name>
```

**vLLM / LM Studio:**

```bash
export NLSH_BASE_URL=http://localhost:8000/v1
export NLSH_MODEL=<model-name>
```

## Nix

### Run directly

```bash
nix run github:PopCat19/nlsh-nix
```

### Temporary shell

```bash
nix shell github:PopCat19/nlsh-nix
nlsh
```

### Install to profile

```bash
nix profile add github:PopCat19/nlsh-nix
nlsh
```

### Update

```bash
nix profile upgrade nlsh-nix --refresh
```

### Remove

```bash
nix profile remove nlsh-nix
rm -rf ~/.config/nlsh
```

### Flake inputs

```nix
{
  inputs.nlsh-nix.url = "github:PopCat19/nlsh-nix";
}
```

## Differences from upstream

- OpenAI-compatible API (supports OpenAI, Ollama, vLLM, etc.)
- Modular codebase (config, history, llm, ui, main)
- Config at `~/.config/nlsh/config` (XDG-friendly)
- One-shot mode with command-line args
- Shell context (aliases/fish abbr) included in prompts
- Single-key confirmation (Enter/r/a/Esc)
- Ask menu with numbered options (1-0)
- Model-initiated clarification with choices
- Regen history visible to model for learning
- Timeout indicator with progress
- Interactive `!api` menu with cancel