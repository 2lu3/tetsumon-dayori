"""Celery Beat スケジューラータスク"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.task import Task, TaskStatus
import pytz

logger = logging.getLogger(__name__)
jst = pytz.timezone("Asia/Tokyo")


@celery_app.task(name="app.jobs.scheduler.scan_reminders")
def scan_reminders():
    """リマインド対象タスクをスキャンしてジョブをenqueue"""
    db: Session = SessionLocal()
    try:
        now = datetime.now(jst)
        
        # next_remind_at <= now のタスクを取得
        tasks = db.query(Task).filter(
            Task.status == TaskStatus.OPEN,
            Task.next_remind_at <= now,
            Task.next_remind_at.isnot(None),
        ).all()
        
        for task in tasks:
            if task.remind_kind:
                from app.jobs.send_reminder import send_reminder
                send_reminder.delay(task_id=task.id, kind=task.remind_kind.value)
                logger.info(f"Enqueued reminder for task {task.id} (kind: {task.remind_kind.value})")
        
        logger.info(f"Scanned reminders: found {len(tasks)} tasks")
        
    except Exception as e:
        logger.error(f"Error in scan_reminders: {e}", exc_info=True)
    finally:
        db.close()


@celery_app.task(name="app.jobs.scheduler.scan_escalations")
def scan_escalations():
    """エスカレーション対象タスクをスキャンしてジョブをenqueue"""
    db: Session = SessionLocal()
    try:
        now = datetime.now(jst)
        
        # escalate_at <= now のタスクを取得
        tasks = db.query(Task).filter(
            Task.status == TaskStatus.OPEN,
            Task.escalate_at <= now,
            Task.escalate_at.isnot(None),
        ).all()
        
        for task in tasks:
            from app.jobs.escalate import escalate_after_2_5_months
            escalate_after_2_5_months.delay(task_id=task.id)
            logger.info(f"Enqueued escalation for task {task.id}")
        
        logger.info(f"Scanned escalations: found {len(tasks)} tasks")
        
    except Exception as e:
        logger.error(f"Error in scan_escalations: {e}", exc_info=True)
    finally:
        db.close()
