"""
Prompt Loader

Loads prompt templates from YAML files or returns defaults.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    Loads prompt templates from YAML configuration.
    
    Falls back to default templates if files not found.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize prompt loader.
        
        Args:
            config_dir: Directory containing prompt YAML files
        """
        self.config_dir = config_dir or self._get_default_config_dir()
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def _get_default_config_dir(self) -> Path:
        """Get default config directory."""
        # Look for config/prompts relative to this file
        current = Path(__file__).parent.parent.parent.parent.parent
        return current / "config" / "prompts"
    
    def load(self, category: str, name: str) -> Optional[str]:
        """
        Load a specific prompt template.
        
        Args:
            category: Category (e.g., "agents", "phases")
            name: Template name (e.g., "technical_analyst")
            
        Returns:
            Prompt string or None if not found
        """
        cache_key = f"{category}/{name}"
        
        if cache_key in self._cache:
            return self._cache[cache_key].get("prompt")
        
        # Try to load from file
        file_path = self.config_dir / category / f"{name}.yml"
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self._cache[cache_key] = data
                    return data.get("prompt") or data.get("system_prompt")
            except Exception as e:
                logger.warning(f"Failed to load prompt {cache_key}: {e}")
        
        return None
    
    def load_agent_prompt(self, agent_id: str, language: str = "en") -> Optional[str]:
        """Load agent system prompt."""
        prompt = self.load("agents", agent_id.lower())
        
        # Check for language-specific version
        if not prompt and language != "en":
            prompt = self.load("agents", f"{agent_id.lower()}_{language}")
        
        return prompt
    
    def load_phase_prompt(self, phase_name: str) -> Optional[str]:
        """Load phase prompt template."""
        return self.load("phases", phase_name.lower().replace(" ", "_"))
