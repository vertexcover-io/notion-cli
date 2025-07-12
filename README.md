# Notion CLI

A modern command-line interface for Notion database operations using natural language. Built with Python and designed for developers who want to interact with their Notion databases efficiently from the terminal.

## Features

- **Simple Authentication** - Token-based authentication with secure storage
- **Database Operations** - List databases, view entries, and explore data
- **AI-Powered Creation & Editing** - Create and update entries using natural language
- **File Upload Support** - Upload files directly to Notion properties
- **Interactive Mode** - Revise prompts when AI output isn't quite right
- **Advanced Filtering** - Powerful filter expressions with logical operators
- **Custom Columns** - Select specific columns to display
- **Save Views** - Save and reuse database view configurations
- **Rich Terminal UI** - Beautiful tables with smart column sizing
- **Environment Variables** - Secure configuration with .env file support
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

3. **Configure Environment Variables (Optional):**
   ```bash
   # Copy the sample environment file
   cp .env.sample .env
   
   # Edit .env with your credentials
   OPENAI_API_KEY=your_openai_api_key_here
   NOTION_TOKEN=your_notion_integration_token_here
   NOTION_CLI_LLM_MODEL=gpt-3.5-turbo  # Optional: change AI model
   ```

4. **Authenticate the CLI:**
   ```bash
   uv run notion-cli auth setup --token <your-integration-token>
   ```

5. **Test the connection:**
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

### Page Management Commands

Find and access Notion pages quickly with link management functionality.

```bash
# List all accessible pages
notion-cli page list

# Find pages by name (fuzzy search)
notion-cli page find "Meeting"
notion-cli page find "project notes"

# Find with exact matching
notion-cli page find "Meeting Notes" --exact

# Limit search results
notion-cli page find "task" --limit 5

# Get a specific page link
notion-cli page link "Meeting Notes"

# Copy link to clipboard
notion-cli page link "Meeting Notes" --copy

# Get only public URL (if page is shared publicly)
notion-cli page link "Meeting Notes" --public
```

#### Page Search Features

- **Fuzzy Matching**: Search finds pages containing your query
  - `"meeting"` matches "Meeting Notes", "Team Meeting", "Meeting with John"
- **Smart Ranking**: Results sorted by relevance score
  - Exact matches → Starts with query → Contains query
- **Match Scoring**: See how well each result matches your search
- **Result Limiting**: Control number of results with `--limit`
- **Exact Mode**: Use `--exact` for precise name matching

#### Link Management

- **Private URLs**: Always available for pages you have access to
- **Public URLs**: Shown when pages are shared publicly
- **Clipboard Support**: Use `--copy` to copy links directly
- **Quick Access**: Find and copy page links in one command

#### Example Output

```bash
$ notion-cli page find "meeting"
📄 Found 3 page(s) matching 'meeting'

1. Meeting Notes
   Match Score: 0.90
   Page ID: a749072d-9835-4a67-9cd2-87a1d6f5dd12
   Private URL: https://www.notion.so/Meeting-Notes-a749072d...
   Public URL: Not shared publicly

2. Team Meeting Minutes
   Match Score: 0.75
   Page ID: b851083e-a946-5b78-ac3e-98b2e7g6ee23
   Private URL: https://www.notion.so/Team-Meeting-Minutes-b851083e...
   Public URL: https://notion.site/Team-Meeting-Minutes-b851083e...
```

### AI-Powered Database Operations

Create and update Notion database entries using natural language with AI assistance.

#### Creating Entries

```bash
# Create a new entry using natural language
notion-cli db create "Tasks" "Create a high priority task to review quarterly reports due next Friday"

# Create with custom AI model
notion-cli db create "Projects" "New machine learning project for customer segmentation" --model gpt-4

# Skip confirmation prompt
notion-cli db create "Contacts" "Add John Smith as a new client contact" --yes

# Interactive mode - revise prompt if AI output isn't right
notion-cli db create "Tasks" "Schedule team meeting" --interactive

# Create entry with file uploads
notion-cli db create "Candidates" "New applicant Sarah Johnson with strong Python skills" \
  --file /path/to/resume.pdf \
  --file /path/to/portfolio.zip

# Combine interactive mode with files
notion-cli db create "Projects" "New documentation project" \
  --interactive \
  --file /path/to/requirements.md \
  --file /path/to/mockups.png
```

#### Editing Entries

