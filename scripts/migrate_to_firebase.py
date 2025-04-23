"""
SQLiteからFirebaseへのデータ移行スクリプト
"""

import os
import sys
import sqlite3
import json
from dotenv import load_dotenv

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 環境変数をロード
load_dotenv()

# Firebaseデータベースマネージャーをインポート
from app.services.firebase_database import FirebaseDatabaseManager

def migrate_data():
    """SQLiteからFirebaseへデータを移行する"""
    print("SQLiteからFirebaseへのデータ移行を開始します...")
    
    # SQLiteデータベースに接続
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.getenv("SQLITE_DB_PATH", os.path.join(base_dir, "user_tokens.db"))
    
    print(f"SQLiteデータベースに接続: {db_path}")
    sqlite_conn = sqlite3.connect(db_path)
    cursor = sqlite_conn.cursor()
    
    # Firebaseデータベースマネージャーを初期化
    firebase_db = FirebaseDatabaseManager()
    
    # ユーザートークンデータを取得
    print("ユーザートークンデータを取得中...")
    cursor.execute("SELECT * FROM user_tokens")
    rows = cursor.fetchall()
    
    # 各ユーザーのデータをFirebaseに移行
    success_count = 0
    error_count = 0
    
    for row in rows:
        user_id = row[0]
        token_info = {
            "token": row[1],
            "refresh_token": row[2],
            "token_uri": row[3],
            "client_id": row[4],
            "client_secret": row[5],
            "scopes": json.loads(row[6]) if row[6] else []
        }
        
        print(f"ユーザー {user_id} のデータを移行中...")
        
        try:
            # Firebaseにデータを保存
            if firebase_db.save_user_tokens(user_id, token_info):
                success_count += 1
                print(f"  ✓ ユーザー {user_id} のデータを正常に移行しました")
            else:
                error_count += 1
                print(f"  ✗ ユーザー {user_id} のデータ移行に失敗しました")
        except Exception as e:
            error_count += 1
            print(f"  ✗ エラー: {e}")
    
    # 結果を表示
    print("\n移行完了:")
    print(f"  成功: {success_count}")
    print(f"  失敗: {error_count}")
    print(f"  合計: {success_count + error_count}")
    
    # 接続を閉じる
    sqlite_conn.close()
    print("SQLite接続を閉じました")

if __name__ == "__main__":
    migrate_data()
