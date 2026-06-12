#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Conversation Manager Tests
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path

from acas_pro.llm.conversation import Conversation, ConversationManager


class TestConversation:
    """Conversation tests"""
    
    def test_conversation_creation(self):
        """Test conversation creation"""
        conv = Conversation(id="conv_001", title="Test Conversation")
        
        assert conv.id == "conv_001"
        assert conv.title == "Test Conversation"
        assert len(conv.messages) == 0
        assert conv.created_at is not None
    
    def test_add_message(self):
        """Test add message"""
        conv = Conversation(id="conv_001")
        conv.add_message("user", "Hello")
        
        assert len(conv.messages) == 1
        assert conv.messages[0].role == "user"
        assert conv.messages[0].content == "Hello"
        assert conv.updated_at >= conv.created_at
    
    def test_get_context_window(self):
        """Test get context window"""
        conv = Conversation(id="conv_001")
        
        # Add many messages
        for i in range(10):
            conv.add_message("user", f"Message {i}" * 100)
        
        window = conv.get_context_window(max_tokens=1000)
        
        # Should return some messages within budget
        assert len(window) > 0
        assert len(window) <= 10
    
    def test_to_dict(self):
        """Test convert to dict"""
        conv = Conversation(id="conv_001", title="Test")
        conv.add_message("user", "Hello")
        conv.add_message("assistant", "Hi there")
        
        data = conv.to_dict()
        
        assert data["id"] == "conv_001"
        assert data["title"] == "Test"
        assert len(data["messages"]) == 2
    
    def test_from_dict(self):
        """Test create from dict"""
        data = {
            "id": "conv_001",
            "title": "Test",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"}
            ],
            "created_at": 1234567890,
            "updated_at": 1234567891,
            "metadata": {"key": "value"}
        }
        
        conv = Conversation.from_dict(data)
        
        assert conv.id == "conv_001"
        assert len(conv.messages) == 2
        assert conv.messages[0].role == "user"


class TestConversationManager:
    """Conversation manager tests"""
    
    @pytest.fixture
    def temp_dir(self):
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)
    
    @pytest.fixture
    def manager(self, temp_dir):
        return ConversationManager(storage_path=temp_dir)
    
    def test_init(self, manager, temp_dir):
        """Test initialization"""
        assert manager.storage_path == Path(temp_dir)
        assert manager.storage_path.exists()
    
    def test_create_conversation(self, manager):
        """Test create conversation"""
        conv = manager.create_conversation(title="Test")
        
        assert conv.id is not None
        assert conv.title == "Test"
        assert manager._active_conversation == conv.id
    
    def test_get_conversation(self, manager):
        """Test get conversation"""
        conv = manager.create_conversation(title="Test")
        retrieved = manager.get_conversation(conv.id)
        
        assert retrieved is not None
        assert retrieved.id == conv.id
    
    def test_get_conversation_not_found(self, manager):
        """Test get conversation not found"""
        result = manager.get_conversation("nonexistent")
        assert result is None
    
    def test_get_active(self, manager):
        """Test get active conversation"""
        conv = manager.create_conversation(title="Active")
        active = manager.get_active()
        
        assert active is not None
        assert active.id == conv.id
    
    def test_get_active_none(self, manager):
        """Test get active when none set"""
        manager._active_conversation = None
        result = manager.get_active()
        assert result is None
    
    def test_set_active(self, manager):
        """Test set active conversation"""
        conv = manager.create_conversation(title="Test")
        manager.set_active(conv.id)
        
        assert manager._active_conversation == conv.id
    
    def test_list_conversations(self, manager):
        """Test list conversations"""
        manager.create_conversation(title="Conv 1")
        manager.create_conversation(title="Conv 2")
        
        convs = manager.list_conversations()
        
        assert len(convs) == 2
    
    def test_list_conversations_limit(self, manager):
        """Test list conversations with limit"""
        for i in range(5):
            manager.create_conversation(title=f"Conv {i}")
        
        convs = manager.list_conversations(limit=3)
        
        assert len(convs) == 3
    
    def test_delete_conversation(self, manager):
        """Test delete conversation"""
        conv = manager.create_conversation(title="To Delete")
        result = manager.delete_conversation(conv.id)
        
        assert result is True
        assert manager.get_conversation(conv.id) is None
    
    def test_delete_conversation_not_found(self, manager):
        """Test delete nonexistent conversation"""
        result = manager.delete_conversation("nonexistent")
        assert result is False
    
    def test_search_conversations(self, manager):
        """Test search conversations"""
        conv = manager.create_conversation(title="Test Search")
        conv.add_message("user", "search keyword here")
        manager.update_conversation(conv)
        
        results = manager.search_conversations("keyword")
        
        assert len(results) > 0
        assert results[0]["id"] == conv.id
    
    def test_search_conversations_not_found(self, manager):
        """Test search not found"""
        results = manager.search_conversations("nonexistent_keyword_xyz")
        assert len(results) == 0
    
    def test_clear_all(self, manager):
        """Test clear all conversations"""
        manager.create_conversation(title="Conv 1")
        manager.create_conversation(title="Conv 2")
        
        manager.clear_all()
        
        assert len(manager._conversations) == 0
        assert manager._active_conversation is None
    
    def test_export_json(self, manager):
        """Test export conversation as JSON"""
        conv = manager.create_conversation(title="Export Test")
        conv.add_message("user", "Hello")
        manager.update_conversation(conv)
        
        exported = manager.export_conversation(conv.id, format="json")
        
        data = json.loads(exported)
        assert data["id"] == conv.id
        assert len(data["messages"]) == 1
    
    def test_export_markdown(self, manager):
        """Test export conversation as Markdown"""
        conv = manager.create_conversation(title="Export Test")
        conv.add_message("user", "Hello")
        manager.update_conversation(conv)
        
        exported = manager.export_conversation(conv.id, format="markdown")
        
        assert "# Export Test" in exported
        assert "Hello" in exported
    
    def test_export_not_found(self, manager):
        """Test export nonexistent conversation"""
        exported = manager.export_conversation("nonexistent")
        assert exported == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
