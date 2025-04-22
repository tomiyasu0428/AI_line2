import os
from fastapi import APIRouter, Request, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

from app.services.database import save_user_tokens, get_user_tokens

router = APIRouter(prefix="/google", tags=["google"])

CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [f"{os.getenv('APP_BASE_URL')}/google/oauth2callback"]
    }
}

SCOPES = ["https://www.googleapis.com/auth/calendar"]

@router.get("/authorize")
async def authorize(user_id: str):
    flow = Flow.from_client_config(
        client_config=CLIENT_CONFIG,
        scopes=SCOPES
    )
    flow.redirect_uri = f"{os.getenv('APP_BASE_URL')}/google/oauth2callback"
    
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # 毎回同意画面を表示し、リフレッシュトークンを確実に取得
        state=user_id
    )
    
    return RedirectResponse(authorization_url)

@router.get("/oauth2callback")
async def oauth2callback(request: Request):
    query_params = dict(request.query_params)
    code = query_params.get("code")
    state = query_params.get("state")  # stateにはuser_idが含まれている
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Invalid request")
    
    flow = Flow.from_client_config(
        client_config=CLIENT_CONFIG,
        scopes=SCOPES
    )
    flow.redirect_uri = f"{os.getenv('APP_BASE_URL')}/google/oauth2callback"
    
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    # デバッグ情報を出力
    print(f"OAuth2コールバック - ユーザーID: {state}")
    print(f"取得したトークン情報:")
    print(f"  - アクセストークン: {credentials.token[:10]}...")
    print(f"  - リフレッシュトークン: {credentials.refresh_token[:10] if credentials.refresh_token else 'なし'}")
    print(f"  - トークンURI: {credentials.token_uri}")
    print(f"  - スコープ: {credentials.scopes}")
    
    user_id = state
    token_info = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }
    save_user_tokens(user_id, token_info)
    
    # HTMLレスポンスを返す（LINEに戻るための指示を含む）
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>認証完了</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                line-height: 1.6;
                text-align: center;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #4CAF50;
            }
            .button {
                display: inline-block;
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                margin: 20px 0;
                border-radius: 5px;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>認証が完了しました</h1>
            <p>Googleカレンダーへのアクセス許可が正常に設定されました。</p>
            <p>LINEアプリに戻って、カレンダー機能を使用してください。</p>
            <p>例えば、「今日の予定を教えて」や「明日の午後3時から会議を設定して」などと入力できます。</p>
        </div>
    </body>
    </html>
    """
    return Response(content=html_content, media_type="text/html")
