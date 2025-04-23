"""
LangGraphを使用したAIプロセッサ
会話履歴を管理し、ユーザーのメッセージを処理するためのモジュール
"""

import os
import warnings
from typing import List, TypedDict, Literal, Dict, Any, Optional, Tuple

# 外部ライブラリのインポート
from dotenv import load_dotenv
import google.generativeai as genai

# LangGraph関連のインポート
from langgraph.graph import StateGraph, END

# LangChain関連のインポート
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentType, initialize_agent

# アプリケーション内のインポート
from app.services.calendar_tools import (
    create_event_tool,
    get_events_tool,
    update_event_tool,
    delete_event_tool,
    search_events_by_title_tool,
    get_current_datetime_tool,
    parse_date_tool,
)

# 非推奨の警告を抑制
warnings.filterwarnings("ignore", category=UserWarning)

# .env ファイルをロード
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(dotenv_path=dotenv_path, verbose=True)

# Gemini API設定: APIキーを使用して認証
api_key = None
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    # サービスアカウントキーを使用
    print("サービスアカウントキーを使用して認証します...")
    genai.configure(service_account_json=os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
elif "GEMINI_API_KEY" in os.environ:
    # APIキーを使用
    api_key = os.environ["GEMINI_API_KEY"]
    print(f"取得したAPIキーの最初の5文字: {api_key[:5]}...")
    genai.configure(api_key=api_key)
else:
    raise ValueError("GEMINI_API_KEY または GOOGLE_APPLICATION_CREDENTIALS が設定されていません")

# LLMの設定
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-04-17",
    temperature=0.7,
    convert_system_message_to_human=True,
    verbose=False,
    google_api_key=api_key,  # APIキーを明示的に指定
)

# ユーザーごとのメモリを保持する辞書
user_memories = {}


class AgentState(TypedDict):
    """
    エージェントの状態を表すクラス

    Attributes:
        messages: 現在の会話メッセージリスト
        user_id: ユーザーID
        chat_history: 過去の会話履歴
    """

    messages: List[BaseMessage]
    user_id: str
    chat_history: List[BaseMessage]


# ツールの定義
tools = [
    create_event_tool,
    get_events_tool,
    update_event_tool,
    delete_event_tool,
    search_events_by_title_tool,
    get_current_datetime_tool,
    parse_date_tool,
]


def parse_user_input(state: AgentState) -> AgentState:
    """
    ユーザー入力を解析し、ユーザーIDを抽出する

    Args:
        state: 現在のエージェント状態

    Returns:
        更新されたエージェント状態
    """
    print("ユーザー入力を解析中...")
    # 既存の状態をコピー
    new_state = state.copy()
    print(f"ユーザーID: {new_state['user_id']}")
    return new_state


def retrieve_context(state: AgentState) -> AgentState:
    """
    会話履歴や関連情報を取得

    Args:
        state: 現在のエージェント状態

    Returns:
        更新されたエージェント状態
    """
    print("コンテキストを取得中...")
    return state


