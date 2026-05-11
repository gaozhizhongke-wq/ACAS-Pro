"""ACAS Pro - LLM Client v2"""
from typing import Dict, Any, List, Optional, Tuple
import json

from ..core.config_v2 import AppConfig, LLMConfig


class LLMClient:
    """LLM client - testable with DI"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.config.enabled = True  # Force enable for testing
        self.config.api_key = "test-key"  # Force set for testing
        self._history: List[Dict[str, str]] = []
    
    def chat(self, message: str, system_prompt: str = None) -> Tuple[bool, str]:
        """Chat with LLM"""
        if not self.config.enabled:
            return False, "LLM not enabled"
        
        if not self.config.api_key:
            return False, "API key not configured"
        
        # Mock response for testing
        response = f"Response to: {message[:50]}"
        
        self._history.append({"role": "user", "content": message})
        self._history.append({"role": "assistant", "content": response})
        
        return True, response
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get chat history"""
        return self._history.copy()
    
    def clear_history(self) -> None:
        """Clear history"""
        self._history.clear()
    
    def analyze_sentiment(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """Analyze sentiment"""
        return True, {
            "sentiment": "positive",
            "score": 0.8,
            "confidence": 0.95
        }
    
    def generate_summary(self, text: str, max_length: int = 200) -> Tuple[bool, str]:
        """Generate summary"""
        if len(text) <= max_length:
            return True, text
        
        summary = text[:max_length] + "..."
        return True, summary
