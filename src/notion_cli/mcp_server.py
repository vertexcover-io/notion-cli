"""MCP server implementation for Notion CLI AI."""

import sys
import traceback
from typing import Any

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from .client import NotionClientWrapper
from .config import ConfigManager
from .filters import FilterParser, NotionFilterConverter
from .llm import get_default_llm_service
from .mcp_accounts import AccountManager, NotionAccount
from .mcp_cache import MCPCacheManager
from .notion_data import NotionDataConverter
from .views import DatabaseView, ViewsManager


# Pydantic models for tool parameters
class AccountSwitchParams(BaseModel):
    account_id: str = Field(description="ID of the account to switch to")


class DatabaseQueryParams(BaseModel):
    database_name: str | None = Field(None, description="Name or prefix of database to query")
    filter_expr: str | None = Field(None, description="Filter expression for querying")
    columns: list[str] | None = Field(None, description="Specific columns to return")
    limit: int | None = Field(None, description="Maximum number of results to return")
    sort_by: str | None = Field(None, description="Column to sort by")
    sort_descending: bool | None = Field(False, description="Sort in descending order")


class CreateEntryParams(BaseModel):
    database_name: str = Field(description="Name of database to create entry in")
    entry_data: dict[str, Any] = Field(description="Entry data as key-value pairs")


class UpdateEntryParams(BaseModel):
    database_name: str = Field(description="Name of database containing the entry")
    entry_id: str = Field(description="ID of entry to update")
    updates: dict[str, Any] = Field(description="Updates as key-value pairs")


class TextToEntryParams(BaseModel):
    database_name: str = Field(description="Name of database to create entry in")
    text_description: str = Field(description="Natural language description of the entry")


class TextToFilterParams(BaseModel):
    database_name: str = Field(description="Name of database to generate filter for")
    filter_description: str = Field(description="Natural language description of the filter")


class ViewParams(BaseModel):
    view_name: str = Field(description="Name of the view")


class SaveViewParams(BaseModel):
    view_name: str = Field(description="Name for the saved view")
    database_name: str = Field(description="Database name the view is for")
    columns: list[str] | None = Field(None, description="Columns to include in view")
    filter_expr: str | None = Field(None, description="Filter expression for view")
    limit: int | None = Field(None, description="Result limit for view")
    description: str | None = Field(None, description="Description of the view")


class SearchPagesParams(BaseModel):
    query: str | None = Field(None, description="Search query text")
    filter_expr: str | None = Field(None, description="Filter expression")
    limit: int | None = Field(20, description="Maximum results to return")


class PageParams(BaseModel):
    page_id: str = Field(description="ID of the page")


