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
        self,
        database_id: str,
        limit: int | None = None,
        filter_conditions: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Get entries from a database with pagination support."""
        try:
            all_entries = []
            start_cursor = None

            while True:
                # If limit is None, get all entries (max 100 per page)
                # If limit is set, calculate remaining entries needed
                if limit is None:
                    page_size = 100  # Notion API max per page
                else:
                    remaining = limit - len(all_entries)
                    if remaining <= 0:
                        break
                    page_size = min(100, remaining)

                response = self.query_database(
                    database_id=database_id,
                    filter_conditions=filter_conditions,
                    start_cursor=start_cursor,
                    page_size=page_size,
                )

                entries = response.get("results", [])
                all_entries.extend(entries)

                # Check if there are more pages
                if not response.get("has_more", False):
                    break

                start_cursor = response.get("next_cursor")
                if not start_cursor:
                    break

            # Apply limit if specified
            if limit is not None:
                return all_entries[:limit]
            else:
                return all_entries
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
            url = property_data["url"]
            # Extract domain name for display
            try:
                from urllib.parse import urlparse

                parsed = urlparse(url)
                domain = parsed.netloc or url
                return f"[link={url}]{domain}[/link]"
            except Exception:
                return url
        elif prop_type == "email" and property_data.get("email"):
            email = property_data["email"]
            return f"[link=mailto:{email}]{email}[/link]"
        elif prop_type == "phone_number" and property_data.get("phone_number"):
            return property_data["phone_number"]
        elif prop_type == "people" and property_data.get("people"):
            return ", ".join([p.get("name", "") for p in property_data["people"]])
        elif prop_type == "files" and property_data.get("files"):
            files = property_data["files"]
            if not files:
                return "—"
            elif len(files) == 1:
                # Show single file with name and link
                file_obj = files[0]
                if file_obj.get("type") == "external":
                    # External file - show name and URL
                    name = file_obj.get("name", "File")
                    url = file_obj.get("external", {}).get("url", "")
                    if url:
                        return f"[link={url}]{name}[/link]"
                    else:
                        return name
                elif file_obj.get("type") == "file":
                    # Notion-hosted file - show name and URL
                    name = file_obj.get("name", "File")
                    url = file_obj.get("file", {}).get("url", "")
                    if url:
                        return f"[link={url}]{name}[/link]"
                    else:
                        return name
                else:
                    return file_obj.get("name", "File")
            else:
                # Multiple files - show count and first file name
                first_file = files[0]
                first_name = first_file.get("name", "File")
                return f"{first_name} (+{len(files) - 1} more)"
        elif prop_type == "status" and property_data.get("status"):
            return property_data["status"].get("name", "")
        else:
            return str(property_data.get(prop_type, ""))[:50]  # Truncate long values

    def prioritize_columns(self, properties: dict[str, Any]) -> list[str]:
        """Prioritize columns based on importance and type."""
        # Define priority levels
        high_priority = []
        medium_priority = []
        low_priority = []
        hidden_types = {
            "created_by",
            "last_edited_by",
            "created_time",
            "last_edited_time",
        }

        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type", "")
            prop_name_lower = prop_name.lower()

            # Skip hidden types
            if prop_type in hidden_types:
                continue

            # High priority: title-like properties
            if prop_type == "title" or prop_name_lower in {
                "name",
                "title",
                "task",
                "item",
                "entry",
            }:
                high_priority.append(prop_name)

            # High priority: status-like properties
            elif prop_type in {"status", "select"} and prop_name_lower in {
                "status",
                "state",
                "stage",
                "phase",
                "priority",
            }:
                high_priority.append(prop_name)

            # Medium priority: important data types
            elif prop_type in {"date", "number", "checkbox", "people", "multi_select"}:
                medium_priority.append(prop_name)

            # Medium priority: common important names
            elif prop_name_lower in {
                "assignee",
                "owner",
                "due",
                "deadline",
                "tags",
                "category",
                "type",
            }:
                medium_priority.append(prop_name)

            # Low priority: everything else
            else:
                low_priority.append(prop_name)

        # Combine in priority order
        return high_priority + medium_priority + low_priority

    def calculate_optimal_columns(
        self,
        properties: dict[str, Any],
        terminal_width: int,
        user_columns: list[str] | None = None,
    ) -> tuple[list[str], list[int]]:
        """Calculate optimal columns and widths based on terminal size."""
        if user_columns:
            # User specified columns - validate they exist
            valid_columns = [col for col in user_columns if col in properties]
            if not valid_columns:
                # Fallback to prioritized if no valid user columns
                prioritized = self.prioritize_columns(properties)
                valid_columns = prioritized
            columns = valid_columns
        else:
            # Use smart prioritization
            columns = self.prioritize_columns(properties)

        # Calculate available width (account for borders and spacing)
        # Each column needs: content + 2 spaces + 1 border = 3 extra chars minimum
        border_overhead = len(columns) * 3 + 1  # +1 for final border
        available_width = max(terminal_width - border_overhead, 60)  # Increased minimum

        # Calculate widths
        widths = []
        if not columns:
            return [], []

        # Define priority weights for different column types
        min_width = 8  # Minimum readable width

        # First pass: assign base widths based on column type importance
        type_weights = {}
        total_weight = 0

        for col_name in columns:
            prop_data = properties.get(col_name, {})
            prop_type = prop_data.get("type", "")

            # Assign weights based on content type and importance
            if prop_type == "title":
                weight = 3.0  # Titles need more space
            elif prop_type in {"rich_text", "url", "email"}:
                weight = 2.5  # Text content needs space
            elif prop_type in {"select", "status", "multi_select"}:
                weight = 1.5  # Status/select moderate space
            elif prop_type == "files":
                weight = 2.0  # File names can be long
            elif prop_type in {"date", "number"}:
                weight = 1.0  # Dates/numbers are compact
            elif prop_type == "checkbox":
                weight = 0.5  # Checkboxes minimal space
            else:
                weight = 1.5  # Default moderate space

            type_weights[col_name] = weight
            total_weight += weight

        # Second pass: distribute available width proportionally
        for col_name in columns:
            if total_weight > 0:
                weight_ratio = type_weights[col_name] / total_weight
                proportional_width = int(weight_ratio * available_width)
                width = max(proportional_width, min_width)
            else:
                width = min_width

            widths.append(width)

        # If we exceed terminal width, trim columns from the end
        total_width = sum(widths) + border_overhead
        while total_width > terminal_width and len(columns) > 1:
            columns.pop()
            widths.pop()
            total_width = sum(widths) + border_overhead

        return columns, widths
