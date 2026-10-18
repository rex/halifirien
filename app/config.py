"""Runtime settings, read from the environment (see .env.example)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every knob the beacon has. Hosts and URLs arrive as env; the code names none."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"

    interval_seconds: int = 900
    uptime_days: int = 90
    source_timeout_seconds: float = 10.0

    topology_path: Path = Path("/var/lib/halifirien/topology/topology.json")
    gatus_url: str = "http://localhost:8080"
    metrics_url: str = "http://localhost:8428"
    alertmanager_url: str = "http://localhost:9093"

    publish_enabled: bool = False
    s3_bucket: str = ""
    s3_key: str = "status/status.json"
    s3_cache_control: str = "public, max-age=60"
    aws_region: str = "us-east-1"

    app_version: str = "dev"


@lru_cache
def get_settings() -> Settings:
    """The process-wide settings, built once."""
    return Settings()
