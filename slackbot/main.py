"""FastAPIアプリケーション"""
import logging
from fastapi import FastAPI
from app.api.slack_events import router as slack_events_router
from app.core.config import settings

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Slack Task Management Bot")

# ルーター登録
app.include_router(slack_events_router, prefix="", tags=["slack"])


@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
