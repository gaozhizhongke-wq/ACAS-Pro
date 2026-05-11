"""ACAS Pro - Script Generator v2"""
from typing import Dict, Any, List, Optional, Tuple

from ..core.config_v2 import AppConfig


class ScriptGenerator:
    """Script generator - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
    
    def generate(self, topic: str, style: str = "professional", 
                 length: int = 500) -> Tuple[bool, str]:
        """Generate script"""
        script = f"""
# {topic}

## Introduction
Welcome to our presentation on {topic}.

## Main Content
This is a {style} style script about {topic}.
It contains approximately {length} words.

## Conclusion
Thank you for your attention.
        """.strip()
        
        return True, script
    
    def analyze_keywords(self, text: str) -> Tuple[bool, List[str]]:
        """Analyze keywords"""
        words = text.lower().split()
        keywords = list(set(w for w in words if len(w) > 3))
        return True, keywords[:10]
