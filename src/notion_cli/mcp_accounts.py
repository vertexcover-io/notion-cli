"""Multi-account management for MCP server."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir
from pydantic import BaseModel

from .config import ConfigManager


@dataclass
class NotionAccount:
    """Represents a Notion account configuration."""

    account_id: str
    email: str
    workspace_name: str
    integration_token: str
    is_default: bool = False
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AccountConfig(BaseModel):
    """Configuration model for account storage."""

    accounts: dict[str, dict[str, Any]] = {}
    default_account_id: str | None = None


class AccountManager:
    """Manages multiple Notion accounts for MCP server."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize account manager."""
        if config_path:
            self.accounts_path = config_path
        else:
            config_dir = Path(user_config_dir("notion", "notion"))
            self.accounts_path = config_dir / "mcp_accounts.json"

        # Ensure directory exists
        self.accounts_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize with legacy config if no accounts exist
        self._migrate_legacy_config()

    def _migrate_legacy_config(self) -> None:
        """Migrate from legacy single-account config to multi-account."""
        if self.accounts_path.exists():
            return

        # Check if legacy config exists
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()

            if config.integration_token:
                # Create default account from legacy config
                account = NotionAccount(
                    account_id="default",
                    email="migrated@legacy.com",
                    workspace_name="Legacy Workspace",
                    integration_token=config.integration_token,
                    is_default=True,
                )
                self.add_account(account)
        except Exception:
            # If migration fails, continue without it
            pass

    def load_accounts(self) -> AccountConfig:
        """Load all accounts from storage."""
        if not self.accounts_path.exists():
            return AccountConfig()

        try:
            with open(self.accounts_path) as f:
                data = json.load(f)
            return AccountConfig(**data)
        except (json.JSONDecodeError, ValueError):
            return AccountConfig()

    def save_accounts(self, config: AccountConfig) -> None:
        """Save accounts to storage."""
        with open(self.accounts_path, "w") as f:
            json.dump(config.model_dump(), f, indent=2)

    def add_account(self, account: NotionAccount) -> None:
        """Add or update an account."""
        config = self.load_accounts()

        # If this is the first account, make it default
        if not config.accounts:
            account.is_default = True
            config.default_account_id = account.account_id

        # If setting as default, unset previous default
        if account.is_default:
            for acc_data in config.accounts.values():
                acc_data["is_default"] = False
            config.default_account_id = account.account_id

        config.accounts[account.account_id] = asdict(account)
        self.save_accounts(config)

    def remove_account(self, account_id: str) -> bool:
        """Remove an account."""
        config = self.load_accounts()

        if account_id not in config.accounts:
            return False

        was_default = config.accounts[account_id].get("is_default", False)
        del config.accounts[account_id]

        # If removed account was default, set first remaining as default
        if was_default and config.accounts:
            first_account_id = next(iter(config.accounts.keys()))
            config.accounts[first_account_id]["is_default"] = True
            config.default_account_id = first_account_id
        elif was_default:
            config.default_account_id = None

        self.save_accounts(config)
        return True

    def get_account(self, account_id: str) -> NotionAccount | None:
        """Get account by ID."""
        config = self.load_accounts()

        if account_id not in config.accounts:
            return None

        account_data = config.accounts[account_id]
        return NotionAccount(**account_data)

    def get_default_account(self) -> NotionAccount | None:
        """Get the default account."""
        config = self.load_accounts()

        if not config.default_account_id:
            return None

        return self.get_account(config.default_account_id)

    def list_accounts(self) -> list[NotionAccount]:
        """List all accounts."""
        config = self.load_accounts()
        accounts = []

        for account_data in config.accounts.values():
            accounts.append(NotionAccount(**account_data))

        return accounts

    def set_default_account(self, account_id: str) -> bool:
        """Set an account as default."""
        config = self.load_accounts()

        if account_id not in config.accounts:
            return False

        # Unset previous default
        for acc_data in config.accounts.values():
            acc_data["is_default"] = False

        # Set new default
        config.accounts[account_id]["is_default"] = True
        config.default_account_id = account_id

        self.save_accounts(config)
        return True

    def test_account_connection(self, account_id: str) -> bool:
        """Test if an account's token is valid."""
        account = self.get_account(account_id)
        if not account:
            return False

        try:
            from notion_client import Client

            client = Client(auth=account.integration_token)
            client.users.me()
            return True
        except Exception:
            return False
