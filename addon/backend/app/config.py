from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("./data")
    host: str = "0.0.0.0"
    port: int = 8099
    static_dir: Path = Path("./frontend/dist")
    ha_url: str = "http://supervisor/core"
    ha_token: str = ""
    allow_all_hosts: bool = True
    ingress_only_ip: str = "172.30.32.2"

    @field_validator("allow_all_hosts", mode="before")
    @classmethod
    def parse_bool(cls, v):  # noqa: ANN001
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes", "on")
        return v


settings = Settings()
