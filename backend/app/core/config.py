from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str = ""
    JWT_SECRET: str = "change-me-in-production"
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    class Config:
        env_file = ".env"


settings = Settings()