from fastapi import Depends
from sqlalchemy.orm import Session
from infrastructure.database import get_db
from infrastructure.repositories import (
    SQLAlchemyPlatformRepository, SQLAlchemyAccountRepository,
    SQLAlchemyGoalRepository, SQLAlchemyTaskRepository, SQLAlchemyTaskLogRepository
)

def get_platform_repo(db: Session = Depends(get_db)):
    return SQLAlchemyPlatformRepository(db)

def get_account_repo(db: Session = Depends(get_db)):
    return SQLAlchemyAccountRepository(db)

def get_goal_repo(db: Session = Depends(get_db)):
    return SQLAlchemyGoalRepository(db)

def get_task_repo(db: Session = Depends(get_db)):
    return SQLAlchemyTaskRepository(db)

def get_task_log_repo(db: Session = Depends(get_db)):
    return SQLAlchemyTaskLogRepository(db)
