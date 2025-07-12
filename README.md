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
   ```bash
   echo "OPENAI_API_KEY=your_key_here" > .env
   ```

### Basic Usage

```bash
# List databases
notion db list

# View database entries
notion db show "Tasks"

# Create entry with AI
notion db create "Tasks" "Add high priority task to review quarterly reports due Friday"

# Edit entries with AI
notion db edit "Tasks" "Mark all completed tasks as archived"

# Create a page from a file
notion page create "path/to/your/file.md"

# Get database/entry links
notion db link "Tasks"
notion db entry-link "Tasks" "meeting"
```

## Key Features

- **AI-powered creation/editing** - Use natural language to create and update entries
- **Smart filtering** - `--filter "status=Done,priority=High"`
- **Custom columns** - `--columns "Name,Status,Priority"`
- **File uploads** - `--file resume.pdf`
- **Interactive mode** - `--interactive` to revise AI prompts
- **Shell completions** - `notion completion install bash`

## Advanced Examples

```bash
# Filter and save as view
notion db show "Hiring" --filter "status not in 'Rejected,Declined'" --save-view "active-candidates"

# Use saved view
notion view show "active-candidates"

# Create a page from a file with a specific parent
notion page create "path/to/file.md" --parent-name "Parent Page Title"

# Interactive AI creation
notion db create "Projects" "New ML project for customer segmentation" --interactive --file requirements.txt

# Copy page links to clipboard
notion page link "Meeting Notes" --copy
```

## Configuration

Create `.env` file for API keys:
```bash
OPENAI_API_KEY=sk-...
NOTION_TOKEN=ntn_...  # optional, can use auth command instead
NOTION_CLI_LLM_MODEL=gpt-4  # optional, defaults to gpt-3.5-turbo
```

## Help

```bash
notion --help           # General help
notion db --help        # Database commands
notion completion install bash  # Enable tab completion
```

For detailed documentation and examples, see the [full documentation](docs/).

---

Built with [Claude Code](https://claude.ai/code) in one day. Open source at [github.com/vertexcover-io/notion-cli-ai](https://github.com/vertexcover-io/notion-cli-ai).