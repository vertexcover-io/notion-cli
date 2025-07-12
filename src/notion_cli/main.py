"""Main CLI application entry point."""

import shutil

import typer
from rich.console import Console
from rich.table import Table

from .client import NotionClientWrapper
from .config import ConfigManager
from .filters import FilterParser, NotionFilterConverter
from .views import DatabaseView, ViewsManager

app = typer.Typer(
    help="A CLI tool for Notion database operations using natural language"
)
auth_app = typer.Typer(help="Authentication commands")
db_app = typer.Typer(help="Database commands")
view_app = typer.Typer(help="View management commands")

app.add_typer(auth_app, name="auth")
app.add_typer(db_app, name="db")
app.add_typer(view_app, name="view")

console = Console()


@auth_app.command("setup")
def setup_auth(
    token: str = typer.Option(..., "--token", "-t", help="Notion integration token"),
) -> None:
    """Set up authentication with Notion integration token."""
    try:
        config_manager = ConfigManager()
        config_manager.set_token(token)

        # Test the connection
        client = NotionClientWrapper(config_manager)
        if client.test_connection():
            console.print("✅ Authentication successful!", style="green")
            console.print(f"Config saved to: {config_manager.config_path}")
        else:
            console.print(
                "❌ Authentication failed. Please check your token.", style="red"
            )

    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


