import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from application.usecases import ListGoalsUseCase, ListPlatformsUseCase, CreateGoalUseCase, GetGoalUseCase, UpdateGoalUseCase, DeleteGoalUseCase
from ..dependencies import get_db, get_platform_repo, get_goal_repo
from datetime import date
from typing import List, Optional

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def parse_env_vars(form_data, field_name: str) -> dict:
    env_vars = {}
    env_str = form_data.get(field_name, "")
    if env_str:
        for line in env_str.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


@router.get("/goals", response_class=HTMLResponse)
def get_goals_page(req: Request, db: Session = Depends(get_db)):
    """Displays a list of all created goals."""
    use_case = ListGoalsUseCase(get_goal_repo(db))
    goals = use_case.execute()

    return templates.TemplateResponse(
        "goals.html",
        {"request": req, "goals": goals, "page_title": "Manage Goals"}
    )

@router.get("/goals/add", response_class=HTMLResponse)
def get_add_goal_form(req: Request, db: Session = Depends(get_db)):
    platform_repo = get_platform_repo(db)
    platforms_with_accounts = []
    platforms = ListPlatformsUseCase(platform_repo).execute()

    # This is inefficient but simple for now.
    # TODO: create a usecase for this?
    from infrastructure.repositories import SQLAlchemyAccountRepository
    acc_repo = SQLAlchemyAccountRepository(db)
    for p in platforms:
        accounts = acc_repo.list_by_platform(p.id)
        platforms_with_accounts.append({
            "id": p.id, "name": p.name,
            "accounts": [{"id": a.id, "username": a.username} for a in accounts]
        })

    return templates.TemplateResponse(
        "add_goal.html",
        {"request": req, "platforms_json": json.dumps(platforms_with_accounts), "page_title": "Create New Goal"}
    )

@router.post("/goals/add")
async def handle_add_goal(req: Request, db: Session = Depends(get_db)):
    form_data = await req.form()

    account_ids = form_data.getlist("account_ids")

    print("-"*80)
    print(form_data)
    # Simple env var parsing from a string like "KEY=VALUE\nKEY2=VALUE2"
    env_vars = {}
    env_str = form_data.get("execution_script_env_vars", "")
    if env_str:
        for line in env_str.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    goal_data = {
        "platform_id": int(form_data.get("platform_id")),
        "description": form_data.get("description"),
        "start_date": date.fromisoformat(form_data.get("start_date")),
        "policy_type": form_data.get("policy_type"),
        "interval_days": int(form_data.get("interval_days")) if form_data.get("interval_days") else None,
        "deadline_date": date.fromisoformat(form_data.get("deadline_date")) if form_data.get("deadline_date") else date.fromisoformat(form_data.get("state_based_deadline_date")) if form_data.get("state_based_deadline_date") else None,
        "total_occurrences": int(form_data.get("total_occurrences")) if form_data.get("total_occurrences") else None,
        "freeze_on_miss": bool(form_data.get("freeze_on_miss")),
        "account_ids": [int(id) for id in account_ids] if form_data.get("goal_scope") == "accounts" else None,
        "task_distribution_strategy": form_data.get("task_distribution_strategy"),
        "catchup_strategy": form_data.get("catchup_strategy"),
        "execution_strategy_type": form_data.get("execution_strategy"),
        "execution_script_content": form_data.get("execution_script_content"),
        "execution_script_env_vars": env_vars
    }

    use_case = CreateGoalUseCase(get_goal_repo(db))
    use_case.execute(goal_data)

    return RedirectResponse(url="/all-tasks", status_code=303)


@router.get("/goals/{goal_id}/edit", response_class=HTMLResponse)
def get_edit_goal_form(req: Request, goal_id: int, db: Session = Depends(get_db)):
    """Displays the form to edit an existing goal, pre-filled with its data."""
    goal_repo = get_goal_repo(db)
    platform_repo = get_platform_repo(db)

    goal = GetGoalUseCase(goal_repo).execute(goal_id=goal_id)
    if not goal:
        return HTMLResponse("Goal not found", status_code=404)

    # We need the same platform/account data as the 'add' page
    from infrastructure.repositories import SQLAlchemyAccountRepository
    acc_repo = SQLAlchemyAccountRepository(db)
    platforms_with_accounts = []
    platforms = ListPlatformsUseCase(platform_repo).execute()
    for p in platforms:
        accounts = acc_repo.list_by_platform(p.id)
        platforms_with_accounts.append({
            "id": p.id, "name": p.name,
            "accounts": [{"id": a.id, "username": a.username} for a in accounts]
        })

    return templates.TemplateResponse(
        "edit_goal.html",
        {
            "request": req,
            "goal": goal,
            "platforms_json": json.dumps(platforms_with_accounts),
            "page_title": "Edit Goal"
        }
    )

@router.post("/goals/{goal_id}/edit")
async def handle_edit_goal(req: Request, goal_id: int, db: Session = Depends(get_db)):
    """Handles the submission of the goal edit form."""
    form_data = await req.form()
    account_ids = form_data.getlist("account_ids")


    goal_data = {
        "platform_id": int(form_data.get("platform_id")),
        "description": form_data.get("description"),
        "start_date": date.fromisoformat(form_data.get("start_date")),
        "policy_type": form_data.get("policy_type"),
        "interval_days": int(form_data.get("interval_days")) if form_data.get("interval_days") else None,
        "deadline_date": date.fromisoformat(form_data.get("deadline_date")) if form_data.get("deadline_date") else None,
        "total_occurrences": int(form_data.get("total_occurrences")) if form_data.get("total_occurrences") else None,
        "freeze_on_miss": bool(form_data.get("freeze_on_miss")),
        "account_ids": [int(id) for id in account_ids] if form_data.get("goal_scope") == "accounts" else None,
        "task_distribution_strategy": form_data.get("task_distribution_strategy"),
        "catchup_strategy": form_data.get("catchup_strategy"),
        "execution_strategy_type": form_data.get("execution_strategy"),
        "execution_script_content": form_data.get("execution_script_content"),
        "execution_script_env_vars": parse_env_vars(form_data, "execution_script_env_vars"),
        "check_strategy_type": form_data.get("check_strategy"),
        "check_script_content": form_data.get("check_script_content"),
        "check_script_env_vars": parse_env_vars(form_data, "check_script_env_vars"),
    }

    use_case = UpdateGoalUseCase(get_goal_repo(db))
    use_case.execute(goal_id=goal_id, data=goal_data)

    return RedirectResponse(url="/goals", status_code=303)


@router.post("/goals/{goal_id}/delete")
def handle_delete_goal(goal_id: int, db: Session = Depends(get_db)):
    """Handles the deletion of a goal."""
    use_case = DeleteGoalUseCase(get_goal_repo(db))
    use_case.execute(goal_id=goal_id)
    return RedirectResponse(url="/goals", status_code=303)
