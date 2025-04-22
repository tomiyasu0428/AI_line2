"""
LangGraphを使用したAIプロセッサ
会話履歴を管理し、ユーザーのメッセージを処理するためのモジュール
"""

import os
import datetime
import warnings
from typing import Dict, Any, List, TypedDict, Annotated, Sequence, Literal, Union, cast
from dotenv import load_dotenv

# 非推奨の警告を抑制
warnings.filterwarnings("ignore", category=UserWarning)

# .env ファイルをロード
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(dotenv_path=dotenv_path, verbose=True)

# LangGraph関連のインポート
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# LangChain関連のインポート
import google.generativeai as genai
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import BaseTool
from langchain.agents import AgentExecutor, create_structured_chat_agent, AgentType, initialize_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# カレンダーツールのインポート
from app.services.calendar_tools import (
    create_event_tool,
    get_events_tool,
    update_event_tool,
    delete_event_tool,
    search_events_by_title_tool,
    get_current_datetime_tool,
    parse_date_tool,
)

# Gemini API設定: APIキーを使用して認証
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
    print("警告: GEMINI_API_KEY または GOOGLE_APPLICATION_CREDENTIALS が設定されていません。")

# LLMの初期化
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-04-17",  # モデル名を修正
    temperature=0.3,
    convert_system_message_to_human=True,
    google_api_key=os.environ.get("GEMINI_API_KEY"),  # APIキーを直接指定
)

# 会話履歴を保存するための辞書
conversation_memories = {}


# 状態の定義
class AgentState(TypedDict):
    """エージェントの状態を表すクラス"""

    messages: List[BaseMessage]  # 現在の会話メッセージ
    user_id: str  # ユーザーID
    chat_history: List[BaseMessage]  # 会話履歴


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

# システムプロンプトの定義
SYSTEM_PROMPT = """あなたは日本語で会話するAIアシスタントで、ユーザーのGoogleカレンダーを管理します。
ユーザーからの要望に応じて、適切なツールを使用してカレンダーの予定を作成、取得、更新、削除してください。

重要: ユーザーIDは「user_id」パラメータとして提供されます。
カレンダー関連のツールを使用する際は、必ずこのユーザーIDを使用してください。
ユーザーIDはユーザーに見せる必要はありません。

**あなたのタスク:**
1. ユーザーの要望を理解し、適切なツールを使用して対応する
2. 必要な情報が不足している場合は、ユーザーに質問する
3. 処理結果を分かりやすく伝える

会話の文脈を理解し、前後のやり取りを考慮して応答してください。
例えば、ユーザーが「明日会議を設定して」と言った後に「13時から15時で」と言った場合、
これは会議の時間を指定していると理解してください。

常に丁寧に対応してください。"""


# ノードの定義
def parse_user_input(state: AgentState) -> AgentState:
    """ユーザー入力を解析し、ユーザーIDを抽出する"""
    # 最新のユーザーメッセージを取得
    user_message = state["messages"][-1].content

    # ユーザーIDの抽出（すでに状態に含まれているはずだが、念のため確認）
    user_id = state["user_id"]

    # デバッグ情報
    print(f"ユーザーID: {user_id}")
    print(f"ユーザーメッセージ: {user_message}")

    return state


def retrieve_context(state: AgentState) -> AgentState:
    """会話履歴や関連情報を取得"""
    # 会話履歴が空でない場合は、それを使用
    if state["chat_history"]:
        print(f"会話履歴: {len(state['chat_history'])}件のメッセージが存在します")
    else:
        print("会話履歴: なし")

    return state


