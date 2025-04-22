import os
import json
import sqlite3
from typing import Dict, Any, Optional

# SQLite DB 初期化
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.getenv("SQLITE_DB_PATH", os.path.join(base_dir, "user_tokens.db"))
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.execute("""
CREATE TABLE IF NOT EXISTS user_tokens (
    user_id TEXT PRIMARY KEY,
    token TEXT,
    refresh_token TEXT,
    token_uri TEXT,
    client_id TEXT,
    client_secret TEXT,
    scopes TEXT
)
""")
conn.commit()

def save_user_tokens(user_id: str, token_info: Dict[str, Any]) -> bool:
    """ユーザーのトークン情報を保存する"""
    try:
        scopes_str = json.dumps(token_info.get("scopes", []))
        conn.execute(
            """
            INSERT INTO user_tokens (user_id, token, refresh_token, token_uri, client_id, client_secret, scopes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                token=excluded.token,
                refresh_token=excluded.refresh_token,
                token_uri=excluded.token_uri,
                client_id=excluded.client_id,
                client_secret=excluded.client_secret,
                scopes=excluded.scopes
            """,
            (
                user_id,
                token_info.get("token"),
                token_info.get("refresh_token"),
                token_info.get("token_uri"),
                token_info.get("client_id"),
                token_info.get("client_secret"),
                scopes_str
            )
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving user tokens: {e}")
        return False

def get_user_tokens(user_id: str) -> Optional[Dict[str, Any]]:
    """ユーザーのトークン情報を取得する"""
    try:
        row = conn.execute(
            "SELECT token, refresh_token, token_uri, client_id, client_secret, scopes FROM user_tokens WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        scopes = json.loads(row[5]) if row[5] else []
        return {
            "token": row[0],
            "refresh_token": row[1],
            "token_uri": row[2],
            "client_id": row[3],
            "client_secret": row[4],
            "scopes": scopes
        }
    except Exception as e:
        print(f"Error getting user tokens: {e}")
        return None
