from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    MONGODB_URI: str = Field(default="mongodb://localhost:27017", env="MONGODB_URI")
    MONGODB_DB: str = Field(default="securities", env="MONGODB_DB")  # Database for GlobeCo Security Service

settings = Settings()
