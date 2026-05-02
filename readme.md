# nlsh-nix

NixOS-compatible packaging for [nlsh](https://github.com/junaid-mahmood/nlsh) with OpenAI-compatible API support.

## Usage

```bash
# Run directly (prompts for config on first run)
nix run github:PopCat19/nlsh-nix

# Install to profile
nix profile install github:PopCat19/nlsh-nix
```

## Configuration

Config stored at `~/.config/nlsh/config`:

| Variable | Required | Description |
|----------|-----------|-------------|
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

## Commands

| Command | Action |
|---------|--------|
| `!api` | Change API key/config |
| `!config` | Show current config |
| `!help` | Show help |
| `!cmd` | Run shell command directly |

## Differences from upstream

- OpenAI-compatible API (supports OpenAI, Ollama, vLLM, etc.)
- Fixed shebang for NixOS compatibility
- Config at `~/.config/nlsh/config` (XDG-friendly)
- Added `nix` commands to shell detection