def should_use_tools(state: AgentState) -> Literal["use_tools", "generate_response"]:
    """ツールを使用するかどうかを判断"""
    # 最新のユーザーメッセージを取得
    user_message = state["messages"][-1].content
    
    # 会話履歴から直近のメッセージを取得（文脈を理解するため）
    recent_context = ""
    if state["chat_history"] and len(state["chat_history"]) > 0:
        # 直近の最大3つのメッセージを取得
        recent_messages = state["chat_history"][-3:]
        recent_context = " ".join([msg.content for msg in recent_messages])

    # 検索対象のテキスト（現在のメッセージと直近の文脈）
    search_text = user_message + " " + recent_context
    
    # ツールを使用する可能性が高いキーワードのリスト
    calendar_keywords = [
        "予定", "スケジュール", "カレンダー", "会議", "ミーティング", "イベント",
        "作成", "登録", "追加", "設定", "入れて", "入力", "予約",
        "確認", "チェック", "見せて", "教えて", "取得", "検索", "探して",
        "変更", "更新", "修正", "編集", "削除", "キャンセル", "取り消し",
        "何時", "何日", "いつ", "どこ", "場所", "明日", "今日", "来週", "先週",
        "午前", "午後", "朝", "昼", "夕方", "夜", "時間", "日程",
        "リマインド", "通知", "アラーム", "参加者", "招待", "出席者"
    ]

    # メッセージ内にカレンダー関連のキーワードが含まれているかチェック
    if any(keyword in search_text for keyword in calendar_keywords):
        print("ツールを使用する可能性があります")
        return "use_tools"
    else:
        print("通常の応答を生成します")
        return "generate_response"


# ツールを使用するノード
def use_tools(state: AgentState) -> AgentState:
    """必要に応じてツールを呼び出す"""
    # システムメッセージを追加
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["chat_history"] + state["messages"]

    # ツール使用のためのプロンプト
    tool_prompt = """
以下のツールを使用できます：
1. create_event_tool: Googleカレンダーに新しいイベントを作成
2. get_events_tool: 指定された期間のGoogleカレンダーイベントを取得
3. update_event_tool: 既存のGoogleカレンダーイベントを更新
4. delete_event_tool: Googleカレンダーからイベントを削除
5. search_events_by_title_tool: タイトルのキーワードでGoogleカレンダーイベントを検索

重要: すべてのツールを使用する際は、必ずユーザーIDを含めてください。ユーザーIDは「user_id」パラメータとして提供されます。

カレンダー関連のリクエストを受けた場合は、適切なツールを使用してください。
ツールを使用する際は、必要なパラメータをすべて指定してください。
日時の形式は ISO 8601 形式（例: '2023-06-01T14:00:00+09:00'）を使用してください。

常に丁寧に対応してください。
"""

    # ツールの使用を促すメッセージを追加
    messages.append(SystemMessage(content=tool_prompt))

    try:
        # より単純なアプローチを使用
        from langchain.agents import AgentType, initialize_agent

        # プロンプトテンプレートを作成
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """あなたはLINEボット上で動作する日本語AIアシスタントです。
ユーザーの質問に丁寧に答え、カレンダー関連のタスクを実行するためのツールを使用できます。

以下のツールを使用できます:
1. create_event_tool: Googleカレンダーに新しいイベントを作成
2. get_events_tool: 指定された期間のGoogleカレンダーイベントを取得
3. update_event_tool: 既存のGoogleカレンダーイベントを更新
4. delete_event_tool: Googleカレンダーからイベントを削除
5. search_events_by_title_tool: タイトルのキーワードでGoogleカレンダーイベントを検索

重要: すべてのツールを使用する際は、必ずユーザーIDを含めてください。ユーザーIDは「user_id」パラメータとして提供されます。

カレンダー関連のリクエストを受けた場合は、適切なツールを使用してください。
ツールを使用する際は、必要なパラメータをすべて指定してください。
日時の形式は ISO 8601 形式（例: '2023-06-01T14:00:00+09:00'）を使用してください。

常に丁寧に対応してください。""",
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # エージェントを作成（より単純な方法）
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
        result = agent_executor.invoke({
            "input": f"ユーザーID: {user_id_str}\n{state['messages'][-1].content}", 
            "chat_history": formatted_chat_history,
            "user_id": user_id_str
        })

        # ツール呼び出しの結果を取得
        tool_result = result["output"]
        
        # 中間ステップ（ツールの実行ステップ）を取得
        if "intermediate_steps" in result and result["intermediate_steps"]:
            # ツールの実行ステップを出力
            print(f"ツール実行ステップ: {len(result['intermediate_steps'])}個")
            for i, step in enumerate(result["intermediate_steps"]):
                action, action_output = step
                print(f"ステップ {i+1}:")
                print(f"  ツール: {action.tool}")
                print(f"  入力: {action.tool_input}")
                print(f"  出力: {action_output}")
                
            # 最後のツール実行結果を使用
            if result["intermediate_steps"]:
                last_step = result["intermediate_steps"][-1]
                _, last_output = last_step
                # デバッグ用にログには出力するが、ユーザーへの応答には含めない
                print(f"実行されたツール: {last_output}")
                # ツールの実行結果をそのまま使用
                tool_result = tool_result

        # デバッグ情報
        print(f"ツール呼び出し結果: {tool_result}")

        # 結果をstateに追加
        state["messages"].append(AIMessage(content=tool_result))
    except Exception as e:
        print(f"ツール呼び出し中にエラーが発生しました: {str(e)}")
        state["messages"].append(
            AIMessage(content=f"申し訳ありません。ツールの使用中にエラーが発生しました: {str(e)}")
        )

    return state


