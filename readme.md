# nlsh-nix

NixOS-compatible packaging for [nlsh](https://github.com/junaid-mahmood/nlsh).

## Usage

```bash
# Run directly
nix run github:PopCat19/nlsh-nix

# Install to profile
nix profile install github:PopCat19/nlsh-nix
```

## NixOS Module

Add to your `flake.nix` inputs:

```nix
inputs.nlsh-nix.url = "github:PopCat19/nlsh-nix";
```

## Differences from upstream

- Fixed shebang (`#!/usr/bin/env python3`) for NixOS compatibility
- Packaged as a Nix flake with all dependencies