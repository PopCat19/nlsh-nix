# nlsh-nix

NixOS-compatible packaging for [nlsh](https://github.com/junaid-mahmoud/nlsh) with OpenAI-compatible API support.

## Usage

### One-shot mode

```bash
nlsh list all python files
nlsh c2d2b91 (20260502) - model: ministral-3:8b

Generated commands:
  1) Find Python files recursively
  ↳ find . -name "*.py"
  2) Use fd for faster search
  ↳ fd -e py
  3) Basic recursive grep
  ↳ ls -R | grep ".py"

[Enter=1 2-3=select s=scout r=regen a=ask Esc=cancel]
```

Press `Enter` for option 1, `2-3` to select, `s` to scout first, `r` to regenerate, `a` to ask for changes, `Esc` to cancel.

### REPL mode

```bash
nlsh
nlsh c2d2b91 (20260502) - model: ministral-3:8b

popcat19 > nixos rebuild

Generated commands:
  1) Switch to new configuration
  ↳ sudo nixos-rebuild switch
  2) Build and test without switching
  ↳ sudo nixos-rebuild build
  3) Dry run to see changes
  ↳ sudo nixos-rebuild dry-build

[Enter=1 2-3=select s=scout r=regen a=ask Esc=cancel]
```

### Scout mode

Press `s` to let the model explore your environment first:

```
[Enter=1 2-3=select s=scout r=regen a=ask Esc=cancel]
s
Scouting...
  1. $ which nixos-rebuild
  [Enter=run s=skip r=regen Esc=cancel]
  ✓ 0s
  
  2. $ ls -la /etc/nixos
  [Enter=run s=skip r=regen Esc=cancel]
  ✓ 0s
  
  3. $ find /home -name "*.nix"
  [Enter=run s=skip r=regen Esc=cancel]
  r
  [regenerating...]
  4. $ cat /etc/nixos/configuration.nix
  [Enter=run s=skip r=regen Esc=cancel]
  ✗ 1s
  [r=regen s=skip]
  s
  [skipped]

Generated commands:
  1) Rebuild with upgrade
  ↳ sudo nixos-rebuild switch --upgrade
  ...
```

Scout commands run with approval:
- `Enter` - Run the scout command
- `s` - Skip this command
- `r` - Generate alternative scout command
- `Esc` - Cancel scout mode

On failure, choose `r=regen` or `s=skip`. Commands blocked if dangerous (`find /`, `rm`, `sudo`, etc.).

Scout runs exploratory commands to gather context before proposing final commands.

### Confirmation

After selecting a command, you see a confirmation prompt:

```
↳ sudo nixos-rebuild switch
[Enter=run c=copy Esc=cancel]
```

- `Enter` - Run the command
- `c` - Copy to clipboard (wl-copy/xclip/xsel)
- `Esc` - Cancel

For sudo commands, a warning is shown:

```
⚠ sudo: sudo nixos-rebuild switch
[Enter=run c=copy Esc=cancel]
```

### Ask menu

Press `a` to request changes:

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

### Running indicator

Commands show elapsed time while running:

```
[running] (3s)
```

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
- Multiple command proposals (3 options) with descriptions
- Scout mode - model explores environment before proposing
- Commands run through `$SHELL` (aliases/functions work)
- Shell context (aliases/fish abbr) included in prompts
- Confirmation before running with copy option
- Sudo detection with warning
- Running indicator with elapsed time
- Ask menu with numbered options (1-0)
- Model-initiated clarification with choices
- Regen history visible to model for learning
- 30s timeout with progress indicator
- Interactive `!api` menu with cancel
- Native ESC/backspace handling in inputs
- Version format: yyyymmdd-<rev>