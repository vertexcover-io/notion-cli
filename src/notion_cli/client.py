"""Notion API client wrapper."""

from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from .config import ConfigManager


class NotionClientWrapper:
    """Wrapper around the official Notion client with additional functionality."""

    def __init__(self, config_manager: ConfigManager | None = None) -> None:
        """Initialize the Notion client wrapper."""
        self.config_manager = config_manager or ConfigManager()
        config = self.config_manager.load_config()

        if not config.integration_token:
            raise ValueError(
                "No Notion integration token found. "
                "Run 'notion-cli auth setup --token <your-token>' first."
            )

        self.client = Client(auth=config.integration_token)
        self.config = config

    def test_connection(self) -> bool:
        """Test if the connection to Notion is working."""
        try:
            self.client.users.me()
            return True
        except APIResponseError:
            return False

    def list_databases(self) -> list[dict[str, Any]]:
        """List all accessible databases."""
        try:
            response = self.client.search(
                filter={"property": "object", "value": "database"}
            )
            return response.get("results", [])
        except APIResponseError as e:
            raise Exception(f"Failed to list databases: {e}")

    def get_database_by_name(self, name: str) -> dict[str, Any] | None:
        """Get a database by its title."""
        databases = self.list_databases()

        for db in databases:
            db_title = ""
            if "title" in db and db["title"]:
                if isinstance(db["title"], list) and db["title"]:
                    db_title = db["title"][0].get("plain_text", "")
                elif isinstance(db["title"], str):
                    db_title = db["title"]

            if db_title.lower() == name.lower():
                return db

        return None

    def get_database_by_id(self, database_id: str) -> dict[str, Any]:
        """Get a database by its ID."""
        try:
            return self.client.databases.retrieve(database_id=database_id)
        except APIResponseError as e:
            raise Exception(f"Failed to get database {database_id}: {e}")

    def query_database(
        self,
        database_id: str,
        filter_conditions: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        start_cursor: str | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """Query a database with optional filters and sorting."""
        try:
            query_params = {}
            if filter_conditions:
                query_params["filter"] = filter_conditions
            if sorts:
                query_params["sorts"] = sorts
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            if page_size:
                query_params["page_size"] = page_size

            return self.client.databases.query(database_id=database_id, **query_params)
        except APIResponseError as e:
            raise Exception(f"Failed to query database {database_id}: {e}")

    def create_page(
        self, database_id: str, properties: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new page in a database."""
        try:
            return self.client.pages.create(
                parent={"database_id": database_id}, properties=properties
            )
        except APIResponseError as e:
            raise Exception(f"Failed to create page in database {database_id}: {e}")

    def update_page(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Update an existing page."""
        try:
            return self.client.pages.update(page_id=page_id, properties=properties)
        except APIResponseError as e:
            raise Exception(f"Failed to update page {page_id}: {e}")

    def delete_page(self, page_id: str) -> dict[str, Any]:
        """Delete a page (archive it)."""
        try:
            return self.client.pages.update(page_id=page_id, archived=True)
        except APIResponseError as e:
            raise Exception(f"Failed to delete page {page_id}: {e}")

    def get_database_entries(
        self, database_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get entries from a database with pagination support."""
        try:
            all_entries = []
            start_cursor = None

            while len(all_entries) < limit:
                page_size = min(100, limit - len(all_entries))  # Notion API max is 100

                response = self.query_database(
                    database_id=database_id,
                    start_cursor=start_cursor,
                    page_size=page_size
                )

                entries = response.get("results", [])
                all_entries.extend(entries)

                # Check if there are more pages
                if not response.get("has_more", False):
                    break

                start_cursor = response.get("next_cursor")
                if not start_cursor:
                    break

            return all_entries[:limit]
        except Exception as e:
            raise Exception(f"Failed to get entries from database {database_id}: {e}")

    def extract_property_value(self, property_data: dict[str, Any]) -> str:
        """Extract a readable value from a Notion property."""
        if not property_data:
            return ""

        prop_type = property_data.get("type", "")

        if prop_type == "title" and property_data.get("title"):
            return "".join([t.get("plain_text", "") for t in property_data["title"]])
        elif prop_type == "rich_text" and property_data.get("rich_text"):
            rich_text = property_data["rich_text"]
            return "".join([t.get("plain_text", "") for t in rich_text])
        elif prop_type == "number" and property_data.get("number") is not None:
            return str(property_data["number"])
        elif prop_type == "select" and property_data.get("select"):
            return property_data["select"].get("name", "")
        elif prop_type == "multi_select" and property_data.get("multi_select"):
            return ", ".join([s.get("name", "") for s in property_data["multi_select"]])
        elif prop_type == "date" and property_data.get("date"):
            start = property_data["date"].get("start", "")
            end = property_data["date"].get("end", "")
            return f"{start}" + (f" → {end}" if end else "")
        elif prop_type == "checkbox":
            return "✓" if property_data.get("checkbox", False) else "✗"
        elif prop_type == "url" and property_data.get("url"):
            return property_data["url"]
        elif prop_type == "email" and property_data.get("email"):
            return property_data["email"]
        elif prop_type == "phone_number" and property_data.get("phone_number"):
            return property_data["phone_number"]
        elif prop_type == "people" and property_data.get("people"):
            return ", ".join([p.get("name", "") for p in property_data["people"]])
        elif prop_type == "files" and property_data.get("files"):
            return f"{len(property_data['files'])} file(s)"
        elif prop_type == "status" and property_data.get("status"):
            return property_data["status"].get("name", "")
        else:
            return str(property_data.get(prop_type, ""))[:50]  # Truncate long values
