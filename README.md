# MCP Quick
## install the pre-commit at .git/hooks
```bash
pre-commit install
```

## sandbox notes
- For local development, `.env.dev` enables `SANDBOX_ALLOW_LOCAL_FALLBACK=true`,
  so runs continue using a separate local subprocess if nix is unavailable.


### windows setup options
Option 1: install Nix directly and keep:

```env
SANDBOX_COMMAND_PREFIX=
SANDBOX_NIX_BINARY=nix
```

Option 2: run the backend directly inside WSL and install Poetry + Nix there.
This keeps backend process and sandbox process in one environment.

If you experiment with a launcher prefix from Windows shell, keep in mind that
cross-environment path handling can be tricky and may require extra tuning.

```env
SANDBOX_COMMAND_PREFIX=wsl.exe
SANDBOX_NIX_BINARY=nix
``
