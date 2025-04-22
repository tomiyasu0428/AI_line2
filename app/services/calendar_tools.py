import datetime
from typing import List, Dict, Any
from langchain_core.tools import tool

from app.services.google_calendar import (
    register_calendar_event,
    get_calendar_events,
    update_calendar_event,
    delete_calendar_event
)


@tool
def create_event_tool(user_id: str, start_time: str, end_time: str, title: str, location: str = "", description: str = "") -> str:
    """
    Googleカレンダーに新しいイベントを作成します。
    
    Args:
        user_id: ユーザーID
        start_time: イベント開始時間 (例: '2023-06-01T14:00:00+09:00')
        end_time: イベント終了時間 (例: '2023-06-01T15:00:00+09:00')
        title: イベントのタイトル
        location: イベントの場所（オプション）
        description: イベントの説明（オプション）
    
    Returns:
        作成されたイベントのIDを含むメッセージ
    """
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
    """
    指定された期間のGoogleカレンダーイベントを取得します。
    
    Args:
        user_id: ユーザーID
        start_time: 取得開始日時 (例: '2023-06-01T00:00:00+09:00')
        end_time: 取得終了日時 (例: '2023-06-07T23:59:59+09:00')
    
    Returns:
        イベントのリスト
    """
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
    """
    既存のGoogleカレンダーイベントを更新します。
    
    Args:
        user_id: ユーザーID
        event_id: 更新するイベントのID
        start_time: 新しいイベント開始時間 (例: '2023-06-01T14:00:00+09:00')
        end_time: 新しいイベント終了時間 (例: '2023-06-01T15:00:00+09:00')
        title: 新しいイベントのタイトル
        location: 新しいイベントの場所
        description: 新しいイベントの説明
    
    Returns:
        更新結果を示すメッセージ
    """
    update_calendar_event(
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
    """
    Googleカレンダーからイベントを削除します。
    
    Args:
        user_id: ユーザーID
        event_id: 削除するイベントのID
    
    Returns:
        削除結果を示すメッセージ
    """
    delete_calendar_event(user_id=user_id, event_id=event_id)
    return f"イベントID: {event_id}が削除されました。"


@tool
def search_events_by_title_tool(user_id: str, title_keyword: str, start_time: str = None, end_time: str = None) -> List[Dict[str, Any]]:
    """
    タイトルのキーワードでGoogleカレンダーイベントを検索します。
    
    Args:
        user_id: ユーザーID
        title_keyword: 検索キーワード
        start_time: 検索開始日時 (例: '2023-06-01T00:00:00+09:00')
        end_time: 検索終了日時 (例: '2023-06-07T23:59:59+09:00')
    
    Returns:
        イベントのリスト
    """
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
    """
    現在の日本時間を取得します。
    
    Returns:
        現在の日本時間
    """
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()


@tool
def parse_date_tool(date_string: str) -> str:
    """
    自然言語の日付文字列をISO形式 (RFC3339) の日付/時刻文字列に変換します。
    
    Args:
        date_string: 変換する日付文字列 (例: '明日の午後3時', '来週の月曜日 10:00')
    
    Returns:
        ISO形式 (RFC3339) の日付/時刻文字列 (例: '2023-06-01T15:00:00+09:00')
    """
    try:
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        
        # 「今日」「明日」などの相対的な日付を処理
        if "今日" in date_string:
            target_date = now
        elif "明日" in date_string:
            target_date = now + datetime.timedelta(days=1)
        elif "明後日" in date_string:
            target_date = now + datetime.timedelta(days=2)
        elif "昨日" in date_string:
            target_date = now - datetime.timedelta(days=1)
        elif "今週" in date_string:
            # 今週の月曜日から日曜日
            weekday = now.weekday()
            start_date = now - datetime.timedelta(days=weekday)
            end_date = start_date + datetime.timedelta(days=6)
            return {
                "start_date": start_date.replace(hour=0, minute=0, second=0).isoformat(),
                "end_date": end_date.replace(hour=23, minute=59, second=59).isoformat()
            }
        elif "来週" in date_string:
            # 来週の特定の曜日を処理
            weekday_mapping = {
                "月曜": 0, "月曜日": 0, "月": 0,
                "火曜": 1, "火曜日": 1, "火": 1,
                "水曜": 2, "水曜日": 2, "水": 2,
                "木曜": 3, "木曜日": 3, "木": 3,
                "金曜": 4, "金曜日": 4, "金": 4,
                "土曜": 5, "土曜日": 5, "土": 5,
                "日曜": 6, "日曜日": 6, "日": 6
            }
            
            target_weekday = None
            for day_name, day_num in weekday_mapping.items():
                if day_name in date_string:
                    target_weekday = day_num
                    break
            
            if target_weekday is not None:
                # 今日の曜日から目標の曜日までの日数を計算
                current_weekday = now.weekday()
                days_until_target = 7 - current_weekday + target_weekday
                if days_until_target >= 7:
                    days_until_target -= 7
                
                # 来週なので7日追加
                days_until_target += 7
                
                target_date = now + datetime.timedelta(days=days_until_target)
            else:
                # 特定の曜日が指定されていない場合は、来週の月曜日から日曜日の範囲を返す
                weekday = now.weekday()
                start_date = now - datetime.timedelta(days=weekday) + datetime.timedelta(days=7)
                end_date = start_date + datetime.timedelta(days=6)
                return {
                    "start_date": start_date.replace(hour=0, minute=0, second=0).isoformat(),
                    "end_date": end_date.replace(hour=23, minute=59, second=59).isoformat()
                }
        else:
            # デフォルトは今日
            target_date = now
        
        # 時間の処理
        if "午前" in date_string or "朝" in date_string:
            if "9時" in date_string or "9:00" in date_string:
                target_date = target_date.replace(hour=9, minute=0, second=0)
            elif "10時" in date_string or "10:00" in date_string:
                target_date = target_date.replace(hour=10, minute=0, second=0)
            elif "11時" in date_string or "11:00" in date_string:
                target_date = target_date.replace(hour=11, minute=0, second=0)
            else:
                target_date = target_date.replace(hour=9, minute=0, second=0)
        elif "午後" in date_string or "夕方" in date_string or "夜" in date_string:
            if "3時" in date_string or "15:00" in date_string or "15時" in date_string:
                target_date = target_date.replace(hour=15, minute=0, second=0)
            elif "6時" in date_string or "18:00" in date_string or "18時" in date_string:
                target_date = target_date.replace(hour=18, minute=0, second=0)
            elif "7時" in date_string or "19:00" in date_string or "19時" in date_string:
                target_date = target_date.replace(hour=19, minute=0, second=0)
            elif "8時" in date_string or "20:00" in date_string or "20時" in date_string:
                target_date = target_date.replace(hour=20, minute=0, second=0)
            else:
                target_date = target_date.replace(hour=15, minute=0, second=0)
        else:
            # デフォルトは午後3時
            target_date = target_date.replace(hour=15, minute=0, second=0)
        
        return target_date.isoformat()
    except Exception as e:
        return f"日付の解析に失敗しました: {str(e)}"