```bash
# Update entries using natural language
notion-cli db edit "Tasks" "Mark all high priority tasks as completed"

# Update specific entries by name
notion-cli db edit "Hiring Pipeline" "Update status to Interview for John Doe"

# Add files to existing entries
notion-cli db edit "Candidates" "Add resume to Sarah Johnson profile" \
  --file /path/to/updated-resume.pdf

# Update with custom AI model
notion-cli db edit "Projects" "Set all machine learning projects to high priority" \
  --model gpt-4

# Skip confirmation prompt
notion-cli db edit "Tasks" "Update all completed tasks to archived status" --yes

# Update multiple properties at once
notion-cli db edit "Candidates" "Update John Smith: set status to Hired, add LinkedIn profile, and set start date to next Monday"
```

#### Interactive Mode

When using `--interactive` mode, you can refine your prompts if the AI doesn't generate the expected output:

```bash
notion-cli db create "Tasks" "Create a task" --interactive
```

The AI will show you the generated result and offer options:
1. **Accept this result** - Use the generated data
2. **Revise the prompt** - Enter a new, more specific prompt
3. **Cancel** - Exit without creating/updating

#### File Upload Support

Upload files directly to Notion properties during creation or editing:

```bash
# Single file upload
notion-cli db create "Documents" "Upload project proposal" \
  --file /path/to/proposal.pdf

# Multiple files
notion-cli db create "Portfolio" "Add new project showcase" \
  --file /path/to/screenshot1.png \
  --file /path/to/screenshot2.png \
  --file /path/to/demo-video.mp4

# Supported file types
# - Documents: .pdf, .docx, .xlsx, .txt
# - Images: .jpg, .png, .gif, .webp
# - Audio: .mp3, .wav, .aac
# - Video: .mp4, .mov, .webm
# - Archives: .zip, .tar.gz
# - And many more...

# File size limits
# - Free workspaces: 5 MB per file
# - Paid workspaces: 5 GB per file
# - Single upload limit: 20 MB (larger files use multi-part upload)
```

#### AI Model Configuration

Configure which AI model to use for natural language processing:

```bash
# Use specific model for one command
notion-cli db create "Tasks" "Create urgent task" --model gpt-4

# Set default model via environment variable
export NOTION_CLI_LLM_MODEL=gpt-4

# Available models (requires appropriate API keys)
# - gpt-3.5-turbo (default, fast and cost-effective)
# - gpt-4 (more capable, slower, more expensive)
# - claude-3-sonnet (requires ANTHROPIC_API_KEY)
# - claude-3-opus (requires ANTHROPIC_API_KEY)
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
notion-cli page --help
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

## Environment Variables

Configure the CLI using environment variables in a `.env` file:

```bash
# Copy the sample file
cp .env.sample .env

# Edit .env with your settings
OPENAI_API_KEY=sk-...                    # Required for AI features
NOTION_TOKEN=ntn_...                     # Optional: set Notion token
NOTION_CLI_LLM_MODEL=gpt-3.5-turbo      # Optional: default AI model

# Optional: Other AI provider keys
ANTHROPIC_API_KEY=sk-ant-...             # For Claude models
GOOGLE_API_KEY=AI...                     # For Gemini models
```

### Supported Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models | None (required for AI features) |
| `NOTION_TOKEN` | Notion integration token | None (can use auth command instead) |
| `NOTION_CLI_LLM_MODEL` | Default AI model to use | `gpt-3.5-turbo` |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | None |
| `GOOGLE_API_KEY` | Google API key for Gemini models | None |

## Troubleshooting

### Common Issues

#### Authentication Problems
```bash
# Issue: "No Notion integration token found"
# Solution: Set up authentication
notion-cli auth setup --token <your-token>

# Issue: "Authentication failed"
# Solution: Check token permissions and database sharing
notion-cli auth test
```

#### AI Feature Issues
```bash
# Issue: "OpenAI API key not found"
# Solution: Set up API key in .env file
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# Issue: AI generates wrong output
# Solution: Use interactive mode and refine prompts
notion-cli db create "Database" "Your prompt" --interactive
```

#### File Upload Issues
```bash
# Issue: "File size exceeds 20MB limit"
# Solution: Use smaller files or upgrade to paid Notion plan
# Files over 20MB require multi-part upload (not yet implemented)

# Issue: "File upload failed"
# Solution: Check file permissions and Notion token access
ls -la /path/to/file
notion-cli auth test
```

#### Database Access Issues
```bash
# Issue: "Database 'Name' not found"
# Solution: Check database name and sharing permissions
notion-cli db list

# Issue: Empty database list
# Solution: Share databases with your integration in Notion
```

### Getting Help

```bash
# Get general help
notion-cli --help

# Get help for specific commands
notion-cli db --help
notion-cli db create --help
notion-cli db edit --help
```

### Debug Mode

Run commands with increased verbosity for troubleshooting:

```bash
# Enable debug output (if implemented)
export DEBUG=1
notion-cli db list

# Check configuration files
cat ~/.config/notion-cli/config.json  # Linux/macOS
cat %APPDATA%\notion-cli\config.json  # Windows
```

