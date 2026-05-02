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

| Variable | Default | Description |
|----------|---------|-------------|
| `NLSH_API_KEY` | (required) | Your API key |
| `NLSH_BASE_URL` | `https://api.openai.com/v1` | API endpoint |
| `NLSH_MODEL` | `gpt-4.1-mini` | Model to use |

### Examples

**OpenAI:**
```
NLSH_API_KEY=sk-...
NLSH_BASE_URL=https://api.openai.com/v1
NLSH_MODEL=gpt-4.1-mini
```

**Ollama:**
```
NLSH_API_KEY=ollama
NLSH_BASE_URL=http://localhost:11434/v1
NLSH_MODEL=llama3.2
```

**vLLM / LM Studio / etc:**
```
NLSH_BASE_URL=http://localhost:8000/v1
NLSH_MODEL=<your-model>
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