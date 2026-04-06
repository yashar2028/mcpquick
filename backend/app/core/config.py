from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
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

    SCORE_WEIGHT_TASK_SUCCESS: float = 0.35
    SCORE_WEIGHT_TOOL_CORRECTNESS: float = 0.25
    SCORE_WEIGHT_LATENCY: float = 0.10
    SCORE_WEIGHT_COST: float = 0.10
    SCORE_WEIGHT_STEPS: float = 0.10
    SCORE_WEIGHT_RELIABILITY: float = 0.10

    class Config:
        env_file = "../.env.dev"
        env_file_encoding = "utf-8"


settings = Settings()
