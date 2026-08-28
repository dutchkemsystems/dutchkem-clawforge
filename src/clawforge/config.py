"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Wallet Configuration
    CLAW_EARN_WALLET: str
    CLAW_EARN_PRIVATE_KEY: str
    CLAW_VAULT_KEY: str = ""

    # API Configuration
    CLAW_EARN_BASE_URL: str = "https://aiagentstore.ai"

    # CORS Configuration
    CORS_ORIGINS: list[str] = ["*"]  # Override in production

    # Storage Paths
    MEMORY_PATH: str = "./data/memory"
    AUDIT_PATH: str = "./data/audit"
    ECONOMY_PATH: str = "./data/economy"
    TASKS_PATH: str = "./data/tasks"
    CREDENTIALS_PATH: str = "./data/credentials"
    SENTINEL_PATH: str = "./data/sentinel"
    PROTOCOL_PATH: str = "./data/protocol"
    CONFIG_PATH: str = "./data/config"

    # Sentinel Configuration
    SENTINEL_HEARTBEAT_INTERVAL: int = 60
    SENTINEL_FRESHNESS_THRESHOLD: int = 90
    SENTINEL_DEAD_MAN_SWITCH: int = 300

    # Economy Configuration
    AUTO_STAKE_PERCENTAGE: float = 0.10
    MAX_GAS_FEE_WEI: int = 50000000000000000  # 0.05 ETH
    MAX_DAILY_STAKE_USDC: float = 1000.0

    # API Authentication
    API_KEY: str = ""  # Empty = auth disabled (for dev)

    # OpenAI (optional)
    OPENAI_API_KEY: str = ""

    def get_memory_path(self) -> Path:
        """Get memory directory path."""
        return Path(self.MEMORY_PATH)

    def get_audit_path(self) -> Path:
        """Get audit directory path."""
        return Path(self.AUDIT_PATH)

    def get_economy_path(self) -> Path:
        """Get economy directory path."""
        return Path(self.ECONOMY_PATH)

    def get_tasks_path(self) -> Path:
        """Get tasks directory path."""
        return Path(self.TASKS_PATH)

    def get_credentials_path(self) -> Path:
        """Get credentials directory path."""
        return Path(self.CREDENTIALS_PATH)

    def get_sentinel_path(self) -> Path:
        """Get sentinel directory path."""
        return Path(self.SENTINEL_PATH)

    def get_protocol_path(self) -> Path:
        """Get protocol directory path."""
        return Path(self.PROTOCOL_PATH)

    def get_config_path(self) -> Path:
        """Get config directory path."""
        return Path(self.CONFIG_PATH)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
