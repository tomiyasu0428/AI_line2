"""
LangGraphプロセッサのテスト用スクリプト
"""

import os
import sys

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.langgraph_processor import process_user_message


def test_simple_conversation():
    """シンプルな会話のテスト"""
    user_id = "test_user_123"

    # 最初のメッセージ
    print("テスト1: 基本的な挨拶")
    response1 = process_user_message(user_id, "こんにちは")
    print(f"応答: {response1}\n")

    # 2回目のメッセージ（会話の継続性をテスト）
    print("テスト2: 会話の継続性")
    response2 = process_user_message(user_id, "あなたは何ができますか？")
    print(f"応答: {response2}\n")

    # カレンダー関連のメッセージ
    print("テスト3: カレンダー関連の質問")
    response3 = process_user_message(user_id, "明日の予定を教えてください")
    print(f"応答: {response3}\n")

    # 複数ターンの会話（文脈理解のテスト）
    print("テスト4: 文脈理解")
    response4 = process_user_message(user_id, "明日会議を設定して")
    print(f"応答: {response4}\n")

    response5 = process_user_message(user_id, "13時から15時で")
    print(f"応答: {response5}\n")


if __name__ == "__main__":
    test_simple_conversation()
