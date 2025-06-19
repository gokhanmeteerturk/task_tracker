from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Task

class InvalidTransition(Exception):
    pass

class TaskState(ABC):
    name: str = "Base"

    def start(self, context: "Task"):
        raise InvalidTransition(f"Cannot start from {self.name}")

    def complete(self, context: "Task"):
        raise InvalidTransition(f"Cannot complete from {self.name}")

    def fail(self, context: "Task"):
        raise InvalidTransition(f"Cannot fail from {self.name}")

    def skip(self, context: "Task"):
        raise InvalidTransition(f"Cannot skip from {self.name}")

class SkippedState(TaskState):
    name = "Skipped"
    # This is a terminal state, no transitions out.

class WaitingState(TaskState):
    name = "Waiting"
    def start(self, context: "Task"):
        context.status = InProgressState()
    def skip(self, context: "Task"):
        context.status = SkippedState()

class InProgressState(TaskState):
    name = "In Progress"
    def complete(self, context: "Task"):
        context.status = CompletedState()
    def fail(self, context: "Task"):
        context.status = FailedState()
    def skip(self, context: "Task"):
        context.status = SkippedState()

class CompletedState(TaskState):
    name = "Completed"
    # Terminal state

class FailedState(TaskState):
    name = "Failed"