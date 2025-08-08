"""Tests for MCP server functionality."""

import json
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from fastmcp import Client
from notion_cli.mcp_server import MCPServer
from notion_cli.mcp_accounts import AccountManager, NotionAccount
from notion_cli.mcp_cache import MCPCacheManager


@pytest.fixture
def mock_account():
    """Create a mock account for testing."""
    return NotionAccount(
        account_id="test_account",
        email="test@example.com", 
        workspace_name="Test Workspace",
        integration_token="test_token_123"
    )


@pytest.fixture
def mock_database():
    """Create a mock Notion database structure."""
    return {
        "id": "db123",
        "title": [{"plain_text": "Test Database"}],
        "url": "https://notion.so/db123",
        "properties": {
            "Name": {"type": "title", "id": "title_id"},
            "Status": {"type": "select", "id": "status_id"},
            "Priority": {"type": "number", "id": "priority_id"}
        }
    }


@pytest.fixture  
def mcp_server(tmp_path):
    """Create MCP server instance for testing."""
    with patch('notion_cli.mcp_server.AccountManager') as mock_account_manager:
        mock_account_manager.return_value.get_default_account.return_value = NotionAccount(
            account_id="test",
            email="test@test.com",
            workspace_name="Test",
            integration_token="token"
        )
        
        server = MCPServer(cache_enabled=False)
        return server


