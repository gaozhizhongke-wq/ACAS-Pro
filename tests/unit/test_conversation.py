#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for llm/conversation.py"""

import pytest
import tempfile
import shutil
from datetime import datetime
from unittest.mock import MagicMock, patch
from acas_pro.llm.conversation import ConversationManager, Conversation


class TestConversation:
    def test_create(self):
        conv = Conversation(id="CONV001", title="Test Conversation")
        assert conv.id == "CONV001"
        assert conv.title == "Test Conversation"
        assert isinstance(conv.messages, list)
        assert len(conv.messages) == 0

    def test_add_message(self):
        conv = Conversation(id="CONV001", title="Test")
        conv.add_message(role="user", content="Hello")
        assert len(conv.messages) == 1
        assert conv.messages[0].role == "user"
        assert conv.messages[0].content == "Hello"

    def test_add_multiple_messages(self):
        conv = Conversation(id="CONV001", title="Test")
        conv.add_message(role="user", content="Hello")
        conv.add_message(role="assistant", content="Hi there!")
        assert len(conv.messages) == 2
        assert conv.messages[1].role == "assistant"

    def test_to_dict(self):
        conv = Conversation(id="CONV001", title="Test")
        conv.add_message(role="user", content="Hello")
        data = conv.to_dict()
        assert data["id"] == "CONV001"
        assert data["title"] == "Test"
        assert len(data["messages"]) == 1
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Hello"

    def test_from_dict(self):
        data = {
            "id": "CONV001",
            "title": "Test",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "created_at": 1700000000.0,
            "updated_at": 1700000000.0,
            "metadata": {}
        }
        conv = Conversation.from_dict(data)
        assert conv.id == "CONV001"
        assert len(conv.messages) == 1
        assert conv.messages[0].role == "user"
        assert conv.messages[0].content == "Hello"


class TestConversationManager:
    def setup_method(self):
        # Create a temporary directory for storage
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ConversationManager(storage_path=self.temp_dir)

    def teardown_method(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        assert self.manager is not None
        assert self.manager.storage_path is not None
        assert self.manager.storage_path.exists()

    def test_create_conversation(self):
        conv = self.manager.create_conversation(title="Test Conversation")
        assert conv is not None
        assert conv.id is not None
        assert conv.title == "Test Conversation"
        assert conv.id in self.manager._conversations

    def test_create_conversation_with_id(self):
        conv = self.manager.create_conversation(title="Custom", id="CUSTOM001")
        assert conv is not None
        assert conv.id == "CUSTOM001"

    def test_get_conversation(self):
        # First create a conversation
        conv = self.manager.create_conversation(title="Test", id="CONV001")
        conv.add_message(role="user", content="Hello")
        self.manager.update_conversation(conv)
        
        # Now retrieve it
        retrieved = self.manager.get_conversation("CONV001")
        assert retrieved is not None
        assert retrieved.id == "CONV001"
        assert len(retrieved.messages) == 1

    def test_get_conversation_not_found(self):
        conv = self.manager.get_conversation("NONEXISTENT")
        assert conv is None

    def test_list_conversations(self):
        # Create some conversations
        self.manager.create_conversation(title="Test 1", id="CONV001")
        self.manager.create_conversation(title="Test 2", id="CONV002")
        
        convs = self.manager.list_conversations()
        assert isinstance(convs, list)
        assert len(convs) == 2

    def test_list_conversations_empty(self):
        convs = self.manager.list_conversations()
        assert isinstance(convs, list)
        assert len(convs) == 0

    def test_list_conversations_pagination(self):
        # Create some conversations
        self.manager.create_conversation(title="Test 1", id="CONV001")
        self.manager.create_conversation(title="Test 2", id="CONV002")
        self.manager.create_conversation(title="Test 3", id="CONV003")
        
        # Test limit
        convs = self.manager.list_conversations(limit=2)
        assert isinstance(convs, list)
        assert len(convs) == 2
        
        # Test offset
        convs = self.manager.list_conversations(limit=2, offset=1)
        assert isinstance(convs, list)
        assert len(convs) == 2

    def test_delete_conversation(self):
        # Create a conversation first
        self.manager.create_conversation(title="Test", id="CONV001")
        
        # Delete it
        result = self.manager.delete_conversation("CONV001")
        assert result is True
        
        # Verify it's gone
        conv = self.manager.get_conversation("CONV001")
        assert conv is None

    def test_set_active(self):
        # Create a conversation first
        self.manager.create_conversation(title="Test", id="CONV001")
        
        # Set it active
        self.manager.set_active("CONV001")
        assert self.manager._active_conversation == "CONV001"

    def test_get_active(self):
        # Create and set active
        conv = self.manager.create_conversation(title="Active", id="CONV001")
        self.manager.set_active("CONV001")
        
        active = self.manager.get_active()
        assert active is not None
        assert active.id == "CONV001"

    def test_get_active_none(self):
        active = self.manager.get_active()
        assert active is None

    def test_update_conversation(self):
        # Create a conversation first
        conv = self.manager.create_conversation(title="Test", id="CONV001")
        conv.add_message(role="user", content="Hello")
        
        # Update it
        self.manager.update_conversation(conv)
        
        # Verify the update
        retrieved = self.manager.get_conversation("CONV001")
        assert retrieved is not None
        assert len(retrieved.messages) == 1

    def test_clear_all(self):
        # Create some conversations
        self.manager.create_conversation(title="Test 1", id="CONV001")
        self.manager.create_conversation(title="Test 2", id="CONV002")
        
        # Clear all
        self.manager.clear_all()
        
        # Verify they're gone
        convs = self.manager.list_conversations()
        assert len(convs) == 0
        assert self.manager._active_conversation is None

    def test_search_conversations(self):
        # Create a conversation with searchable content
        conv = self.manager.create_conversation(title="Test Search", id="CONV001")
        conv.add_message(role="user", content="This is a searchable message")
        self.manager.update_conversation(conv)
        
        results = self.manager.search_conversations("searchable")
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_export_conversation(self):
        # Create a conversation
        conv = self.manager.create_conversation(title="Export Test", id="CONV001")
        conv.add_message(role="user", content="Hello")
        self.manager.update_conversation(conv)
        
        # Export it
        data = self.manager.export_conversation("CONV001", format="json")
        assert isinstance(data, str)
        import json
        parsed = json.loads(data)
        assert parsed["id"] == "CONV001"

    def test_export_conversation_not_found(self):
        data = self.manager.export_conversation("NONEXISTENT")
        assert data == ""
