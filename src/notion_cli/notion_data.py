"""Utilities for converting data to Notion API format."""

from typing import Any


class NotionDataConverter:
    """Converts structured data to Notion API format."""

    @staticmethod
    def convert_to_notion_properties(
        data: dict[str, Any],
        properties_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert structured data to Notion properties format."""
        notion_properties = {}

        for field_name, value in data.items():
            if field_name not in properties_schema or value is None:
                continue

            prop_schema = properties_schema[field_name]
            prop_type = prop_schema.get("type", "")

            # Convert based on property type
            if prop_type == "title":
                notion_properties[field_name] = {
                    "title": [{"text": {"content": str(value)}}],
                }
            elif prop_type == "rich_text":
                notion_properties[field_name] = {
                    "rich_text": [{"text": {"content": str(value)}}],
                }
            elif prop_type == "number":
                try:
                    notion_properties[field_name] = {"number": float(value)}
                except (ValueError, TypeError):
                    continue
            elif prop_type == "select":
                notion_properties[field_name] = {"select": {"name": str(value)}}
            elif prop_type == "multi_select":
                if isinstance(value, list):
                    notion_properties[field_name] = {
                        "multi_select": [{"name": str(v)} for v in value],
                    }
                else:
                    # Handle comma-separated string
                    values = [v.strip() for v in str(value).split(",")]
                    notion_properties[field_name] = {
                        "multi_select": [{"name": v} for v in values],
                    }
            elif prop_type == "date":
                # Expect ISO date format
                notion_properties[field_name] = {"date": {"start": str(value)}}
            elif prop_type == "checkbox":
                notion_properties[field_name] = {"checkbox": bool(value)}
            elif prop_type == "url":
                notion_properties[field_name] = {"url": str(value)}
            elif prop_type == "email":
                notion_properties[field_name] = {"email": str(value)}
            elif prop_type == "phone_number":
                notion_properties[field_name] = {"phone_number": str(value)}
            elif prop_type == "status":
                notion_properties[field_name] = {"status": {"name": str(value)}}
            elif prop_type == "people":
                # For people, we'd need user IDs, which is complex
                # Skip for now or handle as text
                continue
            elif prop_type == "files":
                # Handle file properties
                if value == "__FILE__":
                    # Special marker for file upload - will be handled separately
                    continue
                elif isinstance(value, list):
                    # List of file objects
                    notion_properties[field_name] = {"files": value}
                elif isinstance(value, dict):
                    # Single file object
                    notion_properties[field_name] = {"files": [value]}
                else:
                    # Skip other values for files
                    continue
            else:
                # Default to rich text for unknown types
                notion_properties[field_name] = {
                    "rich_text": [{"text": {"content": str(value)}}],
                }

        return notion_properties

    @staticmethod
    def extract_simple_values(notion_properties: dict[str, Any]) -> dict[str, Any]:
        """Extract simple values from Notion properties for display."""
        simple_data = {}

        for prop_name, prop_data in notion_properties.items():
            prop_type = prop_data.get("type", "")

            if prop_type == "title" and prop_data.get("title"):
                simple_data[prop_name] = "".join(
                    [t.get("plain_text", "") for t in prop_data["title"]],
                )
            elif prop_type == "rich_text" and prop_data.get("rich_text"):
                simple_data[prop_name] = "".join(
                    [t.get("plain_text", "") for t in prop_data["rich_text"]],
                )
            elif prop_type == "number":
                simple_data[prop_name] = prop_data.get("number")
            elif prop_type == "select" and prop_data.get("select"):
                simple_data[prop_name] = prop_data["select"].get("name", "")
            elif prop_type == "multi_select" and prop_data.get("multi_select"):
                simple_data[prop_name] = [s.get("name", "") for s in prop_data["multi_select"]]
            elif prop_type == "date" and prop_data.get("date"):
                simple_data[prop_name] = prop_data["date"].get("start", "")
            elif prop_type == "checkbox":
                simple_data[prop_name] = prop_data.get("checkbox", False)
            elif prop_type == "url":
                simple_data[prop_name] = prop_data.get("url", "")
            elif prop_type == "email":
                simple_data[prop_name] = prop_data.get("email", "")
            elif prop_type == "phone_number":
                simple_data[prop_name] = prop_data.get("phone_number", "")
            elif prop_type == "status" and prop_data.get("status"):
                simple_data[prop_name] = prop_data["status"].get("name", "")
            else:
                simple_data[prop_name] = str(prop_data)

        return simple_data
