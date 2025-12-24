"""
YAML Configuration Loader for Agents

Loads agent configurations from YAML files.
Provides centralized prompt management and easy customization.
"""

import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class AgentYAMLConfig:
    """
    Agent configuration loaded from YAML.
    """
    id: str
    name: str
    role: str = ""
    tools: List[str] = field(default_factory=list)
    
    # LLM parameters
    temperature: float = 0.7
    timeout_seconds: int = 60
    max_tokens: int = 2000
    
    # Prompts
    system_prompt: str = ""
    system_prompt_zh: str = ""
    
    @property
    def has_chinese_prompt(self) -> bool:
        return bool(self.system_prompt_zh)
    
    def get_prompt(self, language: str = "en") -> str:
        """Get prompt for specified language."""
        if language == "zh" and self.has_chinese_prompt:
            return self.system_prompt_zh
        return self.system_prompt
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentYAMLConfig":
        """Create from dictionary."""
        params = data.get("parameters", {})
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            role=data.get("role", ""),
            tools=data.get("tools", []),
            temperature=params.get("temperature", 0.7),
            timeout_seconds=params.get("timeout_seconds", 60),
            max_tokens=params.get("max_tokens", 2000),
            system_prompt=data.get("system_prompt", ""),
            system_prompt_zh=data.get("system_prompt_zh", "")
        )


class YAMLConfigLoader:
    """
    Loads and caches agent configurations from YAML files.
    
    Default location: config/prompts/agents/
    """
    
    _instance: Optional["YAMLConfigLoader"] = None
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize loader.
        
        Args:
            config_dir: Directory containing YAML configs
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Default: config/prompts/agents relative to app root
            self.config_dir = self._get_default_config_dir()
        
        self._cache: Dict[str, AgentYAMLConfig] = {}
        self._loaded = False
    
    @classmethod
    def get_instance(cls) -> "YAMLConfigLoader":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _get_default_config_dir(self) -> Path:
        """Get default config directory."""
        # Navigate from app/core/agents to config/prompts/agents
        current = Path(__file__).parent.parent.parent.parent
        return current / "config" / "prompts" / "agents"
    
    def load_all(self) -> Dict[str, AgentYAMLConfig]:
        """
        Load all agent configs from directory.
        
        Returns:
            Dict of agent_id -> AgentYAMLConfig
        """
        if not self.config_dir.exists():
            logger.warning(f"Config directory not found: {self.config_dir}")
            return {}
        
        configs = {}
        for yaml_file in self.config_dir.glob("*.yml"):
            try:
                config = self._load_file(yaml_file)
                if config:
                    configs[config.id] = config
                    self._cache[config.id] = config
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")
        
        self._loaded = True
        return configs
    
    def load(self, agent_id: str) -> Optional[AgentYAMLConfig]:
        """
        Load config for specific agent.
        
        Args:
            agent_id: Agent identifier (e.g., "technical_analyst")
            
        Returns:
            AgentYAMLConfig or None if not found
        """
        # Check cache first
        if agent_id in self._cache:
            return self._cache[agent_id]
        
        # Try to load from file
        file_path = self.config_dir / f"{agent_id}.yml"
        if file_path.exists():
            config = self._load_file(file_path)
            if config:
                self._cache[agent_id] = config
                return config
        
        # Try alternative naming conventions
        for alt_name in [agent_id.replace("_", "-"), agent_id.lower()]:
            alt_path = self.config_dir / f"{alt_name}.yml"
            if alt_path.exists():
                config = self._load_file(alt_path)
                if config:
                    self._cache[agent_id] = config
                    return config
        
        return None
    
    def _load_file(self, file_path: Path) -> Optional[AgentYAMLConfig]:
        """Load config from YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return AgentYAMLConfig.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return None
    
    def get_prompt(self, agent_id: str, language: str = "en") -> Optional[str]:
        """
        Get prompt for agent.
        
        Args:
            agent_id: Agent identifier
            language: Language code (en/zh)
            
        Returns:
            Prompt string or None
        """
        config = self.load(agent_id)
        if config:
            return config.get_prompt(language)
        return None
    
    def list_agents(self) -> List[str]:
        """List available agent configs."""
        if not self._loaded:
            self.load_all()
        return list(self._cache.keys())
    
    def reload(self) -> None:
        """Reload all configs from disk."""
        self._cache.clear()
        self._loaded = False
        self.load_all()


# Module-level convenience functions
def get_agent_prompt(agent_id: str, language: str = "en") -> Optional[str]:
    """Get agent prompt from YAML config."""
    return YAMLConfigLoader.get_instance().get_prompt(agent_id, language)


def get_agent_config(agent_id: str) -> Optional[AgentYAMLConfig]:
    """Get full agent config from YAML."""
    return YAMLConfigLoader.get_instance().load(agent_id)


def list_yaml_agents() -> List[str]:
    """List all agents with YAML configs."""
    return YAMLConfigLoader.get_instance().list_agents()
