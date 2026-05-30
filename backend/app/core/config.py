from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="INSIGHTPILOT_",
        extra="ignore",
    )

    env: str = "development"
    database_url: str = "sqlite:///./data/insightpilot.sqlite"
    upload_dir: str = "../sample-data/uploads"
    export_dir: str = "../sample-data/exports"
    sample_dataset_path: str = "../sample-data/saas_growth_sample.csv"
    max_upload_mb: int = Field(default=25, ge=1)
    preview_row_limit: int = Field(default=20, ge=1, le=200)
    enable_ai_narrative: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "ENABLE_AI_NARRATIVE",
            "INSIGHTPILOT_ENABLE_AI_NARRATIVE",
            "INSIGHTPILOT_ENABLE_LLM_REPORT_REWRITE",
        ),
    )
    ai_narrative_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AI_NARRATIVE_API_KEY",
            "INSIGHTPILOT_AI_NARRATIVE_API_KEY",
            "INSIGHTPILOT_LLM_API_KEY",
        ),
    )
    ai_narrative_base_url: str = Field(
        default="https://api.openai.com/v1/chat/completions",
        validation_alias=AliasChoices(
            "AI_NARRATIVE_BASE_URL",
            "INSIGHTPILOT_AI_NARRATIVE_BASE_URL",
        ),
    )
    ai_narrative_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices(
            "AI_NARRATIVE_MODEL",
            "INSIGHTPILOT_AI_NARRATIVE_MODEL",
        ),
    )
    cors_origins_raw: str = Field(
        default="http://localhost:3000",
        validation_alias="INSIGHTPILOT_CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
