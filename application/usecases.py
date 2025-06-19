import json
from datetime import date, datetime
from typing import Optional
from domain.models import Platform, Goal, Task, Account, TaskLog
from domain.policies import FixedInterval, DeadlineDistribution, StateBasedGoal
from domain.states import InvalidTransition
from .ports import IPlatformRepository, IGoalRepository, ITaskRepository, IAccountRepository, ITaskLogRepository
from domain.strategies import ManualExecution, ScriptExecution, ManualCheck, ScriptCheck
from infrastructure.script_runner import run_script

class CreatePlatformUseCase:
    def __init__(self, repo: IPlatformRepository): self.repo = repo
    def execute(self, name: str, config: Optional[dict] = None):
        self.repo.save(Platform(id=None, name=name, config=config))

class UpdatePlatformUseCase:
    def __init__(self, repo: IPlatformRepository): self.repo = repo
    def execute(self, platform_id: int, name: str, config: dict):
        platform = self.repo.get_by_id(platform_id)
        if not platform:
            raise ValueError("Platform not found")
        platform.name = name
        platform.config = config
        self.repo.save(platform)

class ListPlatformsUseCase:
    def __init__(self, repo: IPlatformRepository): self.repo = repo
    def execute(self): return self.repo.list_all()

class GetPlatformUseCase:
    def __init__(self, repo: IPlatformRepository): self.repo = repo
    def execute(self, platform_id: int): return self.repo.get_by_id(platform_id)


# --- Account Use Cases ---
class CreateAccountUseCase:
    def __init__(self, repo: IAccountRepository): self.repo = repo
    def execute(self, platform_id: int, username: str, notes: str):
        self.repo.save(Account(id=None, platform_id=platform_id, username=username, notes=notes))

class ListAccountsByPlatformUseCase:
    def __init__(self, repo: IAccountRepository): self.repo = repo
    def execute(self, platform_id: int): return self.repo.list_by_platform(platform_id)

class DeleteAccountUseCase:
    def __init__(self, repo: IAccountRepository): self.repo = repo
    def execute(self, account_id: int): self.repo.delete(account_id)

class GetDashboardDataUseCase:
    def __init__(self, repo: IAccountRepository): self.repo = repo
    def execute(self): return self.repo.get_dashboard_summary()


# --- Goal & Task Use Cases ---
class CreateGoalUseCase:
    def __init__(self, repo: IGoalRepository): self.repo = repo
    def execute(self, data: dict):
        print(data)
        policy_type = data.pop("policy_type")
        policy = None
        if policy_type == "fixed":
            policy = FixedInterval(days=data["interval_days"])
        elif policy_type == "deadline":
            policy = DeadlineDistribution(deadline=data["deadline_date"], total=data["total_occurrences"], freeze=data.get("freeze_on_miss", False))
        elif policy_type == "state_based":
            policy = StateBasedGoal(check_interval_days=data["check_interval_days"])
        else:
            raise ValueError("Invalid policy type")

        exec_strategy_type = data.pop("execution_strategy_type", "Manual")
        exec_strategy = ManualExecution()
        if exec_strategy_type == "CustomScript":
            exec_strategy = ScriptExecution(
                script_content=data.get("execution_script_content", ""),
                env_vars=data.get("execution_script_env_vars", {})
            )

        check_strategy_type = data.pop("check_strategy_type", "ManualCheck")
        check_strategy = ManualCheck()
        if check_strategy_type == "CustomScriptCheck":
            check_strategy = ScriptCheck(
                script_content=data.get("check_script_content", ""),
                env_vars=data.get("check_script_env_vars", {})
            )
        goal = Goal(id=None, platform_id=data["platform_id"], description=data["description"],
                    start_date=data["start_date"], policy=policy, end_date=data.get("deadline_date"),
                    account_ids=data.get("account_ids"),
                    task_distribution_strategy=data.get("task_distribution_strategy", "all"),
                    catchup_strategy=data.get("catchup_strategy", "all"),
                    execution_strategy=exec_strategy,
                    check_strategy=check_strategy)
        self.repo.save(goal)

class ListGoalsUseCase:
    def __init__(self, repo: IGoalRepository): self.repo = repo
    def execute(self): return self.repo.list_all()

class GetGoalUseCase:
    def __init__(self, repo: IGoalRepository): self.repo = repo
    def execute(self, goal_id: int): return self.repo.get_by_id(goal_id)

class DeleteGoalUseCase:
    def __init__(self, repo: IGoalRepository): self.repo = repo
    def execute(self, goal_id: int): self.repo.delete(goal_id)