class TestMCPServer:
    """Test MCP server functionality."""
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, mcp_server):
        """Test server initializes correctly."""
        assert mcp_server.account_manager is not None
        assert mcp_server.cache_manager is not None
        assert mcp_server.views_manager is not None
        assert mcp_server.mcp is not None
    
    @pytest.mark.asyncio
    async def test_list_accounts_tool(self, mcp_server, mock_account):
        """Test list_accounts MCP tool."""
        # Mock account manager
        with patch.object(mcp_server.account_manager, 'list_accounts') as mock_list:
            mock_list.return_value = [mock_account]
            
            async with Client(mcp_server.mcp) as client:
                result = await client.call_tool("list_accounts")
                
                assert result.is_error is False
                accounts = json.loads(result.text)
                assert len(accounts) == 1
                assert accounts[0]["account_id"] == "test_account"
                assert accounts[0]["email"] == "test@example.com"
    
    @pytest.mark.asyncio 
    async def test_switch_account_tool(self, mcp_server, mock_account):
        """Test switch_account MCP tool."""
        with patch.object(mcp_server.account_manager, 'get_account') as mock_get:
            with patch.object(mcp_server.account_manager, 'test_account_connection') as mock_test:
                mock_get.return_value = mock_account
                mock_test.return_value = True
                
                async with Client(mcp_server.mcp) as client:
                    result = await client.call_tool("switch_account", {"account_id": "test_account"})
                    
                    assert result.is_error is False
                    response = json.loads(result.text)
                    assert response["success"] is True
                    assert response["account_id"] == "test_account"
    
    @pytest.mark.asyncio
    async def test_list_databases_tool(self, mcp_server, mock_database):
        """Test list_databases MCP tool."""
        with patch('notion_cli.mcp_server.NotionClientWrapper') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.list_databases.return_value = [mock_database]
            
            async with Client(mcp_server.mcp) as client:
                result = await client.call_tool("list_databases")
                
                assert result.is_error is False
                databases = json.loads(result.text)
                assert len(databases) == 1
                assert databases[0]["id"] == "db123"
                assert databases[0]["title"] == "Test Database"
    
    @pytest.mark.asyncio
    async def test_query_database_tool(self, mcp_server, mock_database):
        """Test query_database MCP tool."""
        mock_pages = {
            "results": [{
                "id": "page123",
                "properties": {
                    "Name": {"title": [{"plain_text": "Test Entry"}]},
                    "Status": {"select": {"name": "Active"}},
                    "Priority": {"number": 1}
                }
            }],
            "has_more": False
        }
        
        with patch('notion_cli.mcp_server.NotionClientWrapper') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.get_database_by_name_or_prefix.return_value = mock_database
            mock_client.client.databases.query.return_value = mock_pages
            
            # Mock data converter
            with patch('notion_cli.mcp_server.NotionDataConverter') as mock_converter_class:
                mock_converter = mock_converter_class.return_value
                mock_converter.convert_page_properties.return_value = {
                    "Name": "Test Entry",
                    "Status": "Active", 
                    "Priority": 1
                }
                
                async with Client(mcp_server.mcp) as client:
                    result = await client.call_tool("query_database", {
                        "database_name": "Test Database",
                        "limit": 10
                    })
                    
                    assert result.is_error is False
                    response = json.loads(result.text)
                    assert response["count"] == 1
                    assert len(response["results"]) == 1
                    assert response["results"][0]["Name"] == "Test Entry"
    
    @pytest.mark.asyncio
    async def test_create_database_entry_tool(self, mcp_server, mock_database):
        """Test create_database_entry MCP tool.""" 
        mock_response = {
            "id": "new_page123",
            "url": "https://notion.so/new_page123"
        }
        
        with patch('notion_cli.mcp_server.NotionClientWrapper') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.get_database_by_name_or_prefix.return_value = mock_database
            mock_client.client.pages.create.return_value = mock_response
            
            # Mock data converter
            with patch('notion_cli.mcp_server.NotionDataConverter') as mock_converter_class:
                mock_converter = mock_converter_class.return_value
                mock_converter.convert_to_notion_properties.return_value = {
                    "Name": {"title": [{"text": {"content": "New Entry"}}]}
                }
                
                async with Client(mcp_server.mcp) as client:
                    result = await client.call_tool("create_database_entry", {
                        "database_name": "Test Database",
                        "entry_data": {"Name": "New Entry"}
                    })
                    
                    assert result.is_error is False
                    response = json.loads(result.text)
                    assert response["success"] is True
                    assert response["page_id"] == "new_page123"
    
    @pytest.mark.asyncio
    async def test_ai_generate_entry_tool(self, mcp_server, mock_database):
        """Test generate_entry_from_text AI tool."""
        mock_generated_data = {"Name": "AI Generated Entry", "Status": "New", "Priority": 2}
        mock_response = {"id": "ai_page123", "url": "https://notion.so/ai_page123"}
        
        with patch('notion_cli.mcp_server.NotionClientWrapper') as mock_client_class:
            with patch('notion_cli.mcp_server.get_default_llm_service') as mock_llm_service:
                mock_client = mock_client_class.return_value
                mock_client.get_database_by_name_or_prefix.return_value = mock_database
                mock_client.client.pages.create.return_value = mock_response
                
                mock_llm = mock_llm_service.return_value
                mock_llm.generate_database_entry.return_value = mock_generated_data
                
                with patch('notion_cli.mcp_server.NotionDataConverter') as mock_converter_class:
                    mock_converter = mock_converter_class.return_value
                    mock_converter.convert_to_notion_properties.return_value = {}
                    
                    async with Client(mcp_server.mcp) as client:
                        result = await client.call_tool("generate_entry_from_text", {
                            "database_name": "Test Database",
                            "text_description": "Create a high priority task for project review"
                        })
                        
                        assert result.is_error is False
                        response = json.loads(result.text)
                        assert response["success"] is True
                        assert response["generated_data"] == mock_generated_data
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server):
        """Test error handling in MCP tools."""
        # Test with non-existent database
        with patch('notion_cli.mcp_server.NotionClientWrapper') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.get_database_by_name_or_prefix.return_value = None
            
            async with Client(mcp_server.mcp) as client:
                result = await client.call_tool("get_database", {"database_name": "NonExistent"})
                
                assert result.is_error is False
                response = json.loads(result.text)
                assert "error" in response
                assert "not found" in response["error"]