def should_use_tools(state: AgentState) -> Dict[str, Any]:
    """
    ツールを使用するかどうかを判断

    Args:
        state: 現在のエージェント状態

    Returns:
        次のステップを示す辞書: {"next": "use_tools"} または {"next": "generate_response"}
    """
    # 最新のユーザーメッセージを取得
    user_message = state["messages"][-1].content

    # 会話履歴から直近のメッセージを取得（文脈を理解するため）
    recent_context = ""
    if state["chat_history"] and len(state["chat_history"]) > 0:
        recent_messages = state["chat_history"][-3:]  # 直近3つのメッセージ
        recent_context = " ".join([msg.content for msg in recent_messages])

    # 検索対象のテキスト（現在のメッセージと直近の文脈）
    search_text = user_message + " " + recent_context

    # ツールを使用する可能性が高いキーワードのリスト
    calendar_keywords = [
        "予定",
        "スケジュール",
        "カレンダー",
        "会議",
        "ミーティング",
        "イベント",
        "作成",
        "登録",
        "追加",
        "設定",
        "入れて",
        "入力",
        "予約",
        "確認",
        "チェック",
        "見せて",
        "教えて",
        "取得",
        "検索",
        "探して",
        "変更",
        "更新",
        "修正",
        "編集",
        "削除",
        "キャンセル",
        "取り消し",
        "何時",
        "何日",
        "いつ",
        "どこ",
        "場所",
        "明日",
        "今日",
        "来週",
        "先週",
        "午前",
        "午後",
        "朝",
        "昼",
        "夕方",
        "夜",
        "時間",
        "日程",
        "リマインド",
        "通知",
        "アラーム",
        "参加者",
        "招待",
        "出席者",
    ]

    # メッセージ内にカレンダー関連のキーワードが含まれているかチェック
    for keyword in calendar_keywords:
        if keyword in search_text:
            print(f"キーワード '{keyword}' が見つかりました。ツールを使用します。")
            return {"next": "use_tools"}

    # 日付や時間の表現が含まれているかチェック
    time_patterns = ["時", "分", "午前", "午後", "AM", "PM", "日", "月", "火", "水", "木", "金", "土"]
    for pattern in time_patterns:
        if pattern in search_text:
            print(f"時間パターン '{pattern}' が見つかりました。ツールを使用します。")
            return {"next": "use_tools"}

    # 数字が含まれているかチェック（時間や日付の可能性）
    if any(char.isdigit() for char in search_text):
        # 数字の前後のコンテキストを確認
        # 単なる数字の言及なのか、時間や日付の指定なのかを判断
        digit_contexts = ["時", "分", "月", "日", "年", "時間", "日間", "週間"]
        for context in digit_contexts:
            if context in search_text:
                print(f"数字と時間コンテキスト '{context}' が見つかりました。ツールを使用します。")
                return {"next": "use_tools"}

    # 特定の質問パターンをチェック
    question_patterns = ["いつ", "どこで", "何時から", "何時まで", "どのくらい"]
    for pattern in question_patterns:
        if pattern in search_text:
            print(f"質問パターン '{pattern}' が見つかりました。ツールを使用します。")
            return {"next": "use_tools"}

    # 以上のパターンに一致しない場合は、通常の応答を生成
    print("ツールを使用する必要はありません。通常の応答を生成します。")
    return {"next": "generate_response"}