@auth_app.command("test")
def test_auth() -> None:
    """Test the current authentication."""
    try:
        client = NotionClientWrapper()
        if client.test_connection():
            console.print("✅ Authentication is working!", style="green")
        else:
            console.print("❌ Authentication failed.", style="red")
            raise typer.Exit(1)

    except ValueError as e:
        console.print(f"❌ {e}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


@db_app.command("list")
def list_databases() -> None:
    """List all accessible databases."""
    try:
        client = NotionClientWrapper()
        databases = client.list_databases()

        if not databases:
            console.print("No databases found.", style="yellow")
            return

        table = Table(title="Notion Databases")
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="magenta")
        table.add_column("URL", style="blue")

        for db in databases:
            # Extract database title
            title = "Untitled"
            if "title" in db and db["title"]:
                if isinstance(db["title"], list) and db["title"]:
                    title = db["title"][0].get("plain_text", "Untitled")
                elif isinstance(db["title"], str):
                    title = db["title"]

            # Get database ID and URL
            db_id = db.get("id", "")
            db_url = db.get("url", "")

            table.add_row(title, db_id, db_url)

        console.print(table)

    except ValueError as e:
        console.print(f"❌ {e}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


@db_app.command("show")
def show_database(
    name: str = typer.Argument(..., help="Database name to show entries for"),
    limit: int | None = typer.Option(
        None, "--limit", "-l", help="Number of entries to show"
    ),
    columns: str = typer.Option(
        None, "--columns", "-c", help="Comma-separated list of columns to show"
    ),
    filter_expr: str = typer.Option(
        None,
        "--filter",
        "-f",
        help="Filter expression (e.g., 'status=Done', 'tags in urgent')",
    ),
    save_view: str = typer.Option(
        None,
        "--save-view",
        help="Save current view with the given name",
    ),
) -> None:
    """Show entries in a specific database by name."""
    try:
        client = NotionClientWrapper()
        database = client.get_database_by_name(name)

        if not database:
            console.print(f"❌ Database '{name}' not found.", style="red")
            console.print(
                "Use 'notion-cli db list' to see available databases.", style="yellow"
            )
            raise typer.Exit(1)

        # Get database info
        db_title = "Untitled"
        if "title" in database and database["title"]:
            if isinstance(database["title"], list) and database["title"]:
                db_title = database["title"][0].get("plain_text", "Untitled")

        database_id = database.get("id", "")

        # Get database properties
        properties = database.get("properties", {})
        if not properties:
            console.print("No properties found in database schema.", style="yellow")
            return

        # Parse filter if provided
        filter_conditions = None
        if filter_expr:
            try:
                parser = FilterParser()
                converter = NotionFilterConverter()
                parsed_filters = parser.parse(filter_expr)
                filter_conditions = converter.convert(parsed_filters, properties)
                msg = f"\n📋 Database: {db_title} (filtered)"
                console.print(msg, style="bold cyan")
            except Exception as e:
                console.print(f"❌ Filter error: {e}", style="red")
                raise typer.Exit(1)
        else:
            console.print(f"\n📋 Database: {db_title}", style="bold cyan")

        # Get all entries with filtering applied (no limit yet)
        all_entries = client.get_database_entries(database_id, None, filter_conditions)

        # Apply limit after filtering
        if limit is not None:
            entries = all_entries[:limit]
            console.print(f"Showing {len(entries)} of {len(all_entries)} entries:\n")
        else:
            entries = all_entries
            console.print(f"Showing all {len(entries)} entries:\n")

        if not entries:
            console.print("No entries found in this database.", style="yellow")
            return

        # Parse user-specified columns
        user_columns = None
        if columns:
            user_columns = [col.strip() for col in columns.split(",")]

        # Get terminal width for dynamic sizing
        terminal_width = shutil.get_terminal_size().columns

        # Calculate optimal columns and widths
        displayed_props, column_widths = client.calculate_optimal_columns(
            properties, terminal_width, user_columns
        )

        if not displayed_props:
            console.print("No suitable columns found to display.", style="yellow")
            return

        # Create table with dynamic columns
        entries_table = Table(title=f"Entries from '{db_title}'")

        # Add columns with calculated widths
        for i, prop_name in enumerate(displayed_props):
            width = column_widths[i] if i < len(column_widths) else 20
            entries_table.add_column(prop_name, style="white", max_width=width)

        # Add rows
        for entry in entries:
            entry_properties = entry.get("properties", {})
            row_values = []

            for i, prop_name in enumerate(displayed_props):
                prop_data = entry_properties.get(prop_name, {})
                value = client.extract_property_value(prop_data)
                # Truncate based on column width, handling rich markup
                max_len = column_widths[i] - 3 if i < len(column_widths) else 20

                # Check if this is a rich markup link
                if "[link=" in value and "]" in value and "[/link]" in value:
                    # For links, preserve the markup but truncate the display text
                    try:
                        link_start = value.find("[link=")
                        link_end = value.find("]", link_start) + 1
                        display_start = link_end
                        display_end = value.find("[/link]")

                        if display_end > display_start:
                            url_part = value[link_start:link_end]
                            display_text = value[display_start:display_end]

                            # Reserve space for markup
                            if len(display_text) > max_len - 10:
                                display_text = display_text[:max_len - 13] + "..."

                            value = f"{url_part}{display_text}[/link]"
                    except (ValueError, IndexError):
                        # Fallback to simple truncation if parsing fails
                        if len(value) > max_len:
                            value = value[:max_len - 3] + "..."
                else:
                    # Simple truncation for non-link text
                    if len(value) > max_len:
                        value = value[:max_len - 3] + "..."

                row_values.append(value or "—")

            entries_table.add_row(*row_values)

        console.print(entries_table)

        # Show helpful information
        total_properties = len(properties)
        displayed_count = len(displayed_props)

        if user_columns:
            invalid_columns = [col for col in user_columns if col not in properties]
            if invalid_columns:
                invalid_str = ", ".join(invalid_columns)
                console.print(
                    f"\n⚠️  Invalid columns ignored: {invalid_str}", style="yellow"
                )

        if displayed_count < total_properties:
            msg = f"\n💡 Showing {displayed_count} of {total_properties} properties"
            console.print(msg, style="dim")

            # Show available columns hint
            all_columns = list(properties.keys())
            available = [col for col in all_columns if col not in displayed_props][:5]
            if available:
                available_str = ", ".join(available)
                suffix = "..." if len(available) == 5 else ""
                console.print(
                    f"💡 Available columns: {available_str}{suffix}", style="dim"
                )

        if limit is not None and len(all_entries) > limit:
            remaining = len(all_entries) - limit
            msg = (
                f"💡 {remaining} more entries available. Use --limit to see more "
                "or remove --limit to see all."
            )
            console.print(msg, style="dim")

        # Save view if requested
        if save_view:
            try:
                views_manager = ViewsManager()
                view = DatabaseView(
                    name=save_view,
                    database_name=name,
                    columns=user_columns,
                    filter_expr=filter_expr,
                    limit=limit,
                    description=f"Saved view for {name} database"
                )
                views_manager.save_view(view)
                msg = f"✅ View '{save_view}' saved successfully!"
                console.print(msg, style="green")
            except Exception as e:
                console.print(f"❌ Failed to save view: {e}", style="red")

        # Show usage hint for custom columns
        if not user_columns and displayed_count < total_properties:
            console.print("💡 Use --columns to specify custom columns", style="dim")

    except ValueError as e:
        console.print(f"❌ {e}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


# View management commands

@view_app.command("list")
def list_views() -> None:
    """List all saved views."""
    try:
        views_manager = ViewsManager()
        views = views_manager.list_views()

        if not views:
            console.print("No saved views found.", style="yellow")
            return

        table = Table(title="Saved Views")
        table.add_column("Name", style="cyan")
        table.add_column("Database", style="green")
        table.add_column("Columns", style="blue")
        table.add_column("Filter", style="magenta")
        table.add_column("Limit", style="white")

        for view in views:
            columns_str = ", ".join(view.columns) if view.columns else "All"
            filter_str = view.filter_expr if view.filter_expr else "None"
            limit_str = str(view.limit) if view.limit else "All"

            table.add_row(
                view.name,
                view.database_name,
                columns_str,
                filter_str,
                limit_str
            )

        console.print(table)

    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


@view_app.command("show")
def show_view(
    view_name: str = typer.Argument(..., help="Name of the view to show")
) -> None:
    """Show a database using a saved view."""
    try:
        views_manager = ViewsManager()
        view = views_manager.load_view(view_name)

        if not view:
            console.print(f"❌ View '{view_name}' not found.", style="red")
            msg = "Use 'notion-cli view list' to see available views."
            console.print(msg, style="yellow")
            raise typer.Exit(1)

        # Call the show_database function with the view's parameters
        show_database(
            name=view.database_name,
            limit=view.limit,
            columns=", ".join(view.columns) if view.columns else None,
            filter_expr=view.filter_expr,
            save_view=None  # Don't save when loading a view
        )

    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


@view_app.command("delete")
def delete_view(
    view_name: str = typer.Argument(..., help="Name of the view to delete")
) -> None:
    """Delete a saved view."""
    try:
        views_manager = ViewsManager()

        if views_manager.delete_view(view_name):
            console.print(f"✅ View '{view_name}' deleted successfully!", style="green")
        else:
            console.print(f"❌ View '{view_name}' not found.", style="red")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


@app.command("version")
def version() -> None:
    """Show the version."""
    from . import __version__

    console.print(f"notion-cli version {__version__}")


if __name__ == "__main__":
    app()
