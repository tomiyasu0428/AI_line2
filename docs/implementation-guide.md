# エージェントベースのカレンダー管理システム実装ガイド

## 実装ステップ

以下のステップに従って、現在のシステムをエージェントベースのアプローチに移行します。

### 1. 必要なパッケージのインストール

```bash
pip install langchain langchain-core langchain-google-genai langgraph
```

### 2. ディレクトリ構造の更新

```
app/
├── services/
│   ├── ai_processor.py        # エージェントベースの実装に更新
│   ├── calendar_tools.py      # カレンダー操作ツールを定義（新規作成）
│   ├── google_calendar.py     # 既存のGoogle Calendar操作関数
│   └── database.py            # 既存のデータベース操作
└── routers/
    ├── line.py                # LINE Webhook処理
    └── google_auth.py         # Google認証処理
```

### 3. カレンダーツールの実装 (calendar_tools.py)

```python
import datetime
from typing import Dict, List, Optional, Any

from langchain_core.tools import tool
from app.services.google_calendar import (
    register_calendar_event,
    get_calendar_events,
    delete_calendar_event,
    update_calendar_event
)

@tool
def create_event_tool(user_id: str, start_time: str, end_time: str, title: str, location: str = "", description: str = "") -> str:
    """予定を新規作成するツール。必要な引数: user_id, start_time, end_time, title, location(任意), description(任意)"""
    event_id = register_calendar_event(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        title=title,
        location=location,
        description=description
    )
    return f"イベントID: {event_id}が作成されました。"

@tool
def get_events_tool(user_id: str, start_time: str, end_time: str) -> List[Dict[str, Any]]:
    """指定された期間の予定を取得するツール。必要な引数: user_id, start_time, end_time"""
    events = get_calendar_events(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time
    )
    
    if not events:
        return []
    
    # イベント情報を整形
    formatted_events = []
    for event in events:
        formatted_events.append({
            "id": event.get("id", ""),
            "summary": event.get("summary", "タイトルなし"),
            "start": event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "")),
            "end": event.get("end", {}).get("dateTime", event.get("end", {}).get("date", "")),
            "location": event.get("location", ""),
            "description": event.get("description", "")
        })
    
    return formatted_events

@tool
def update_event_tool(user_id: str, event_id: str, start_time: str = None, end_time: str = None, 
                     title: str = None, location: str = None, description: str = None) -> str:
    """既存の予定を更新するツール。必要な引数: user_id, event_id、その他更新したい項目"""
    result = update_calendar_event(
        user_id=user_id,
        event_id=event_id,
        start_time=start_time,
        end_time=end_time,
        title=title,
        location=location,
        description=description
    )
    return f"イベントID: {event_id}が更新されました。"

@tool
def delete_event_tool(user_id: str, event_id: str) -> str:
    """予定を削除するツール。必要な引数: user_id, event_id"""
    result = delete_calendar_event(
        user_id=user_id,
        event_id=event_id
    )
    return f"イベントID: {event_id}が削除されました。"

@tool
def search_events_by_title_tool(user_id: str, title_keyword: str, start_time: str = None, end_time: str = None) -> List[Dict[str, Any]]:
    """タイトルのキーワードで予定を検索するツール。必要な引数: user_id, title_keyword, start_time(任意), end_time(任意)"""
    # デフォルト値の設定
    if not start_time:
        start_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(
            hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    if not end_time:
        # 1週間後
        end_time = (datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))) + 
                   datetime.timedelta(days=7)).replace(
            hour=23, minute=59, second=59).isoformat()
    
    # イベントを取得
    events = get_calendar_events(user_id, start_time, end_time)
    
    # タイトルでフィルタリング
    filtered_events = []
    for event in events:
        if title_keyword.lower() in event.get("summary", "").lower():
            filtered_events.append({
                "id": event.get("id", ""),
                "summary": event.get("summary", "タイトルなし"),
                "start": event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "")),
                "end": event.get("end", {}).get("dateTime", event.get("end", {}).get("date", "")),
                "location": event.get("location", ""),
                "description": event.get("description", "")
            })
    
    return filtered_events

@tool
def get_current_datetime_tool() -> str:
    """現在の日本時間を取得するツール。引数は不要"""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()

@tool
def parse_date_tool(date_str: str) -> Dict[str, str]:
    """日付の文字列を解析して標準形式に変換するツール。必要な引数: date_str"""
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    
    # 「今日」「明日」などの相対的な日付を処理
    if "今日" in date_str:
        target_date = now
    elif "明日" in date_str:
        target_date = now + datetime.timedelta(days=1)
    elif "明後日" in date_str:
        target_date = now + datetime.timedelta(days=2)
    elif "昨日" in date_str:
        target_date = now - datetime.timedelta(days=1)
    elif "今週" in date_str:
        # 今週の月曜日から日曜日
        weekday = now.weekday()
        start_date = now - datetime.timedelta(days=weekday)
        end_date = start_date + datetime.timedelta(days=6)
        return {
            "start_date": start_date.replace(hour=0, minute=0, second=0).isoformat(),
            "end_date": end_date.replace(hour=23, minute=59, second=59).isoformat()
        }
    elif "来週" in date_str:
        # 来週の月曜日から日曜日
        weekday = now.weekday()
        start_date = now - datetime.timedelta(days=weekday) + datetime.timedelta(days=7)
        end_date = start_date + datetime.timedelta(days=6)
        return {
            "start_date": start_date.replace(hour=0, minute=0, second=0).isoformat(),
            "end_date": end_date.replace(hour=23, minute=59, second=59).isoformat()
        }
    else:
        # その他の日付形式の解析は必要に応じて実装
        return {"error": "日付の解析に失敗しました"}
    
    # 開始時刻と終了時刻を設定
    start_date = target_date.replace(hour=0, minute=0, second=0).isoformat()
    end_date = target_date.replace(hour=23, minute=59, second=59).isoformat()
    
    return {
        "start_date": start_date,
        "end_date": end_date
    }
```

### 4. エージェントベースのAIプロセッサの実装 (ai_processor.py)

```python
import os
import datetime
from typing import Dict, Any, List

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent

# Gemini API設定
gemini_api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_api_key)

# ツールのインポート
from app.services.calendar_tools import (
    create_event_tool,
    get_events_tool,
    update_event_tool,
    delete_event_tool,
    search_events_by_title_tool,
    get_current_datetime_tool,
    parse_date_tool
)

# ツールのリスト
tools = [
    create_event_tool,
    get_events_tool,
    update_event_tool,
    delete_event_tool,
    search_events_by_title_tool,
    get_current_datetime_tool,
    parse_date_tool
]

# プロンプトテンプレート
prompt = ChatPromptTemplate.from_messages([
    ("system", """あなたは日本語で会話するAIアシスタントで、ユーザーのGoogleカレンダーを管理します。
ユーザーからの要望に応じて、適切なツールを使用してカレンダーの予定を作成、取得、更新、削除してください。

以下のガイドラインに従ってください：
1. ユーザーの意図を正確に理解し、最適なツールを選択する
2. 必要な情報が不足している場合は、ユーザーに質問する
3. 日付や時間が曖昧な場合は、適切に解釈する
4. 処理結果を日本語で分かりやすく説明する

常に丁寧かつ親切な対応を心がけてください。"""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

# LLMの初期化
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

# エージェントの初期化
agent = create_react_agent(llm, tools, prompt)

# エージェントエグゼキューターの初期化
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)

def process_user_message(user_id: str, user_message: str) -> str:
    """エージェントを使用してユーザーのメッセージを処理し、適切な応答を返す"""
    try:
        # ユーザーIDをエージェントに渡す
        response = agent_executor.invoke({
            "input": user_message,
            "user_id": user_id
        })
        
        return response["output"]
    except Exception as e:
        print(f"Error in agent processing: {e}")
        return "申し訳ありません。メッセージ処理中にエラーが発生しました。後でもう一度お試しください。"
```

### 5. LangGraphを使用した代替実装 (ai_processor_langgraph.py)

LangChainは現在、LangGraphというより柔軟なフレームワークへの移行を推奨しています。以下はLangGraphを使用した実装例です：

