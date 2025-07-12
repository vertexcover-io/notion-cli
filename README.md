# Notion CLI

A modern command-line interface for Notion database operations using natural language. Built with Python and designed for developers who want to interact with their Notion databases efficiently from the terminal.

## Features

- **Simple Authentication** - Token-based authentication with secure storage
- **Database Operations** - List databases, view entries, and explore data
- **Advanced Filtering** - Powerful filter expressions with logical operators
- **Custom Columns** - Select specific columns to display
- **Save Views** - Save and reuse database view configurations
- **Rich Terminal UI** - Beautiful tables with smart column sizing
- **Fast & Modern** - Built with modern Python tools (uv, ruff, mypy)
- **Cross-Platform** - Works on macOS, Linux, and Windows
- **Type Safe** - Full type hints and static analysis

## =� Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd notion-cli

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

### Setup

1. **Create a Notion Integration:**
   - Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
   - Click "New integration"
   - Give it a name (e.g., "My CLI Tool")
   - Copy the "Internal Integration Token"

2. **Share databases with your integration:**
   - Open the Notion database you want to access
   - Click "Share" � "Invite" � Select your integration

3. **Authenticate the CLI:**
   ```bash
   uv run notion-cli auth setup --token <your-integration-token>
   ```

4. **Test the connection:**
   ```bash
   uv run notion-cli auth test
   ```

## =� Usage

### Authentication Commands

```bash
# Set up authentication
notion-cli auth setup --token <your-token>

# Test current authentication
notion-cli auth test
```

### Database Commands

```bash
# List all accessible databases
notion-cli db list

# Show entries from a specific database
notion-cli db show "My Database"

# Show entries with custom columns
notion-cli db show "Tasks" --columns "Name,Status,Priority,Due Date"
notion-cli db show "Tasks" -c "Name,Status"

# Show entries with filters
notion-cli db show "Tasks" --filter "status=Done"
notion-cli db show "Tasks" --filter "priority=High,status!=Completed"
notion-cli db show "Tasks" -f "due<2025-01-01"

# Advanced filtering examples
notion-cli db show "Tasks" --filter "status not in 'Rejected,Declined,Hold'"
notion-cli db show "Tasks" --filter "OR(priority=High,priority=Critical)"
notion-cli db show "Tasks" --filter "status=Todo,priority in 'High,Critical'"

# Limit number of entries (no default limit)
notion-cli db show "Tasks" --limit 25
notion-cli db show "Projects" -l 5

# Combine columns, filters, and limits
notion-cli db show "Hiring Pipeline" \
  -c "Name,Status,Resume,Linkedin" \
  --filter "status not in 'Rejected,Declined'" \
  --limit 20

# Save a view for later use
notion-cli db show "Tasks" \
  -c "Name,Status,Priority" \
  --filter "status!=Done" \
  --save-view "active-tasks"
```

### View Management Commands

```bash
# List all saved views
notion-cli view list

# Load and display a saved view
notion-cli view show "active-tasks"

# Update an existing view with new filters or columns
notion-cli view update "active-tasks" --filter "priority=High"
notion-cli view update "active-tasks" --columns "Name,Status,Due Date"
notion-cli view update "active-tasks" --limit 50

# Clear specific settings from a view
notion-cli view update "active-tasks" --clear-filter
notion-cli view update "active-tasks" --clear-columns
notion-cli view update "active-tasks" --clear-limit

# Update multiple settings at once
notion-cli view update "active-tasks" \
  --columns "Name,Priority,Status" \
  --filter "status!=Done" \
  --limit 25

# Delete a saved view
notion-cli view delete "old-view"
```

### General Commands

```bash
# Show version
notion-cli version

# Get help
notion-cli --help
notion-cli auth --help
notion-cli db --help
notion-cli view --help
```

## Advanced Features

### Filtering

The CLI supports powerful filtering capabilities to query your Notion databases:

#### Filter Operators

