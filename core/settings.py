from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    FIREBASE_CREDENTIAL: SecretStr
    SERP_API_KEY: SecretStr
    GEMINI_API_KEY: SecretStr
    VIETMAP_API_KEY: SecretStr
    GEOHASH_PRECISION: int = 5

    HOTEL_DATA_EXPIRE_DAYS: int = 30

    # R2 Storage
    R2_ENDPOINT_URL: str
    R2_ACCESS_KEY_ID: SecretStr
    R2_SECRET_ACCESS_KEY: SecretStr
    R2_BUCKET: str
    R2_REGION: str = "auto"
    R2_PUBLIC_CDN: str

    # Upload policy
    R2_PRESIGN_EXPIRE_SECONDS: int = 300
    R2_MAX_FILE_SIZE_MB: int = 10
    R2_ALLOWED_IMAGE_MIME_TYPES: str = "image/jpeg,image/png,image/webp,image/gif"
    UPLOAD_PENDING_TTL_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore