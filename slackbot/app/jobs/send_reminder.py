"""Job D: SendReminder"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.celery_app import celery_app
from app.core.db import SessionLocal
from app.core.slack import slack_client
from app.models.task import Task, TaskStatus, RemindKind
import pytz

logger = logging.getLogger(__name__)
jst = pytz.timezone("Asia/Tokyo")


@celery_app.task(name="app.jobs.send_reminder.send_reminder")
def send_reminder(task_id: int, kind: str):
    """リマインド送信ジョブ"""
    db: Session = SessionLocal()
    try:
        # 1. statusがopenか確認
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return
        
        if task.status != TaskStatus.OPEN:
            logger.info(f"Task {task_id} is not open, skipping reminder")
            return
        
        # 2. 宛先（メンション対象）を決定
        mention_users = []
        if task.assignee_user_id:
            mention_users = [task.assignee_user_id]
        elif task.reactors:
            mention_users = task.reactors[:3]  # 最大3名
        
        mention_text = " ".join([f"<@{user_id}>" for user_id in mention_users])
        if task.reactors and len(task.reactors) > 3 and not task.assignee_user_id:
            mention_text += f" 他{len(task.reactors) - 3}人"
        
        # 3. Taskチャンネルのタスク投稿スレッドへ投稿
        if kind == "due_minus_1":
            message_text = f"{mention_text}\n期日前日リマインド: このタスクの期日は明日です。{task.source_permalink}"
        elif kind == "weekly":
            message_text = f"{mention_text}\n週次リマインド: このタスクの進捗はいかがですか？{task.source_permalink}"
        else:
            message_text = f"{mention_text}\nリマインド: {task.source_permalink}"
        
        slack_client.chat_postMessage(
            channel=task.task_channel_id,
            thread_ts=task.task_message_ts,
            text=message_text,
        )
        
        # 4. next_remind_at を次に進める
        if kind == "due_minus_1":
            # due_minus_1は送ったら停止
            task.next_remind_at = None
            task.remind_kind = None
        elif kind == "weekly":
            # weeklyは+7日
            if task.next_remind_at:
                task.next_remind_at = task.next_remind_at + timedelta(days=7)
            else:
                # 次回がない場合は現在時刻から+7日
                now = datetime.now(jst)
                task.next_remind_at = now + timedelta(days=7)
        
        db.commit()
        
        logger.info(f"Sent reminder for task {task_id} (kind: {kind})")
        
    except Exception as e:
        logger.error(f"Error in send_reminder: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
