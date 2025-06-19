# pyright: reportImportCycles=false
from datetime import date
from typing import List, Optional
from .policies import DeadlineDistribution, FixedInterval, SchedulingPolicy
from .states import TaskState, WaitingState
from datetime import date, datetime
from typing import List, Optional
from .policies import SchedulingPolicy
from .states import TaskState, WaitingState
from .strategies import ExecutionStrategy, CheckStrategy, ManualExecution, ManualCheck

class TaskLog:
    def __init__(self, id: Optional[int], task_id: int, timestamp: datetime,
                 from_status: str, to_status: str, notes: Optional[str] = None):
        self.id = id
        self.task_id = task_id
        self.timestamp = timestamp
        self.from_status = from_status
        self.to_status = to_status
        self.notes = notes

class Platform:
    def __init__(self, id: int, name: str, config: dict = None):
        self.id = id
        self.name = name
        self.config = config or {}

    def to_dict(self) -> dict:
        return {'id': self.id, 'name': self.name, 'config': self.config}

class Account:
    def __init__(self, id: Optional[int], platform_id: int, username: str, notes: Optional[str] = None):
        self.id = id
        self.platform_id = platform_id
        self.username = username
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'platform_id': self.platform_id,
            'username': self.username,
            'notes': self.notes
        }

class Goal:
    def __init__(self, id: int, platform_id: int, description: str,
                 policy: SchedulingPolicy, start_date: date,
                 execution_strategy: ExecutionStrategy,
                 check_strategy: CheckStrategy,
                 task_distribution_strategy: str = "all",
                 catchup_strategy: str = "all",
                 end_date: Optional[date] = None,
                 account_ids: Optional[List[int]] = None,
                 status: str = "Active"):
        self.id = id
        self.platform_id = platform_id
        self.description = description
        self.policy = policy
        self.start_date = start_date
        self.execution_strategy = execution_strategy or ManualExecution()
        self.check_strategy = check_strategy or ManualCheck()
        self.task_distribution_strategy = task_distribution_strategy
        self.catchup_strategy = catchup_strategy
        self.end_date = end_date
        self.account_ids = account_ids or []
        self.status = status
        self.platform_name: Optional[str] = None

    def get_context_string(self) -> str:
        policy_name = self.policy.__class__.__name__
        if policy_name == "FixedInterval":
            return f"This is a recurring goal that repeats every {self.policy.days} day(s)."
        if policy_name == "DeadlineDistribution":
            return f"Part of a goal to complete {self.policy.total} tasks by {self.policy.deadline.strftime('%B %d, %Y')}."
        if policy_name == "StateBasedGoal": #<-- Add context for new policy
            return f"A goal to achieve a specific state, checked every {self.policy.check_interval_days} day(s)."
        return "A standalone goal."

    def to_dict(self):
        return {
            "id": self.id,
            "platform_id": self.platform_id,
            "description": self.description,
            "account_ids": self.account_ids,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "policy": self.policy.to_dict(),
            "execution_strategy": self.execution_strategy.to_dict(),
            "check_strategy": self.check_strategy.to_dict(),
            "task_distribution_strategy": self.task_distribution_strategy
        }

    def generate_tasks(self, last_task_date: Optional[date], num_completed: int = 0) -> List['Task']:
        """
        Generates due tasks based on the goal's policy and catch-up strategy.

        This method works in three stages:
        1. Collect all potential due dates from the last task up to today.
        2. Apply the catch-up strategy ('all' or 'latest') to filter the dates.
        3. Create the final list of Task domain objects.
        """

        # --- Stage 1: Collect all potential due dates ---
        potential_due_dates = []
        # The starting point for calculation is either the last task's due date
        # or the goal's start date if no tasks exist yet.
        current_last_date = last_task_date or self.start_date

        # Determine the very first due date. If no tasks exist yet, we must calculate
        # from the goal's start_date, not from 'current_last_date' which would be the same.
        # This is critical for DeadlineDistribution to correctly calculate its first interval.
        if last_task_date:
            next_due_date = self.policy.next_due(current_last_date, num_completed)
        else:
            next_due_date = self.policy.next_due(self.start_date, num_completed)

        while next_due_date <= date.today():
            # Stop if the due date is past the goal's end date.
            if self.end_date and next_due_date > self.end_date:
                break

            # For DeadlineDistribution, the 'freeze' option prevents rescheduling if a task was missed.
            if isinstance(self.policy, DeadlineDistribution) and self.policy.freeze:
                if last_task_date and last_task_date < date.today():
                    # A previous task was due in the past and is not 'Completed' yet.
                    # Stop generating new tasks for this goal line.
                    break

            potential_due_dates.append(next_due_date)

            # For the next loop iteration, calculate the next due date from the one we just found.
            current_last_date = next_due_date

            # This is for DeadlineDistribution: As I generate more tasks in this single run,
            # I increment the `num_completed` count to correctly shorten the interval for subsequent dates.
            num_completed_for_next_calc = num_completed + len(potential_due_dates)
            next_due_date = self.policy.next_due(current_last_date, num_completed_for_next_calc)

        # --- Stage 2: Apply the catch-up strategy to filter the dates ---
        if not potential_due_dates:
            return [] # No tasks are due.

        final_due_dates = []

        # This is intentionally NOT applied to DeadlineDistribution, as that policy has
        # its own built-in catch-up logic (shortening intervals).
        if self.catchup_strategy == 'latest' and isinstance(self.policy, FixedInterval):
            # Only take the single most recent due date.
            final_due_dates.append(potential_due_dates[-1])
        else:
            # Default 'all' behavior or any other policy type gets all due tasks.
            final_due_dates = potential_due_dates

        # --- Stage 3: Create the final list of Task domain objects ---
        tasks_to_create = []
        for due_date in final_due_dates:
            tasks_to_create.append(Task(
                id=None,
                goal_id=self.id,
                account_id=None, # This will be set later by the use case
                due_date=due_date,
                status=WaitingState()
            ))

        return tasks_to_create

class Task:
    def __init__(self, id: Optional[int], goal_id: int, due_date: date, status: TaskState, account_id: Optional[int] = None):
        self.id = id
        self.goal_id = goal_id
        self.due_date = due_date
        self.account_id = account_id
        self._status = status
        self.goal_context: Optional[str] = None
        self.goal: Optional[Goal] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'due_date': self.due_date.isoformat(),
            'account_id': self.account_id,
            'status': self.status.name
        }

    @property
    def status(self) -> TaskState:
        return self._status

    def skip(self):
        """Transitions the task to the Skipped state."""
        self._status.skip(self)

    @status.setter
    def status(self, new_state: TaskState):
        print(f"Task {self.id} transitioning from {self._status.name} to {new_state.name}")
        self._status = new_state

    def complete(self):
        self._status.complete(self)

    def fail(self):
        self._status.fail(self)

    def start(self):
        self._status.start(self)