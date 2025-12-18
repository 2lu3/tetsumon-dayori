FROM python:3.11-slim

WORKDIR /app

# uvをインストール
RUN pip install uv

# 依存関係をコピーしてインストール
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# アプリケーションコードをコピー
COPY . .

# uvでインストールしたパッケージを使用
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
