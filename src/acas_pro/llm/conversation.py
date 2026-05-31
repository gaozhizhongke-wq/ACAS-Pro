#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Conversation Management
Multi-turn conversation with context management
"""

import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path

from .llm_client import LLMMessage


@dataclass
class Conversation:
    """Conversation record"""
    id: str
    title: str = ""
    messages: List[LLMMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, **kwargs):
        """Add a message to conversation"""
        msg = LLMMessage(role=role, content=content, **kwargs)
        self.messages.append(msg)
        self.updated_at = time.time()
    
    def get_context_window(self, max_tokens: int = 8000) -> List[LLMMessage]:
        """Get messages within token budget"""
        # Simple token estimation
        estimated = 0
        result = []
        
        # Include messages from newest to oldest until budget exhausted
        for msg in reversed(self.messages):
            msg_tokens = len(msg.content) // 4  # Rough estimate
            if estimated + msg_tokens > max_tokens:
                break
            result.insert(0, msg)
            estimated += msg_tokens
        
        return result
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "name": m.name,
                    "tool_calls": m.tool_calls,
                    "tool_call_id": m.tool_call_id
                }
                for m in self.messages
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Conversation":
        """Create from dictionary"""
        conv = cls(
            id=data["id"],
            title=data.get("title", ""),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            metadata=data.get("metadata", {})
        )
        
        for msg_data in data.get("messages", []):
            conv.messages.append(LLMMessage(
                role=msg_data["role"],
                content=msg_data["content"],
                name=msg_data.get("name"),
                tool_calls=msg_data.get("tool_calls"),
                tool_call_id=msg_data.get("tool_call_id")
            ))
        
        return conv


class ConversationManager:
    """
    Manages conversation history and persistence
    """
    
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_path = str(Path.home() / ".acas-pro" / "conversations")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._conversations: Dict[str, Conversation] = {}
        self._active_conversation: Optional[str] = None
    
    def create_conversation(self, title: str = "", id: str = None) -> Conversation:
        """Create a new conversation"""
        if id is None:
            import secrets
            id = f"conv_{secrets.token_hex(8)}"
        
        conv = Conversation(id=id, title=title)
        self._conversations[id] = conv
        self._active_conversation = id
        self._save_conversation(conv)
        
        return conv
    
    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        if conv_id in self._conversations:
            return self._conversations[conv_id]
        
        # Try to load from storage
        conv = self._load_conversation(conv_id)
        if conv:
            self._conversations[conv_id] = conv
            return conv
        
        return None
    
    def get_active(self) -> Optional[Conversation]:
        """Get active conversation"""
        if self._active_conversation:
            return self.get_conversation(self._active_conversation)
        return None
    
    def set_active(self, conv_id: str):
        """Set active conversation"""
        if conv_id in self._conversations or self._load_conversation(conv_id):
            self._active_conversation = conv_id
    
    def list_conversations(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """List all conversations (metadata only)"""
        # Load all conversation metadata
        conv_list = []
        
        for conv_file in self.storage_path.glob("*.json"):
            try:
                with open(conv_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    conv_list.append({
                        "id": data["id"],
                        "title": data.get("title", ""),
                        "created_at": data.get("created_at", 0),
                        "updated_at": data.get("updated_at", 0),
                        "message_count": len(data.get("messages", []))
                    })
            except Exception as e:
                logger.exception("Unhandled exception")
                continue
        
        # Sort by updated_at descending
        conv_list.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        
        return conv_list[offset:offset + limit]
    
    def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation"""
        if conv_id in self._conversations:
            del self._conversations[conv_id]
        
        conv_file = self.storage_path / f"{conv_id}.json"
        if conv_file.exists():
            conv_file.unlink()
            return True
        
        return False
    
    def update_conversation(self, conv: Conversation):
        """Update conversation in storage"""
        self._save_conversation(conv)
    
    def search_conversations(self, query: str, limit: int = 10) -> List[Dict]:
        """Search conversations by content"""
        results = []
        query_lower = query.lower()
        
        for conv_file in self.storage_path.glob("*.json"):
            try:
                with open(conv_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Search in title and messages
                found = False
                if query_lower in data.get("title", "").lower():
                    found = True
                else:
                    for msg in data.get("messages", []):
                        if query_lower in msg.get("content", "").lower():
                            found = True
                            break
                
                if found:
                    results.append({
                        "id": data["id"],
                        "title": data.get("title", ""),
                        "created_at": data.get("created_at", 0),
                        "updated_at": data.get("updated_at", 0)
                    })
                
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                logger.exception("Unhandled exception")
                continue
        
        return results
    
    def _save_conversation(self, conv: Conversation):
        """Save conversation to disk"""
        conv_file = self.storage_path / f"{conv.id}.json"
        with open(conv_file, "w", encoding="utf-8") as f:
            json.dump(conv.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _load_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Load conversation from disk"""
        conv_file = self.storage_path / f"{conv_id}.json"
        if not conv_file.exists():
            return None
        
        try:
            with open(conv_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Conversation.from_dict(data)
        except Exception as e:
            logger.exception("Unhandled exception")
            return None
    
    def clear_all(self):
        """Clear all conversations"""
        self._conversations.clear()
        self._active_conversation = None
        
        for conv_file in self.storage_path.glob("*.json"):
            conv_file.unlink()
    
    def export_conversation(self, conv_id: str, format: str = "json") -> str:
        """Export conversation to specified format"""
        conv = self.get_conversation(conv_id)
        if not conv:
            return ""
        
        if format == "json":
            return json.dumps(conv.to_dict(), ensure_ascii=False, indent=2)
        elif format == "markdown":
            lines = [f"# {conv.title or conv.id}", ""]
            for msg in conv.messages:
                role_display = {
                    "system": "系统",
                    "user": "用户",
                    "assistant": "助手",
                    "tool": "工具"
                }.get(msg.role, msg.role)
                lines.append(f"**{role_display}**: {msg.content}")
                lines.append("")
            return "\n".join(lines)
        else:
            return ""
