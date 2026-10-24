from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://tower:tower@localhost:5432/tower"
    initial_treasury: int = 100000
    monster_reward: int = 10
    boss_reward: int = 100
    discord_service_key: str = ""
    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
