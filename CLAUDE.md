# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool called `notion-cli-ai` that provides AI-powered database operations for Notion. It uses natural language processing to create and edit Notion database entries, along with traditional database querying capabilities.

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies (uses uv package manager)
uv sync

# Install in development mode with pip
pip install -e .

# Install from source with uv
uv add notion-cli-ai
```

### Code Quality and Testing
```bash
# Install dev dependencies
uv add --dev pre-commit ruff mypy pytest

# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Format code with ruff
uv run ruff format

# Lint code with ruff
uv run ruff check

# Type checking with mypy
uv run mypy src/

# Run tests
uv run pytest tests/

# Run all quality checks manually
uv run ruff check && uv run ruff format && uv run mypy src/

# Run pre-commit hooks on all files
uv run pre-commit run --all-files

# Fix most long line issues (manual helper)
python scripts/fix-long-lines.py src/notion_cli/main.py
```

### Running the CLI
```bash
# Run via uv
uv run notion <command>

# Run directly after installation
notion <command>

# Common development workflow
uv run notion auth setup --token <token>
uv run notion db list
uv run notion db show "Database Name"
```

## Architecture Overview

### Core Components

1. **CLI Interface** (`main.py`): Built with Typer, provides command structure:
   - `auth`: Authentication management
   - `db`: Database operations (list, show, create, edit, link, entry-link)
   - `view`: Saved view management
   - `page`: Page search and link management
   - `completion`: Shell completion installation

2. **Notion API Client** (`client.py`): Wrapper around `notion-client` with:
   - Connection testing and authentication
   - Database and page querying
   - Entry creation/modification
   - File upload capabilities
   - Smart column optimization for terminal display

3. **LLM Integration** (`llm.py`): Uses `litellm` for AI features:
   - Structured data generation from natural language
   - Filter expression generation
   - Update generation for existing entries
   - Support for multiple models (GPT, Claude, etc.)

4. **Configuration** (`config.py`): Platform-aware config management:
   - Uses `platformdirs` for proper config directory placement
   - TOML-based configuration storage
   - Environment variable support via `python-dotenv`

5. **Data Processing**:
   - `filters.py`: Advanced filter parsing and Notion API conversion
   - `notion_data.py`: Data format conversion between CLI and Notion API
   - `views.py`: Saved view management with JSON storage

### Key Dependencies

- **Core**: `typer`, `rich`, `notion-client`, `pydantic`
- **AI**: `litellm`, `python-dotenv`
- **Utilities**: `platformdirs`, `toml`, `requests`, `pyperclip`

### Configuration Locations

- **Config**: `~/.config/notion/config.toml` (Linux/macOS), `%APPDATA%\notion\config.toml` (Windows)
- **Views**: `~/.config/notion/views.json` (same pattern)
- **Environment**: `.env` file in project root (optional)

## Important Implementation Notes

### Code Quality Automation
- Pre-commit hooks run automatically on `git commit`
- Ruff formatter handles most style issues automatically
- **Line length is set to 100 characters** but E501 violations are ignored in linting
- Ruff format will break lines where safe, but won't force break long strings/comments
- Use `python scripts/fix-long-lines.py <file>` if you want to manually fix long lines

### Authentication Flow
- Token stored in platform-specific config directory
- Environment variable `NOTION_TOKEN` can override config file
- Always test connection before operations

### AI Features Requirements
- Requires `OPENAI_API_KEY` environment variable for GPT models
- Model selection via `NOTION_CLI_LLM_MODEL` or `--model` flag
- Interactive mode allows prompt revision when AI output isn't correct

### File Upload Support
- Handles file uploads to Notion file/files properties
- Supports various file types with size limits
- Uses streaming upload for larger files

### Terminal UI
- Smart column width calculation based on terminal size
- Rich text formatting and tables
- Dynamic column prioritization (titles > status > data > misc)

### Filter System
- Advanced filter parsing with logical operators (AND, OR, NOT)
- Support for text matching, list operations, date/number comparisons
- Automatic conversion to Notion API filter format

## Error Handling Patterns

- Use `typer.Exit(1)` for user-facing errors
- Provide helpful error messages with suggested actions
- Always check authentication before operations
- Handle missing databases/entries gracefully

## Testing Approach

Tests are located in `tests/` directory and should use pytest framework based on the pyproject.toml configuration.
