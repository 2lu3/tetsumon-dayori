"""Celeryアプリ初期化"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
import pytz

# Celeryアプリ作成
celery_app = Celery(
    "slackbot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# 設定
celery_app.conf.update(
    timezone=pytz.timezone(settings.TIMEZONE),
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=300,  # 5分
    task_soft_time_limit=240,  # 4分
)

# Beatスケジュール設定
celery_app.conf.beat_schedule = {
    "scan-reminders": {
        "task": "app.jobs.scheduler.scan_reminders",
        "schedule": crontab(minute="*"),  # 毎分
    },
    "scan-escalations": {
        "task": "app.jobs.scheduler.scan_escalations",
        "schedule": crontab(minute="*"),  # 毎分
    },
}
