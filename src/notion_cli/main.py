"""Main CLI application entry point."""

import shutil

import typer
from rich.console import Console
from rich.table import Table

from .client import NotionClientWrapper
from .config import ConfigManager
from .filters import FilterParser, NotionFilterConverter
from .llm import get_default_llm_service
from .notion_data import NotionDataConverter
from .views import DatabaseView, ViewsManager

app = typer.Typer(
    help="A CLI tool for Notion database operations using natural language"
)
auth_app = typer.Typer(help="Authentication commands")
db_app = typer.Typer(help="Database commands")
view_app = typer.Typer(help="View management commands")
page_app = typer.Typer(help="Page management commands")

app.add_typer(auth_app, name="auth")
app.add_typer(db_app, name="db")
app.add_typer(view_app, name="view")
app.add_typer(page_app, name="page")

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


@view_app.command("update")
def update_view(
    view_name: str = typer.Argument(..., help="Name of the view to update"),
    columns: str = typer.Option(
        None, "--columns", "-c", help="Comma-separated list of columns to show"
    ),
    filter_expr: str = typer.Option(
        None,
        "--filter",
        "-f",
        help="Filter expression (e.g., 'status=Done', 'tags in urgent')",
    ),
    limit: int | None = typer.Option(
        None, "--limit", "-l", help="Number of entries to show"
    ),
    clear_filter: bool = typer.Option(
        False, "--clear-filter", help="Clear the current filter"
    ),
    clear_columns: bool = typer.Option(
        False, "--clear-columns", help="Clear custom columns (show all)"
    ),
    clear_limit: bool = typer.Option(
        False, "--clear-limit", help="Clear the limit (show all entries)"
    ),
) -> None:
    """Update an existing saved view with new filters, columns, or limits."""
    try:
        views_manager = ViewsManager()
        view = views_manager.load_view(view_name)

        if not view:
            console.print(f"❌ View '{view_name}' not found.", style="red")
            console.print(
                "Use 'notion-cli view list' to see available views.", style="yellow"
            )
            raise typer.Exit(1)

        # Track what's being updated
        updates = []

        # Update columns
        if clear_columns:
            view.columns = None
            updates.append("cleared columns")
        elif columns:
            view.columns = [col.strip() for col in columns.split(",")]
            updates.append(f"set columns to: {', '.join(view.columns)}")

        # Update filter
        if clear_filter:
            view.filter_expr = None
            updates.append("cleared filter")
        elif filter_expr:
            view.filter_expr = filter_expr
            updates.append(f"set filter to: {filter_expr}")

        # Update limit
        if clear_limit:
            view.limit = None
            updates.append("cleared limit")
        elif limit is not None:
            view.limit = limit
            updates.append(f"set limit to: {limit}")

        if not updates:
            console.print(
                "❌ No updates specified. Use --columns, --filter, --limit, or "
                "their --clear- variants.",
                style="red"
            )
            raise typer.Exit(1)

        # Save the updated view
        views_manager.save_view(view)

        # Show what was updated
        console.print(f"✅ View '{view_name}' updated successfully!", style="green")
        for update in updates:
            console.print(f"  • {update}", style="dim")

        # Show the updated view details
        console.print(f"\n📋 Updated view '{view_name}':", style="bold cyan")
        columns_str = ", ".join(view.columns) if view.columns else "All"
        filter_str = view.filter_expr if view.filter_expr else "None"
        limit_str = str(view.limit) if view.limit else "All"

        console.print(f"  Database: {view.database_name}")
        console.print(f"  Columns: {columns_str}")
        console.print(f"  Filter: {filter_str}")
        console.print(f"  Limit: {limit_str}")

        # Ask if user wants to view the updated results
        if typer.confirm("\n👀 Show the updated view?"):
            show_view(view_name)

    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


# LLM-powered database entry commands

