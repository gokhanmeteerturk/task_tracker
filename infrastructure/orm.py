import json
from sqlalchemy import Column, Integer, String, Date, ForeignKey, JSON, Text, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Platform(Base):
    __tablename__ = "platforms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    config = Column(JSON, default=dict)
    goals = relationship("Goal", back_populates="platform")
    accounts = relationship("Account", back_populates="platform", cascade="all, delete-orphan")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    username = Column(String, nullable=False)
    notes = Column(Text)
    platform = relationship("Platform", back_populates="accounts")
    tasks = relationship("Task", back_populates="account")

class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String)
    platform_id = Column(Integer, ForeignKey("platforms.id"))
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    policy_json = Column(String)
    execution_strategy_json = Column(Text, default='{"type": "Manual"}')
    check_strategy_json = Column(Text, default='{"type": "Manual"}')
    catchup_strategy = Column(String, default="all", nullable=False)
    account_ids_json = Column(JSON)
    status = Column(String, default="Active", nullable=False)
    task_distribution_strategy = Column(String, default="all", nullable=False)
    platform = relationship("Platform", back_populates="goals")
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    due_date = Column(Date)
    status = Column(String)
    goal = relationship("Goal", back_populates="tasks")
    account = relationship("Account", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")

class TaskLog(Base):
    __tablename__ = "task_logs"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    from_status = Column(String)
    to_status = Column(String)
    notes = Column(Text, nullable=True)
    task = relationship("Task", back_populates="logs")
