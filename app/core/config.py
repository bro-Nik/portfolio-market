import os


class Settings:
    JWT_SECRET: str = os.getenv("JWT_SECRET", '')
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", '')


settings = Settings()