@db_app.command("create")
def create_entry(
    database_name: str = typer.Argument(..., help="Database name to create entry in"),
    prompt: str = typer.Argument(..., help="Natural language description of the entry"),
    model: str = typer.Option(
        None, "--model", "-m", help="LLM model to use (default: gpt-4.1)"
    ),
    auto_confirm: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompt"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Enable interactive prompt revision"
    ),
    files: list[str] = typer.Option(
        None, "--file", "-f", help="File paths to upload and attach to entry"
    ),
) -> None:
    """Create a new database entry using natural language."""
    try:
        client = NotionClientWrapper()
        database = client.get_database_by_name(database_name)

        if not database:
            console.print(f"❌ Database '{database_name}' not found.", style="red")
            console.print(
                "Use 'notion-cli db list' to see available databases.",
                style="yellow"
            )
            raise typer.Exit(1)

        database_id = database.get("id", "")
        properties = database.get("properties", {})

        console.print(f"🤖 Generating entry for database: {database_name}")
        console.print(f"📝 Prompt: {prompt}")

        # Get LLM service
        llm_service = get_default_llm_service()
        if model:
            llm_service.config.model = model

        # Generate structured data
        with console.status("🧠 Processing with LLM..."):
            schema = llm_service._create_notion_schema(properties)
            structured_data = llm_service.generate_structured_data(
                prompt=prompt,
                schema=schema,
                context=f"Creating entry in Notion database '{database_name}'",
                allow_revision=interactive,
                files=files
            )

        # Handle file uploads if files were provided
        if files:
            # Find file properties marked with __FILE__
            file_properties = [
                prop_name for prop_name, value in structured_data.items() 
                if value == "__FILE__"
            ]
            
            if file_properties:
                with console.status(f"📁 Uploading {len(files)} file(s) to Notion..."):
                    file_data = client.prepare_file_properties(files, file_properties)
                console.print(f"✅ Successfully uploaded {len(files)} file(s)!", style="green")
                
                # Update structured data with actual file objects
                for prop_name, file_objects in file_data.items():
                    structured_data[prop_name] = file_objects

        # Convert to Notion format
        notion_properties = NotionDataConverter.convert_to_notion_properties(
            structured_data, properties
        )

        if not notion_properties:
            console.print("❌ No valid properties generated from prompt.", style="red")
            raise typer.Exit(1)

        # Show summary
        console.print("\n📋 Entry Summary:", style="bold cyan")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        for prop_name, value in structured_data.items():
            if value is not None:
                display_value = str(value)
                if isinstance(value, list):
                    display_value = ", ".join(str(v) for v in value)
                table.add_row(prop_name, display_value)

        console.print(table)

        # Confirm creation
        if not auto_confirm:
            confirm = typer.confirm("\n✨ Create this entry?")
            if not confirm:
                console.print("❌ Entry creation cancelled.", style="yellow")
                return

        # Create the entry
        with console.status("📝 Creating entry..."):
            result = client.create_page(database_id, notion_properties)

        entry_id = result.get("id", "")
        entry_url = result.get("url", "")

        console.print("✅ Entry created successfully!", style="green")
        console.print(f"🆔 Entry ID: {entry_id}")
        if entry_url:
            console.print(f"🔗 URL: {entry_url}")

    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