```python
import os
import datetime
from typing import Dict, Any, List

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

# Gemini API設定
gemini_api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_api_key)

# ツールのインポート
from app.services.calendar_tools import (
    create_event_tool,
    get_events_tool,
    update_event_tool,
    delete_event_tool,
    search_events_by_title_tool,
    get_current_datetime_tool,
    parse_date_tool
)

# ツールのリスト
tools = [
    create_event_tool,
    get_events_tool,
    update_event_tool,
    delete_event_tool,
    search_events_by_title_tool,
    get_current_datetime_tool,
    parse_date_tool
]

# LLMの初期化
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

# LangGraphエージェントの作成
langgraph_agent = create_react_agent(llm, tools)

# ユーザーごとの会話履歴を保存する辞書
conversation_histories = {}

def process_user_message(user_id: str, user_message: str) -> str:
    """LangGraphエージェントを使用してユーザーのメッセージを処理し、適切な応答を返す"""
    try:
        # ユーザーの会話履歴を取得または初期化
        if user_id not in conversation_histories:
            conversation_histories[user_id] = []
        
        # システムメッセージを追加（初回のみ）
        if not conversation_histories[user_id]:
            conversation_histories[user_id].append(
                ("system", """あなたは日本語で会話するAIアシスタントで、ユーザーのGoogleカレンダーを管理します。
ユーザーからの要望に応じて、適切なツールを使用してカレンダーの予定を作成、取得、更新、削除してください。

以下のガイドラインに従ってください：
1. ユーザーの意図を正確に理解し、最適なツールを選択する
2. 必要な情報が不足している場合は、ユーザーに質問する
3. 日付や時間が曖昧な場合は、適切に解釈する
4. 処理結果を日本語で分かりやすく説明する

常に丁寧かつ親切な対応を心がけてください。""")
            )
        
        # ユーザーメッセージを追加
        conversation_histories[user_id].append(("human", user_message))
        
        # エージェントを実行
        config = {"configurable": {"user_id": user_id}}
        result = langgraph_agent.invoke(
            {"messages": conversation_histories[user_id]},
            config=config
        )
        
        # 応答を会話履歴に追加
        conversation_histories[user_id] = result["messages"]
        
        # 最後のメッセージ（AIの応答）を返す
        return result["messages"][-1][1]
    except Exception as e:
        print(f"Error in LangGraph agent processing: {e}")
        return "申し訳ありません。メッセージ処理中にエラーが発生しました。後でもう一度お試しください。"
```

### 6. LINE Webhookの非同期処理の実装 (line.py)

LINE Webhookのタイムアウト問題を解決するために、非同期処理を実装します：

```python
from fastapi import APIRouter, Request, BackgroundTasks
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage
)

# 既存のコードは省略...

@router.post("/callback")
async def callback(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()
    body_decode = body.decode('utf-8')
    
    try:
        handler.handle(body_decode, signature)
    except InvalidSignatureError:
        return {"error": "Invalid signature"}
    
    return {"message": "OK"}

async def process_message_async(event):
    user_id = event.source.user_id
    user_message = event.message.text
    
    # ユーザーの認証状態を確認
    is_authenticated = db.is_user_authenticated(user_id)
    
    if not is_authenticated and any(keyword in user_message for keyword in ["カレンダー", "予定", "会議", "ミーティング", "スケジュール"]):
        auth_url = f"{os.getenv('APP_BASE_URL')}/google/authorize?user_id={user_id}"
        reply_text = f"Googleカレンダーへのアクセス許可が必要です。以下のリンクから認証を行ってください。\n{auth_url}"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    elif is_authenticated:
        # AIプロセッサを使用してメッセージを処理
        response = process_user_message(user_id, user_message)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response)
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="こんにちは！カレンダーの予定を管理するには、「予定」「スケジュール」などのキーワードを含むメッセージを送ってください。")
        )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # バックグラウンドタスクとしてメッセージ処理を実行
    background_tasks = BackgroundTasks()
    background_tasks.add_task(process_message_async, event)
    
    # 即座に200 OKを返す
    return
```

## 実装上の注意点

### 1. エラーハンドリング

エージェントの実行中に発生する可能性のあるエラーを適切に処理するために、try-except文を使用しています。エラーが発生した場合は、ユーザーに分かりやすいエラーメッセージを返します。

### 2. 非同期処理

LINE Webhookは3秒以内の応答を期待するため、FastAPIのBackgroundTasksを使用して非同期処理を実装しています。これにより、Webhookへの応答を即座に返しつつ、バックグラウンドでメッセージ処理を行うことができます。

### 3. 日付と時間の処理

日本語の日付表現（「今日」「明日」など）を適切に処理するために、parse_date_toolを実装しています。これにより、ユーザーが自然な言葉で日付を指定できるようになります。

## テスト方法

1. サーバーを起動
   ```
   python run.py
   ```

2. ngrokを使用してローカルサーバーを公開
   ```
   ngrok http 8080
   ```

3. LINE DevelopersコンソールでWebhook URLを更新

4. LINEアプリからボットにメッセージを送信して動作確認

## デプロイ手順

1. 本番環境用の.envファイルを作成

2. サーバーにコードをデプロイ

3. LINE DevelopersコンソールとGoogle Cloud Consoleの設定を更新

4. サーバーを起動し、動作確認

## まとめ

エージェントベースのアプローチに移行することで、より柔軟で対話的なカレンダー管理システムを実現できます。ユーザーは自然な言葉でリクエストを行い、AIアシスタントが適切なツールを選択して処理を行うことで、ユーザーエクスペリエンスが大幅に向上します。LangChainの最新APIを活用することで、より堅牢で保守性の高いシステムを構築できます。
