# エージェントベースのカレンダー管理システムへの移行提案

## 概要

現在のシステムは、固定されたプロンプトテンプレートを使用してGemini APIからJSONレスポンスを取得し、そのレスポンスに基づいてカレンダー操作を行っています。より柔軟で対話的なシステムにするために、ツールを使用するエージェントベースのアプローチに移行することを提案します。

## 現状の課題

1. 現在のシステムは固定のプロンプトと決められたJSONフォーマットに依存しており、柔軟性に欠ける
2. エラーハンドリングが限定的で、ユーザーの意図を正確に把握できないケースがある
3. 複雑なリクエスト（例：「来週の会議を全て1時間後にずらして」など）の処理が難しい

## 提案するアプローチ：LangChain Agentsの導入

LangChainのエージェントフレームワークを使用して、AIが自律的に判断してツールを呼び出す仕組みに変更します。

### 1. ツールの定義

カレンダー操作を行うための各機能をツールとして定義します：

```python
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# カレンダーツールの定義
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
def get_events_tool(user_id: str, start_time: str, end_time: str) -> list:
    """指定された期間の予定を取得するツール。必要な引数: user_id, start_time, end_time"""
    events = get_calendar_events(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time
    )
    return events
```

### 2. エージェントの初期化

```python
# Gemini 2.0 Flashモデルを使用
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

# プロンプトの定義
prompt = ChatPromptTemplate.from_messages([
    ("system", """あなたは日本語で会話するAIアシスタントで、ユーザーのGoogleカレンダーを管理します。
ユーザーからの要望に応じて、適切なツールを使用してカレンダーの予定を作成、取得、更新、削除してください。"""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

# エージェントの作成
agent = create_react_agent(llm, tools)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
```

### 3. LangGraphを使用した代替実装

LangChainは現在、LangGraphというより柔軟なフレームワークへの移行を推奨しています：

```python
from langgraph.prebuilt import create_react_agent

# LangGraphエージェントの作成
langgraph_agent = create_react_agent(llm, tools)

# 使用例
def process_user_message(user_id: str, user_message: str) -> str:
    # エージェントを実行
    result = langgraph_agent.invoke({
        "messages": [("human", user_message)]
    })
    return result["messages"][-1][1]
```

## 実装手順

1. LangChainパッケージのインストール
   ```
   pip install langchain langchain-core langchain-google-genai langgraph
   ```

2. `app/services/ai_processor.py`の書き換え
   - 現在のコードをエージェントベースのアプローチに置き換える
   - 必要なツールとヘルパー関数を実装

3. エラーハンドリングの強化
   - エージェントの実行中に発生する可能性のあるエラーを適切に処理
   - ユーザーに分かりやすいエラーメッセージを返す

4. テスト
   - 様々なユーザーリクエストに対するエージェントの応答をテスト
   - エッジケースの処理を確認

## 期待される利点

1. **柔軟性の向上**: 固定のJSONフォーマットに依存せず、自然言語での多様なリクエストに対応
2. **対話性の改善**: 必要な情報が不足している場合、エージェントが自動的に質問
3. **複雑なリクエストの処理**: 複数のステップを要する複雑なリクエストも処理可能
4. **エラー回復力の向上**: エラーが発生した場合でも、エージェントが代替アプローチを試行

## 注意点

1. LangChainのエージェントは処理に時間がかかる場合があり、LINE Webhookの3秒タイムアウト制限に注意
2. 必要に応じてBackgroundTasksを使用して非同期処理を実装
3. エージェントのプロンプトエンジニアリングは継続的な改善が必要

## 結論

エージェントベースのアプローチに移行することで、より柔軟で対話的なカレンダー管理システムを実現できます。ユーザーは自然な言葉でリクエストを行い、AIアシスタントが適切なツールを選択して処理を行うことで、ユーザーエクスペリエンスが大幅に向上します。
