import os
import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

# .env ファイルをロード (必ず ChatGoogleGenerativeAI 初期化より前に！)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path=dotenv_path, verbose=True)

import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentType, initialize_agent

# Gemini API設定: APIキーを使用して認証
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]  # 環境変数を完全に削除

# 環境変数からAPIキーを取得
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY が見つかりません。GOOGLE_API_KEY を試します。")
    api_key = os.getenv("GOOGLE_API_KEY")

# APIキーが取得できているか確認
if not api_key:
    print("--------------------------------------------------------------------")
    print("エラー: GEMINI_API_KEY も GOOGLE_API_KEY も環境変数に見つかりません。")
    print(f".env ファイルのパス: {dotenv_path}")
    print("--------------------------------------------------------------------")
    raise ValueError("API Key not found in environment variables. Check .env file and variable names.")
else:
    # キーの一部を表示して確認（全部表示しないように注意）
    print(f"取得したAPIキーの最初の5文字: {api_key[:5]}...")
    print("--------------------------------------------------------------------")

# Gemini API設定
genai.configure(api_key=api_key)

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

**あなたのタスク:**
1. ユーザーの入力 (`input`) と、そのユーザーを識別する `user_id` を受け取ります。(`human` メッセージに `user_id:` として表示されます)
2. カレンダーを操作する必要がある場合、以下のツールを使用します。
   - `create_event_tool`
   - `get_events_tool`
   - `update_event_tool`
   - `delete_event_tool`
   - `search_events_by_title_tool`
3. **重要:** これらのカレンダーツールを呼び出す際には、**必ず** `human` メッセージで提供された `user_id` をツールの **第一引数** として渡してください。例えば、`get_events_tool` を使う場合は `get_events_tool(user_id='<実際のユーザーID>', start_time='...', end_time='...')` のように呼び出す必要があります。
4. 他のツール (`get_current_datetime_tool`, `parse_date_tool`) は `user_id` を必要としません。
5. 必要な情報が不足している場合は、ユーザーに質問してください。
6. 日付や時間の処理に関する重要なルール:
   - 「今日」「明日」「明後日」などの相対的な日付表現は、`parse_date_tool`を使用して適切な日付に変換してください。
   - 「今日の予定」「明日の予定」などの質問には、現在の日付から自動的に計算して回答してください。ユーザーに日付を尋ねる必要はありません。
   - 日付が曖昧な場合のみ、具体的な日付をユーザーに尋ねてください。
7. 処理結果を日本語で分かりやすく説明してください。
8. 会話の文脈を理解し、一貫性のある応答を心がけてください。
9. ユーザーの質問に対して、可能な限り1回の応答で完結するようにしてください。

利用可能なツール:
{tools}

ツール名リスト:
{tool_names}

常に丁寧に対応してください。"""),
    ("human", "user_id: {user_id}\ninput: {input}"),
    ("ai", "{agent_scratchpad}")
])

# LLMの初期化
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-04-17",
    temperature=0,
    google_api_key=api_key,  # APIキーを明示的に渡す
    convert_system_message_to_human=True  # システムメッセージを人間のメッセージに変換（Geminiの互換性向上）
)

# エージェントの初期化
agent_executor = initialize_agent(
    tools,
    llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    prompt=prompt,
    max_iterations=3  # イテレーション数を減らして処理を高速化
)

def process_user_message(user_id: str, user_message: str) -> str:
    """エージェントを使用してユーザーのメッセージを処理し、適切な応答を返す"""
    try:
        # ツール名のリストを作成
        tool_names = [tool.name for tool in tools]
        
        # デバッグ情報を出力
        print(f"処理するユーザーID: {user_id}")
        
        # ユーザーIDをエージェントに渡す
        # ユーザーメッセージを修正して、正しいユーザーIDを明示的に含める
        modified_message = f"以下のコマンドでは必ず user_id=\"{user_id}\" を使用してください。\n{user_message}"
        
        response = agent_executor.invoke({
            "input": modified_message,
            "user_id": user_id,  # 実際のユーザーIDを渡す
            "tools": tools,
            "tool_names": tool_names
        })
        
        # 応答をチェックして、ツール呼び出しがそのまま出力されていないか確認
        output = response["output"]
        if output.startswith("tools.") or "(" in output and ")" in output and "=" in output:
            # ツール呼び出しと思われる文字列が含まれている場合は、汎用的なメッセージに置き換える
            return "申し訳ありません。処理中にエラーが発生しました。もう一度お試しください。"
        
        # エラーメッセージをチェック
        if "ユーザーの認証情報が見つかりません" in output:
            auth_url = f"{os.getenv('APP_BASE_URL')}/google/authorize?user_id={user_id}"
            return f"Googleカレンダーへのアクセス許可が必要です。以下のリンクから認証を行ってください。\n{auth_url}"
        
        return output
    except Exception as e:
        print(f"エージェント実行中にエラーが発生: {e}")
        return f"申し訳ありません。処理中にエラーが発生しました: {str(e)}"
