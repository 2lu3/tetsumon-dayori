"""Job C: ReanalyzeThread"""
import logging
import json
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from openai import OpenAI
from app.celery_app import celery_app
from app.core.db import SessionLocal
from app.core.slack import slack_client
from app.core.config import settings
from app.models.task import Task, RemindKind
import pytz

logger = logging.getLogger(__name__)
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
jst = pytz.timezone(settings.TIMEZONE)


@celery_app.task(name="app.jobs.reanalyze_thread.reanalyze_thread")
def reanalyze_thread(task_id: Optional[int] = None, task_message_ts: Optional[str] = None):
    """スレッド解析ジョブ"""
    db: Session = SessionLocal()
    try:
        # タスク取得
        if task_id:
            task = db.query(Task).filter(Task.id == task_id).first()
        elif task_message_ts:
            task = db.query(Task).filter(Task.task_message_ts == task_message_ts).first()
        else:
            logger.error("Either task_id or task_message_ts must be provided")
            return
        
        if not task:
            logger.warning(f"Task not found: task_id={task_id}, task_message_ts={task_message_ts}")
            return
        
        # 1. Taskチャンネルの該当メッセージスレッドを取得
        replies_response = slack_client.conversations_replies(
            channel=task.task_channel_id,
            ts=task.task_message_ts,
        )
        
        if not replies_response.get("ok"):
            logger.error(f"Failed to get thread replies: {replies_response}")
            return
        
        messages = replies_response.get("messages", [])
        
        # 2. LLMへ投入（スレッド全文 + now(JST)）
        thread_text = "\n".join([
            f"[{msg.get('user', 'unknown')}] {msg.get('text', '')}"
            for msg in messages
        ])
        
        now_jst = datetime.now(jst).isoformat()
        
        prompt = f"""以下のSlackスレッドから、タスクの担当者と期日を抽出してください。
現在時刻（JST）: {now_jst}

スレッド内容:
{thread_text}

以下のJSON形式で回答してください。判明しない場合はnullを返してください。
{{
  "assignee": {{
    "user_id": "U123456" または null,
    "rationale": "理由（任意）"
  }},
  "due_date": {{
    "date": "2024-12-31" または null,
    "rationale": "理由（任意）"
  }}
}}"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたはSlackスレッドからタスク情報を抽出するアシスタントです。JSON形式で回答してください。"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # 3. JSON結果をtasksに保存
        assignee_info = result.get("assignee", {})
        due_date_info = result.get("due_date", {})
        
        task.assignee_user_id = assignee_info.get("user_id")
        
        due_date_str = due_date_info.get("date")
        if due_date_str:
            task.due_date = datetime.fromisoformat(due_date_str).date()
        else:
            task.due_date = None
        
        # 4. リマインド計画を再計算して保存
        now = datetime.now(jst)
        
        if task.due_date:
            # 期日あり：due_date前日 09:00 JST
            due_datetime = jst.localize(datetime.combine(task.due_date, datetime.min.time()))
            due_datetime = due_datetime.replace(hour=9, minute=0)
            remind_datetime = due_datetime - timedelta(days=1)
            
            if remind_datetime > now:
                task.next_remind_at = remind_datetime
                task.remind_kind = RemindKind.DUE_MINUS_1
            else:
                task.next_remind_at = None
                task.remind_kind = None
        else:
            # 期日なし：task_created_at起点で次の週次
            created_at_jst = task.created_at.astimezone(jst)
            # 次の週次（月曜09:00 JST）
            days_until_monday = (7 - created_at_jst.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            next_monday = created_at_jst + timedelta(days=days_until_monday)
            next_monday = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)
            
            if next_monday > now:
                task.next_remind_at = next_monday
                task.remind_kind = RemindKind.WEEKLY
            else:
                # 既に過ぎている場合は次の週次
                task.next_remind_at = next_monday + timedelta(days=7)
                task.remind_kind = RemindKind.WEEKLY
        
        # エスカレーション時刻（2.5ヶ月後）
        if task.created_at:
            escalate_datetime = task.created_at + timedelta(days=75)  # 約2.5ヶ月
            task.escalate_at = escalate_datetime
        
        db.commit()
        
        # 5. Botの「認識リアクション」を付与/更新（MVPでは単純付与のみ）
        # 既存のリアクションを確認してから追加（重複回避は簡易的）
        try:
            slack_client.reactions_add(
                channel=task.task_channel_id,
                timestamp=task.task_message_ts,
                name="white_check_mark",
            )
        except Exception as e:
            # 既にリアクションがある場合はエラーになる可能性があるが、無視
            logger.debug(f"Could not add reaction (may already exist): {e}")
        
        logger.info(f"Reanalyzed thread for task {task.id}")
        
    except Exception as e:
        logger.error(f"Error in reanalyze_thread: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
