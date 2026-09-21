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
    llm_model: str = "llama3.2:3b"

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

    def ensure_dirs(self) -> None:
        for directory in (self.data_dir, self.uploads_dir, self.index_dir, self.logs_dir, self.backups_dir):
            directory.mkdir(parents=True, exist_ok=True)
