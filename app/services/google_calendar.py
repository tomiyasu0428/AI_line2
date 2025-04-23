"""
Googleカレンダーとの連携を管理するモジュール
"""

import datetime
from typing import Dict, List, Any, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request as GoogleRequest

from app.services.database_factory import get_user_tokens, save_user_tokens


def check_user_auth_status(user_id: str) -> bool:
    """
    ユーザーのGoogle認証状態を確認する

    Args:
        user_id: ユーザーID

    Returns:
        認証済みの場合はTrue、それ以外はFalse
    """
    try:
        tokens = get_user_tokens(user_id)
        return bool(tokens)
    except Exception as e:
        print(f"認証状態確認中にエラーが発生しました: {e}")
        return False


def get_google_calendar_service(user_id: str):
    """
    Google Calendar APIのサービスオブジェクトを取得する

    Args:
        user_id: ユーザーID

    Returns:
        Google Calendar APIのサービスオブジェクト

    Raises:
        ValueError: ユーザーの認証情報が見つからない場合
        HttpError: Google APIとの通信中にエラーが発生した場合
    """
    try:
        print(f"Google Calendar サービス取得 - ユーザーID: {user_id}")
        token_info = get_user_tokens(user_id)
        if not token_info:
            print(f"ユーザーID '{user_id}' の認証情報が見つかりません")
            raise ValueError("ユーザーの認証情報が見つかりません")

        print(f"トークン情報取得成功 - アクセストークン: {token_info.get('token')[:10]}...")

        # 認証情報の作成
        creds = Credentials(
            token=token_info.get("token"),
            refresh_token=token_info.get("refresh_token"),
            token_uri=token_info.get("token_uri"),
            client_id=token_info.get("client_id"),
            client_secret=token_info.get("client_secret"),
            scopes=token_info.get("scopes"),
        )

        # トークンの有効期限が切れている場合は更新
        if creds.expired and creds.refresh_token:
            print("トークンの有効期限が切れています。更新を試みます...")
            creds.refresh(GoogleRequest())

            # 更新したトークン情報を保存
            updated_token_info = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
            }
            save_user_tokens(user_id, updated_token_info)
            print("トークン情報を更新しました")

        # Google Calendar APIのサービスを構築
        service = build("calendar", "v3", credentials=creds)
        return service

    except HttpError as error:
        print(f"Google API エラー: {error}")
        raise
    except Exception as e:
        print(f"Error getting calendar service: {e}")
        raise ValueError(f"カレンダーサービスの取得中にエラーが発生しました: {e}")


def register_calendar_event(
    user_id: str, start_time: str, end_time: str, title: str, location: str = "", description: str = ""
) -> str:
    """
    Googleカレンダーに予定を登録する

    Args:
        user_id: ユーザーID
        start_time: 開始時間（ISO 8601形式）
        end_time: 終了時間（ISO 8601形式）
        title: イベントのタイトル
        location: 場所（オプション）
        description: 説明（オプション）

    Returns:
        作成されたイベントのID

    Raises:
        ValueError: パラメータが不正、または認証情報が見つからない場合
        HttpError: Google APIとの通信中にエラーが発生した場合
    """
    try:
        service = get_google_calendar_service(user_id)

        # イベントの作成
        event = {
            "summary": title,
            "location": location,
            "description": description,
            "start": {
                "dateTime": start_time,
                "timeZone": "Asia/Tokyo",
            },
            "end": {
                "dateTime": end_time,
                "timeZone": "Asia/Tokyo",
            },
        }

        # イベントをカレンダーに挿入
        created_event = service.events().insert(calendarId="primary", body=event).execute()
        print(f"イベントを作成しました: {created_event.get('htmlLink')}")

        return created_event["id"]

    except HttpError as error:
        print(f"Google API エラー: {error}")
        raise ValueError(f"イベント作成中にエラーが発生しました: {error}")
    except Exception as e:
        print(f"イベント作成中に予期しないエラーが発生しました: {e}")
        raise ValueError(f"イベント作成中にエラーが発生しました: {e}")


