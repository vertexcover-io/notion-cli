"""Configuration management for Notion CLI."""

import os
from pathlib import Path

import toml
from platformdirs import user_config_dir
from pydantic import BaseModel


class NotionConfig(BaseModel):
    """Configuration model for Notion CLI."""

    integration_token: str | None = None
    databases: dict[str, str] = {}


class ConfigManager:
    """Manages configuration file operations."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize config manager with optional custom path."""
        if config_path:
            self.config_path = config_path
        else:
            # Use platformdirs to get the proper config directory for the platform
            config_dir = Path(user_config_dir("notion", "notion"))
            self.config_path = config_dir / "config.toml"

        # Ensure the config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> NotionConfig:
        """Load configuration from file or environment."""
        config_data = {}

        # Load from file if exists
        if self.config_path.exists():
            config_data = toml.load(self.config_path)

        # Override with environment variable if set
        if env_token := os.getenv("NOTION_TOKEN"):
            config_data["integration_token"] = env_token

        return NotionConfig(**config_data)

    def save_config(self, config: NotionConfig) -> None:
        """Save configuration to file."""
        config_dict = config.model_dump(exclude_none=True)
        with open(self.config_path, "w") as f:
            toml.dump(config_dict, f)

    def set_token(self, token: str) -> None:
        """Set the integration token."""
        config = self.load_config()
        config.integration_token = token
        self.save_config(config)

    def add_database(self, name: str, database_id: str) -> None:
        """Add a database mapping."""
        config = self.load_config()
        config.databases[name] = database_id
        self.save_config(config)
