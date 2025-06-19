# domain/strategies.py
from abc import ABC, abstractmethod
from typing import Dict, Optional

class ExecutionStrategy(ABC):
    """Abstract base class for how a task is performed."""
    name: str = "BaseExecution"

    def to_dict(self) -> Dict:
        return {"type": self.name}

class ManualExecution(ExecutionStrategy):
    """Represents a task that is performed manually by the user."""
    name: str = "Manual"

class ScriptExecution(ExecutionStrategy):
    """Represents a task performed by a custom Python script."""
    name: str = "CustomScript"

    def __init__(self, script_content: str, env_vars: Optional[Dict[str, str]] = None):
        self.script_content = script_content
        self.env_vars = env_vars or {}

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            "script_content": self.script_content,
            "env_vars": self.env_vars
        })
        return data


class CheckStrategy(ABC):
    """Abstract base class for how a task's completion is verified."""
    name: str = "BaseCheck"

    def to_dict(self) -> Dict:
        return {"type": self.name}

class ManualCheck(CheckStrategy):
    """Represents a task whose completion is marked manually."""
    name: str = "Manual"

class ScriptCheck(CheckStrategy):
    """Represents a task whose completion is verified by a custom script."""
    name: str = "CustomScriptCheck"

    def __init__(self, script_content: str, env_vars: Optional[Dict[str, str]] = None):
        self.script_content = script_content
        self.env_vars = env_vars or {}

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            "script_content": self.script_content,
            "env_vars": self.env_vars
        })
        return data
