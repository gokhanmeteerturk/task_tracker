import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler

from infrastructure.database import engine, get_db
from infrastructure.orm import Base
from infrastructure.repositories import (
    SQLAlchemyGoalRepository,
    SQLAlchemyTaskRepository,
    SQLAlchemyAccountRepository,
)
from application.usecases import GenerateDueTasksUseCase
from ui.routers import platforms, goals, tasks, dashboard

# I'm using alembic now so skipping this:
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Tracker")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(platforms.router, tags=["Platforms & Accounts"])
app.include_router(goals.router, tags=["Goals"])
app.include_router(tasks.router, tags=["Tasks"])

def run_daily_task_generation():
    """Job function for the scheduler."""
    print(f"Scheduler running at {__import__('datetime').datetime.now()}: Generating due tasks...")
    db_session = next(get_db())
    try:
        task_repo = SQLAlchemyTaskRepository(db_session)
        goal_repo = SQLAlchemyGoalRepository(db_session)
        account_repo = SQLAlchemyAccountRepository(db_session)

        use_case = GenerateDueTasksUseCase(goal_repo, task_repo, account_repo)
        use_case.execute()
        print("Scheduler finished.")
    finally:
        db_session.close()

scheduler = BackgroundScheduler()

# every day at 2:00 AM
scheduler.add_job(run_daily_task_generation, "cron", hour=2, minute=0)
scheduler.start()

if __name__ == "__main__":
    print("Running initial task generation on startup...")
    run_daily_task_generation()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)