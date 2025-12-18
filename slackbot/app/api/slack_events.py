"""Slack Events API エンドポイント"""
import logging
from fastapi import APIRouter, Request, Response, HTTPException
from slack_bolt.verification import RequestVerifier
from app.core.config import settings
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()

# slack-boltのRequestVerifierで署名検証
request_verifier = RequestVerifier(signing_secret=settings.SLACK_SIGNING_SECRET)


@router.post("/slack/events")
async def slack_events(request: Request):
    """Slack Events API エンドポイント（slack-boltの署名検証を使用）"""
    body = await request.body()
    headers = dict(request.headers)
    
    # slack-boltのRequestVerifierで署名検証
    if not request_verifier.is_valid(
        body=body,
        timestamp=headers.get("X-Slack-Request-Timestamp", ""),
        signature=headers.get("X-Slack-Signature", ""),
    ):
        logger.warning("Invalid signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # リクエストをパースしてイベントを取得
    import json
    data = json.loads(body.decode())
    
    # URL verification
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
    
    # イベント処理
    event = data.get("event", {})
    event_type = event.get("type")
    
    # 3秒以内にACKを返すため、処理は非同期で実行
    if event_type == "reaction_added":
        reaction = event.get("reaction")
        if reaction == "task":
            # CreateTaskFromReaction ジョブを enqueue
            celery_app.send_task(
                "app.jobs.create_task.create_task_from_reaction",
                kwargs={
                    "source_channel_id": event.get("item", {}).get("channel"),
                    "source_message_ts": event.get("item", {}).get("ts"),
                    "reactor_user_id": event.get("user"),
                },
            )
            logger.info(f"Enqueued create_task_from_reaction for {event.get('item', {}).get('ts')}")
        elif reaction == "done":
            # MarkDoneFromReaction ジョブを enqueue
            celery_app.send_task(
                "app.jobs.mark_done.mark_done_from_reaction",
                kwargs={
                    "task_channel_id": event.get("item", {}).get("channel"),
                    "task_message_ts": event.get("item", {}).get("ts"),
                    "actor_user_id": event.get("user"),
                },
            )
            logger.info(f"Enqueued mark_done_from_reaction for {event.get('item', {}).get('ts')}")
    
    elif event_type == "message":
        # Taskチャンネルのスレッド投稿をチェック
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts")
        
        if channel_id == settings.SLACK_TASK_CHANNEL_ID and thread_ts:
            # ReanalyzeThread ジョブを enqueue
            celery_app.send_task(
                "app.jobs.reanalyze_thread.reanalyze_thread",
                kwargs={
                    "task_message_ts": thread_ts,
                },
            )
            logger.info(f"Enqueued reanalyze_thread for {thread_ts}")
    
    # 3秒以内にACKを返す
    return Response(status_code=200)
