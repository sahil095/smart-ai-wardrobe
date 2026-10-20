"""Application configuration loaded from environment / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# Always load the project-root .env, even if uvicorn is started from another cwd.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Prefer the project .env over a stale Windows/user GROQ_API_KEY.
        # On Render there is usually no .env, so dashboard env vars still win.
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    # Database
    database_url: str = "sqlite:///./wardrobe.db"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    # Cloudinary (optional -> local fallback if unset)
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # Outfit engine
    outfit_count: int = 2

    # Image standardization (Cloudinary on-the-fly transformations)
    standardize_images: bool = True
    image_bg_color: str = "F5F6F8"  # hex without '#'
    image_aspect: str = "1:1"  # e.g. "1:1" or "3:4"

    # Wardrobe gap analysis cache
    gap_cache_hours: int = 24

    @field_validator(
        "groq_api_key",
        "groq_model",
        "cloudinary_cloud_name",
        "cloudinary_api_key",
        "cloudinary_api_secret",
        "image_bg_color",
        "image_aspect",
        mode="before",
    )
    @classmethod
    def _strip_whitespace(cls, v):
        # Guard against trailing spaces / newlines / surrounding quotes that
        # commonly sneak into copied API keys and cause 401s.
        if isinstance(v, str):
            return v.strip().strip('"').strip("'").strip()
        return v

    @property
    def cloudinary_enabled(self) -> bool:
        return bool(
            self.cloudinary_cloud_name
            and self.cloudinary_api_key
            and self.cloudinary_api_secret
        )

    @property
    def groq_enabled(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
