"""Notion API client wrapper."""

import os
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
                "Run 'notion auth setup --token <your-token>' first."
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

    def create_page_in_page(
        self, parent_page_id: str | None, title: str, children: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Create a new page within another page."""
        try:
            parent = {}
            if parent_page_id:
                parent = {"page_id": parent_page_id}
            
            return self.client.pages.create(
                parent=parent,
                properties={"title": {"title": [{"text": {"content": title}}]}},
                children=children,
            )
        except APIResponseError as e:
            raise Exception(f"Failed to create page: {e}")

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

    def upload_file(self, file_path: str) -> dict[str, Any]:
        """Upload a file to Notion and return the file object."""
        import os
        import mimetypes
        import requests
        
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # Check file size limit (20MB for single-part upload)
        max_size = 20 * 1024 * 1024  # 20MB in bytes
        if file_size > max_size:
            raise ValueError(f"File size ({file_size} bytes) exceeds 20MB limit for single-part upload")
        
        try:
            # Step 1: Create file upload object
            create_response = requests.post(
                "https://api.notion.com/v1/file_uploads",
                json={"filename": file_name},
                headers={
                    "Authorization": f"Bearer {self.config.integration_token}",
                    "Content-Type": "application/json",
                    "Notion-Version": "2022-06-28"
                }
            )
            create_response.raise_for_status()
            upload_data = create_response.json()
            
            file_upload_id = upload_data["id"]
            
            # Step 2: Upload file contents
            with open(file_path, "rb") as f:
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = "application/octet-stream"
                
                files = {"file": (file_name, f, mime_type)}
                upload_response = requests.post(
                    f"https://api.notion.com/v1/file_uploads/{file_upload_id}/send",
                    headers={
                        "Authorization": f"Bearer {self.config.integration_token}",
                        "Notion-Version": "2022-06-28"
                    },
                    files=files
                )
                upload_response.raise_for_status()
            
            # Return file object for use in properties
            # Use file_upload type with the upload ID
            return {
                "name": file_name,
                "type": "file_upload", 
                "file_upload": {
                    "id": file_upload_id
                }
            }
            
        except requests.exceptions.RequestException as e:
            if hasattr(e.response, 'json'):
                error_details = e.response.json()
                raise ValueError(f"File upload failed: {error_details}")
            else:
                raise ValueError(f"File upload failed: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error during file upload: {e}")

    def prepare_file_properties(
        self, 
        files: list[str], 
        file_properties: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        """Prepare file objects for Notion properties."""
        if not files:
            return {}
        
        file_objects = []
        for file_path in files:
            try:
                file_obj = self.upload_file(file_path)
                file_objects.append(file_obj)
                print(f"✅ Uploaded: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"❌ Failed to upload {os.path.basename(file_path)}: {e}")
                continue
        
        if not file_objects:
            return {}
        
        # Map files to file properties
        result = {}
        for prop_name in file_properties:
            result[prop_name] = file_objects
        
        return result

    def search_pages(self, query: str = "") -> list[dict[str, Any]]:
        """Search for pages in the workspace."""
        try:
            search_params = {
                "filter": {"property": "object", "value": "page"}
            }
            
            if query:
                search_params["query"] = query
            
            response = self.client.search(**search_params)
            return response.get("results", [])
        except APIResponseError as e:
            raise Exception(f"Failed to search pages: {e}")

    def get_page_by_name(self, name: str, fuzzy: bool = True) -> list[dict[str, Any]]:
        """Get pages by name with optional fuzzy matching."""
        all_pages = self.search_pages()
        
        if not all_pages:
            return []
        
        matching_pages = []
        name_lower = name.lower()
        
        for page in all_pages:
            page_title = self._extract_page_title(page)
            page_title_lower = page_title.lower()
            
            if fuzzy:
                # Fuzzy matching - check if query is contained in title
                if name_lower in page_title_lower:
                    matching_pages.append({
                        **page,
                        "_title": page_title,
                        "_match_score": self._calculate_match_score(name_lower, page_title_lower)
                    })
            else:
                # Exact matching
                if page_title_lower == name_lower:
                    matching_pages.append({
                        **page,
                        "_title": page_title,
                        "_match_score": 1.0
                    })
        
        # Sort by match score (higher is better)
        matching_pages.sort(key=lambda x: x["_match_score"], reverse=True)
        return matching_pages

    def _extract_page_title(self, page: dict[str, Any]) -> str:
        """Extract title from a page object."""
        properties = page.get("properties", {})
        
        # Look for title property
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_content = prop_data.get("title", [])
                if title_content:
                    return title_content[0].get("plain_text", "Untitled")
        
        # Fallback to page title in root
        if "title" in page and page["title"]:
            if isinstance(page["title"], list) and page["title"]:
                return page["title"][0].get("plain_text", "Untitled")
            elif isinstance(page["title"], str):
                return page["title"]
        
        return "Untitled"

    def _calculate_match_score(self, query: str, title: str) -> float:
        """Calculate a simple match score for fuzzy search."""
        if query == title:
            return 1.0
        elif title.startswith(query):
            return 0.9
        elif query in title:
            # Score based on how much of the title matches
            return len(query) / len(title)
        else:
            return 0.0

    def get_page_urls(self, page: dict[str, Any]) -> dict[str, str]:
        """Get both private and public URLs for a page."""
        page_id = page.get("id", "")
        notion_url = page.get("url", "")
        
        urls = {
            "private": notion_url,
            "public": None
        }
        
        # Check if page has public access
        # Note: Notion API doesn't directly expose public URL info
        # We can only provide the private URL and let users know about public sharing
        public_url = page.get("public_url")  # This field may not exist in API
        if public_url:
            urls["public"] = public_url
        
        return urls

    def get_database_entry_by_name(
        self, 
        database_name: str, 
        entry_name: str, 
        fuzzy: bool = True
    ) -> list[dict[str, Any]]:
        """Get database entries by searching for a specific name/title."""
        database = self.get_database_by_name(database_name)
        if not database:
            raise ValueError(f"Database '{database_name}' not found")
        
        database_id = database.get("id", "")
        properties = database.get("properties", {})
        
        # Get all entries
        all_entries = self.get_database_entries(database_id)
        
        if not all_entries:
            return []
        
        matching_entries = []
        entry_name_lower = entry_name.lower()
        
        for entry in all_entries:
            entry_properties = entry.get("properties", {})
            
            # Look for title-like properties
            entry_title = self._extract_entry_title(entry_properties)
            entry_title_lower = entry_title.lower()
            
            if fuzzy:
                # Fuzzy matching - check if query is contained in title
                if entry_name_lower in entry_title_lower:
                    matching_entries.append({
                        **entry,
                        "_title": entry_title,
                        "_match_score": self._calculate_match_score(entry_name_lower, entry_title_lower)
                    })
            else:
                # Exact matching
                if entry_title_lower == entry_name_lower:
                    matching_entries.append({
                        **entry,
                        "_title": entry_title,
                        "_match_score": 1.0
                    })
        
        # Sort by match score (higher is better)
        matching_entries.sort(key=lambda x: x["_match_score"], reverse=True)
        return matching_entries

    def _extract_entry_title(self, entry_properties: dict[str, Any]) -> str:
        """Extract title from database entry properties."""
        # Look for title property first
        for prop_name, prop_data in entry_properties.items():
            if prop_data.get("type") == "title":
                title_content = prop_data.get("title", [])
                if title_content:
                    return title_content[0].get("plain_text", "Untitled")
        
        # Look for common name fields
        name_fields = ["Name", "Title", "Task", "Subject", "Item"]
        for field_name in name_fields:
            if field_name in entry_properties:
                prop_data = entry_properties[field_name]
                value = self.extract_property_value(prop_data)
                if value and value.strip():
                    return value.strip()
        
        # Fallback to first text-like property
        for prop_name, prop_data in entry_properties.items():
            prop_type = prop_data.get("type", "")
            if prop_type in ["rich_text", "title"]:
                value = self.extract_property_value(prop_data)
                if value and value.strip():
                    return value.strip()
        
        return "Untitled"

    def get_entry_urls(self, entry: dict[str, Any]) -> dict[str, str]:
        """Get URLs for a database entry."""
        entry_id = entry.get("id", "")
        entry_url = entry.get("url", "")
        
        urls = {
            "private": entry_url,
            "public": None
        }
        
        # Check if entry has public access
        # Note: Database entries inherit public access from the database
        public_url = entry.get("public_url")  # This field may not exist in API
        if public_url:
            urls["public"] = public_url
        
        return urls
