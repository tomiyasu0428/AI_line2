import os
import datetime
import warnings
from typing import Dict, Any, List
from dotenv import load_dotenv

# 非推奨の警告を抑制
warnings.filterwarnings("ignore", category=UserWarning, message="Convert_system_message_to_human will be deprecated!")

# .env ファイルをロード (必ず ChatGoogleGenerativeAI 初期化より前に！)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(dotenv_path=dotenv_path, verbose=True)

import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferMemory

# 会話履歴を保存するための辞書
conversation_memories = {}

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
    parse_date_tool,
)

# ツールのリスト
tools = [
    create_event_tool,
    get_events_tool,
    update_event_tool,
    delete_event_tool,
    search_events_by_title_tool,
    get_current_datetime_tool,
    parse_date_tool,
]

# LLMの初期化
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-04-17",
    temperature=0,
    google_api_key=api_key,  # APIキーを明示的に渡す
    convert_system_message_to_human=True,  # システムメッセージを人間のメッセージに変換（Geminiの互換性向上）
)

def get_or_create_memory(user_id: str) -> ConversationBufferMemory:
    """ユーザーIDに基づいてメモリを取得または作成する"""
    if user_id not in conversation_memories:
        conversation_memories[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="input",  # 入力キーを明示的に指定
            return_messages=True
        )
    return conversation_memories[user_id]

def process_user_message(user_id: str, user_message: str) -> str:
    """エージェントを使用してユーザーのメッセージを処理し、適切な応答を返す"""
    try:
        # ツール名のリストを作成
        tool_names = [tool.name for tool in tools]

        # デバッグ情報を出力
        print(f"処理するユーザーID: {user_id}")
        print(f"ユーザーメッセージ: {user_message}")

        # ユーザーIDをエージェントに渡す
        # ユーザーメッセージを修正して、正しいユーザーIDを明示的に含める
        modified_message = f'ユーザーID: {user_id}\n{user_message}'

        # 会話履歴を取得
        memory = get_or_create_memory(user_id)
        
        # プロンプトテンプレート
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """あなたは日本語で会話するAIアシスタントで、ユーザーのGoogleカレンダーを管理します。
ユーザーからの要望に応じて、適切なツールを使用してカレンダーの予定を作成、取得、更新、削除してください。

重要: 各メッセージの先頭に「ユーザーID: XXX」という形式でユーザーIDが含まれています。
カレンダー関連のツールを使用する際は、必ずこのユーザーIDを使用してください。
ユーザーIDはユーザーに見せる必要はありません。

**あなたのタスク:**
1. ユーザーの要望を理解し、適切なツールを使用して対応する
2. 必要な情報が不足している場合は、ユーザーに質問する
3. 処理結果を分かりやすく伝える

会話の文脈を理解し、前後のやり取りを考慮して応答してください。
例えば、ユーザーが「明日会議を設定して」と言った後に「13時から15時で」と言った場合、
これは会議の時間を指定していると理解してください。

**使用可能なツール:**

1. create_event_tool: 新しい予定を作成します
   - user_id: ユーザーID（必須）
   - start_time: 開始時間（必須、ISO形式）
   - end_time: 終了時間（必須、ISO形式）
   - title: イベントのタイトル（必須）
   - location: 場所（オプション）
   - description: 説明（オプション）

2. get_events_tool: 指定期間の予定を取得します
   - user_id: ユーザーID（必須）
   - start_time: 開始時間（必須、ISO形式）
   - end_time: 終了時間（必須、ISO形式）

3. update_event_tool: 既存の予定を更新します
   - user_id: ユーザーID（必須）
   - event_id: イベントID（必須）
   - start_time: 新しい開始時間（オプション、ISO形式）
   - end_time: 新しい終了時間（オプション、ISO形式）
   - title: 新しいタイトル（オプション）
   - location: 新しい場所（オプション）
   - description: 新しい説明（オプション）

4. delete_event_tool: 予定を削除します
   - user_id: ユーザーID（必須）
   - event_id: イベントID（必須）

5. search_events_by_title_tool: タイトルで予定を検索します
   - user_id: ユーザーID（必須）
   - title_keyword: 検索キーワード（必須）
   - start_time: 検索開始時間（オプション、ISO形式）
   - end_time: 検索終了時間（オプション、ISO形式）

6. get_current_datetime_tool: 現在の日時を取得します

7. parse_date_tool: 自然言語の日付を解析してISO形式に変換します
   - date_string: 変換する日付文字列（例: '明日の午後3時'）

常に丁寧に対応してください。""",
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                ("ai", "{agent_scratchpad}"),
            ]
        )

        # エージェントの初期化
        agent_executor = initialize_agent(
            tools,
            llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            prompt=prompt,
            memory=memory,
            max_iterations=10,  # イテレーション数を増やして複雑なタスクに対応
            early_stopping_method="force",  # 強制的に早期停止する
        )

        # エージェントを実行
        response = agent_executor.invoke(
            {
                "input": modified_message,
            }
        )

        # 応答をチェックして、ツール呼び出しがそのまま出力されていないか確認
        output = response["output"]
        
        # イテレーション制限やエラーを検出
        if "Agent stopped due to iteration limit" in output or "Agent stopped due to time limit" in output:
            return "申し訳ありません。このリクエストは複雑すぎるようです。もう少し具体的な指示をいただけますか？"
            
        if output.startswith("tools.") or "(" in output and ")" in output and "=" in output:
            # ツール呼び出しと思われる文字列が含まれている場合は、汎用的なメッセージに置き換える
            return "申し訳ありません。処理中にエラーが発生しました。もう一度お試しください。"

        # エラーメッセージをチェック
        if "ユーザーの認証情報が見つかりません" in output:
            auth_url = f"{os.getenv('APP_BASE_URL')}/google/authorize?user_id={user_id}"
            return f"Googleカレンダーへのアクセス許可が必要です。以下のリンクから認証を行ってください。\n{auth_url}"

        # デバッグ情報
        print(f"AIの応答: {output}")
        
        return output
    except Exception as e:
        print(f"エージェント実行中にエラーが発生: {e}")
        return f"申し訳ありません。処理中にエラーが発生しました: {str(e)}"
