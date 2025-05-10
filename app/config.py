from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    MONGODB_URI: str = Field(default="mongodb://localhost:27017", env="MONGODB_URI")
    MONGODB_DB: str = Field(default="globeco_security_service", env="MONGODB_DB")

settings = Settings()
