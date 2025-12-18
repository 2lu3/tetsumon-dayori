"""Slack API クライアント"""
from slack_bolt import App
from app.core.config import settings

# slack-boltのAppインスタンスを作成
slack_app = App(token=settings.SLACK_BOT_TOKEN)

# WebClientにアクセス（slack-boltのAppは内部でWebClientを持っている）
slack_client = slack_app.client
