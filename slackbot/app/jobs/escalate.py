"""Job E: EscalateAfter2_5Months"""
import logging
from sqlalchemy.orm import Session
from app.celery_app import celery_app
from app.core.db import SessionLocal
from app.core.slack import slack_client
from app.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="app.jobs.escalate.escalate_after_2_5_months")
def escalate_after_2_5_months(task_id: int):
    """2.5ヶ月エスカレーションジョブ"""
    db: Session = SessionLocal()
    try:
        # 1. statusがopenか確認
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return
        
        if task.status != TaskStatus.OPEN:
            logger.info(f"Task {task_id} is not open, skipping escalation")
            return
        
        # 2. Taskチャンネルへ新規投稿
        message_text = f"このメッセージがもうすぐ見えなくなります: {task.source_permalink}"
        
        slack_client.chat_postMessage(
            channel=task.task_channel_id,
            text=message_text,
        )
        
        # 3. 元タスクを status=closed に更新
        task.status = TaskStatus.CLOSED
        
        # 4. next_remind_at/escalate_atを無効化
        task.next_remind_at = None
        task.escalate_at = None
        task.remind_kind = None
        
        db.commit()
        
        logger.info(f"Escalated task {task_id} after 2.5 months")
        
    except Exception as e:
        logger.error(f"Error in escalate_after_2_5_months: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