class UpdateGoalUseCase:
    def __init__(self, repo: IGoalRepository): self.repo = repo
    def execute(self, goal_id: int, data: dict):
        policy_type = data.pop("policy_type")
        policy = None
        if policy_type == "fixed":
            policy = FixedInterval(days=data["interval_days"])
        elif policy_type == "deadline":
            policy = DeadlineDistribution(deadline=data["deadline_date"], total=data["total_occurrences"], freeze=data.get("freeze_on_miss", False))
        elif policy_type == "state_based":
            policy = StateBasedGoal(check_interval_days=data["check_interval_days"])
        else:
            raise ValueError("Invalid policy type")

        exec_strategy_type = data.pop("execution_strategy_type", "Manual")
        exec_strategy = ManualExecution()
        if exec_strategy_type == "CustomScript":
            exec_strategy = ScriptExecution(
                script_content=data.get("execution_script_content", ""),
                env_vars=data.get("execution_script_env_vars", {})
            )

        check_strategy_type = data.pop("check_strategy_type", "ManualCheck")
        check_strategy = ManualCheck()
        if check_strategy_type == "CustomScriptCheck":
            check_strategy = ScriptCheck(
                script_content=data.get("check_script_content", ""),
                env_vars=data.get("check_script_env_vars", {})
            )

        goal = Goal(id=goal_id, platform_id=data["platform_id"], description=data["description"],
                    start_date=data["start_date"], policy=policy, end_date=data.get("deadline_date"),
                    account_ids=data.get("account_ids"),
                    task_distribution_strategy=data.get("task_distribution_strategy", "all"),
                    catchup_strategy=data.get("catchup_strategy", "all"),
                    execution_strategy=exec_strategy,
                    check_strategy=check_strategy)

        self.repo.update(goal)

class GenerateDueTasksUseCase:
    def __init__(self, goal_repo: IGoalRepository, task_repo: ITaskRepository, account_repo: IAccountRepository):
        self.goal_repo = goal_repo
        self.task_repo = task_repo
        self.account_repo = account_repo


    def execute(self):
        active_goals = [g for g in self.goal_repo.list_all() if g.status == "Active"]

        for goal in active_goals:
            if goal.end_date and goal.end_date < date.today():
                continue

            if not goal.account_ids or goal.task_distribution_strategy == "all":
                target_account_ids = goal.account_ids if goal.account_ids else [None]
                for acc_id in target_account_ids:
                    latest_task = self.task_repo.find_latest_for_goal(goal.id, acc_id)
                    last_task_date = latest_task.due_date if latest_task else None

                    num_completed = 0
                    if isinstance(goal.policy, DeadlineDistribution):
                        # Count completed for the specific account line
                        num_completed = self.task_repo.count_completed_for_goal(goal.id, [acc_id] if acc_id else None)

                    new_tasks = goal.generate_tasks(last_task_date=last_task_date, num_completed=num_completed)
                    for task in new_tasks:
                        task.account_id = acc_id
                        self.task_repo.save(task)

            # "round-robin" logic
            elif goal.task_distribution_strategy == "round_robin":
                latest_task = self.task_repo.find_latest_for_goal_any_account(goal.id)
                last_task_date = latest_task.due_date if latest_task else None

                next_account_id = goal.account_ids[0] # Default to the first account
                if latest_task and latest_task.account_id in goal.account_ids:
                    try:
                        last_index = goal.account_ids.index(latest_task.account_id)
                        next_index = (last_index + 1) % len(goal.account_ids)
                        next_account_id = goal.account_ids[next_index]
                    except ValueError:
                        pass

                num_completed = 0
                if isinstance(goal.policy, DeadlineDistribution):
                    # for round-robin deadline the count is for the whole group
                    num_completed = self.task_repo.count_completed_for_goal(goal.id, goal.account_ids)

                new_tasks = goal.generate_tasks(last_task_date=last_task_date, num_completed=num_completed)
                for task in new_tasks:
                    task.account_id = next_account_id
                    self.task_repo.save(task)
class ListTasksUseCase:
    def __init__(self, repo: ITaskRepository): self.repo = repo
    def execute(self): return self.repo.list_all()