def get_calendar_events(user_id: str, start_time: str, end_time: str) -> List[Dict[str, Any]]:
    """
    指定期間のカレンダー予定を取得する

    Args:
        user_id: ユーザーID
        start_time: 取得開始時間（ISO 8601形式）
        end_time: 取得終了時間（ISO 8601形式）

    Returns:
        イベントのリスト

    Raises:
        ValueError: 認証情報が見つからない場合
        HttpError: Google APIとの通信中にエラーが発生した場合
    """
    try:
        service = get_google_calendar_service(user_id)

        # イベントの取得
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        print(f"{len(events)}件のイベントを取得しました")

        return events

    except HttpError as error:
        print(f"Google API エラー: {error}")
        return []
    except Exception as e:
        print(f"イベント取得中にエラーが発生しました: {e}")
        return []


def find_event_by_query(service, event_query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    クエリ条件に一致する予定を検索する

    Args:
        service: Google Calendar APIのサービスオブジェクト
        event_query: 検索条件（id, summaryなど）

    Returns:
        見つかったイベント、または None
    """
    try:
        # イベントIDが指定されている場合は直接取得
        if "id" in event_query:
            event = service.events().get(calendarId="primary", eventId=event_query["id"]).execute()
            return event

        # タイトルで検索する場合
        if "summary" in event_query:
            # 今日から1ヶ月間のイベントを取得
            now = datetime.datetime.utcnow()
            time_min = now.isoformat() + "Z"
            one_month_later = (now + datetime.timedelta(days=30)).isoformat() + "Z"

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=one_month_later,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            # タイトルが一致するイベントを検索
            for event in events:
                if event_query["summary"].lower() in event.get("summary", "").lower():
                    return event

        return None

    except HttpError as error:
        print(f"Google API エラー: {error}")
        return None
    except Exception as e:
        print(f"イベント検索中にエラーが発生しました: {e}")
        return None


def update_calendar_event(user_id: str, event_query: Dict[str, Any], updated_data: Dict[str, Any]) -> bool:
    """
    カレンダー予定を更新する

    Args:
        user_id: ユーザーID
        event_query: 更新対象のイベントを特定するクエリ（id, summaryなど）
        updated_data: 更新するデータ（start_time, end_time, title, location, descriptionなど）

    Returns:
        更新成功の場合はTrue、失敗の場合はFalse

    Raises:
        ValueError: 更新対象のイベントが見つからない場合
    """
    try:
        service = get_google_calendar_service(user_id)

        # イベントを検索
        event = find_event_by_query(service, event_query)
        if not event:
            raise ValueError("更新対象のイベントが見つかりません")

        # 更新データの適用
        if "title" in updated_data:
            event["summary"] = updated_data["title"]
        if "location" in updated_data:
            event["location"] = updated_data["location"]
        if "description" in updated_data:
            event["description"] = updated_data["description"]
        if "start_time" in updated_data:
            event["start"] = {
                "dateTime": updated_data["start_time"],
                "timeZone": "Asia/Tokyo",
            }
        if "end_time" in updated_data:
            event["end"] = {
                "dateTime": updated_data["end_time"],
                "timeZone": "Asia/Tokyo",
            }

        # イベントの更新
        updated_event = (
            service.events().update(calendarId="primary", eventId=event["id"], body=event).execute()
        )

        print(f"イベントを更新しました: {updated_event.get('htmlLink')}")
        return True

    except HttpError as error:
        print(f"Google API エラー: {error}")
        return False
    except Exception as e:
        print(f"イベント更新中にエラーが発生しました: {e}")
        return False


def delete_calendar_event(user_id: str, event_query: Dict[str, Any]) -> bool:
    """
    カレンダー予定を削除する

    Args:
        user_id: ユーザーID
        event_query: 削除対象のイベントを特定するクエリ（id, summaryなど）

    Returns:
        削除成功の場合はTrue、失敗の場合はFalse

    Raises:
        ValueError: 削除対象のイベントが見つからない場合
    """
    try:
        service = get_google_calendar_service(user_id)

        # イベントを検索
        event = find_event_by_query(service, event_query)
        if not event:
            raise ValueError("削除対象のイベントが見つかりません")

        # イベントの削除
        service.events().delete(calendarId="primary", eventId=event["id"]).execute()

        print(f"イベントを削除しました: {event.get('summary')}")
        return True

    except HttpError as error:
        print(f"Google API エラー: {error}")
        return False
    except Exception as e:
        print(f"イベント削除中にエラーが発生しました: {e}")
        return False