class TestAccountManager:
    """Test account management functionality."""
    
    def test_account_creation(self, tmp_path):
        """Test creating and saving accounts."""
        config_path = tmp_path / "test_accounts.json"
        manager = AccountManager(config_path)
        
        account = NotionAccount(
            account_id="test123",
            email="test@example.com",
            workspace_name="Test Workspace", 
            integration_token="token123"
        )
        
        manager.add_account(account)
        
        # Verify account was saved
        loaded_account = manager.get_account("test123")
        assert loaded_account is not None
        assert loaded_account.email == "test@example.com"
        assert loaded_account.is_default is True  # First account becomes default
    
    def test_multiple_accounts(self, tmp_path):
        """Test managing multiple accounts."""
        config_path = tmp_path / "test_accounts.json" 
        manager = AccountManager(config_path)
        
        # Add first account
        account1 = NotionAccount("acc1", "user1@test.com", "Workspace 1", "token1")
        manager.add_account(account1)
        
        # Add second account
        account2 = NotionAccount("acc2", "user2@test.com", "Workspace 2", "token2")
        manager.add_account(account2)
        
        # Check accounts list
        accounts = manager.list_accounts()
        assert len(accounts) == 2
        
        # First account should still be default
        default = manager.get_default_account()
        assert default.account_id == "acc1"
        
        # Set second as default
        manager.set_default_account("acc2")
        default = manager.get_default_account()
        assert default.account_id == "acc2"
    
    def test_account_removal(self, tmp_path):
        """Test removing accounts."""
        config_path = tmp_path / "test_accounts.json"
        manager = AccountManager(config_path)
        
        # Add accounts
        account1 = NotionAccount("acc1", "user1@test.com", "Workspace 1", "token1")
        account2 = NotionAccount("acc2", "user2@test.com", "Workspace 2", "token2")
        manager.add_account(account1)
        manager.add_account(account2)
        
        # Remove first account (default)
        success = manager.remove_account("acc1")
        assert success is True
        
        # Second account should become default
        default = manager.get_default_account()
        assert default.account_id == "acc2"
        
        # Verify first account is gone
        assert manager.get_account("acc1") is None


class TestCacheManager:
    """Test cache management functionality."""
    
    def test_cache_operations(self, tmp_path):
        """Test basic cache operations."""
        cache_dir = tmp_path / "cache"
        manager = MCPCacheManager(cache_dir, enabled=True)
        
        # Test cache miss
        result = manager.get("acc1", "list_databases", {})
        assert result is None
        
        # Test cache set and hit
        test_data = {"databases": ["db1", "db2"]}
        manager.set("acc1", "list_databases", {}, test_data)
        
        cached_result = manager.get("acc1", "list_databases", {})
        assert cached_result == test_data
    
    def test_cache_invalidation(self, tmp_path):
        """Test cache invalidation."""
        cache_dir = tmp_path / "cache"
        manager = MCPCacheManager(cache_dir, enabled=True)
        
        # Cache some data
        manager.set("acc1", "list_databases", {}, {"data": "test1"})
        manager.set("acc1", "query_database", {"db": "test"}, {"data": "test2"})
        manager.set("acc2", "list_databases", {}, {"data": "test3"})
        
        # Invalidate account
        manager.invalidate_account("acc1")
        
        # acc1 data should be gone, acc2 should remain
        assert manager.get("acc1", "list_databases", {}) is None
        assert manager.get("acc1", "query_database", {"db": "test"}) is None
        assert manager.get("acc2", "list_databases", {}) == {"data": "test3"}
    
    def test_cache_stats(self, tmp_path):
        """Test cache statistics."""
        cache_dir = tmp_path / "cache"
        manager = MCPCacheManager(cache_dir, enabled=True)
        
        # Add some cache entries
        manager.set("acc1", "list_databases", {}, {"data": "test1"})
        manager.set("acc2", "query_database", {"db": "test"}, {"data": "test2"})
        
        stats = manager.get_cache_stats()
        assert stats["enabled"] is True
        assert stats["total_entries"] == 2
        assert "acc1" in stats["entries_by_account"]
        assert "acc2" in stats["entries_by_account"] 
        assert "list_databases" in stats["entries_by_operation"]
        assert "query_database" in stats["entries_by_operation"]
    
    def test_cache_disabled(self, tmp_path):
        """Test cache when disabled."""
        cache_dir = tmp_path / "cache"
        manager = MCPCacheManager(cache_dir, enabled=False)
        
        # Operations should be no-ops when disabled
        manager.set("acc1", "test", {}, {"data": "test"})
        result = manager.get("acc1", "test", {})
        assert result is None
        
        stats = manager.get_cache_stats()
        assert stats["enabled"] is False


if __name__ == "__main__":
    pytest.main([__file__])