@db_app.command("edit")
def edit_entries(
    database_name: str = typer.Argument(..., help="Database name to edit entries in"),
    prompt: str = typer.Argument(..., help="Natural language description of changes"),
    model: str = typer.Option(
        None, "--model", "-m", help="LLM model to use (default: gpt-3.5-turbo)"
    ),
    auto_confirm: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompt"
    ),
    files: list[str] = typer.Option(
        None, "--file", "-f", help="File paths to upload and attach to entries"
    ),
) -> None:
    """Edit database entries using natural language."""
    try:
        client = NotionClientWrapper()
        database = client.get_database_by_name(database_name)

        if not database:
            console.print(f"❌ Database '{database_name}' not found.", style="red")
            console.print(
                "Use 'notion-cli db list' to see available databases.",
                style="yellow"
            )
            raise typer.Exit(1)

        database_id = database.get("id", "")
        properties = database.get("properties", {})

        console.print(f"🤖 Processing edit request for database: {database_name}")
        console.print(f"📝 Prompt: {prompt}")

        # Get LLM service
        llm_service = get_default_llm_service()
        if model:
            llm_service.config.model = model

        # Generate filter from prompt
        with console.status("🧠 Analyzing prompt to find entries..."):
            filter_expression = llm_service.generate_filters_from_prompt(
                prompt, properties
            )

        console.print(f"🔍 Generated filter: {filter_expression}")

        # Parse and apply filter
        if filter_expression and filter_expression.lower() != "none":
            try:
                parser = FilterParser()
                converter = NotionFilterConverter()
                parsed_filters = parser.parse(filter_expression)
                filter_conditions = converter.convert(parsed_filters, properties)
            except Exception as e:
                console.print(f"⚠️ Filter parsing failed: {e}", style="yellow")
                filter_conditions = None
        else:
            filter_conditions = None

        # Get entries to edit
        with console.status("📊 Fetching entries..."):
            entries = client.get_database_entries(database_id, 10, filter_conditions)

        if not entries:
            console.print("❌ No entries found matching the criteria.", style="red")
            return

        console.print(f"📊 Found {len(entries)} entries to potentially edit")

        # Show entries that will be affected
        table = Table(title="Entries to Edit")
        table.add_column("Index", style="cyan")
        table.add_column("ID", style="dim")

        # Add key columns for identification
        key_columns = ["Name", "Title", "Task"]
        displayed_columns = []
        for col in key_columns:
            if col in properties:
                table.add_column(col, style="white")
                displayed_columns.append(col)
                break

        for i, entry in enumerate(entries):
            entry_props = entry.get("properties", {})
            row = [str(i + 1), entry.get("id", "")[:8] + "..."]

            for col in displayed_columns:
                if col in entry_props:
                    value = client.extract_property_value(entry_props[col])
                    row.append(value or "—")
                else:
                    row.append("—")

            table.add_row(*row)

        console.print(table)

        # Generate updates
        with console.status("🧠 Generating updates..."):
            update_data = llm_service.generate_updates_from_prompt(
                prompt, properties, files=files if files else None
            )

        if not update_data:
            console.print("❌ No valid updates generated from prompt.", style="red")
            return

        # Show update summary
        console.print("\n📝 Planned Updates:", style="bold cyan")
        update_table = Table(show_header=True, header_style="bold magenta")
        update_table.add_column("Property", style="cyan")
        update_table.add_column("New Value", style="white")

        for prop_name, value in update_data.items():
            if value is not None:
                display_value = str(value)
                if isinstance(value, list):
                    display_value = ", ".join(str(v) for v in value)
                update_table.add_row(prop_name, display_value)

        console.print(update_table)

        # Handle file uploads if files were provided
        if files:
            # Find file properties marked with __FILE__
            file_properties = [
                prop_name for prop_name, value in update_data.items() 
                if value == "__FILE__"
            ]
            
            if file_properties:
                with console.status(f"📁 Uploading {len(files)} file(s) to Notion..."):
                    file_data = client.prepare_file_properties(files, file_properties)
                console.print(f"✅ Successfully uploaded {len(files)} file(s)!", style="green")
                
                # Update structured data with actual file objects
                for prop_name, file_objects in file_data.items():
                    update_data[prop_name] = file_objects

        # Confirm updates
        if not auto_confirm:
            console.print(
                f"\n⚠️ This will update {len(entries)} entries", style="yellow"
            )
            confirm = typer.confirm("✨ Proceed with updates?")
            if not confirm:
                console.print("❌ Update cancelled.", style="yellow")
                return

        # Convert to Notion format
        notion_updates = NotionDataConverter.convert_to_notion_properties(
            update_data, properties
        )

        # Apply updates
        success_count = 0
        with console.status("📝 Applying updates..."):
            for entry in entries:
                try:
                    client.update_page(entry["id"], notion_updates)
                    success_count += 1
                except Exception as e:
                    console.print(
                        f"⚠️ Failed to update entry {entry['id']}: {e}",
                        style="yellow"
                    )

        console.print(
            f"✅ Successfully updated {success_count}/{len(entries)} entries!",
            style="green"
        )

    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


