from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb: str = "fraud_db"
    
    rabbitmq_host: str = "rabbitmq"
    rabbit_heartbeat: int = 60
    rabbit_url: str = "amqp://guest:guest@rabbitmq:5672/"

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra = "ignore"
    )

settings = Settings()