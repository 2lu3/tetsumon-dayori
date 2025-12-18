"""Job B: MarkDoneFromReaction"""
import logging
from sqlalchemy.orm import Session
from app.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="app.jobs.mark_done.mark_done_from_reaction")
def mark_done_from_reaction(
    task_channel_id: str,
    task_message_ts: str,
    actor_user_id: str,
):
    """タスク完了ジョブ"""
    db: Session = SessionLocal()
    try:
        # 1. tasksを検索（task_message_ts一致）
        task = db.query(Task).filter(
            Task.task_message_ts == task_message_ts,
        ).first()
        
        if not task:
            logger.warning(f"Task not found for task_message_ts: {task_message_ts}")
            return
        
        # 2. status = done に更新
        task.status = TaskStatus.DONE
        
        # 3. next_remind_at / escalate_at を無効化
        task.next_remind_at = None
        task.escalate_at = None
        task.remind_kind = None
        
        db.commit()
        
        logger.info(f"Marked task {task.id} as done")
        
    except Exception as e:
        logger.error(f"Error in mark_done_from_reaction: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