# Page management commands

@page_app.command("list")
def list_pages() -> None:
    """List all accessible pages."""
    try:
        client = NotionClientWrapper()
        pages = client.search_pages()

        if not pages:
            console.print("No pages found.", style="yellow")
            return

        table = Table(title="Notion Pages")
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="magenta")
        table.add_column("URL", style="blue")

        for page in pages:
            title = client._extract_page_title(page)
            page_id = page.get("id", "")
            page_url = page.get("url", "")

            table.add_row(title, page_id, page_url)

        console.print(table)

    except ValueError as e:
        console.print(f"❌ {e}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


@page_app.command("find")
def find_page(
    name: str = typer.Argument(..., help="Page name to search for"),
    exact: bool = typer.Option(
        False, "--exact", "-e", help="Use exact matching instead of fuzzy search"
    ),
    limit: int = typer.Option(
        10, "--limit", "-l", help="Maximum number of results to show"
    ),
) -> None:
    """Find pages by name and show their links."""
    try:
        client = NotionClientWrapper()
        pages = client.get_page_by_name(name, fuzzy=not exact)

        if not pages:
            console.print(f"❌ No pages found matching '{name}'.", style="red")
            console.print("Use 'notion-cli page list' to see all pages.", style="yellow")
            raise typer.Exit(1)

        # Limit results
        if len(pages) > limit:
            pages = pages[:limit]
            console.print(f"📄 Showing top {limit} results (found {len(pages)} total)")
        else:
            console.print(f"📄 Found {len(pages)} page(s) matching '{name}'")

        for i, page in enumerate(pages, 1):
            title = page.get("_title", "Untitled")
            match_score = page.get("_match_score", 0)
            page_id = page.get("id", "")
            
            # Get URLs
            urls = client.get_page_urls(page)
            
            console.print(f"\n{i}. {title}", style="bold cyan")
            console.print(f"   Match Score: {match_score:.2f}", style="dim")
            console.print(f"   Page ID: {page_id}", style="dim")
            console.print(f"   Private URL: {urls['private']}", style="blue")
            
            if urls['public']:
                console.print(f"   Public URL: {urls['public']}", style="green")
            else:
                console.print("   Public URL: Not shared publicly", style="yellow")

    except ValueError as e:
        console.print(f"❌ {e}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)


@page_app.command("link")
def get_page_link(
    name: str = typer.Argument(..., help="Page name to get link for"),
    copy: bool = typer.Option(
        False, "--copy", "-c", help="Copy the link to clipboard"
    ),
    public_only: bool = typer.Option(
        False, "--public", "-p", help="Only show public link if available"
    ),
) -> None:
    """Get the link for a specific page."""
    try:
        client = NotionClientWrapper()
        pages = client.get_page_by_name(name, fuzzy=True)

        if not pages:
            console.print(f"❌ No pages found matching '{name}'.", style="red")
            raise typer.Exit(1)

        # Get the best match (first result)
        page = pages[0]
        title = page.get("_title", "Untitled")
        urls = client.get_page_urls(page)

        console.print(f"📄 Page: {title}", style="bold cyan")

        if public_only:
            if urls['public']:
                console.print(f"🔗 Public URL: {urls['public']}", style="green")
                url_to_copy = urls['public']
            else:
                console.print("❌ This page is not shared publicly.", style="red")
                raise typer.Exit(1)
        else:
            console.print(f"🔗 Private URL: {urls['private']}", style="blue")
            url_to_copy = urls['private']
            
            if urls['public']:
                console.print(f"🌐 Public URL: {urls['public']}", style="green")

        # Copy to clipboard if requested
        if copy:
            try:
                import pyperclip
                pyperclip.copy(url_to_copy)
                console.print("✅ Link copied to clipboard!", style="green")
            except ImportError:
                console.print(
                    "⚠️ pyperclip not installed. Install with: pip install pyperclip", 
                    style="yellow"
                )
            except Exception as e:
                console.print(f"⚠️ Failed to copy to clipboard: {e}", style="yellow")

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
