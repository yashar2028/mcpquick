# MCP Quick
## install the pre-commit at .git/hooks
```bash
pre-commit install
```

## sandbox notes
- For local development, `.env.dev` enables `SANDBOX_ALLOW_LOCAL_FALLBACK=true`,
  so runs continue using a separate local subprocess if nix is unavailable.
- Run submissions accept session API keys and currently support provider calls for:
    - OpenAI (`provider=openai`)
    - Anthropic/Claude (`provider=anthropic` or `provider=claude`)
    - Google Gemini (`provider=gemini` or `provider=google`)
- Evaluation is deterministic and heuristic-based. No AI judge model is used.

### provider model guidance
- OpenAI recommended models: `gpt-4o-mini`, `gpt-4o`
- Anthropic recommended models: `claude-3-5-sonnet-latest`, `claude-3-5-haiku-latest`
- Gemini recommended models: `gemini-2.0-flash`, `gemini-1.5-flash`

The runtime uses official SDKs when available and keeps an HTTP fallback path for
portability in constrained sandbox environments.


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
```
