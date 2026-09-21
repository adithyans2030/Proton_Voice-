"""Application settings, read from STUDYBOT_* environment variables or a .env file."""
import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_home() -> Path:
    """Runtime data root. Kept outside OneDrive so sync never touches live databases."""
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "StudyBot"
    return Path.home() / ".studybot"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STUDYBOT_", env_file=".env", extra="ignore")

    home: Path = Field(default_factory=default_home)
    host: str = "127.0.0.1"
    port: int = 8000
    ollama_url: str = "http://127.0.0.1:11434"
    llm_model: str = "gemma2:2b"
    num_ctx: int = 4096  # Ollama's default is 2048, which silently truncates RAG prompts

    embed_model: str = "BAAI/bge-small-en-v1.5"
    rerank_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    use_reranker: bool = False
    # Chunks sent to the LLM. On this GPU, prompt processing dominates latency (~130 tok/s):
    # 4 chunks gave ~6 s to first token vs ~11 s with 6, with no accuracy loss on a 12-question test.
    retrieve_k: int = 4
    candidates: int = 30
    # Below this best-match cosine (bge-small), skip the LLM and say "not in your materials".
    # 0.55 is provisional: it falsely refused 0 of 67 answerable questions on the golden set. Re-run
    # `python -m eval.run_retrieval` to recalibrate as the golden set grows.
    min_dense_score: float = 0.55

    # Sizes are approximate tokens; bge-small truncates input at 512.
    chunk_target_tokens: int = 320
    chunk_max_tokens: int = 420
    chunk_min_tokens: int = 80
    chunk_overlap_tokens: int = 40

    @field_validator("home")
    @classmethod
    def home_must_not_be_synced(cls, value: Path) -> Path:
        if any("onedrive" in part.lower() for part in value.resolve().parts):
            raise ValueError(
                f"STUDYBOT_HOME={value} is inside OneDrive. Syncing live SQLite/vector "
                "files corrupts them; choose a path outside OneDrive."
            )
        return value

    @property
    def data_dir(self) -> Path:
        return self.home / "data"

    @property
    def uploads_dir(self) -> Path:
        return self.home / "uploads"

    @property
    def index_dir(self) -> Path:
        return self.home / "index"

    @property
    def logs_dir(self) -> Path:
        return self.home / "logs"

    @property
    def backups_dir(self) -> Path:
        return self.home / "backups"

    @property
    def models_dir(self) -> Path:
        """Embedding/reranker model files. Never the OS temp dir, which Windows may clean."""
        return self.home / "models"

    @property
    def cache_dir(self) -> Path:
        return self.home / "cache"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "studybot.db"

    def ensure_dirs(self) -> None:
        for directory in (self.data_dir, self.uploads_dir, self.index_dir, self.logs_dir,
                          self.backups_dir, self.models_dir, self.cache_dir):
            directory.mkdir(parents=True, exist_ok=True)
