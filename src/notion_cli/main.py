"""Main CLI application entry point."""

import typer
from rich.console import Console
from rich.table import Table

from .client import NotionClientWrapper
from .config import ConfigManager

app = typer.Typer(
    help="A CLI tool for Notion database operations using natural language"
)
auth_app = typer.Typer(help="Authentication commands")
db_app = typer.Typer(help="Database commands")

app.add_typer(auth_app, name="auth")
app.add_typer(db_app, name="db")

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
    limit: int = typer.Option(10, "--limit", "-l", help="Number of entries to show"),
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

        # Get database entries
        console.print(f"\n📋 Database: {db_title}", style="bold cyan")
        console.print(f"Showing {limit} entries:\n")

        entries = client.get_database_entries(database_id, limit)

        if not entries:
            console.print("No entries found in this database.", style="yellow")
            return

        # Get property names from database schema
        properties = database.get("properties", {})
        property_names = list(properties.keys())

        if not property_names:
            console.print("No properties found in database schema.", style="yellow")
            return

        # Create table with dynamic columns
        entries_table = Table(title=f"Entries from '{db_title}'")

        # Add columns for each property (limit to avoid wide tables)
        displayed_props = property_names[:6]  # Show max 6 columns
        for prop_name in displayed_props:
            entries_table.add_column(prop_name, style="white", max_width=30)

        # Add rows
        for entry in entries:
            entry_properties = entry.get("properties", {})
            row_values = []

            for prop_name in displayed_props:
                prop_data = entry_properties.get(prop_name, {})
                value = client.extract_property_value(prop_data)
                # Truncate long values for table display
                if len(value) > 50:
                    value = value[:47] + "..."
                row_values.append(value or "—")

            entries_table.add_row(*row_values)

        console.print(entries_table)

        # Show info about truncated data
        if len(property_names) > 6:
            displayed_count = len(displayed_props)
            total_count = len(property_names)
            msg = f"\n💡 Showing {displayed_count} of {total_count} properties"
            console.print(msg, style="dim")

        if len(entries) == limit:
            msg = f"💡 Showing first {limit} entries. Use --limit to see more."
            console.print(msg, style="dim")

    except ValueError as e:
        console.print(f"❌ {e}", style="red")
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
