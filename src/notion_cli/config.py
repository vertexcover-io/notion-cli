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
    llm_model: str | None = None
    llm_api_key: str | None = None
    default_database: str | None = None
    default_view: str | None = None


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

        # Override with environment variables if set
        if env_token := os.getenv("NOTION_TOKEN"):
            config_data["integration_token"] = env_token
        if llm_model := os.getenv("NOTION_CLI_LLM_MODEL"):
            config_data["llm_model"] = llm_model
        # Legacy support for API keys from environment
        if openai_key := os.getenv("OPENAI_API_KEY"):
            config_data["llm_api_key"] = openai_key
            if not config_data.get("llm_model"):
                config_data["llm_model"] = "gpt-4.1-mini"
        elif anthropic_key := os.getenv("ANTHROPIC_API_KEY"):
            config_data["llm_api_key"] = anthropic_key
            if not config_data.get("llm_model"):
                config_data["llm_model"] = "claude-3-haiku-20240307"
        elif google_key := os.getenv("GOOGLE_API_KEY"):
            config_data["llm_api_key"] = google_key
            if not config_data.get("llm_model"):
                config_data["llm_model"] = "gemini-pro"

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

    def set_llm_config(self, model: str, api_key: str) -> None:
        """Set LLM model and API key."""
        config = self.load_config()
        config.llm_model = model
        config.llm_api_key = api_key
        self.save_config(config)

    def get_llm_config(self) -> tuple[str | None, str | None]:
        """Get LLM model and API key."""
        config = self.load_config()
        return config.llm_model, config.llm_api_key

    def set_default_database(self, database_name: str) -> None:
        """Set the default database."""
        config = self.load_config()
        config.default_database = database_name
        self.save_config(config)

    def get_default_database(self) -> str | None:
        """Get the default database."""
        config = self.load_config()
        return config.default_database

    def set_default_view(self, view_name: str) -> None:
        """Set the default view."""
        config = self.load_config()
        config.default_view = view_name
        self.save_config(config)

    def get_default_view(self) -> str | None:
        """Get the default view."""
        config = self.load_config()
        return config.default_view