class MCPServer:
    """MCP Server for Notion CLI AI operations."""

    def __init__(self, cache_enabled: bool = False) -> None:
        """Initialize MCP server."""
        self.account_manager = AccountManager()
        self.cache_manager = MCPCacheManager(enabled=cache_enabled)
        self.views_manager = ViewsManager()

        # Current session account (per-client context)
        self.current_account_id: str | None = None

        # Initialize FastMCP server
        self.mcp = FastMCP("Notion CLI AI Server")
        self._register_tools()

    def _get_current_account(self) -> NotionAccount:
        """Get the current account for operations."""
        if self.current_account_id:
            account = self.account_manager.get_account(self.current_account_id)
            if account:
                return account

        # Fall back to default account
        default_account = self.account_manager.get_default_account()
        if default_account:
            self.current_account_id = default_account.account_id
            return default_account

        raise ValueError("No account available. Please add an account first.")

    def _get_notion_client(self) -> NotionClientWrapper:
        """Get Notion client for current account."""
        account = self._get_current_account()

        # Create temporary config for this account
        config_manager = ConfigManager()
        config = config_manager.load_config()
        config.integration_token = account.integration_token

        return NotionClientWrapper(config_manager)

    def _cached_operation(self, operation: str, params: dict[str, Any], func):
        """Execute operation with caching support."""
        account = self._get_current_account()

        # Try cache first for read operations
        if operation not in self.cache_manager.WRITE_OPERATIONS:
            cached_result = self.cache_manager.get(account.account_id, operation, params)
            if cached_result is not None:
                return cached_result

        # Execute operation
        result = func()

        # Cache result for read operations
        if operation not in self.cache_manager.WRITE_OPERATIONS:
            self.cache_manager.set(account.account_id, operation, params, result)
        else:
            # Invalidate related cache entries for write operations
            self.cache_manager.invalidate_related_operations(account.account_id, operation)

        return result

    def _register_tools(self) -> None:
        """Register all MCP tools."""

        @self.mcp.tool
        def list_accounts(ctx: Context) -> list[dict[str, Any]]:
            """List all configured Notion accounts."""
            try:
                accounts = self.account_manager.list_accounts()
                return [
                    {
                        "account_id": acc.account_id,
                        "email": acc.email,
                        "workspace_name": acc.workspace_name,
                        "is_default": acc.is_default,
                        "is_current": acc.account_id == self.current_account_id,
                    }
                    for acc in accounts
                ]
            except Exception as e:
                return {"error": str(e)}

        @self.mcp.tool
        def switch_account(ctx: Context, params: AccountSwitchParams) -> dict[str, Any]:
            """Switch to a different account for subsequent operations."""
            try:
                account = self.account_manager.get_account(params.account_id)
                if not account:
                    return {"error": f"Account '{params.account_id}' not found"}

                # Test connection
                if not self.account_manager.test_account_connection(params.account_id):
                    return {
                        "error": f"Cannot connect to account '{params.account_id}'. Check token."
                    }

                self.current_account_id = params.account_id
                return {
                    "success": True,
                    "account_id": params.account_id,
                    "email": account.email,
                    "workspace_name": account.workspace_name,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp.tool
        def list_databases(ctx: Context) -> list[dict[str, Any]]:
            """List all accessible Notion databases."""

            def _list_databases():
                try:
                    client = self._get_notion_client()
                    databases = client.list_databases()

                    result = []
                    for db in databases:
                        title = ""
                        if "title" in db and db["title"]:
                            if isinstance(db["title"], list) and db["title"]:
                                title = db["title"][0].get("plain_text", "")
                            elif isinstance(db["title"], str):
                                title = db["title"]

                        result.append(
                            {
                                "id": db["id"],
                                "title": title,
                                "url": db.get("url", ""),
                                "created_time": db.get("created_time", ""),
                                "last_edited_time": db.get("last_edited_time", ""),
                            }
                        )

                    return result
                except Exception as e:
                    return {"error": str(e)}

            return self._cached_operation("list_databases", {}, _list_databases)

        @self.mcp.tool
        def get_database(ctx: Context, database_name: str) -> dict[str, Any]:
            """Get detailed information about a specific database."""

            def _get_database():
                try:
                    client = self._get_notion_client()
                    db = client.get_database_by_name_or_prefix(database_name, interactive=False)

                    if not db:
                        return {"error": f"Database '{database_name}' not found"}

                    # Extract database properties for schema info
                    properties = {}
                    if "properties" in db:
                        for prop_name, prop_data in db["properties"].items():
                            properties[prop_name] = {
                                "type": prop_data.get("type", "unknown"),
                                "id": prop_data.get("id", ""),
                            }

                    title = ""
                    if "title" in db and db["title"]:
                        if isinstance(db["title"], list) and db["title"]:
                            title = db["title"][0].get("plain_text", "")
                        elif isinstance(db["title"], str):
                            title = db["title"]

                    return {
                        "id": db["id"],
                        "title": title,
                        "url": db.get("url", ""),
                        "properties": properties,
                        "created_time": db.get("created_time", ""),
                        "last_edited_time": db.get("last_edited_time", ""),
                    }
                except Exception as e:
                    return {"error": str(e)}

            return self._cached_operation(
                "get_database", {"database_name": database_name}, _get_database
            )

        @self.mcp.tool
        def query_database(ctx: Context, params: DatabaseQueryParams) -> dict[str, Any]:
            """Query a database with optional filters and formatting."""

            def _query_database():
                try:
                    client = self._get_notion_client()

                    # Get database name (use default if not provided)
                    if not params.database_name:
                        config_manager = ConfigManager()
                        default_db = config_manager.get_default_database()
                        if not default_db:
                            return {"error": "No database specified and no default database set"}
                        database_name = default_db
                    else:
                        database_name = params.database_name

                    # Get database
                    db = client.get_database_by_name_or_prefix(database_name, interactive=False)
                    if not db:
                        return {"error": f"Database '{database_name}' not found"}

                    # Build query
                    query_params = {}

                    # Add filter if provided
                    if params.filter_expr:
                        try:
                            parser = FilterParser()
                            converter = NotionFilterConverter(db)
                            parsed_filter = parser.parse(params.filter_expr)
                            notion_filter = converter.convert_filter(parsed_filter)
                            query_params["filter"] = notion_filter
                        except Exception as e:
                            return {"error": f"Filter error: {str(e)}"}

                    # Add sorting if provided
                    if params.sort_by:
                        query_params["sorts"] = [
                            {
                                "property": params.sort_by,
                                "direction": "descending"
                                if params.sort_descending
                                else "ascending",
                            }
                        ]

                    # Add page size limit
                    if params.limit:
                        query_params["page_size"] = min(params.limit, 100)

                    # Execute query
                    response = client.client.databases.query(db["id"], **query_params)

                    # Convert results
                    converter = NotionDataConverter(db)
                    results = []

                    for page in response.get("results", []):
                        converted = converter.convert_page_properties(page)

                        # Filter columns if specified
                        if params.columns:
                            filtered = {}
                            for col in params.columns:
                                if col in converted:
                                    filtered[col] = converted[col]
                            converted = filtered

                        results.append(converted)

                    return {
                        "results": results,
                        "count": len(results),
                        "has_more": response.get("has_more", False),
                    }

                except Exception as e:
                    return {"error": str(e)}

            cache_params = params.model_dump()
            return self._cached_operation("query_database", cache_params, _query_database)

        @self.mcp.tool
        def create_database_entry(ctx: Context, params: CreateEntryParams) -> dict[str, Any]:
            """Create a new entry in a database."""
            try:
                client = self._get_notion_client()

                # Get database
                db = client.get_database_by_name_or_prefix(params.database_name, interactive=False)
                if not db:
                    return {"error": f"Database '{params.database_name}' not found"}

                # Convert entry data to Notion format
                converter = NotionDataConverter(db)
                notion_properties = converter.convert_to_notion_properties(params.entry_data)

                # Create page
                response = client.client.pages.create(
                    parent={"database_id": db["id"]}, properties=notion_properties
                )

                # Trigger cache invalidation
                account = self._get_current_account()
                self.cache_manager.invalidate_related_operations(
                    account.account_id, "create_database_entry"
                )

                return {"success": True, "page_id": response["id"], "url": response.get("url", "")}

            except Exception as e:
                return {"error": str(e)}

        @self.mcp.tool
        def list_views(ctx: Context) -> list[dict[str, Any]]:
            """List all saved database views."""

            def _list_views():
                try:
                    views = self.views_manager.load_all_views()
                    return [
                        {
                            "name": view.name,
                            "database_name": view.database_name,
                            "description": view.description,
                            "columns": view.columns,
                            "filter_expr": view.filter_expr,
                            "limit": view.limit,
                        }
                        for view in views.values()
                    ]
                except Exception as e:
                    return {"error": str(e)}

            return self._cached_operation("list_views", {}, _list_views)

        @self.mcp.tool
        def get_view(ctx: Context, params: ViewParams) -> dict[str, Any]:
            """Get details of a specific saved view."""

            def _get_view():
                try:
                    view = self.views_manager.load_view_by_name_or_prefix(
                        params.view_name, interactive=False
                    )
                    if not view:
                        return {"error": f"View '{params.view_name}' not found"}

                    return {
                        "name": view.name,
                        "database_name": view.database_name,
                        "description": view.description,
                        "columns": view.columns,
                        "filter_expr": view.filter_expr,
                        "limit": view.limit,
                    }
                except Exception as e:
                    return {"error": str(e)}

            return self._cached_operation("get_view", {"view_name": params.view_name}, _get_view)

        @self.mcp.tool
        def save_view(ctx: Context, params: SaveViewParams) -> dict[str, Any]:
            """Save a new database view."""
            try:
                # Create view object
                view = DatabaseView(
                    name=params.view_name,
                    database_name=params.database_name,
                    columns=params.columns,
                    filter_expr=params.filter_expr,
                    limit=params.limit,
                    description=params.description,
                )

                # Save view
                self.views_manager.save_view(view)

                # Trigger cache invalidation
                account = self._get_current_account()
                self.cache_manager.invalidate_related_operations(account.account_id, "save_view")

                return {
                    "success": True,
                    "view_name": params.view_name,
                    "message": f"View '{params.view_name}' saved successfully",
                }

            except Exception as e:
                return {"error": str(e)}

        @self.mcp.tool
        def delete_view(ctx: Context, params: ViewParams) -> dict[str, Any]:
            """Delete a saved view."""
            try:
                # Check if view exists
                view = self.views_manager.load_view_by_name_or_prefix(
                    params.view_name, interactive=False
                )
                if not view:
                    return {"error": f"View '{params.view_name}' not found"}

                # Delete view
                success = self.views_manager.delete_view(view.name)

                if success:
                    # Trigger cache invalidation
                    account = self._get_current_account()
                    self.cache_manager.invalidate_related_operations(
                        account.account_id, "delete_view"
                    )

                    return {"success": True, "message": f"View '{view.name}' deleted successfully"}
                else:
                    return {"error": f"Failed to delete view '{params.view_name}'"}

            except Exception as e:
                return {"error": str(e)}

        @self.mcp.tool
        def update_database_entry(ctx: Context, params: UpdateEntryParams) -> dict[str, Any]:
            """Update an existing database entry."""
            try:
                client = self._get_notion_client()

                # Get database for property conversion
                db = client.get_database_by_name_or_prefix(params.database_name, interactive=False)
                if not db:
                    return {"error": f"Database '{params.database_name}' not found"}

                # Convert updates to Notion format
                converter = NotionDataConverter(db)
                notion_properties = converter.convert_to_notion_properties(params.updates)

                # Update page
                response = client.client.pages.update(
                    page_id=params.entry_id, properties=notion_properties
                )

                # Trigger cache invalidation
                account = self._get_current_account()
                self.cache_manager.invalidate_related_operations(
                    account.account_id, "update_database_entry"
                )

                return {"success": True, "page_id": response["id"], "url": response.get("url", "")}

            except Exception as e:
                return {"error": str(e)}

        @self.mcp.tool
        def search_pages(ctx: Context, params: SearchPagesParams) -> dict[str, Any]:
            """Search for pages with optional filters."""

            def _search_pages():
                try:
                    client = self._get_notion_client()

                    # Build search parameters
                    search_params = {}

                    if params.query:
                        search_params["query"] = params.query

                    if params.filter_expr:
                        # Simple filter - could be enhanced with filter parser
                        search_params["filter"] = {"property": "object", "value": "page"}
                    else:
                        search_params["filter"] = {"property": "object", "value": "page"}

                    if params.limit:
                        search_params["page_size"] = min(params.limit, 100)

                    # Execute search
                    response = client.client.search(**search_params)

                    # Format results
                    results = []
                    for page in response.get("results", []):
                        title = ""
                        if "properties" in page and "title" in page["properties"]:
                            title_prop = page["properties"]["title"]
                            if "title" in title_prop and title_prop["title"]:
                                title = title_prop["title"][0].get("plain_text", "")

                        results.append(
                            {
                                "id": page["id"],
                                "title": title,
                                "url": page.get("url", ""),
                                "created_time": page.get("created_time", ""),
                                "last_edited_time": page.get("last_edited_time", ""),
                            }
                        )

                    return {
                        "results": results,
                        "count": len(results),
                        "has_more": response.get("has_more", False),
                    }

                except Exception as e:
                    return {"error": str(e)}

            cache_params = params.model_dump()
            return self._cached_operation("search_pages", cache_params, _search_pages)

        @self.mcp.tool
        def get_page(ctx: Context, params: PageParams) -> dict[str, Any]:
            """Get details of a specific page."""

            def _get_page():
                try:
                    client = self._get_notion_client()

                    # Get page
                    response = client.client.pages.retrieve(params.page_id)

                    # Extract title
                    title = ""
                    if "properties" in response and "title" in response["properties"]:
                        title_prop = response["properties"]["title"]
                        if "title" in title_prop and title_prop["title"]:
                            title = title_prop["title"][0].get("plain_text", "")

                    return {
                        "id": response["id"],
                        "title": title,
                        "url": response.get("url", ""),
                        "created_time": response.get("created_time", ""),
                        "last_edited_time": response.get("last_edited_time", ""),
                        "properties": response.get("properties", {}),
                    }

                except Exception as e:
                    return {"error": str(e)}

            return self._cached_operation("get_page", {"page_id": params.page_id}, _get_page)

        @self.mcp.tool
        def generate_entry_from_text(ctx: Context, params: TextToEntryParams) -> dict[str, Any]:
            """Create database entry from natural language description using AI."""
            try:
                client = self._get_notion_client()

                # Get database to understand schema
                db = client.get_database_by_name_or_prefix(params.database_name, interactive=False)
                if not db:
                    return {"error": f"Database '{params.database_name}' not found"}

                # Get LLM service
                llm_service = get_default_llm_service()

                # Generate structured data from text
                entry_data = llm_service.generate_database_entry(params.text_description, db)

                # Convert to Notion format and create entry
                converter = NotionDataConverter(db)
                notion_properties = converter.convert_to_notion_properties(entry_data)

                response = client.client.pages.create(
                    parent={"database_id": db["id"]}, properties=notion_properties
                )

                # Trigger cache invalidation
                account = self._get_current_account()
                self.cache_manager.invalidate_related_operations(
                    account.account_id, "create_database_entry"
                )

                return {
                    "success": True,
                    "page_id": response["id"],
                    "url": response.get("url", ""),
                    "generated_data": entry_data,
                    "source_text": params.text_description,
                }

            except Exception as e:
                return {"error": str(e)}

        @self.mcp.tool
        def generate_filter_from_text(ctx: Context, params: TextToFilterParams) -> dict[str, Any]:
            """Generate database filter from natural language description."""
            try:
                client = self._get_notion_client()

                # Get database to understand schema
                db = client.get_database_by_name_or_prefix(params.database_name, interactive=False)
                if not db:
                    return {"error": f"Database '{params.database_name}' not found"}

                # Get LLM service
                llm_service = get_default_llm_service()

                # Generate filter expression
                filter_expr = llm_service.generate_filter_expression(params.filter_description, db)

                # Validate filter by parsing it
                try:
                    parser = FilterParser()
                    converter = NotionFilterConverter(db)
                    parsed_filter = parser.parse(filter_expr)
                    notion_filter = converter.convert_filter(parsed_filter)

                    return {
                        "success": True,
                        "filter_expression": filter_expr,
                        "description": params.filter_description,
                        "notion_filter": notion_filter,
                    }

                except Exception as parse_error:
                    return {
                        "error": f"Generated filter is invalid: {parse_error}",
                        "generated_filter": filter_expr,
                        "description": params.filter_description,
                    }

            except Exception as e:
                return {"error": str(e)}

        @self.mcp.tool
        def update_entry_from_text(
            ctx: Context, database_name: str, entry_id: str, text_description: str
        ) -> dict[str, Any]:
            """Update database entry using natural language description."""
            try:
                client = self._get_notion_client()

                # Get database and current entry
                db = client.get_database_by_name_or_prefix(database_name, interactive=False)
                if not db:
                    return {"error": f"Database '{database_name}' not found"}

                # Get current entry data
                current_page = client.client.pages.retrieve(entry_id)
                converter = NotionDataConverter(db)
                current_data = converter.convert_page_properties(current_page)

                # Get LLM service
                llm_service = get_default_llm_service()

                # Generate updates from text
                updates = llm_service.generate_database_update(text_description, db, current_data)

                # Convert to Notion format and update
                notion_properties = converter.convert_to_notion_properties(updates)

                response = client.client.pages.update(
                    page_id=entry_id, properties=notion_properties
                )

                # Trigger cache invalidation
                account = self._get_current_account()
                self.cache_manager.invalidate_related_operations(
                    account.account_id, "update_database_entry"
                )

                return {
                    "success": True,
                    "page_id": response["id"],
                    "url": response.get("url", ""),
                    "updates_applied": updates,
                    "source_text": text_description,
                }

            except Exception as e:
                return {"error": str(e)}

        # Cache management tools
        @self.mcp.tool
        def get_cache_stats(ctx: Context) -> dict[str, Any]:
            """Get cache statistics and information."""
            try:
                return self.cache_manager.get_cache_stats()
            except Exception as e:
                return {"error": str(e)}

        @self.mcp.tool
        def clear_cache(ctx: Context, account_id: str | None = None) -> dict[str, Any]:
            """Clear cache entries. If account_id provided, clear only for that account."""
            try:
                if account_id:
                    self.cache_manager.invalidate_account(account_id)
                    return {"success": True, "message": f"Cache cleared for account '{account_id}'"}
                else:
                    removed_count = self.cache_manager.clear_all()
                    return {
                        "success": True,
                        "message": f"All cache cleared. Removed {removed_count} entries.",
                    }
            except Exception as e:
                return {"error": str(e)}


def main():
    """Main entry point for the MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="Notion CLI AI MCP Server")
    parser.add_argument("--cache", action="store_true", help="Enable disk caching")
    parser.add_argument(
        "--transport", default="stdio", choices=["stdio", "sse", "http"], help="Transport protocol"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP/SSE transport")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE transport")
    parser.add_argument("--path", default="/mcp", help="Path for HTTP transport")

    args = parser.parse_args()

    try:
        # Initialize server
        server = MCPServer(cache_enabled=args.cache)

        # Run server with specified transport
        if args.transport == "stdio":
            server.mcp.run(transport="stdio")
        elif args.transport == "sse":
            server.mcp.run(transport="sse", host=args.host, port=args.port)
        elif args.transport == "http":
            server.mcp.run(transport="http", host=args.host, port=args.port, path=args.path)

    except KeyboardInterrupt:
        print("\nMCP server stopped.")
    except Exception as e:
        print(f"Error starting MCP server: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
