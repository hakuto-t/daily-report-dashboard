"""
日報データ自動蓄積スクリプト
毎日実行することで、Chatwork APIの100件制限を回避し、全データを蓄積する。

動作:
1. Chatwork APIから最新100件を取得
2. 既存の raw_messages.json とマージ（message_idで重複排除）
3. 保存

Windows タスクスケジューラで毎日実行推奨:
  python scripts/auto_collect.py
"""
import json
import os
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import CHATWORK_API_TOKEN, CHATWORK_ROOM_ID, DATA_DIR

LOG_FILE = os.path.join(DATA_DIR, "collect_log.txt")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def fetch_latest():
    """Chatwork APIから最新100件取得"""
    import requests
    url = f"https://api.chatwork.com/v2/rooms/{CHATWORK_ROOM_ID}/messages?force=1"
    headers = {"X-ChatWorkToken": CHATWORK_API_TOKEN}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def format_msg(msg):
    unix_time = msg["send_time"]
    dt = datetime.fromtimestamp(unix_time)
    return {
        "message_id": str(msg["message_id"]),
        "account_id": msg["account"]["account_id"],
        "account_name": msg["account"]["name"],
        "body": msg["body"],
        "send_time": dt.strftime("%Y/%m/%d %H:%M:%S"),
        "send_time_unix": unix_time,
    }


def main():
    if not CHATWORK_API_TOKEN:
        log("ERROR: CHATWORK_API_TOKEN not set")
        sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)
    output_path = os.path.join(DATA_DIR, "raw_messages.json")

    # Load existing
    existing = []
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    existing_ids = {m["message_id"] for m in existing}
    log(f"既存: {len(existing)}件")

    # Fetch new
    try:
        raw = fetch_latest()
        formatted = [format_msg(m) for m in raw]
        log(f"API取得: {len(formatted)}件")
    except Exception as e:
        log(f"API ERROR: {e}")
        sys.exit(1)

    # Merge
    new_count = 0
    for m in formatted:
        if m["message_id"] not in existing_ids:
            existing.append(m)
            existing_ids.add(m["message_id"])
            new_count += 1

    existing.sort(key=lambda x: x["send_time_unix"])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    log(f"新規追加: {new_count}件 → 合計: {len(existing)}件")

    # Backup
    backup_dir = os.path.join(DATA_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_name = f"raw_messages_{datetime.now().strftime('%Y%m%d')}.json"
    backup_path = os.path.join(backup_dir, backup_name)
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    log(f"バックアップ: {backup_path}")


if __name__ == "__main__":
    main()
