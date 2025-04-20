AI予定管理秘書アプリ MVP実装手順
1. はじめに
このドキュメントは、「【改訂版】AI予定管理秘書アプリ構想（LINE連携）」ドキュメントで定義されたMVP（Minimum Viable Product）を実装するための具体的な手順を記述します。
MVPのスコープ:
個人予定の自然言語による登録・確認・変更・削除 (F-1)
Googleアカウント認証 (OAuth 2.0) (F-2)
グループ空き時間検索（基本ロジック）(F-3)
候補日提示と簡易投票機能 (LINE Flex Message等) (F-4)
投票結果に基づくカレンダー自動登録 (F-5)
2. 前提条件
LINE Developersアカウント
Google Cloud Platform (GCP) アカウント
Python開発環境 (Python 3.9以降推奨)
各種APIキー/認証情報
LINE Messaging API (Channel Access Token, Channel Secret)
Google Calendar API (有効化、OAuth 2.0 クライアントIDとシークレット)
Gemini API キー
3. 開発環境構築
プロジェクトフォルダ作成: 作業用フォルダを作成します。
仮想環境作成・有効化:
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows


必要ライブラリインストール:
pip install langchain google-generativeai google-api-python-client google-auth-httplib2 google-auth-oauthlib fastapi uvicorn[standard] python-dotenv line-bot-sdk firebase-admin # Firestore使う場合


.envファイル作成: APIキーやシークレットなどの機密情報を管理するために .env ファイルを作成し、gitignoreに追加します。
LINE_CHANNEL_ACCESS_TOKEN="..."
LINE_CHANNEL_SECRET="..."
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."
GOOGLE_PROJECT_ID="..." # GCPプロジェクトID
GEMINI_API_KEY="..."
DATABASE_URL="..." # Firestoreなど使う場合
SECRET_KEY="..." # FastAPIのセッション等で利用
APP_BASE_URL="..." # デプロイ先のURL (OAuthリダイレクト用)


4. LINE Bot 設定
LINE Developersコンソール:
プロバイダーを作成（または選択）。
Messaging APIチャネルを作成。
チャネル基本設定で Channel Access Token (long-lived) と Channel Secret を取得し、.env に設定。
Webhook URLを設定（一時的にngrok等、最終的にはデプロイ先のURL + /callback など）。
Webhookの利用をオンにする。
LINE公式アカウント機能の「応答メッセージ」をオフ、「Webhook」をオンにする。
5. Google Cloud / API 設定
GCPコンソール:
新規プロジェクトを作成（または既存プロジェクトを選択）。
APIとサービス > ライブラリ で Google Calendar API を検索し、有効にする。
APIとサービス > 認証情報 で以下を作成:
OAuth 同意画面:
User Typeを「外部」に設定。
アプリ名、ユーザーサポートメール、デベロッパー連絡先情報を入力。
スコープ: https://www.googleapis.com/auth/calendar (または必要最低限の calendar.events, calendar.readonly 等) を追加。
テストユーザーを追加（開発中は自分のGoogleアカウント）。
認証情報を作成 > OAuth クライアント ID:
アプリケーションの種類で「ウェブ アプリケーション」を選択。
名前を設定。
承認済みのリダイレクト URI に APP_BASE_URL + /oauth2callback などを追加。
作成後、クライアントID と クライアントシークレット を取得し、.env に設定。
(任意) Firestore設定: Firestoreを使用する場合、データベースを作成し、サービスアカウントキーを生成して安全な場所に保管（またはCloud Run等の環境変数として設定）。
6. 認証フロー実装 (OAuth 2.0 for Google)
FastAPIエンドポイント作成:
/authorize: ユーザーをGoogleの認証画面にリダイレクトさせるエンドポイント。user_id (LINE等) をstateパラメータに含めてCSRF対策。
/oauth2callback: Googleからのリダイレクトを受け取り、認証コードからアクセストークンとリフレッシュトークンを取得するエンドポイント。取得したトークンをユーザーIDに紐付けて Firestore やセキュアなDBに保存。
ライブラリ利用: google-auth-oauthlib を使用してフローを実装。
LINEでのトリガー: ユーザーが初めてカレンダー連携機能を使おうとした際や、認証が必要な場合に、/authorize へのリンクをLINEメッセージで送信。
7. バックエンド (Webhook) 実装 (FastAPI)
メインファイル作成 (main.py 等):
import os
from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv
# 他のインポート (LangChain, Google Calendar Clientなど)

