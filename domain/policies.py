from abc import ABC, abstractmethod
from datetime import date, timedelta

class SchedulingPolicy(ABC):
    @abstractmethod
    def next_due(self, last_date: date, num_completed: int = 0) -> date:
        ...

    def to_dict(self) -> dict:
        """Returns a dictionary representation of the policy."""
        return {'type': self.__class__.__name__}

class FixedInterval(SchedulingPolicy):
    def __init__(self, days: int):
        if days <= 0:
            raise ValueError("Interval must be positive")
        self.days = days

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['days'] = self.days
        return data

    def next_due(self, last_date: date, num_completed: int = 0) -> date:
        return last_date + timedelta(days=self.days)

class DeadlineDistribution(SchedulingPolicy):
    def __init__(self, deadline: date, total: int, freeze: bool):
        if deadline <= date.today():
            raise ValueError("Deadline must be in the future")
        if total <= 0:
            raise ValueError("Total must be positive")
        self.deadline = deadline
        self.total = total
        self.freeze = freeze

    def next_due(self, last_date: date, num_completed: int = 0) -> date:
        remaining_tasks = self.total - num_completed
        # If all tasks are done, or the deadline has passed, return a date in the far future
        # so no new tasks will be generated.
        if remaining_tasks <= 0 or last_date >= self.deadline:
            return date.max
        days_to_deadline = (self.deadline - last_date).days
        # Avoid division by zero and ensure at least 1 day interval
        interval_days = max(1, days_to_deadline // remaining_tasks)

        return last_date + timedelta(days=interval_days)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            'deadline': self.deadline.isoformat(),
            'total': self.total,
            'freeze': self.freeze
        })
        return data

class StateBasedGoal(SchedulingPolicy):
    """
    A policy for goals that are met by achieving an external state.
    Generates periodic "check" tasks until the goal's end_date.
    """
    def __init__(self, check_interval_days: int):
        if check_interval_days <= 0:
            raise ValueError("Check interval must be positive")
        self.check_interval_days = check_interval_days

    def next_due(self, last_date: date, num_completed: int = 0) -> date:
        # This policy doesn't care about num_completed.
        return last_date + timedelta(days=self.check_interval_days)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['check_interval_days'] = self.check_interval_days
        return data