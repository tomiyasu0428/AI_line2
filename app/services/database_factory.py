"""
データベースの抽象化レイヤーを提供するモジュール
環境変数に基づいて適切なデータベース実装を選択します
"""

import os
from typing import Dict, Any, Optional

# データベース実装のインポート
from app.services.database import DatabaseManager as SQLiteDatabaseManager
from app.services.firebase_database import FirebaseDatabaseManager


class DatabaseFactory:
    """
    データベース実装を選択するファクトリークラス
    環境変数 DATABASE_TYPE に基づいて適切な実装を返します
    """
    
    @staticmethod
    def get_database_manager():
        """
        環境変数に基づいて適切なデータベースマネージャーを返す
        
        Returns:
            データベースマネージャーのインスタンス
        """
        db_type = os.getenv("DATABASE_TYPE", "sqlite").lower()
        
        if db_type == "firebase":
            # Firebase実装を使用
            return FirebaseDatabaseManager()
        else:
            # デフォルトはSQLite
            return SQLiteDatabaseManager()


# データベースマネージャーのインスタンスを取得
db_manager = DatabaseFactory.get_database_manager()

# 外部から使用するための関数
def save_user_tokens(user_id: str, token_info: Dict[str, Any]) -> bool:
    """ユーザーのトークン情報を保存する"""
    return db_manager.save_user_tokens(user_id, token_info)

def get_user_tokens(user_id: str) -> Optional[Dict[str, Any]]:
    """ユーザーのトークン情報を取得する"""
    return db_manager.get_user_tokens(user_id)

# グループスケジュール関連の関数（Firebaseのみサポート）
def save_group_schedule(group_id: str, event_data: Dict[str, Any]) -> bool:
    """
    グループスケジュールデータを保存する
    
    Note:
        この機能はFirebaseデータベースでのみサポートされています
    """
    if isinstance(db_manager, FirebaseDatabaseManager):
        return db_manager.save_group_schedule(group_id, event_data)
    else:
        print("Warning: グループスケジュール機能はFirebaseデータベースでのみサポートされています")
        return False

def get_group_schedules(group_id: str) -> list:
    """
    グループに関連するすべてのスケジュールを取得する
    
    Note:
        この機能はFirebaseデータベースでのみサポートされています
    """
    if isinstance(db_manager, FirebaseDatabaseManager):
        return db_manager.get_group_schedules(group_id)
    else:
        print("Warning: グループスケジュール機能はFirebaseデータベースでのみサポートされています")
        return []

def update_vote(event_id: str, user_id: str, date_option: str, vote: bool) -> bool:
    """
    日程投票を更新する
    
    Note:
        この機能はFirebaseデータベースでのみサポートされています
    """
    if isinstance(db_manager, FirebaseDatabaseManager):
        return db_manager.update_vote(event_id, user_id, date_option, vote)
    else:
        print("Warning: 投票機能はFirebaseデータベースでのみサポートされています")
        return False

def close_vote(event_id: str, selected_date: str) -> bool:
    """
    投票を締め切り、選択された日程を確定する
    
    Note:
        この機能はFirebaseデータベースでのみサポートされています
    """
    if isinstance(db_manager, FirebaseDatabaseManager):
        return db_manager.close_vote(event_id, selected_date)
    else:
        print("Warning: 投票締め切り機能はFirebaseデータベースでのみサポートされています")
        return False