def generate_response(state: AgentState) -> AgentState:
    """最終的な応答を生成"""
    # システムメッセージを追加
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["chat_history"] + state["messages"]

    # LLMを使用して応答を生成
    response = llm.invoke(messages)

    # 応答をstateに追加
    state["messages"].append(response)

    return state


def update_chat_history(state: AgentState) -> AgentState:
    """会話履歴を更新"""
    # 現在の会話を履歴に追加
    # 最初のメッセージ（ユーザー）と最後のメッセージ（AI）を履歴に追加
    if len(state["messages"]) >= 2:
        state["chat_history"].append(state["messages"][0])  # ユーザーメッセージ
        state["chat_history"].append(state["messages"][-1])  # AIの応答

    # 履歴が長すぎる場合は、古いメッセージを削除（最大10往復=20メッセージまで保持）
    max_history_length = 20
    if len(state["chat_history"]) > max_history_length:
        state["chat_history"] = state["chat_history"][-max_history_length:]

    return state


# グラフの構築
def build_graph() -> StateGraph:
    """LangGraphのワークフローを構築"""
    workflow = StateGraph(AgentState)

    # ノードの追加
    workflow.add_node("parse_input", parse_user_input)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("use_tools", use_tools)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("update_chat_history", update_chat_history)

    # エッジの定義
    # STARTノードから最初のノードへのエッジを追加
    workflow.set_entry_point("parse_input")

    workflow.add_edge("parse_input", "retrieve_context")
    workflow.add_conditional_edges(
        "retrieve_context",
        should_use_tools,
        {"use_tools": "use_tools", "generate_response": "generate_response"},
    )
    workflow.add_edge("use_tools", "update_chat_history")
    workflow.add_edge("generate_response", "update_chat_history")
    workflow.add_edge("update_chat_history", END)

    # コンパイル
    return workflow.compile()


# グラフのインスタンスを作成
agent_graph = build_graph()


def get_or_create_memory(user_id: str) -> List[BaseMessage]:
    """ユーザーIDに基づいてメモリを取得または作成"""
    if user_id not in conversation_memories:
        conversation_memories[user_id] = []
    return conversation_memories[user_id]


def process_user_message(user_id: str, user_message: str) -> str:
    """ユーザーメッセージを処理"""
    try:
        # ユーザーIDをメッセージに含める
        modified_message = user_message

        # 会話履歴を取得
        chat_history = get_or_create_memory(user_id)

        # デバッグ情報
        print(f"ユーザーメッセージ: {modified_message}")
        print(f"ユーザーID: {user_id}")

        # 初期状態を作成
        state = {
            "messages": [HumanMessage(content=modified_message)],
            "user_id": user_id,
            "chat_history": chat_history,
        }

        # グラフを実行
        result = agent_graph.invoke(state)

        # 応答を取得
        output = result["messages"][-1].content

        # デバッグ情報
        print(f"AIの応答: {output}")

        # エラーメッセージをチェック
        if "ユーザーの認証情報が見つかりません" in output:
            auth_url = f"{os.getenv('APP_BASE_URL')}/google/authorize?user_id={user_id}"
            return f"Googleカレンダーの機能を使用するには、以下のリンクから認証を行ってください。\n\n認証リンク：\n{auth_url}\n\n認証が完了したら、「予定を確認して」などと入力してください。"

        return output
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return f"申し訳ありません。エラーが発生しました: {str(e)}"
