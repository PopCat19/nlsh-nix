# nlsh-nix

NixOS-compatible packaging for [nlsh](https://github.com/junaid-mahmood/nlsh) with OpenAI-compatible API support.

## Usage

### One-shot mode

```bash
nlsh list all python files
[awaiting API response...] (1s/30s)
→ find . -name "*.py"
[Enter=run r=regen c=clarify Esc=cancel]
```

Press `Enter` to run, `r` to regenerate, `c` to clarify, `Esc` to cancel.

### REPL mode

```bash
nlsh
nlsh e005ac3 (20260502) - model: ministral-3:8b

!api       - Change API key/config
!config   - Show current config
!help      - Show this help
!cmd <cmd>  - Run shell command directly
!quit, !q   - Exit

popcat19 > nixos rebuild
[awaiting API response...] (2s/30s)
→ nixos-rebuild switch
[Enter=run r=regen c=clarify Esc=cancel]
```

### Clarifying suggestions

When the suggestion isn't quite right, press `c` to provide guidance:

```
→ nix-env -f /nix/store/... rebuild switch
[Enter=run r=regen c=clarify Esc=cancel]
c
Clarify: use home-manager
[awaiting API response...] (1s/30s)
→ home-manager switch
[Enter=run r=regen c=clarify Esc=cancel] (regen 1)
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
| `r` | Regenerate suggestion |
| `c` | Clarify with comment and regenerate |
| `Esc` | Cancel (back to prompt) |

The `(regen N)` counter shows how many times you've regenerated.

### Behavior

- Type naturally → suggests a shell command
- Shell commands (`ls`, `git`, `nix`, etc.) run directly without LLM
- `cd` works natively for directory navigation
- Shell-aware: uses your aliases (bash/zsh) and abbreviations (fish)
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
- Fixed shebang for NixOS compatibility
- Config at `~/.config/nlsh/config` (XDG-friendly)
- One-shot mode with command-line args
- Shell context (aliases/fish abbr) included in prompts
- Single-key confirmation (Enter/r/c/Esc)
- Clarify mode for guided regeneration
- Regen counter to track iterations
- Timeout indicator with progress
- Interactive `!api` menu with cancel option