"""
Chatwork REST APIからメッセージを取得し、data/raw_messages.json に保存する。
差分取得: 既存ファイルがあれば message_id で重複排除してマージ。
"""

import json
import os
import sys
from datetime import datetime

import requests

# プロジェクトルートをパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import CHATWORK_API_TOKEN, CHATWORK_ROOM_ID, DATA_DIR


def fetch_messages(room_id: int, token: str) -> list[dict]:
    """Chatwork APIから最新100件のメッセージを取得する。"""
    url = f"https://api.chatwork.com/v2/rooms/{room_id}/messages?force=1"
    headers = {"X-ChatWorkToken": token}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    messages = response.json()
    return messages


def format_message(msg: dict) -> dict:
    """APIレスポンスを保存用フォーマットに変換する。"""
    unix_time = msg["send_time"]
    dt = datetime.fromtimestamp(unix_time)
    send_time_str = dt.strftime("%Y/%m/%d %H:%M:%S")

    return {
        "message_id": str(msg["message_id"]),
        "account_id": msg["account"]["account_id"],
        "account_name": msg["account"]["name"],
        "body": msg["body"],
        "send_time": send_time_str,
        "send_time_unix": unix_time,
    }


def load_existing_messages(filepath: str) -> list[dict]:
    """既存の raw_messages.json を読み込む。存在しなければ空リストを返す。"""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_messages(existing: list[dict], new: list[dict]) -> list[dict]:
    """既存メッセージと新規メッセージを message_id で重複排除してマージする。"""
    seen = {}
    for msg in existing:
        seen[msg["message_id"]] = msg
    for msg in new:
        seen[msg["message_id"]] = msg

    merged = sorted(seen.values(), key=lambda m: m["send_time_unix"])
    return merged


def main():
    if not CHATWORK_API_TOKEN:
        print("エラー: CHATWORK_API_TOKEN が設定されていません。")
        print("環境変数 CHATWORK_API_TOKEN を設定してください。")
        sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)
    output_path = os.path.join(DATA_DIR, "raw_messages.json")

    print(f"Chatwork ルーム {CHATWORK_ROOM_ID} からメッセージを取得中...")
    raw_messages = fetch_messages(CHATWORK_ROOM_ID, CHATWORK_API_TOKEN)
    print(f"  取得件数: {len(raw_messages)} 件")

    formatted = [format_message(msg) for msg in raw_messages]

    existing = load_existing_messages(output_path)
    print(f"  既存メッセージ: {len(existing)} 件")

    merged = merge_messages(existing, formatted)
    print(f"  マージ後: {len(merged)} 件")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"保存完了: {output_path}")


if __name__ == "__main__":
    main()
