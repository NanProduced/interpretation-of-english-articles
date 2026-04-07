from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_project_root() -> Path:
    return Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "Claread透读"
    app_env: str = "development"
    log_level: str = "INFO"
    default_model_profile: str = ""
    annotation_model_profile: str = ""
    model_profiles_json: str = ""
    model_presets_json: str = ""
    langsmith_enabled: bool = False
    langsmith_tracing: bool = True
    langsmith_project: str = "english-article-interpretation-dev"
    langsmith_api_key: str = ""
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_workspace_id: str = ""

    # 数据库
    database_url: str = "postgresql://claread:claread_dev@127.0.0.1:5432/claread"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_max_inactive_connection_lifetime: int = 3600

    # Redis（可选，第二阶段增强）
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_enabled: bool = False  # False = 不尝试连接，启动不阻塞

    # 微信认证
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    auth_session_expiry_days: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def resolve_config_path(self, path: str) -> str:
        if not path:
            return path
        if os.path.isabs(path):
            return path
        if path.startswith("config/"):
            return str(_get_project_root() / path)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
