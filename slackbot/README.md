# Slackタスク管理Bot

Slack Events APIを使用したタスク管理Bot（MVP版）

## 機能

- `:task:` リアクションでタスク作成
- `:done:` リアクションでタスク完了
- LLMによるスレッド解析（担当者・期日抽出）
- リマインド送信（期日前日・週次）
- 2.5ヶ月後のエスカレーション

## セットアップ

### 1. 環境変数の設定

`env.example`を参考に`.env`ファイルを作成してください。

```bash
cp env.example .env
# .envファイルを編集
```

### 2. Docker Composeで起動

```bash
docker-compose up -d
```

### 3. データベース初期化

データベースは自動的に初期化されます（`scripts/init_db.sql`が実行されます）。

### 4. Slack Events API設定

Slack Appの設定で、Events APIのエンドポイントを以下に設定してください：

```
http://your-server:8000/slack/events
```

必要なイベント：
- `reaction_added`
- `reaction_removed`（将来用）
- `message`

## アーキテクチャ

- **FastAPI**: Slack Events API受信
- **Celery Worker**: 非同期ジョブ処理
- **Celery Beat**: 定期スケジューラー（1分ごと）
- **PostgreSQL**: タスク状態管理
- **Redis**: Celeryブローカー
- **OpenAI API**: スレッド解析

## 開発

### 依存関係のインストール

```bash
uv sync
```

### ローカル実行

```bash
# データベースとRedisを起動
docker-compose up -d db redis

# アプリケーション起動
uvicorn main:app --reload

# Celery Worker起動（別ターミナル）
celery -A app.celery_app worker --loglevel=info

# Celery Beat起動（別ターミナル）
celery -A app.celery_app beat --loglevel=info
```

## 注意事項（MVP版）

- event_idデデュープなし（重複実行が発生する可能性あり）
- 重複投稿は運用で対応
- エラーハンドリングは最小限
