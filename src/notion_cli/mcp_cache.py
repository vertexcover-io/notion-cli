"""Optional disk caching layer for MCP server operations."""

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir


@dataclass
class CacheEntry:
    """Represents a cache entry."""

    key: str
    data: Any
    timestamp: float
    ttl_seconds: int
    account_id: str
    operation: str

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds <= 0:  # No expiration
            return False
        return time.time() - self.timestamp > self.ttl_seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        """Create from dictionary."""
        return cls(**data)


class MCPCacheManager:
    """Manages disk-based caching for MCP operations."""

    # Default TTL values in seconds
    DEFAULT_TTLS = {
        "list_databases": 300,  # 5 minutes
        "get_database": 180,  # 3 minutes
        "query_database": 60,  # 1 minute
        "list_views": 300,  # 5 minutes
        "get_view": 300,  # 5 minutes
        "search_pages": 120,  # 2 minutes
        "get_page": 180,  # 3 minutes
        "default": 120,  # 2 minutes default
    }

    # Operations that should invalidate cache on write
    WRITE_OPERATIONS = {
        "create_database_entry",
        "update_database_entry",
        "delete_database_entry",
        "save_view",
        "delete_view",
        "create_page",
        "update_page",
    }

    def __init__(self, cache_dir: Path | None = None, enabled: bool = True) -> None:
        """Initialize cache manager."""
        self.enabled = enabled

        if cache_dir:
            self.cache_dir = cache_dir
        else:
            self.cache_dir = Path(user_cache_dir("notion-cli-ai", "cache"))

        # Ensure cache directory exists
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_cache_key(self, account_id: str, operation: str, params: dict[str, Any]) -> str:
        """Generate a unique cache key for operation and parameters."""
        # Create a stable hash from parameters
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]

        return f"{account_id}:{operation}:{params_hash}"

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        # Use first 2 chars of key for directory sharding
        shard_dir = self.cache_dir / cache_key[:2]
        shard_dir.mkdir(exist_ok=True)
        return shard_dir / f"{cache_key}.json"

    def _get_ttl_for_operation(self, operation: str) -> int:
        """Get TTL for specific operation."""
        return self.DEFAULT_TTLS.get(operation, self.DEFAULT_TTLS["default"])

    def get(self, account_id: str, operation: str, params: dict[str, Any]) -> Any | None:
        """Get cached result for operation."""
        if not self.enabled:
            return None

        cache_key = self._generate_cache_key(account_id, operation, params)
        cache_file = self._get_cache_file_path(cache_key)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                entry_data = json.load(f)

            entry = CacheEntry.from_dict(entry_data)

            # Check if expired
            if entry.is_expired():
                cache_file.unlink(missing_ok=True)
                return None

            return entry.data

        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            # Remove corrupted cache file
            cache_file.unlink(missing_ok=True)
            return None

    def set(self, account_id: str, operation: str, params: dict[str, Any], data: Any) -> None:
        """Cache result for operation."""
        if not self.enabled:
            return

        cache_key = self._generate_cache_key(account_id, operation, params)
        ttl = self._get_ttl_for_operation(operation)

        entry = CacheEntry(
            key=cache_key,
            data=data,
            timestamp=time.time(),
            ttl_seconds=ttl,
            account_id=account_id,
            operation=operation,
        )

        cache_file = self._get_cache_file_path(cache_key)

        try:
            with open(cache_file, "w") as f:
                json.dump(entry.to_dict(), f, indent=2)
        except Exception:
            # If caching fails, continue without error
            pass

    def invalidate_account(self, account_id: str) -> None:
        """Invalidate all cache entries for an account."""
        if not self.enabled:
            return

        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                with open(cache_file) as f:
                    entry_data = json.load(f)

                if entry_data.get("account_id") == account_id:
                    cache_file.unlink(missing_ok=True)

            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                cache_file.unlink(missing_ok=True)

    def invalidate_operation(self, account_id: str, operation: str) -> None:
        """Invalidate cache entries for specific operation."""
        if not self.enabled:
            return

        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                with open(cache_file) as f:
                    entry_data = json.load(f)

                entry_account = entry_data.get("account_id")
                entry_operation = entry_data.get("operation")

                if entry_account == account_id and entry_operation == operation:
                    cache_file.unlink(missing_ok=True)

            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                cache_file.unlink(missing_ok=True)

    def invalidate_related_operations(self, account_id: str, write_operation: str) -> None:
        """Invalidate cache entries related to a write operation."""
        if not self.enabled or write_operation not in self.WRITE_OPERATIONS:
            return

        # Map write operations to related read operations that should be invalidated
        invalidation_map = {
            "create_database_entry": ["list_databases", "query_database"],
            "update_database_entry": ["query_database", "get_database"],
            "delete_database_entry": ["query_database", "get_database"],
            "save_view": ["list_views"],
            "delete_view": ["list_views"],
            "create_page": ["search_pages"],
            "update_page": ["search_pages", "get_page"],
        }

        operations_to_invalidate = invalidation_map.get(write_operation, [])

        for operation in operations_to_invalidate:
            self.invalidate_operation(account_id, operation)

    def cleanup_expired(self) -> int:
        """Remove all expired cache entries. Returns number of entries removed."""
        if not self.enabled:
            return 0

        removed_count = 0

        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                with open(cache_file) as f:
                    entry_data = json.load(f)

                entry = CacheEntry.from_dict(entry_data)

                if entry.is_expired():
                    cache_file.unlink(missing_ok=True)
                    removed_count += 1

            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                cache_file.unlink(missing_ok=True)
                removed_count += 1

        return removed_count

    def clear_all(self) -> int:
        """Clear all cache entries. Returns number of entries removed."""
        if not self.enabled:
            return 0

        removed_count = 0

        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                cache_file.unlink()
                removed_count += 1
            except FileNotFoundError:
                pass

        return removed_count

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False}

        stats = {
            "enabled": True,
            "total_entries": 0,
            "expired_entries": 0,
            "cache_size_mb": 0,
            "entries_by_account": {},
            "entries_by_operation": {},
        }

        total_size = 0

        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                file_size = cache_file.stat().st_size
                total_size += file_size

                with open(cache_file) as f:
                    entry_data = json.load(f)

                entry = CacheEntry.from_dict(entry_data)
                stats["total_entries"] += 1

                if entry.is_expired():
                    stats["expired_entries"] += 1

                # Count by account
                account_id = entry.account_id
                if account_id not in stats["entries_by_account"]:
                    stats["entries_by_account"][account_id] = 0
                stats["entries_by_account"][account_id] += 1

                # Count by operation
                operation = entry.operation
                if operation not in stats["entries_by_operation"]:
                    stats["entries_by_operation"][operation] = 0
                stats["entries_by_operation"][operation] += 1

            except (json.JSONDecodeError, KeyError, FileNotFoundError, OSError):
                continue

        stats["cache_size_mb"] = round(total_size / (1024 * 1024), 2)
        return stats
