from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEDIA_BATCH_",
        extra="ignore",
    )

    database_url: str | None = None
    dashboard_database_url: str | None = None
    source_bucket: str = "ktooh-raw"
    timezone_name: str = "UTC"
    raw_source_root: Path = Path("../project-pooh-kt/docs")
    local_demographic_filename: str = "demographic.jsonl"
    local_floating_filename: str = "floating.jsonl"
    include_pedestrian_pattern: bool = False
    traffic_direction_mode: str = "status"

    def effective_dashboard_database_url(self) -> str | None:
        return self.dashboard_database_url or self.database_url
