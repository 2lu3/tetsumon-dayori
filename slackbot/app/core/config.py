"""設定管理"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Slack設定
    SLACK_SIGNING_SECRET: str
    SLACK_BOT_TOKEN: str
    SLACK_TASK_CHANNEL_ID: str
    
    # データベース設定
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/slackbot"
    
    # Redis設定
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # OpenAI設定
    OPENAI_API_KEY: str
    
    # タイムゾーン
    TIMEZONE: str = "Asia/Tokyo"  # JST


settings = Settings()
