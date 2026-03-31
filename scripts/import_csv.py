"""
Chatworkエクスポート CSV をインポートして raw_messages.json に追加する。

使い方:
  python scripts/import_csv.py <CSVファイルパス>

Chatwork管理画面 → エクスポート → メッセージ でCSVをダウンロードし、
このスクリプトで読み込む。

CSVの想定カラム（Chatworkエクスポート形式）:
  送信日時, 送信者アカウントID, 送信者名, メッセージ本文
  ※形式が異なる場合はカラムマッピングを調整
"""
import csv
import json
import os
import re
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import DATA_DIR


def detect_encoding(filepath):
    """BOM付きUTF-8 or Shift-JIS を判定"""
    with open(filepath, "rb") as f:
        head = f.read(3)
    if head == b"\xef\xbb\xbf":
        return "utf-8-sig"
    # Try UTF-8 first
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            f.read(1000)
        return "utf-8"
    except UnicodeDecodeError:
        return "cp932"


def parse_csv(filepath):
    """CSVファイルを読み込みメッセージリストを返す"""
    enc = detect_encoding(filepath)
    messages = []

    with open(filepath, "r", encoding=enc, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)

        if not header:
            print("ERROR: CSVが空です")
            return []

        # カラム位置を自動検出
        h_lower = [h.strip().lower() for h in header]
        dt_col = None
        id_col = None
        name_col = None
        body_col = None

        for i, h in enumerate(h_lower):
            if "日時" in h or "date" in h or "time" in h or "送信" in h:
                if dt_col is None:
                    dt_col = i
            if "アカウントid" in h or "account_id" in h or "aid" in h:
                id_col = i
            if "送信者" in h or "名前" in h or "name" in h or "アカウント名" in h:
                if name_col is None:
                    name_col = i
            if "本文" in h or "メッセージ" in h or "body" in h or "message" in h:
                body_col = i

        # Fallback: 4カラム想定
        if dt_col is None:
            dt_col = 0
        if id_col is None and len(header) >= 4:
            id_col = 1
        if name_col is None:
            name_col = id_col + 1 if id_col is not None else 1
        if body_col is None:
            body_col = len(header) - 1

        print(f"CSV encoding: {enc}")
        print(f"Columns: datetime={dt_col}, account_id={id_col}, name={name_col}, body={body_col}")
        print(f"Header: {header}")

        for row_num, row in enumerate(reader, start=2):
            if len(row) <= max(dt_col, body_col):
                continue

            dt_str = row[dt_col].strip()
            account_id = 0
            if id_col is not None and id_col < len(row):
                try:
                    account_id = int(row[id_col].strip())
                except (ValueError, IndexError):
                    pass
            account_name = row[name_col].strip() if name_col < len(row) else ""
            body = row[body_col].strip() if body_col < len(row) else ""

            if not body:
                continue

            # Parse datetime
            unix_ts = 0
            send_time = dt_str
            for fmt in [
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y/%m/%d %H:%M",
                "%Y-%m-%d %H:%M",
            ]:
                try:
                    dt = datetime.strptime(dt_str, fmt)
                    unix_ts = int(dt.timestamp())
                    send_time = dt.strftime("%Y/%m/%d %H:%M:%S")
                    break
                except ValueError:
                    continue

            # Generate a stable message_id from content if not available
            msg_id = f"csv_{unix_ts}_{account_id}_{hash(body) % 10**10}"

            messages.append({
                "message_id": msg_id,
                "account_id": account_id,
                "account_name": account_name,
                "body": body,
                "send_time": send_time,
                "send_time_unix": unix_ts,
            })

    return messages


def main():
    if len(sys.argv) < 2:
        print("使い方: python scripts/import_csv.py <CSVファイルパス>")
        print("")
        print("Chatwork管理画面からエクスポートしたCSVを指定してください。")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"ERROR: ファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print(f"CSVインポート: {csv_path}")
    csv_messages = parse_csv(csv_path)
    print(f"  CSV読み込み: {len(csv_messages)}件")

    # Load existing
    output_path = os.path.join(DATA_DIR, "raw_messages.json")
    existing = []
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # Merge by checking unix timestamp + account_id + body hash to avoid dups
    existing_keys = set()
    for m in existing:
        key = f"{m['send_time_unix']}_{m['account_id']}"
        existing_keys.add(key)

    new_count = 0
    for m in csv_messages:
        key = f"{m['send_time_unix']}_{m['account_id']}"
        if key not in existing_keys:
            existing.append(m)
            existing_keys.add(key)
            new_count += 1

    existing.sort(key=lambda x: x["send_time_unix"])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"  新規追加: {new_count}件")
    print(f"  合計: {len(existing)}件")

    if existing:
        dates = [m["send_time"][:10] for m in existing]
        print(f"  期間: {dates[0]} ~ {dates[-1]}")

    print(f"  保存先: {output_path}")


if __name__ == "__main__":
    main()
