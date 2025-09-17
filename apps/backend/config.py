from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DATABASE_URL format (aka DSN = Data Source Name/URL):
    # postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
    DATABASE_URL: str = (
        "postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma"
    )

    class Config:
        env_file = ".env"  # optional: load variables from a .env file in dev


settings = Settings()
