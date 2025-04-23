FROM python:3.12-slim

WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements-prod.txt ./requirements.txt

# 依存関係のインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 環境変数の設定（ハードコード）
ENV PORT=8080

# サーバー起動コマンド
CMD uvicorn app.main:app --host 0.0.0.0 --port 8080
