"""Job A: CreateTaskFromReaction"""
import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.celery_app import celery_app
from app.core.db import SessionLocal
from app.core.slack import slack_client
from app.core.config import settings
from app.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="app.jobs.create_task.create_task_from_reaction")
def create_task_from_reaction(
    source_channel_id: str,
    source_message_ts: str,
    reactor_user_id: str,
):
    """タスク作成ジョブ"""
    db: Session = SessionLocal()
    try:
        # 1. 元メッセージのpermalinkを取得
        permalink_response = slack_client.chat_getPermalink(
            channel=source_channel_id,
            message_ts=source_message_ts,
        )
        if not permalink_response["ok"]:
            logger.error(f"Failed to get permalink: {permalink_response}")
            return
        
        source_permalink = permalink_response["permalink"]
        
        # 2. 元メッセージのリアクション情報を取得（reactors一覧）
        reactions_response = slack_client.reactions_get(
            channel=source_channel_id,
            timestamp=source_message_ts,
        )
        reactors: List[str] = []
        if reactions_response.get("ok") and reactions_response.get("message", {}).get("reactions"):
            for reaction in reactions_response["message"]["reactions"]:
                if reaction["name"] == "task":
                    reactors = reaction.get("users", [])
                    break
        
        # reactor_user_idがreactorsに含まれていない場合は追加
        if reactor_user_id and reactor_user_id not in reactors:
            reactors.append(reactor_user_id)
        
        # 3. tasksテーブルにupsert
        task = db.query(Task).filter(
            Task.source_channel_id == source_channel_id,
            Task.source_message_ts == source_message_ts,
        ).first()
        
        if task:
            # 既存タスクのreactorsを更新
            if reactors:
                existing_reactors = task.reactors or []
                task.reactors = list(set(existing_reactors + reactors))
                db.commit()
        else:
            # 新規タスク作成
            task = Task(
                source_channel_id=source_channel_id,
                source_message_ts=source_message_ts,
                source_permalink=source_permalink,
                task_channel_id=settings.SLACK_TASK_CHANNEL_ID,
                reactors=reactors,
                status=TaskStatus.OPEN,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
        
        # 4. Taskチャンネルに新規投稿（permalinkのみ）
        post_response = slack_client.chat_postMessage(
            channel=settings.SLACK_TASK_CHANNEL_ID,
            text=source_permalink,
        )
        
        if not post_response["ok"]:
            logger.error(f"Failed to post message: {post_response}")
            return
        
        task_message_ts = post_response["ts"]
        
        # 5. task_message_tsをDBへ保存
        task.task_message_ts = task_message_ts
        db.commit()
        
        # 6. BotがTask投稿に:done:リアクションを付与
        slack_client.reactions_add(
            channel=settings.SLACK_TASK_CHANNEL_ID,
            timestamp=task_message_ts,
            name="done",
        )
        
        # 7. 元メッセージのスレッドへ返信
        # メンションは最大3名＋他N人
        mention_text = ""
        if reactors:
            mention_users = reactors[:3]
            mention_text = " ".join([f"<@{user_id}>" for user_id in mention_users])
            if len(reactors) > 3:
                mention_text += f" 他{len(reactors) - 3}人"
        
        task_permalink_response = slack_client.chat_getPermalink(
            channel=settings.SLACK_TASK_CHANNEL_ID,
            message_ts=task_message_ts,
        )
        task_permalink = task_permalink_response.get("permalink", "")
        
        reply_text = f"{mention_text}\nTaskチャンネルにタスクを作成しました: {task_permalink}"
        
        slack_client.chat_postMessage(
            channel=source_channel_id,
            thread_ts=source_message_ts,
            text=reply_text,
        )
        
        # 8. スレッド解析ジョブをenqueue
        from app.jobs.reanalyze_thread import reanalyze_thread
        reanalyze_thread.delay(task_id=task.id)
        
        logger.info(f"Created task {task.id} from reaction")
        
    except Exception as e:
        logger.error(f"Error in create_task_from_reaction: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
