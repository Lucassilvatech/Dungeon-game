from typing import Literal
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
    medical_fee_base: int = Field(default=100, ge=0)
    respawn_hp_percent: int = Field(default=100, ge=1, le=100)
    min_auction_start_price: int = Field(default=1, ge=1)
    auction_duration_hours: float = Field(default=24, gt=0)
    auction_proceeds_destination: Literal["treasury", "sink"] = "treasury"
    auction_sweep_seconds: float = Field(default=30, ge=1)
    adventure_boss_increment: float = Field(default=0.01, ge=0, le=0.09)
    procedural_proximity_k: float = Field(default=3, ge=0, le=10)
    procedural_level_weight: float = Field(default=0.65, ge=0, le=1)
    encounter_max_enemies: int = Field(default=2, ge=2, le=3)
    encounter_radius: int = Field(default=8, ge=1, le=12)
    collection_slots: int = Field(default=30, ge=1, le=1000)
    lunar_resource_spawn_enabled: bool = True
    lunar_resource_spawn_chance_ppm: int = Field(default=20000, ge=0, le=1000000)
    lunar_resource_weight_bands: list[dict[str, int]] = Field(
        default_factory=lambda: [
            {"min_g": 100, "max_g": 200, "percent": 80},
            {"min_g": 201, "max_g": 700, "percent": 15},
            {"min_g": 701, "max_g": 1000, "percent": 5},
        ]
    )
    lunar_guild_buy_rate_milliunits_per_gram: int = Field(
        default=800, ge=0, le=1000000000
    )
    royal_admin_extraordinary_controls_enabled: bool = True
    # Legacy configuration keys are compatibility only, never current pricing/generation.
    lunar_resource_weight_distribution: dict[str, int] = Field(
        default_factory=lambda: {
            "nugget_small": 90,
            "nugget_medium": 9,
            "nugget_large": 1,
        }
    )
    lunar_guild_prices: dict[str, int] = Field(
        default_factory=lambda: {
            "nugget_small": 0,
            "nugget_medium": 0,
            "nugget_large": 0,
        }
    )
    max_active_contracts: int = Field(default=3, ge=1, le=10)
    rate_limits_enabled: bool = True
    rate_limit_scale: float = Field(default=1, ge=0.01, le=10)
    discord_service_key: str = ""
    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()


def runtime_setting(db, name):
    from .models import GameSetting

    row = db.get(GameSetting, name)
    return row.value["value"] if row else getattr(settings, name)