load_dotenv()

app = FastAPI()

configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers['X-Line-Signature']
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text
    line_bot_api = MessagingApi(ApiClient(configuration))

    # --- ここからAI処理、カレンダー処理などを呼び出す ---
    # 1. ユーザー認証状態を確認
    # 2. テキストをLangChain/Geminiに渡して意図解釈・情報抽出
    # 3. 結果に応じてGoogle Calendar API呼び出し or 投票作成など
    # 4. 応答メッセージを生成して返信

    reply_text = f"Received: {text}" # 仮の応答

    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply_text)]
        )
    )

# --- OAuth用のエンドポイントなどもここに追加 ---
# /authorize
# /oauth2callback

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


環境変数読み込み: dotenv を使用。
LINE SDK初期化: line-bot-sdk (v3) を使用。
8. 自然言語処理 (AI) 実装 (LangChain + Gemini)
Geminiクライアント初期化: google-generativeai を使用。
LangChain設定:
LLMラッパー: ChatGoogleGenerativeAI を使用。
プロンプトテンプレート: ユーザーの指示（例: 「明日の10時に会議」）から、{action: "create", datetime_start: "...", datetime_end: "...", title: "...", location: "..."} のような構造化データを抽出するためのプロンプトを作成。予定確認、削除、変更用のプロンプトも用意。
出力パーサー: PydanticOutputParser や JsonOutputParser を使い、LLMの出力をPythonオブジェクトやJSONとして扱えるようにする。
Chain/Agent:
単純な抽出なら LLMChain。
複数のツール（カレンダー登録、確認、削除）を使い分ける必要があるため、Agent (create_react_agent や create_structured_chat_agent 等) の利用を推奨。Agentがユーザーの意図に応じて適切なツール（後述）を呼び出すように設計。
ツール定義:
@tool デコレータ等を使って、以下の機能を持つツールを定義。
register_calendar_event(start_time, end_time, title, description=None, location=None): Google Calendarに予定を登録するツール。
get_calendar_events(start_time, end_time): 指定期間の予定を取得するツール。
delete_calendar_event(event_id): 予定を削除するツール（event_idの特定方法も考慮）。
update_calendar_event(event_id, ...): 予定を変更するツール。
FastAPI連携: handle_message 内で、ユーザーテキストをAgentに渡し、実行結果を取得。
9. Google Calendar連携実装
Google APIクライアント: google-api-python-client を使用。
認証情報取得: ユーザーIDに紐づけてDB等に保存したリフレッシュトークンを使って、アクセストークンを再取得する処理を実装。
API呼び出し:
service = build('calendar', 'v3', credentials=credentials) でサービスオブジェクト作成。
service.events().insert(...), service.events().list(...), service.events().delete(...), service.events().update(...) 等を、LangChainのツール内から呼び出す。
11. テスト
単体テスト: 各関数、クラス（特にカレンダーAPI連携、自然言語処理部分）のテストを作成 (pytest 等)。
結合テスト: LINEからのWebhook受信 → AI処理 → カレンダー操作 → LINEへの応答、という一連の流れをテスト。
手動テスト: 実際にLINE Botを友だち追加し、様々な自然言語パターンで指示を送り、動作を確認。グループ機能もテスト。
12. デプロイ (簡易)
プラットフォーム選択: Google Cloud Run, Cloud Functions, Heroku, Render など。
Dockerfile作成 (Cloud Run等): アプリケーションをコンテナ化。
デプロイ: 各プラットフォームの手順に従いデプロイ。
Webhook URL更新: LINE Developersコンソールで、Webhook URLをデプロイしたアプリケーションのURLに更新。
環境変数設定: デプロイ環境に .env の内容を安全に設定（Secret Manager等推奨）。
13. 次のステップ
MVPの動作確認とフィードバック収集。
ロードマップ v1.1 以降の機能（音声入力、PDF読み取り、カスタムリマインド等）の開発に着手。
ログ監視、エラーハンドリングの強化。
パフォーマンスチューニング。
この手順はあくまで一例です。詳細な実装は、選択したライブラリや設計によって異なります。特にエラーハンドリング、セキュリティ対策、状態管理（どのユーザーがどの処理の途中かなど）は慎重に設計・実装する必要があります。
