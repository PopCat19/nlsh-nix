# nlsh-nix

NixOS-compatible packaging for [nlsh](https://github.com/junaid-mahmood/nlsh) with OpenAI-compatible API support.

## Usage

Start nlsh, type natural language, get shell commands:

```
15:41:22 ~
❯ list all python files
→ find . -name "*.py"
./main.py
./utils/helper.py

15:41:36 ~/projects
❯ commit with message fixed the bug
→ git commit -m "fixed the bug"
[main abc123] fixed the bug
 2 files changed, 5 insertions(+)

15:41:41 ~/projects
❯ find files larger than 100MB
→ find . -size +100M
./data/archive.tar.gz
```

### Commands

| Command | Description |
|--------|-------------|
| `!api` | Reconfigure API key/base URL/model |
| `!config` | Show current configuration |
| `!help` | Show available commands |
| `!cmd <shell>` | Run shell command directly |
| `!quit`, `!q` | Exit |
| `Ctrl+D` | Exit |

### Behavior

- Type naturally → suggests a shell command
- Press Enter to execute, type anything else to cancel
- Shell commands (`ls`, `git`, `nix`, etc.) run directly without LLM
- `cd` works natively for directory navigation

### First run

Prompts for:

1. API key (press Enter to skip for local services)
2. Base URL (e.g. `https://api.openai.com/v1`)
3. Model name (e.g. `gpt-4.1-mini`, `llama3.2`)

## Configuration

Config stored at `~/.config/nlsh/config`:

| Variable | Required | Description |
|----------|----------|-------------|
| `NLSH_BASE_URL` | yes | API endpoint |
| `NLSH_MODEL` | yes | Model to use |
| `NLSH_API_KEY` | no | API key (skip for local services) |

**Env vars take precedence over config file.** Set values in your shell to skip prompts or override:

```bash
export NLSH_API_KEY=<api-key>
export NLSH_BASE_URL=<base-url>
export NLSH_MODEL=<model>
```

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
- Added `nix` commands to shell detection