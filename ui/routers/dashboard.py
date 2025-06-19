import subprocess
import threading
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from application.usecases import (
    GetDashboardDataUseCase,
    ListTasksUseCase,
)
from ..dependencies import (
    get_db,
    get_account_repo,
    get_task_repo,
    get_goal_repo,
    get_platform_repo,
)
from settings import SERVICES

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse, tags=["Dashboard"])
def home(request: Request, db: Session = Depends(get_db)):
    use_case = GetDashboardDataUseCase(get_account_repo(db))
    platforms_data = use_case.execute()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "platforms": platforms_data,
            "page_title": "Dashboard",
            "services": SERVICES,
        },
    )


@router.post("/services/{service_name}/start", response_class=JSONResponse)
def start_service(service_name: str):
    service = SERVICES.get(service_name)
    if not service:
        return JSONResponse({"error": "Service not found"}, status_code=404)

    def run_bat():
        subprocess.Popen(
            ["cmd.exe", "/c", service["start_cmd"]],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=service.get("cwd"),
        )

    threading.Thread(target=run_bat, daemon=True).start()
    return {"status": "started"}


@router.get("/all-tasks", response_class=HTMLResponse)
def get_all_tasks(req: Request, db: Session = Depends(get_db)):
    tasks = ListTasksUseCase(get_task_repo(db)).execute()
    goal_repo = get_goal_repo(db)

    for task in tasks:
        if hasattr(task, "goal_id"):
            goal = goal_repo.get_by_id(task.goal_id)

            if goal is not None:
                platform_repo = get_platform_repo(db)
                goal.platform = platform_repo.get_by_id(goal.platform_id)
            task.goal = goal
    return templates.TemplateResponse(
        "all_tasks.html", {"request": req, "tasks": tasks, "page_title": "All Tasks"}
    )
