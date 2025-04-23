"""
Firebase Firestoreを使用したデータベース接続と認証情報の管理を行うモジュール
"""

import os
import json
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore


class FirebaseDatabaseManager:
    """Firebase Firestoreを使用したデータベース接続と操作を管理するクラス"""

    _instance = None

    def __new__(cls):
        """シングルトンパターンを実装"""
        if cls._instance is None:
            cls._instance = super(FirebaseDatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Firestore接続を初期化"""
        # Firebase初期化（まだ初期化されていない場合）
        if not firebase_admin._apps:
            # 環境変数から認証情報を取得する方法を決定
            cred = None

            # 方法1: 環境変数から直接JSON文字列を読み取る
            if "FIREBASE_CREDENTIALS" in os.environ:
                try:
                    cred_dict = json.loads(os.environ["FIREBASE_CREDENTIALS"])
                    cred = credentials.Certificate(cred_dict)
                    print("環境変数から直接Firebase認証情報を読み込みました")
                except Exception as e:
                    print(f"環境変数からの認証情報読み込みに失敗しました: {e}")

            # 方法2: 環境変数からファイルパスを読み取る
            if cred is None and "FIREBASE_CREDENTIALS_PATH" in os.environ:
                cred_path = os.environ["FIREBASE_CREDENTIALS_PATH"]
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    print(f"ファイルからFirebase認証情報を読み込みました: {cred_path}")
                else:
                    raise ValueError(f"指定されたパスに認証情報ファイルが見つかりません: {cred_path}")

            # どちらの方法でも認証情報が取得できなかった場合
            if cred is None:
                raise ValueError("FIREBASE_CREDENTIALS または FIREBASE_CREDENTIALS_PATH が設定されていません")

            # Firebaseアプリを初期化
            firebase_admin.initialize_app(cred)

        # Firestoreクライアントを取得
        self.db = firestore.client()

    def save_user_tokens(self, user_id: str, token_info: Dict[str, Any]) -> bool:
        """
        ユーザーのトークン情報をFirestoreに保存する

        Args:
            user_id: ユーザーID
            token_info: トークン情報の辞書

        Returns:
            保存が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # トークン情報をFirestoreに適した形式に変換
            data = {
                "token": token_info.get("token"),
                "refresh_token": token_info.get("refresh_token"),
                "token_uri": token_info.get("token_uri"),
                "client_id": token_info.get("client_id"),
                "client_secret": token_info.get("client_secret"),
                "scopes": token_info.get("scopes", []),
                "updated_at": firestore.SERVER_TIMESTAMP,
            }

            # ドキュメントを更新または作成
            self.db.collection("user_tokens").document(user_id).set(data)
            return True

        except Exception as e:
            print(f"Firestoreにトークン情報を保存中にエラーが発生しました: {e}")
            return False

    def get_user_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        ユーザーのトークン情報をFirestoreから取得する

        Args:
            user_id: ユーザーID

        Returns:
            トークン情報の辞書、存在しない場合はNone
        """
        try:
            # ドキュメントを取得
            doc_ref = self.db.collection("user_tokens").document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                return None

            # ドキュメントデータを取得
            data = doc.to_dict()

            # アプリケーションで使用する形式に変換
            return {
                "token": data.get("token"),
                "refresh_token": data.get("refresh_token"),
                "token_uri": data.get("token_uri"),
                "client_id": data.get("client_id"),
                "client_secret": data.get("client_secret"),
                "scopes": data.get("scopes", []),
            }

        except Exception as e:
            print(f"Firestoreからトークン情報を取得中にエラーが発生しました: {e}")
            return None

    def save_group_schedule(self, group_id: str, event_data: Dict[str, Any]) -> bool:
        """
        グループスケジュールデータを保存する

        Args:
            group_id: グループID
            event_data: イベントデータ

        Returns:
            保存が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            event_data["updated_at"] = firestore.SERVER_TIMESTAMP

            # イベントIDがある場合はそれを使用、なければ自動生成
            event_id = event_data.get("event_id", self.db.collection("group_events").document().id)
            event_data["event_id"] = event_id

            # ドキュメントを更新または作成
            self.db.collection("group_events").document(event_id).set(event_data)

            # グループとイベントの関連付け
            self.db.collection("groups").document(group_id).collection("events").document(event_id).set(
                {"event_id": event_id, "created_at": firestore.SERVER_TIMESTAMP}
            )

            return True

        except Exception as e:
            print(f"グループスケジュールデータの保存中にエラーが発生しました: {e}")
            return False

    def get_group_schedules(self, group_id: str) -> list:
        """
        グループに関連するすべてのスケジュールを取得する

        Args:
            group_id: グループID

        Returns:
            スケジュールのリスト
        """
        try:
            # グループに関連するイベントIDを取得
            event_refs = self.db.collection("groups").document(group_id).collection("events").stream()
            event_ids = [event_ref.to_dict().get("event_id") for event_ref in event_refs]

            # 各イベントの詳細を取得
            events = []
            for event_id in event_ids:
                doc = self.db.collection("group_events").document(event_id).get()
                if doc.exists:
                    events.append(doc.to_dict())

            return events

        except Exception as e:
            print(f"グループスケジュールの取得中にエラーが発生しました: {e}")
            return []

    def update_vote(self, event_id: str, user_id: str, date_option: str, vote: bool) -> bool:
        """
        日程投票を更新する

        Args:
            event_id: イベントID
            user_id: ユーザーID
            date_option: 日程オプション
            vote: 投票値（True=参加可能、False=参加不可）

        Returns:
            更新が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # トランザクションを使用して安全に更新
            transaction = self.db.transaction()
            event_ref = self.db.collection("group_events").document(event_id)

            @firestore.transactional
            def update_in_transaction(transaction, event_ref):
                event = event_ref.get(transaction=transaction).to_dict()

                # 投票データがなければ初期化
                if "votes" not in event:
                    event["votes"] = {}
                if date_option not in event["votes"]:
                    event["votes"][date_option] = {}

                # 投票を更新
                event["votes"][date_option][user_id] = vote

                # 更新をコミット
                transaction.update(event_ref, {"votes": event["votes"]})
                return True

            return update_in_transaction(transaction, event_ref)

        except Exception as e:
            print(f"投票の更新中にエラーが発生しました: {e}")
            return False

    def close_vote(self, event_id: str, selected_date: str) -> bool:
        """
        投票を締め切り、選択された日程を確定する

        Args:
            event_id: イベントID
            selected_date: 選択された日程

        Returns:
            更新が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            self.db.collection("group_events").document(event_id).update(
                {
                    "status": "confirmed",
                    "confirmed_date": selected_date,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }
            )
            return True

        except Exception as e:
            print(f"投票締め切り処理中にエラーが発生しました: {e}")
            return False


# データベースマネージャーのインスタンスを作成
firebase_db_manager = FirebaseDatabaseManager()


# 外部から使用するための関数
def save_user_tokens(user_id: str, token_info: Dict[str, Any]) -> bool:
    """ユーザーのトークン情報を保存する"""
    return firebase_db_manager.save_user_tokens(user_id, token_info)


def get_user_tokens(user_id: str) -> Optional[Dict[str, Any]]:
    """ユーザーのトークン情報を取得する"""
    return firebase_db_manager.get_user_tokens(user_id)


def save_group_schedule(group_id: str, event_data: Dict[str, Any]) -> bool:
    """グループスケジュールデータを保存する"""
    return firebase_db_manager.save_group_schedule(group_id, event_data)


def get_group_schedules(group_id: str) -> list:
    """グループに関連するすべてのスケジュールを取得する"""
    return firebase_db_manager.get_group_schedules(group_id)


def update_vote(event_id: str, user_id: str, date_option: str, vote: bool) -> bool:
    """日程投票を更新する"""
    return firebase_db_manager.update_vote(event_id, user_id, date_option, vote)


def close_vote(event_id: str, selected_date: str) -> bool:
    """投票を締め切り、選択された日程を確定する"""
    return firebase_db_manager.close_vote(event_id, selected_date)