class ProcessTaskCompletionUseCase:
    """
    Completes a task and then checks if this completion also completes the parent goal.
    """
    def __init__(self, task_repo: ITaskRepository, log_repo: ITaskLogRepository, goal_repo: IGoalRepository):
        self.task_repo = task_repo
        self.log_repo = log_repo
        self.goal_repo = goal_repo
        self.mark_done_uc = MarkTaskDoneUseCase(task_repo, log_repo)

    def execute(self, task_id: int, notes: Optional[str] = None, complete_parent_goal: bool = True):
        """
        Completes a task and conditionally completes the parent goal.
        """
        # 1. Mark the task as done
        self.mark_done_uc.execute(task_id, notes=notes)

        task = self.task_repo.get_by_id(task_id)
        if not task: return

        goal = self.goal_repo.get_by_id(task.goal_id)
        if not goal: return

        # 2. Conditionally check if the parent goal should be completed
        if not complete_parent_goal:
            print(f"Task {task.id} completed, but parent goal {goal.id} will remain active as requested.")
            return

        if isinstance(goal.policy, StateBasedGoal):
            goal.status = "Completed"
            self.goal_repo.update(goal)
            print(f"Goal {goal.id} has been completed because its state-based task was achieved.")

class MarkTaskDoneUseCase:
    # Now requires both a task repo and a log repo
    def __init__(self, task_repo: ITaskRepository, log_repo: ITaskLogRepository):
        self.task_repo = task_repo
        self.log_repo = log_repo

    def execute(self, task_id: int, notes: Optional[str] = None):
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")

        old_status = task.status.name
        task.complete() # this internally changes the status so we are good
        self.task_repo.save(task)

        # Create the log entry
        log_entry = TaskLog(
            id=None,
            task_id=task.id,
            timestamp=datetime.utcnow(),
            from_status=old_status,
            to_status=task.status.name,
            notes=notes
        )
        self.log_repo.save(log_entry)

class StartTaskUseCase:
    def __init__(self, task_repo: ITaskRepository, log_repo: ITaskLogRepository):
        self.task_repo = task_repo
        self.log_repo = log_repo

    def execute(self, task_id: int):
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")

        old_status = task.status.name
        task.start()
        self.task_repo.save(task)

        log_entry = TaskLog(
            id=None, task_id=task.id, timestamp=datetime.utcnow(),
            from_status=old_status, to_status=task.status.name
        )
        self.log_repo.save(log_entry)

class SkipTaskUseCase:
    """Use case for a user to skip a task."""
    def __init__(self, task_repo: ITaskRepository, log_repo: ITaskLogRepository):
        self.task_repo = task_repo
        self.log_repo = log_repo

    def execute(self, task_id: int, notes: Optional[str] = None):
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")

        old_status = task.status.name
        task.skip()
        print(task) # for debug
        self.task_repo.save(task)

        log_entry = TaskLog(id=None, task_id=task.id, timestamp=datetime.utcnow(),
                            from_status=old_status, to_status=task.status.name, notes=notes)
        self.log_repo.save(log_entry)

class FailTaskUseCase:
    def __init__(self, task_repo: ITaskRepository, log_repo: ITaskLogRepository):
        self.task_repo = task_repo
        self.log_repo = log_repo

    def execute(self, task_id: int, notes: Optional[str] = None):
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")

        old_status = task.status.name
        task.fail()
        self.task_repo.save(task)

        log_entry = TaskLog(
            id=None, task_id=task.id, timestamp=datetime.utcnow(),
            from_status=old_status, to_status=task.status.name, notes=notes
        )
        self.log_repo.save(log_entry)

class ListTaskLogsUseCase:
    def __init__(self, log_repo: ITaskLogRepository, task_repo: ITaskRepository):
        self.log_repo = log_repo
        self.task_repo = task_repo

    def execute(self, task_id: int) -> dict:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")

        logs = self.log_repo.list_by_task_id(task_id)
        return {"task": task, "logs": logs}