def use_tools(state: AgentState) -> AgentState:
    """
    必要に応じてツールを呼び出す

    Args:
        state: 現在のエージェント状態

    Returns:
        更新されたエージェント状態（ツール実行結果を含む）
    """
    print("ツールを使用中...")

    # システムプロンプトの定義
    system_prompt = """
あなたはLINEユーザーのためのAIアシスタントです。ユーザーのカレンダー予定を管理します。
以下のツールを使用して、ユーザーの要求に応えてください：

1. create_event - 新しい予定をGoogleカレンダーに作成します
2. get_events - 指定された期間の予定を取得します
3. update_event - 既存の予定を更新します
4. delete_event - 予定を削除します
5. search_events_by_title - タイトルで予定を検索します
6. get_current_datetime - 現在の日時を取得します
7. parse_date - 自然言語の日付表現をISO形式に変換します

ユーザーIDは必ず各ツールに渡してください。
ユーザーの要求を理解し、適切なツールを選択して実行してください。
日本語で丁寧に対応してください。
常に丁寧に対応してください。
"""

    # プロンプトテンプレートの作成
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # エージェントを作成
    agent_executor = initialize_agent(
        tools,
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False,
        handle_parsing_errors=True,
        prompt=prompt,
        max_iterations=10,
        early_stopping_method="force",
        return_intermediate_steps=True,
    )

    try:
        # ユーザーIDをより明示的に指定
        user_id_str = state["user_id"]
        print(f"ツール呼び出し時のユーザーID: {user_id_str}")

        # 会話履歴をフォーマット
        formatted_chat_history = []
        for msg in state["chat_history"]:
            if isinstance(msg, HumanMessage):
                formatted_chat_history.append({"role": "human", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted_chat_history.append({"role": "ai", "content": msg.content})

        # ツール呼び出し時にユーザーIDを明示的に含める
        result = agent_executor.invoke(
            {
                "input": f"ユーザーID: {user_id_str}\n{state['messages'][-1].content}",
                "chat_history": formatted_chat_history,
                "user_id": user_id_str,
            }
        )

        # ツール呼び出しの結果を取得
        tool_result = result["output"]

        # 中間ステップ（ツールの実行ステップ）を取得
        if "intermediate_steps" in result and result["intermediate_steps"]:
            # ツールの実行ステップを出力
            print("ツール実行ステップ:")
            for i, (action, action_output) in enumerate(result["intermediate_steps"]):
                print(f"ステップ {i+1}:")
                print(f"  ツール: {action.tool}")
                print(f"  入力: {action.tool_input}")
                print(f"  出力: {action_output}")

            # 最後のツール実行結果を使用
            if result["intermediate_steps"]:
                last_step = result["intermediate_steps"][-1]
                last_action, last_output = last_step
                print(f"最後のツール実行: {last_action.tool}")
                print(f"最後のツール出力: {last_output}")

        # 新しい状態を作成
        new_state = state.copy()

        # AIの応答を追加
        new_state["messages"] = state["messages"] + [AIMessage(content=tool_result)]

        return new_state

    except Exception as e:
        print(f"ツール使用中にエラーが発生しました: {e}")
        # エラーが発生した場合は、エラーメッセージを応答として追加
        error_message = f"申し訳ありません。処理中にエラーが発生しました。もう一度お試しください。"
        new_state = state.copy()
        new_state["messages"] = state["messages"] + [AIMessage(content=error_message)]
        return new_state


def generate_response(state: AgentState) -> AgentState:
    """
    最終的な応答を生成

    Args:
        state: 現在のエージェント状態

    Returns:
        更新されたエージェント状態（AI応答を含む）
    """
    print("応答を生成中...")
    response = llm.invoke(state["messages"])
    new_state = state.copy()
    new_state["messages"] = state["messages"] + [response]
    return new_state


def update_chat_history(state: AgentState) -> AgentState:
    """
    会話履歴を更新

    Args:
        state: 現在のエージェント状態

    Returns:
        更新されたエージェント状態（更新された会話履歴を含む）
    """
    print("会話履歴を更新中...")
    new_state = state.copy()
    # 現在のメッセージを履歴に追加
    new_state["chat_history"] = state["chat_history"] + state["messages"]
    return new_state


def build_graph() -> StateGraph:
    """
    LangGraphのワークフローを構築

    Returns:
        構築されたStateGraphインスタンス
    """
    # グラフの作成
    workflow = StateGraph(AgentState)

    # ノードの追加
    workflow.add_node("parse_user_input", parse_user_input)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("should_use_tools", should_use_tools)
    workflow.add_node("use_tools", use_tools)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("update_chat_history", update_chat_history)

    # エントリーポイントを設定
    workflow.set_entry_point("parse_user_input")

    # エッジの追加
    workflow.add_edge("parse_user_input", "retrieve_context")
    workflow.add_edge("retrieve_context", "should_use_tools")
    workflow.add_conditional_edges(
        "should_use_tools",
        lambda x: x["next"],
        {
            "use_tools": "use_tools",
            "generate_response": "generate_response",
        },
    )
    workflow.add_edge("use_tools", "update_chat_history")
    workflow.add_edge("generate_response", "update_chat_history")
    workflow.add_edge("update_chat_history", END)

    # グラフをコンパイル
    return workflow.compile()


# グラフのインスタンスを作成
agent_graph = build_graph()


def get_or_create_memory(user_id: str) -> List[BaseMessage]:
    """
    ユーザーIDに基づいてメモリを取得または作成

    Args:
        user_id: ユーザーID

    Returns:
        ユーザーの会話履歴
    """
    if user_id not in user_memories:
        user_memories[user_id] = []
    return user_memories[user_id]


def process_user_message(user_id: str, user_message: str) -> str:
    """
    ユーザーメッセージを処理

    Args:
        user_id: ユーザーID
        user_message: ユーザーからのメッセージ

    Returns:
        AIからの応答
    """
    print(f"ユーザーメッセージを処理中... ユーザーID: {user_id}")
    print(f"メッセージ: {user_message}")

    # ユーザーの会話履歴を取得
    chat_history = get_or_create_memory(user_id)

    # 初期状態の設定
    config = {"recursion_limit": 50}
    inputs = {
        "messages": [HumanMessage(content=user_message)],
        "user_id": user_id,
        "chat_history": chat_history,
    }

    try:
        # グラフを実行
        result = agent_graph.invoke(inputs, config=config)

        # 結果から最後のAIメッセージを取得
        messages = result["messages"]
        ai_message = None
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                ai_message = message
                break

        if not ai_message:
            return "申し訳ありません。応答の生成中にエラーが発生しました。"

        # 会話履歴を更新
        user_memories[user_id] = result["chat_history"]

        # AIの応答を返す
        return ai_message.content

    except Exception as e:
        print(f"メッセージ処理中にエラーが発生しました: {e}")
        return f"申し訳ありません。エラーが発生しました: {str(e)}"
