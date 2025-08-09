# Notion CLI AI - MCP Server

A powerful Model Context Protocol (MCP) server that provides AI assistants with comprehensive access to Notion database operations using natural language processing.

## Overview

The Notion CLI AI MCP Server transforms the existing CLI tool into a standardized MCP interface, enabling AI assistants to:

- Manage multiple Notion accounts
- Query and manipulate database entries
- Create entries from natural language descriptions
- Generate complex filters using AI
- Manage saved database views
- Search and manage pages

## Features

### 🏗️ **Multi-Account Support**
- Support for multiple Notion workspace accounts
- Session-based account switching
- Account metadata tracking (email, workspace, tokens)
- Legacy configuration migration

### 💾 **Optional Disk Caching**
- Smart cache key generation based on account, operation, and parameters
- TTL-based expiration (configurable per operation type)
- Automatic cache invalidation on write operations
- Comprehensive cache statistics and management

### 🤖 **AI-Powered Operations**
- Natural language to structured database entries
- Intelligent filter generation from descriptions
- Context-aware database updates using AI

### 🔧 **18 Available MCP Tools**

#### Account Management
- **`list_accounts`** - List all configured Notion accounts
- **`switch_account`** - Switch to a different account for operations

#### Database Operations  
- **`list_databases`** - List all accessible Notion databases
- **`get_database`** - Get detailed database schema and information
- **`query_database`** - Query database with filters, sorting, and column selection
- **`create_database_entry`** - Create new database entries
- **`update_database_entry`** - Update existing database entries

#### View Management
- **`list_views`** - List all saved database views
- **`get_view`** - Get details of a specific saved view
- **`save_view`** - Save a new database view configuration
- **`delete_view`** - Remove a saved view

#### Page Operations
- **`search_pages`** - Search for pages with optional filters
- **`get_page`** - Get detailed information about a specific page

#### AI-Powered Tools
- **`generate_entry_from_text`** - Create database entries from natural language descriptions
- **`generate_filter_from_text`** - Generate complex database filters from natural language
- **`update_entry_from_text`** - Update database entries using natural language instructions

#### Cache Management
- **`get_cache_stats`** - View cache statistics and performance metrics
- **`clear_cache`** - Clear cache entries (all or by account)

## Installation & Setup

### Prerequisites
- Python 3.11+
- Notion integration token(s)
- OpenAI API key (for AI-powered features)

### Install Dependencies
```bash
# Install the package with MCP support
uv sync

# Or install directly
pip install -e .
```

### Environment Variables
```bash
# Required for AI features
export OPENAI_API_KEY="your-openai-api-key"

# Optional: Override Notion token
export NOTION_TOKEN="your-notion-token"

# Optional: Set LLM model
export NOTION_CLI_LLM_MODEL="gpt-4"
```

## Usage

### Starting the MCP Server

#### STDIO Mode (Default)
```bash
# Start with basic configuration
notion mcp start

# Start with caching enabled
notion mcp start --cache

# Using standalone entry point
notion-mcp --cache
```

#### HTTP Mode
```bash
# Start HTTP server
notion mcp start --transport http --port 8000 --host 127.0.0.1

# With custom path
notion mcp start --transport http --path /api/mcp
```

#### Server-Sent Events (SSE)
```bash
# Start SSE server
notion mcp start --transport sse --port 8000
```

### Account Management

```bash
# Add a new account
notion mcp accounts --add "work:user@work.com:Work Workspace:secret_token_123"

# List all accounts
notion mcp accounts --list

# Set default account
notion mcp accounts --set-default work

# Test account connection
notion mcp accounts --test work

# Remove an account
notion mcp accounts --remove work
```

### Cache Management

```bash
# View cache statistics
notion mcp cache --stats

# Clear all cache
notion mcp cache --clear

# Clear cache for specific account
notion mcp cache --clear-account work

# Clean up expired entries
notion mcp cache --cleanup
```

## MCP Tool Examples

### Account Operations

```json
{
  "tool": "list_accounts",
  "arguments": {}
}
```

```json
{
  "tool": "switch_account", 
  "arguments": {
    "account_id": "work"
  }
}
```

### Database Operations

```json
{
  "tool": "query_database",
  "arguments": {
    "database_name": "Tasks",
    "filter_expr": "Status = 'In Progress' AND Priority > 5",
    "columns": ["Name", "Status", "Priority", "Due Date"],
    "limit": 10,
    "sort_by": "Priority",
    "sort_descending": true
  }
}
```

```json
{
  "tool": "create_database_entry",
  "arguments": {
    "database_name": "Tasks", 
    "entry_data": {
      "Name": "Review MCP Implementation",
      "Status": "Not Started",
      "Priority": 8,
      "Due Date": "2024-12-15"
    }
  }
}
```

### AI-Powered Operations

```json
{
  "tool": "generate_entry_from_text",
  "arguments": {
    "database_name": "Tasks",
    "text_description": "Create a high priority task to review the quarterly budget report by Friday"
  }
}
```

