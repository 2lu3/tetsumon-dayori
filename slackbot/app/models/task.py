"""Taskモデル"""
import enum
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Date, DateTime, Enum as SQLEnum, JSON, UniqueConstraint
from sqlalchemy.sql import func
from app.core.db import Base


class TaskStatus(str, enum.Enum):
    """タスクステータス"""
    OPEN = "open"
    DONE = "done"
    CLOSED = "closed"


class RemindKind(str, enum.Enum):
    """リマインド種別"""
    DUE_MINUS_1 = "due_minus_1"
    WEEKLY = "weekly"


class Task(Base):
    """タスクモデル"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # ソース情報
    source_channel_id = Column(String, nullable=False, index=True)
    source_message_ts = Column(String, nullable=False, index=True)
    source_permalink = Column(String, nullable=False)
    
    # Taskチャンネル情報
    task_channel_id = Column(String, nullable=False)
    task_message_ts = Column(String, nullable=True, index=True)
    
    # ステータス
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.OPEN, nullable=False, index=True)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # LLM抽出情報
    assignee_user_id = Column(String, nullable=True)
    due_date = Column(Date, nullable=True, index=True)
    
    # リマインド計画
    next_remind_at = Column(DateTime(timezone=True), nullable=True, index=True)
    remind_kind = Column(SQLEnum(RemindKind), nullable=True)
    escalate_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # 補助情報
    reactors = Column(JSON, nullable=True)  # user_id list
    
    __table_args__ = (
        UniqueConstraint('source_channel_id', 'source_message_ts', name='uq_source'),
    )
