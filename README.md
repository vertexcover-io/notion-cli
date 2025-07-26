# Notion CLI

A command-line tool for managing Notion databases with AI-powered natural language entry creation.

## Quick Start

### Installation

```bash
pip install notion-cli-ai
```

### Setup

1. **Create a Notion Integration:**
   - Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
   - Create new integration and copy the token
   - Share your databases with the integration

2. **Authenticate:**
   ```bash
   notion auth setup --token <your-integration-token>
   ```

3. **Set up AI (optional):**
   - API keys will be prompted for automatically when needed

### Basic Usage

```bash
# List databases
notion db list

# Set default database to avoid typing it repeatedly
notion db set-default "Tasks"

# View database entries (uses default database if no name provided)
notion db show "Tasks"
notion db show  # Uses default database

# Create entry with AI (new improved syntax - prompt first)
notion db create "Add high priority task to review quarterly reports due Friday" --database "Tasks"
notion db create "Add high priority task to review quarterly reports due Friday"  # Uses default database

# Edit entries with AI (prompt first syntax)
notion db edit "Mark all completed tasks as archived" --database "Tasks"
notion db edit "Mark all completed tasks as archived"  # Uses default database

# Use prefix matching for database names
notion db show "Task"  # Matches "Tasks" automatically
notion db show "Pro"   # Shows selection menu if multiple matches like "Projects", "Proposals"

# Create a page from a file
notion page create "path/to/your/file.md"

# Get database/entry links (clickable in terminal)
notion db link "Tasks"
notion db entry-link "Tasks" "meeting"
```

## Key Features

- **🧠 AI-powered creation/editing** - Use natural language to create and update entries with improved filter generation
- **🎯 Default database/view support** - Set defaults to avoid typing database names repeatedly
- **🔍 Prefix matching** - Use partial database/view names with auto-completion and selection menus
- **🖱️ Clickable links** - Database and entry URLs are clickable in terminal output
- **🔑 Automatic API key management** - CLI prompts for missing keys and saves them
- **Smart filtering** - `--filter "status=Done,priority=High"`
- **Custom columns** - `--columns "Name,Status,Priority"`
- **File uploads** - `--file resume.pdf`
- **Interactive mode** - `--interactive` to revise AI prompts
- **Shell completions** - `notion completion install bash`

## Advanced Examples

```bash
# Set defaults to streamline workflow
notion db set-default "Hiring"
notion view set-default "active-candidates"

# Filter and save as view (with prefix matching)
notion db show "Hir" --filter "status not in 'Rejected,Declined'" --save-view "active-candidates"

# Use saved view with prefix matching
notion view show "active"  # Matches "active-candidates"
notion view show  # Uses default view

# Create a page from a file with a specific parent
notion page create "path/to/file.md" --parent-name "Parent Page Title"

# Interactive AI creation with improved syntax
notion db create "New ML project for customer segmentation" --database "Projects" --interactive --file requirements.txt

# Copy page links to clipboard
notion page link "Meeting Notes" --copy

# View current defaults
notion db get-default
notion view get-default

# Prefix matching with multiple matches shows selection menu
notion db show "Pro"  # If you have "Projects" and "Proposals", shows menu to choose
```

## Configuration

The CLI automatically prompts for both model selection and API key when first using AI features. No manual configuration required!

```bash
# Example: First time using AI features
notion db create "Add a new task"
# ↳ Will show model selection menu and prompt for API key
# ↳ Saves configuration for future use

# Optional environment variables
NOTION_TOKEN=ntn_...  # optional, can use 'notion auth setup' instead
NOTION_CLI_LLM_MODEL=gpt-4o  # optional, overrides saved model choice
```

### Supported Models
- **OpenAI**: All OpenAI models (gpt-4.1-mini is default)
- **Anthropic**: All Claude models
- **Google**: All Gemini models
- **Other**: Any model supported by LiteLLM


## Help

```bash
notion --help           # General help
notion db --help        # Database commands
notion completion install bash  # Enable tab completion
```
