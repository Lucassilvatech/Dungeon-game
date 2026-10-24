from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://tower:tower@localhost:5432/tower"
    initial_treasury: int = 100000
    monster_reward: int = 10
    boss_reward: int = 100
    secret_chance: float = Field(default=0.25, ge=0, le=1)
    secret_first_reward: int = Field(default=250, ge=0)
    secret_repeat_reward: int = Field(default=1, ge=0)
    damage_min: int = Field(default=2, ge=1)
    damage_max: int = Field(default=999, ge=1)
    skill_bonus: int = Field(default=5, ge=0)
    guard_bonus: int = Field(default=4, ge=0)
    wander_interval: float = Field(default=4, ge=1)
    discord_service_key: str = ""
    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
