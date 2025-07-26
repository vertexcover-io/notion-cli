"""Views management for saving and loading database views."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_config_dir


@dataclass
class DatabaseView:
    """Represents a saved database view."""

    name: str
    database_name: str
    columns: list[str] | None = None
    filter_expr: str | None = None
    limit: int | None = None
    description: str | None = None


class ViewsManager:
    """Manages saving and loading of database views."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the views manager."""
        if config_path:
            self.views_path = config_path
        else:
            config_dir = Path(user_config_dir("notion", "notion"))
            self.views_path = config_dir / "views.json"

        # Ensure the directory exists
        self.views_path.parent.mkdir(parents=True, exist_ok=True)

    def save_view(self, view: DatabaseView) -> None:
        """Save a view to the views file."""
        views = self.load_all_views()
        views[view.name] = view
        self._write_views(views)

    def load_view(self, view_name: str) -> DatabaseView | None:
        """Load a specific view by name."""
        views = self.load_all_views()
        return views.get(view_name)

    def find_views_by_prefix(self, prefix: str) -> list[tuple[str, DatabaseView]]:
        """Find views that start with the given prefix."""
        views = self.load_all_views()
        matches = []

        for name, view in views.items():
            if name.lower().startswith(prefix.lower()):
                matches.append((name, view))

        return matches

    def load_view_by_name_or_prefix(
        self, name: str, interactive: bool = True
    ) -> DatabaseView | None:
        """Load a view by exact name or prefix with user confirmation for multiple matches."""
        import typer
        from rich.console import Console
        from rich.table import Table

        console = Console()

        # First try exact match
        exact_match = self.load_view(name)
        if exact_match:
            return exact_match

        # Then try prefix matching
        matches = self.find_views_by_prefix(name)

        if not matches:
            return None
        elif len(matches) == 1:
            view_name, view = matches[0]
            if interactive:
                console.print(f"🎯 Using view: {view_name} (matched prefix '{name}')", style="cyan")
            return view
        else:
            # Multiple matches - ask user to choose
            if not interactive:
                # In non-interactive mode, return None for ambiguous matches
                return None

            console.print(f"🔍 Multiple views match prefix '{name}':", style="yellow")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=3)
            table.add_column("View Name", style="cyan")
            table.add_column("Database", style="green")

            for i, (view_name, view) in enumerate(matches, 1):
                table.add_row(str(i), view_name, view.database_name)

            console.print(table)

            while True:
                try:
                    choice = typer.prompt(f"Select view (1-{len(matches)})", type=int)
                    if 1 <= choice <= len(matches):
                        selected_name, selected_view = matches[choice - 1]
                        console.print(f"✅ Selected: {selected_name}", style="green")
                        return selected_view
                    else:
                        console.print(
                            f"❌ Please enter a number between 1 and {len(matches)}", style="red"
                        )
                except (ValueError, KeyboardInterrupt):
                    console.print("❌ Operation cancelled", style="yellow")
                    raise typer.Exit(1)

    def load_all_views(self) -> dict[str, DatabaseView]:
        """Load all views from the views file."""
        if not self.views_path.exists():
            return {}

        try:
            with open(self.views_path) as f:
                data = json.load(f)

            views = {}
            for name, view_data in data.items():
                views[name] = DatabaseView(**view_data)

            return views
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"Invalid views file format: {e}")

    def delete_view(self, view_name: str) -> bool:
        """Delete a view. Returns True if deleted, False if not found."""
        views = self.load_all_views()
        if view_name in views:
            del views[view_name]
            self._write_views(views)
            return True
        return False

    def list_views(self) -> list[DatabaseView]:
        """List all saved views."""
        views = self.load_all_views()
        return list(views.values())

    def _write_views(self, views: dict[str, DatabaseView]) -> None:
        """Write views to the views file."""
        data = {}
        for name, view in views.items():
            data[name] = asdict(view)

        with open(self.views_path, "w") as f:
            json.dump(data, f, indent=2)
