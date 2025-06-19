import json
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case
from typing import List, Optional, Dict
from datetime import date, datetime

from domain.models import (
    Platform as DomainPlatform, Goal as DomainGoal, Task as DomainTask, 
    Account as DomainAccount, TaskLog as DomainTaskLog
)
from domain.policies import FixedInterval, DeadlineDistribution, SchedulingPolicy
from domain.states import SkippedState, WaitingState, InProgressState, CompletedState, FailedState, TaskState
from domain.strategies import (
    ExecutionStrategy, CheckStrategy, ManualExecution,
    ScriptExecution, ManualCheck, ScriptCheck
)

from . import orm

STATE_MAP_TO_DOMAIN: Dict[str, TaskState] = {
    "Waiting": WaitingState(),
    "In Progress": InProgressState(),
    "Completed": CompletedState(),
    "Failed": FailedState(),
    "Skipped": SkippedState(),
}

def orm_to_domain_task(t: orm.Task) -> DomainTask:
    task = DomainTask(
        id=t.id,
        goal_id=t.goal_id,
        due_date=t.due_date,
        status=STATE_MAP_TO_DOMAIN.get(t.status, WaitingState()),
        account_id=t.account_id
    )
    if t.goal:
        domain_goal = orm_to_domain_goal(t.goal)
        task.goal_description = domain_goal.description
        if t.goal.platform:
            task.platform_name = t.goal.platform.name
        else:
            task.platform_name = "N/A"
        task.goal_context = domain_goal.get_context_string()
        task.goal = domain_goal
    else:
        task.goal_description = "N/A"
        task.platform_name = "N/A"

    task.account_username = t.account.username if t.account else "Platform-Level"
    return task

class SQLAlchemyTaskLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, log: DomainTaskLog):
        orm_log = orm.TaskLog(
            task_id=log.task_id,
            timestamp=log.timestamp,
            from_status=log.from_status,
            to_status=log.to_status,
            notes=log.notes
        )
        self.db.add(orm_log)
        self.db.commit()

    def list_by_task_id(self, task_id: int) -> List[DomainTaskLog]:
        orm_logs = self.db.query(orm.TaskLog).filter(orm.TaskLog.task_id == task_id).order_by(orm.TaskLog.timestamp.asc()).all()
        return [orm_to_domain_task_log(log) for log in orm_logs]

STATE_MAP_TO_DOMAIN: Dict[str, TaskState] = {
    "Waiting": WaitingState(),
    "In Progress": InProgressState(),
    "Completed": CompletedState(),
    "Failed": FailedState(),
    "Skipped": SkippedState(),
}

def orm_to_domain_task_log(log: orm.TaskLog) -> DomainTaskLog:
    return DomainTaskLog(
        id=log.id,
        task_id=log.task_id,
        timestamp=log.timestamp,
        from_status=log.from_status,
        to_status=log.to_status,
        notes=log.notes
    )

def orm_to_domain_strategy(strategy_json: str) -> ExecutionStrategy | CheckStrategy:
    data = json.loads(strategy_json)
    strategy_type = data.pop("type")

    # Execution strategies
    if strategy_type == "Manual":
        return ManualExecution()
    if strategy_type == "CustomScript":
        return ScriptExecution(**data)

    # Check strategies
    if strategy_type == "ManualCheck":
        return ManualCheck()
    if strategy_type == "CustomScriptCheck":
        return ScriptCheck(**data)

    raise NotImplementedError(f"Strategy type {strategy_type} not implemented")


def orm_to_domain_policy(policy_json: str) -> SchedulingPolicy:
    data = json.loads(policy_json)
    policy_type = data.pop("type")
    if policy_type == "FixedInterval":
        return FixedInterval(**data)
    if policy_type == "DeadlineDistribution":
        data['deadline'] = date.fromisoformat(data['deadline'])
        return DeadlineDistribution(**data)
    raise NotImplementedError(f"Policy type {policy_type} not implemented")

def orm_to_domain_platform(p: orm.Platform) -> DomainPlatform:
    return DomainPlatform(id=p.id, name=p.name, config=p.config or {})

def orm_to_domain_account(a: orm.Account) -> DomainAccount:
    return DomainAccount(id=a.id, platform_id=a.platform_id, username=a.username, notes=a.notes)

def orm_to_domain_goal(g: orm.Goal) -> DomainGoal:
    goal = DomainGoal(
        id=g.id,
        platform_id=g.platform_id,
        description=g.description,
        start_date=g.start_date,
        end_date=g.end_date,
        policy=orm_to_domain_policy(g.policy_json),
        account_ids=g.account_ids_json,
        execution_strategy=orm_to_domain_strategy(g.execution_strategy_json),
        check_strategy=orm_to_domain_strategy(g.check_strategy_json),
        task_distribution_strategy=g.task_distribution_strategy,
        catchup_strategy=g.catchup_strategy,
        status=g.status
    )
    if g.platform:
        goal.platform_name = g.platform.name
    return goal

