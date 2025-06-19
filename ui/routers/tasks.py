from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from application.usecases import (
    ProcessTaskCompletionUseCase, StartTaskUseCase, FailTaskUseCase, ListTaskLogsUseCase,
    RunExecutionScriptUseCase, RunCheckScriptUseCase, SkipTaskUseCase
)
from infrastructure.database import SessionLocal
from domain.states import InvalidTransition
from application.usecases import SkipTaskUseCase

from ..dependencies import get_db, get_task_repo, get_task_log_repo, get_goal_repo, get_account_repo, get_platform_repo

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.post("/tasks/{task_id}/run-execution")
def run_task_execution_script(task_id: int, background_tasks: BackgroundTasks, redirect_url: str = Form("/all-tasks")):
    """
    Schedules the script to run in the background with its own DB session.
    """
    def run_script_and_update_db(task_id: int):
        """will be executed in the background"""
        db = SessionLocal()
        try:
            task_repo = get_task_repo(db)
            goal_repo = get_goal_repo(db)
            log_repo = get_task_log_repo(db)
            account_repo = get_account_repo(db)
            platform_repo = get_platform_repo(db)
            use_case = RunExecutionScriptUseCase(task_repo, goal_repo, log_repo, account_repo, platform_repo)
            use_case.execute(task_id=task_id)
        finally:
            db.close()

    background_tasks.add_task(run_script_and_update_db, task_id)

    return RedirectResponse(url=redirect_url, status_code=303)
@router.post("/tasks/generate-due")
def generate_due_tasks(background_tasks: BackgroundTasks, redirect_url: str = Form("/all-tasks")):
    from application.usecases import GenerateDueTasksUseCase

    def run_generation():
        db = SessionLocal()
        try:
            task_repo = get_task_repo(db)
            goal_repo = get_goal_repo(db)
            account_repo = get_account_repo(db)
            use_case = GenerateDueTasksUseCase(goal_repo, task_repo, account_repo)
            use_case.execute()
        finally:
            db.close()

    background_tasks.add_task(run_generation)
    return RedirectResponse(url=redirect_url, status_code=303)

@router.post("/tasks/{task_id}/run-check")
def run_task_check_script(task_id: int, background_tasks: BackgroundTasks, redirect_url: str = Form("/all-tasks")):
    def run_check_and_update_db(task_id: int):
        db = SessionLocal()
        try:
            task_repo = get_task_repo(db)
            goal_repo = get_goal_repo(db)
            log_repo = get_task_log_repo(db)
            account_repo = get_account_repo(db)
            platform_repo = get_platform_repo(db)
            use_case = RunCheckScriptUseCase(task_repo, goal_repo, log_repo, account_repo, platform_repo)
            use_case.execute(task_id=task_id)
        finally:
            db.close()

    background_tasks.add_task(run_check_and_update_db, task_id)
    return RedirectResponse(url=redirect_url, status_code=303)

@router.post("/tasks/{task_id}/skip")
def skip_task(task_id: int, redirect_url: str = Form("/all-tasks"), notes: str = Form(None), db: Session = Depends(get_db)):
    """Endpoint to handle skipping a task."""
    use_case = SkipTaskUseCase(get_task_repo(db), get_task_log_repo(db))
    try:
        use_case.execute(task_id, notes=notes)
    except InvalidTransition as e:
        print(f"Could not skip task {task_id}: {e}")
    return RedirectResponse(url=redirect_url, status_code=303)

@router.post("/tasks/{task_id}/complete")
def mark_task_complete(task_id: int, redirect_url: str = Form("/all-tasks"), notes: str = Form(None), db: Session = Depends(get_db)):
    task_repo = get_task_repo(db)
    log_repo = get_task_log_repo(db)
    goal_repo = get_goal_repo(db)
    use_case = ProcessTaskCompletionUseCase(task_repo, log_repo, goal_repo)
    use_case.execute(task_id, notes=notes)
    return RedirectResponse(url=redirect_url, status_code=303)

@router.post("/tasks/{task_id}/start")
def start_task(task_id: int, redirect_url: str = Form("/all-tasks"), db: Session = Depends(get_db)):
    task_repo = get_task_repo(db)
    log_repo = get_task_log_repo(db)
    use_case = StartTaskUseCase(task_repo, log_repo)
    use_case.execute(task_id)
    return RedirectResponse(url=redirect_url, status_code=303)

@router.post("/tasks/{task_id}/fail")
def fail_task(task_id: int, redirect_url: str = Form("/all-tasks"), notes: str = Form(None), db: Session = Depends(get_db)):
    task_repo = get_task_repo(db)
    log_repo = get_task_log_repo(db)
    use_case = FailTaskUseCase(task_repo, log_repo)
    use_case.execute(task_id, notes=notes)
    return RedirectResponse(url=redirect_url, status_code=303)

@router.get("/tasks/{task_id}/logs", response_class=HTMLResponse)
def get_task_logs(request: Request, task_id: int, db: Session = Depends(get_db)):
    task_repo = get_task_repo(db)
    log_repo = get_task_log_repo(db)
    use_case = ListTaskLogsUseCase(log_repo, task_repo)
    data = use_case.execute(task_id)
    return templates.TemplateResponse(
        "task_logs.html",
        {"request": request, "task": data["task"], "logs": data["logs"], "page_title": f"History for Task #{task_id}"}
    )