- **Equality**: `=`, `!=`
- **Text matching**: `~` (contains), `!~` (does not contain)
- **List operations**: `in`, `not in` (for multiple values)
- **Mathematical**: `>`, `<`, `>=`, `<=` (for numbers and dates)

#### Filter Examples

```bash
# Simple equality
notion-cli db show "Tasks" --filter "status=Done"

# Multiple conditions (AND by default)
notion-cli db show "Tasks" --filter "status=Todo,priority=High"

# Text contains
notion-cli db show "Tasks" --filter "title~bug"

# Not equal
notion-cli db show "Tasks" --filter "status!=Completed"

# Multiple values with 'in' operator
notion-cli db show "Tasks" --filter "status in 'Todo,InProgress'"

# Exclude multiple values with 'not in'
notion-cli db show "Hiring" --filter "status not in 'Rejected,Declined,Hold'"

# Date comparisons
notion-cli db show "Tasks" --filter "due<2025-01-01"
notion-cli db show "Tasks" --filter "created>=2024-12-01"

# Number comparisons
notion-cli db show "Tasks" --filter "priority_score>=8"
```

#### Logical Functions

Use logical functions for complex queries:

```bash
# OR - matches any condition
notion-cli db show "Tasks" --filter "OR(status=Done,status=InProgress)"

# AND - explicit grouping
notion-cli db show "Tasks" --filter "AND(priority=High,status=Todo)"

# NOT - negation
notion-cli db show "Tasks" --filter "NOT(status=Done)"

# Nested logical operations
notion-cli db show "Tasks" --filter "priority=High,OR(status=Todo,status=InProgress)"
```

### Column Selection

Control which columns are displayed in the output:

```bash
# Show specific columns
notion-cli db show "Tasks" --columns "Name,Status,Priority"
notion-cli db show "Tasks" -c "Name,Status"

# Show all columns (default behavior when no limit is set)
notion-cli db show "Tasks"

# Combine with filters
notion-cli db show "Tasks" -c "Name,Status" --filter "priority=High"
```

**Smart Column Prioritization**: When no columns are specified, the CLI automatically prioritizes:
1. **Title fields** (Name, Title, Task, etc.)
2. **Status fields** (Status, State, Priority, etc.)
3. **Important data** (Dates, Numbers, People, etc.)
4. **Other fields** (URLs, Files, Text, etc.)

### Views System

Save and reuse your frequently used database configurations:

#### Saving Views

```bash
# Save a view with current settings
notion-cli db show "Hiring Pipeline" \
  -c "Name,Status,Resume,Linkedin" \
  --filter "status not in 'Rejected,Declined'" \
  --limit 20 \
  --save-view "active-candidates"
```

#### Managing Views

```bash
# List all saved views
notion-cli view list

# Use a saved view
notion-cli view show "active-candidates"

# Update an existing view
notion-cli view update "active-candidates" --filter "status=Interview"
notion-cli view update "active-candidates" --columns "Name,Status,Experience"
notion-cli view update "active-candidates" --clear-filter --limit 50

# Delete a view
notion-cli view delete "old-view"
```

#### View Storage

Views are stored in platform-specific locations:
- **macOS**: `~/Library/Application Support/notion-cli/views.json`
- **Linux**: `~/.config/notion-cli/views.json`
- **Windows**: `%APPDATA%\notion-cli\views.json`

### Column Width Optimization

The CLI automatically optimizes column widths based on:
- **Content type**: Titles get more space, checkboxes get minimal space
- **Terminal width**: Dynamically adjusts to use full screen width
- **Smart distribution**: Proportional allocation based on importance

**Column Weight Distribution**:
- **Title fields**: 3.0x weight (maximum space)
- **Text/URL/Email**: 2.5x weight (generous space)
- **Files**: 2.0x weight (moderate space)
- **Select/Status**: 1.5x weight (standard space)
- **Date/Number**: 1.0x weight (compact space)
- **Checkbox**: 0.5x weight (minimal space)

