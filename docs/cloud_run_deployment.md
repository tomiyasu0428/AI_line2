# Google Cloud Runへのデプロイ手順と問題解決

## 1. 準備作業

### 1.1 必要なツールとアカウント
- Google Cloud SDK
- Docker
- Google Cloudアカウント（課金設定済み）

### 1.2 環境設定
- プロジェクト設定: `line-manageai`
- リージョン: `asia-northeast1`
- 必要なAPIの有効化:
  ```bash
  gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
  ```

## 2. Dockerイメージの準備

### 2.1 Dockerfileの作成
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements-prod.txt ./requirements.txt

# 依存関係のインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 環境変数の設定
ENV PORT=8080

# サーバー起動コマンド
CMD uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### 2.2 依存関係の問題解決
- 依存関係の競合が発生した場合、バージョン指定を緩和する
- 特に`google-generativeai`と`langchain-google-genai`の互換性に注意
- 解決策: 厳密なバージョン指定を避け、最小バージョン指定（>=）を使用

### 2.3 .dockerignoreファイルの作成
```
.venv
__pycache__
*.pyc
.git
.gitignore
.env
.env.example
*.json
README.md
*.db
.pytest_cache
.coverage
htmlcov/
```

## 3. Google Cloud設定

### 3.1 Artifact Registryリポジトリの作成
```bash
gcloud artifacts repositories create line-bot-repo --repository-format=docker --location=asia-northeast1 --description="LINE Bot用リポジトリ"
```

### 3.2 IAM権限の設定
```bash
# ビルド権限
gcloud projects add-iam-policy-binding line-manageai --member=user:YOUR_EMAIL --role=roles/cloudbuild.builds.editor

# ストレージ権限
gcloud projects add-iam-policy-binding line-manageai --member=user:YOUR_EMAIL --role=roles/storage.admin
```

## 4. シークレット管理

### 4.1 Secret Managerの設定
```bash
# シークレットの作成
gcloud secrets create firebase-credentials --data-file=firebase-credentials.json

# サービスアカウントにアクセス権を付与
gcloud secrets add-iam-policy-binding firebase-credentials --member=serviceAccount:YOUR_SERVICE_ACCOUNT --role=roles/secretmanager.secretAccessor
```

## 5. デプロイ手順

### 5.1 Dockerイメージのビルドとプッシュ
```bash
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/line-manageai/line-bot-repo/line-bot:v1
```

### 5.2 Cloud Runへのデプロイ
```bash
gcloud run deploy line-bot-service \
  --image asia-northeast1-docker.pkg.dev/line-manageai/line-bot-repo/line-bot:v1 \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

### 5.3 環境変数とシークレットの設定
```bash
gcloud run services update line-bot-service \
  --platform managed \
  --region asia-northeast1 \
  --update-secrets=FIREBASE_CREDENTIALS=firebase-credentials:latest \
  --set-env-vars="DATABASE_TYPE=firebase,GEMINI_API_KEY=YOUR_KEY,LINE_CHANNEL_SECRET=YOUR_SECRET,LINE_CHANNEL_ACCESS_TOKEN=YOUR_TOKEN,APP_BASE_URL=YOUR_URL"
```

## 6. よくあるエラーと解決策

### 6.1 依存関係の競合
**エラー**: `ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/#dealing-with-dependency-conflicts`

**解決策**:
- バージョン指定を緩和する（`==`を`>=`に変更）
- 競合するパッケージのバージョンを調整する
- 依存関係を最小限に抑える

### 6.2 権限エラー
**エラー**: `PERMISSION_DENIED: The caller does not have permission`

**解決策**:
- 必要なIAMロールを付与する
- サービスアカウントの権限を確認する
- プロジェクトの課金設定を確認する

### 6.3 Webhook 404エラー
**エラー**: `The webhook returned an HTTP status code other than 200.(404 Not Found)`

**解決策**:
- ルーターのエンドポイント（`@router.post("/webhook")`）とLINE Developersコンソールの設定が一致しているか確認
- Cloud Runのログを確認して、リクエストが到達しているか確認
- アプリケーションが正しく起動しているか確認

## 7. 更新とメンテナンス

### 7.1 コードの更新
```bash
# 新しいバージョンのイメージをビルド
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/line-manageai/line-bot-repo/line-bot:v2

# Cloud Runサービスを更新
gcloud run services update line-bot-service --image asia-northeast1-docker.pkg.dev/line-manageai/line-bot-repo/line-bot:v2 --platform managed --region asia-northeast1
```

### 7.2 環境変数の更新
```bash
gcloud run services update line-bot-service --platform managed --region asia-northeast1 --set-env-vars="KEY=VALUE"
```

### 7.3 シークレットの更新
```bash
# シークレットの更新
gcloud secrets versions add firebase-credentials --data-file=new-credentials.json
```

## 8. モニタリングとデバッグ

### 8.1 ログの確認
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=line-bot-service" --limit 20
```

### 8.2 サービスの状態確認
```bash
gcloud run services describe line-bot-service --platform managed --region asia-northeast1
```