class SQLAlchemyPlatformRepository:
    def __init__(self, db: Session): self.db = db
    def save(self, platform: DomainPlatform):
        if platform.id:
            orm_platform = self.db.query(orm.Platform).filter(orm.Platform.id == platform.id).first()
            if orm_platform:
                orm_platform.name = platform.name
                orm_platform.config = platform.config or {}
        else:
            orm_platform = orm.Platform(name=platform.name, config=platform.config or {})
            self.db.add(orm_platform)
        self.db.commit()
    def get_by_id(self, platform_id: int) -> Optional[DomainPlatform]:
        orm_platform = self.db.query(orm.Platform).filter(orm.Platform.id == platform_id).first()
        return orm_to_domain_platform(orm_platform) if orm_platform else None
    def list_all(self) -> List[DomainPlatform]:
        return [orm_to_domain_platform(p) for p in self.db.query(orm.Platform).options(joinedload(orm.Platform.accounts)).all()]

class SQLAlchemyAccountRepository:
    def __init__(self, db: Session): self.db = db
    def save(self, account: DomainAccount):
        orm_account = orm.Account(platform_id=account.platform_id, username=account.username, notes=account.notes)
        self.db.add(orm_account)
        self.db.commit()
    def get_by_id(self, account_id: int) -> Optional[DomainAccount]:
        orm_acc = self.db.query(orm.Account).filter(orm.Account.id == account_id).first()
        return orm_to_domain_account(orm_acc) if orm_acc else None
    def list_by_platform(self, platform_id: int) -> List[DomainAccount]:
        return [orm_to_domain_account(a) for a in self.db.query(orm.Account).filter(orm.Account.platform_id == platform_id).all()]
    def delete(self, account_id: int):
        orm_acc = self.db.query(orm.Account).filter(orm.Account.id == account_id).first()
        if orm_acc:
            self.db.delete(orm_acc)
            self.db.commit()

    def get_dashboard_summary(self) -> List[dict]:
        """
        Generates a dashboard summary with detailed task counts per account.
        This new version uses conditional aggregation to count multiple task statuses at once.
        """
        all_platforms = self.db.query(orm.Platform).options(joinedload(orm.Platform.accounts)).order_by(orm.Platform.name).all()
        platforms_dict = {p.id: {"id": p.id, "name": p.name, "accounts": []} for p in all_platforms}

        # Subquery to get the last completed activity date for each account
        last_completed_q = self.db.query(
            orm.Task.account_id, func.max(orm.Task.due_date).label("last_activity_date")
        ).filter(orm.Task.status == "Completed").group_by(orm.Task.account_id).subquery()

        # Subquery to get aggregated counts of tasks in various states for each account
        task_counts_q = self.db.query(
            orm.Task.account_id,
            func.sum(case((orm.Task.status == "Waiting", 1), else_=0)).label("waiting_count"),
            func.sum(case((orm.Task.status == "In Progress", 1), else_=0)).label("in_progress_count"),
            func.sum(case((orm.Task.status == "Failed", 1), else_=0)).label("failed_count"),
            func.sum(case((orm.Task.status == "Skipped", 1), else_=0)).label("skipped_count")
        ).group_by(orm.Task.account_id).subquery()

        # Main query joining account info with the two subqueries
        accounts_data = self.db.query(
            orm.Account,
            last_completed_q.c.last_activity_date,
            task_counts_q.c.waiting_count,
            task_counts_q.c.in_progress_count,
            task_counts_q.c.failed_count,
            task_counts_q.c.skipped_count
        ).outerjoin(last_completed_q, orm.Account.id == last_completed_q.c.account_id) \
         .outerjoin(task_counts_q, orm.Account.id == task_counts_q.c.account_id).all()

        for account, last_activity, waiting, in_progress, failed, skipped in accounts_data:
            if account.platform_id in platforms_dict:
                platforms_dict[account.platform_id]["accounts"].append({
                    "id": account.id, "username": account.username,
                    "last_activity": last_activity,
                    "waiting_count": waiting or 0,
                    "in_progress_count": in_progress or 0,
                    "failed_count": failed or 0,
                    "skipped_count": skipped or 0
                })
        return list(platforms_dict.values())