class RunExecutionScriptUseCase:
    """Runs an execution script, moving task from Waiting -> In Progress on success."""
    def __init__(self, task_repo: ITaskRepository, goal_repo: IGoalRepository, log_repo: ITaskLogRepository, account_repo: IAccountRepository, platform_repo: IPlatformRepository):
        self.task_repo = task_repo
        self.goal_repo = goal_repo
        self.log_repo = log_repo
        self.account_repo = account_repo
        self.platform_repo = platform_repo

    def execute(self, task_id: int):
        task = self.task_repo.get_by_id(task_id)
        goal = self.goal_repo.get_by_id(task.goal_id)
        strategy = goal.execution_strategy

        account = self.account_repo.get_by_id(task.account_id) if task.account_id else None
        platform = self.platform_repo.get_by_id(goal.platform_id)

        context = {
            "task": task.to_dict() if task else None,
            "goal": goal.to_dict() if goal else None,
            "account": account.to_dict() if account else None,
            "platform": platform.to_dict() if platform else None,
        }
        context_json = json.dumps(context)

        if not isinstance(strategy, ScriptExecution):
            raise TypeError("Task does not have an execution script.")
        if task.status.name != 'Waiting':
            raise InvalidTransition("Can only execute scripts for tasks in 'Waiting' state.")

        # For execution, i only care about the exit code, not a keyword.
        script_env = strategy.env_vars.copy()
        script_env['TASK_CONTEXT'] = context_json
        success, logs = run_script(strategy.script_content, script_env, success_keyword=None)

        old_status = task.status.name
        new_status_name = ""

        if success:
            task.start() # move state to In Progress
            new_status_name = task.status.name
        else:
            task.fail() # move state to Failed
            new_status_name = task.status.name

        self.task_repo.save(task)
        log = TaskLog(id=None, task_id=task.id, timestamp=datetime.utcnow(), 
                      from_status=old_status, to_status=new_status_name, notes=logs)
        self.log_repo.save(log)


class RunCheckScriptUseCase:
    """
    Runs a check script, interpreting specific keywords to determine
    the outcome for both the task and the parent goal.
    """
    def __init__(self, task_repo: ITaskRepository, goal_repo: IGoalRepository, log_repo: ITaskLogRepository, account_repo: IAccountRepository, platform_repo: IPlatformRepository):
        self.task_repo = task_repo
        self.goal_repo = goal_repo
        self.log_repo = log_repo
        self.account_repo = account_repo
        self.platform_repo = platform_repo

        self.process_completion_uc = ProcessTaskCompletionUseCase(task_repo, log_repo, goal_repo)
        self.fail_task_uc = FailTaskUseCase(task_repo, log_repo)

    def execute(self, task_id: int):
        """
        Executes the check script for a given task and processes the result.
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            print(f"Error: Task with ID {task_id} not found.")
            return

        goal = self.goal_repo.get_by_id(task.goal_id)
        if not goal:
            print(f"Error: Goal for task {task_id} not found.")
            return

        strategy = goal.check_strategy
        if not isinstance(strategy, ScriptCheck):
            print(f"Error: Task {task_id} does not have a check script strategy.")
            return

        if task.status.name != 'In Progress':
            print(f"Error: Can only run check scripts for tasks in 'In Progress' state. Task {task_id} is '{task.status.name}'.")
            return

        # --- Prepare and run the script ---
        account = self.account_repo.get_by_id(task.account_id) if task.account_id else None
        platform = self.platform_repo.get_by_id(goal.platform_id)

        context = {
            "task": task.to_dict() if task else None,
            "goal": goal.to_dict() if goal else None,
            "account": account.to_dict() if account else None,
            "platform": platform.to_dict() if platform else None,
        }
        context_json = json.dumps(context)

        script_env = strategy.env_vars.copy()
        script_env['TASK_CONTEXT'] = context_json

        # TODO: I don't use the success_keyword anymore.
        # I should modify the run_script function to remove it.
        success, logs = run_script(strategy.script_content, script_env, success_keyword=None)

        # Case 1: The script itself failed (non-zero exit code, timeout, etc.).
        if not success:
            notes = f"Check script failed to execute with a non-zero exit code.\n\n{logs}"
            self.fail_task_uc.execute(task_id, notes=notes)
            return

        output_lower = logs.lower()

        # Case 2: The script explicitly states the overall goal is met.
        if "goal_met" in output_lower:
            notes = f"Check script returned GOAL_MET.\n\n{logs}"
            self.process_completion_uc.execute(task_id, notes=notes, complete_parent_goal=True)

        # Case 3: The script confirms the check was successful, but the goal is not yet met.
        elif "check_success" in output_lower:
            notes = f"Check script returned CHECK_SUCCESS.\n\n{logs}"
            self.process_completion_uc.execute(task_id, notes=notes, complete_parent_goal=False)

        # Case 4: The script ran but explicitly states its internal logic failed (e.g., API error).
        elif "check_fail" in output_lower:
            notes = f"Check script returned CHECK_FAIL.\n\n{logs}"
            self.fail_task_uc.execute(task_id, notes=notes)

        # Case 5: The script ran but did not provide any of the expected keywords.
        # To avoid ambiguity, this is treated as a failure.
        else:
            notes = f"Check script ran successfully but did not return a valid keyword (GOAL_MET, CHECK_SUCCESS, or CHECK_FAIL).\n\n{logs}"
            self.fail_task_uc.execute(task_id, notes=notes)