```json
{
  "tool": "generate_filter_from_text", 
  "arguments": {
    "database_name": "Tasks",
    "filter_description": "Show all high priority tasks assigned to me that are overdue"
  }
}
```

### View Management

```json
{
  "tool": "save_view",
  "arguments": {
    "view_name": "High Priority Tasks",
    "database_name": "Tasks", 
    "filter_expr": "Priority > 7",
    "columns": ["Name", "Status", "Priority", "Due Date"],
    "limit": 20,
    "description": "Tasks with priority 8 or higher"
  }
}
```

## Configuration

### Account Storage
Accounts are stored in platform-specific configuration directories:
- **Linux/macOS**: `~/.config/notion/mcp_accounts.json`
- **Windows**: `%APPDATA%\notion\mcp_accounts.json`

### Cache Storage (Optional)
Cache files are stored in platform-specific cache directories:
- **Linux/macOS**: `~/.cache/notion-cli-ai/cache/`
- **Windows**: `%LOCALAPPDATA%\notion-cli-ai\cache\`

### Cache Configuration
Default TTL values:
- `list_databases`: 5 minutes
- `get_database`: 3 minutes  
- `query_database`: 1 minute
- `list_views`: 5 minutes
- `get_view`: 5 minutes
- `search_pages`: 2 minutes
- `get_page`: 3 minutes

## Architecture

### Core Components

#### **MCP Server** (`src/notion_cli/mcp_server.py`)
- FastMCP-based server implementation
- Tool registration and request handling
- Error handling and response formatting
- Account context injection

#### **Account Manager** (`src/notion_cli/mcp_accounts.py`)
- Multi-account storage and retrieval
- Account switching and validation
- Legacy configuration migration
- Connection testing

#### **Cache Manager** (`src/notion_cli/mcp_cache.py`)
- Disk-based caching with TTL support
- Smart cache key generation
- Write operation invalidation
- Cache statistics and cleanup

### Design Patterns

#### **Cache Strategy**
- **Cache Key**: `{account_id}:{operation}:{params_hash}`
- **Read-First**: Check cache before API calls
- **Write-Invalidate**: Clear related cache entries on mutations
- **TTL-Based**: Automatic expiration based on operation type

#### **Error Handling**
- Consistent error response format: `{"error": "description"}`
- Graceful degradation when services unavailable
- Helpful error messages with suggested actions

#### **Account Context**
- Session-based account selection
- Automatic fallback to default account
- Per-tool account validation

## Integration Examples

### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "notion-cli-ai": {
      "command": "notion-mcp",
      "args": ["--cache"],
      "env": {
        "OPENAI_API_KEY": "your-openai-key"
      }
    }
  }
}
```

### Cline/Cody Configuration
```json
{
  "mcp": {
    "servers": {
      "notion": {
        "command": "notion",
        "args": ["mcp", "start", "--cache", "--transport", "stdio"]
      }
    }
  }
}
```

## Performance Considerations

### Caching Benefits
- **Reduced API Calls**: Cache frequently accessed data
- **Improved Response Times**: Serve cached results instantly  
- **Rate Limit Protection**: Avoid hitting Notion API limits

### Cache Invalidation Strategy
Write operations automatically invalidate related cache entries:
- `create_database_entry` → clears `list_databases`, `query_database`
- `update_database_entry` → clears `query_database`, `get_database`  
- `save_view` → clears `list_views`
- `delete_view` → clears `list_views`

## Troubleshooting

### Common Issues

#### **Authentication Errors**
```bash
# Test account connection
notion mcp accounts --test account_id

# Add account with correct token format
notion mcp accounts --add "id:email:workspace:token"
```

#### **Cache Issues**
```bash
# Clear all cache
notion mcp cache --clear

# View cache statistics  
notion mcp cache --stats

# Clean up expired entries
notion mcp cache --cleanup
```

#### **Connection Problems**
```bash
# Verify server startup
notion mcp start --transport http --port 8001

# Check logs for detailed error messages
```

### Debug Mode
Set environment variable for detailed logging:
```bash
export NOTION_CLI_DEBUG=1
notion mcp start --cache
```

## Development

### Running Tests
```bash
# Run all tests
uv run pytest tests/

# Run MCP-specific tests
uv run pytest tests/test_mcp_server.py

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

### Code Quality
```bash
# Format code
uv run ruff format

# Check linting
uv run ruff check

# Type checking
uv run mypy src/
```

## Security Considerations

- **Token Storage**: Integration tokens stored in local config files
- **Network Access**: MCP server only accepts local connections by default
- **Cache Security**: Cache files stored in user-specific directories
- **Input Validation**: All inputs validated before processing

## Limitations

- **Notion API Rate Limits**: Respects Notion's API rate limiting
- **File Upload Size**: Limited by Notion's file size restrictions
- **Cache Storage**: Disk space usage grows with cache size
- **Account Limits**: No enforced limit on number of accounts

## Contributing

See the main [README.md](README.md) for contribution guidelines and development setup instructions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.