class SQLAlchemyGoalRepository:
    def __init__(self, db: Session): self.db = db
    def save(self, goal: DomainGoal):
        policy_dict = {"type": goal.policy.__class__.__name__}
        if isinstance(goal.policy, FixedInterval):
            policy_dict["days"] = goal.policy.days
        elif isinstance(goal.policy, DeadlineDistribution):
            policy_dict.update({
                "deadline": goal.policy.deadline.isoformat(),
                "total": goal.policy.total,
                "freeze": goal.policy.freeze
            })

        orm_goal = orm.Goal(
            description=goal.description, platform_id=goal.platform_id,
            start_date=goal.start_date, end_date=goal.end_date,
            policy_json=json.dumps(policy_dict),
            account_ids_json=goal.account_ids,
            execution_strategy_json=json.dumps(goal.execution_strategy.to_dict()),
            check_strategy_json=json.dumps(goal.check_strategy.to_dict()),
            task_distribution_strategy=goal.task_distribution_strategy,
            catchup_strategy=goal.catchup_strategy,
            status=goal.status
        )
        self.db.add(orm_goal)
        self.db.commit()
    def list_all(self) -> List[DomainGoal]:
        orm_goals = self.db.query(orm.Goal).options(
            joinedload(orm.Goal.platform)
        ).order_by(orm.Goal.id.desc()).all()
        return [orm_to_domain_goal(g) for g in orm_goals]
    def get_by_id(self, goal_id: int) -> Optional[DomainGoal]:
        orm_goal = self.db.query(orm.Goal).filter(orm.Goal.id == goal_id).first()
        return orm_to_domain_goal(orm_goal) if orm_goal else None
    def update(self, goal: DomainGoal):
        orm_goal = self.db.query(orm.Goal).filter(orm.Goal.id == goal.id).first()
        if not orm_goal:
            return

        # Create the policy JSON
        policy_dict = {"type": goal.policy.__class__.__name__}
        if isinstance(goal.policy, FixedInterval):
            policy_dict["days"] = goal.policy.days
        elif isinstance(goal.policy, DeadlineDistribution):
            policy_dict.update({
                "deadline": goal.policy.deadline.isoformat(),
                "total": goal.policy.total,
                "freeze": goal.policy.freeze
            })

        orm_goal.description = goal.description
        orm_goal.platform_id = goal.platform_id
        orm_goal.start_date = goal.start_date
        orm_goal.end_date = goal.end_date
        orm_goal.policy_json = json.dumps(policy_dict)
        orm_goal.account_ids_json = goal.account_ids
        orm_goal.status = goal.status
        orm_goal.execution_strategy_json = json.dumps(goal.execution_strategy.to_dict())
        orm_goal.check_strategy_json = json.dumps(goal.check_strategy.to_dict())
        orm_goal.task_distribution_strategy = goal.task_distribution_strategy
        orm_goal.catchup_strategy = goal.catchup_strategy

        self.db.commit()

    def delete(self, goal_id: int):
        orm_goal = self.db.query(orm.Goal).filter(orm.Goal.id == goal_id).first()
        if orm_goal:
            self.db.delete(orm_goal)
            self.db.commit()

class SQLAlchemyTaskRepository:
    def __init__(self, db: Session): self.db = db
    def save(self, task: DomainTask):
        if task.id:
            orm_task = self.db.query(orm.Task).filter(orm.Task.id == task.id).first()
            if orm_task:
                orm_task.status = task.status.name
        else:
            orm_task = orm.Task(
                goal_id=task.goal_id, due_date=task.due_date,
                status=task.status.name, account_id=task.account_id
            )
            self.db.add(orm_task)
        self.db.commit()

    def find_latest_for_goal_any_account(self, goal_id: int) -> Optional[DomainTask]:
        """Finds the most recent task for a goal, irrespective of the account."""
        orm_task = self.db.query(orm.Task)\
            .filter(orm.Task.goal_id == goal_id)\
            .order_by(orm.Task.due_date.desc())\
            .first()
        return orm_to_domain_task(orm_task) if orm_task else None
    def get_by_id(self, task_id: int) -> Optional[DomainTask]:
        orm_task = self.db.query(orm.Task).filter(orm.Task.id == task_id).first()
        return orm_to_domain_task(orm_task) if orm_task else None

    def count_completed_for_goal(self, goal_id: int, account_ids: Optional[List[int]]) -> int:
        """Counts completed tasks for a goal, for platform-level or specific accounts."""
        query = self.db.query(func.count(orm.Task.id)).filter(
            orm.Task.goal_id == goal_id,
            orm.Task.status == "Completed"
        )
        if account_ids is None:
            # Handles platform-level goals (no accounts associated)
            query = query.filter(orm.Task.account_id.is_(None))
        else:
            # Handles goals with one or more accounts
            query = query.filter(orm.Task.account_id.in_(account_ids))
        return query.scalar() or 0

    def list_all(self) -> List[DomainTask]:
        orm_tasks = self.db.query(orm.Task).options(
            joinedload(orm.Task.goal).joinedload(orm.Goal.platform),
            joinedload(orm.Task.account)
        ).order_by(orm.Task.due_date.desc()).all()
        return [orm_to_domain_task(t) for t in orm_tasks]

    def find_latest_for_goal(self, goal_id: int, account_id: Optional[int]) -> Optional[DomainTask]:
        query = self.db.query(orm.Task).filter(orm.Task.goal_id == goal_id)
        query = query.filter(orm.Task.account_id == account_id) if account_id else query.filter(orm.Task.account_id.is_(None))
        orm_task = query.order_by(orm.Task.due_date.desc()).first()
        return orm_to_domain_task(orm_task) if orm_task else None
