"""Application settings loaded from environment variables and .env files."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized runtime configuration for API, auth, scoring, and sandbox."""

    DATABASE_URL: str
    AUTH_JWT_SECRET: str = "secreewt654321"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    SANDBOX_PROFILE: str = "nix-sandbox-v1"
    ENABLE_GITHUB_MCP_INGESTION: bool = False
    SANDBOX_COMMAND_PREFIX: str = ""
    SANDBOX_NIX_BINARY: str = "nix"
    SANDBOX_NIX_FLAKE_REF: str = "./sandbox-nix#mcp-runner"
    SANDBOX_RUNTIME_MODULE: str = "app.sandbox.runtime_entry"
    SANDBOX_TIMEOUT_SECONDS: int = 120
    SANDBOX_RUN_BASE_DIR: str = ".sandbox_runs"
    SANDBOX_ALLOW_LOCAL_FALLBACK: bool = True
    SANDBOX_LOCAL_PYTHON_BINARY: str = "python"

    JUDGE_ANTHROPIC_API_KEY: str
    JUDGE_ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"

    SCORE_WEIGHT_TASK_SUCCESS: float = 0.35
    SCORE_WEIGHT_TOOL_CORRECTNESS: float = 0.25
    SCORE_WEIGHT_LATENCY: float = 0.10
    SCORE_WEIGHT_COST: float = 0.10
    SCORE_WEIGHT_STEPS: float = 0.10
    SCORE_WEIGHT_RELIABILITY: float = 0.10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
