"""
テキスト形式の過去チャットログを raw_messages.json にインポートする。

Chatwork Web UIからコピー&ペーストしたテキストログを解析し、
raw_messages.json に追加する。既存データとの重複は自動排除。

使い方:
  python scripts/import_text_log.py [テキストファイルパス]
  ※省略時は「過去のチャット日報ログ.txt」を読み込む
"""
import json
import os
import re
import sys
from datetime import datetime
from hashlib import md5

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import DATA_DIR, MANAGERS, ROOKIES

# --- 正規表現 ---

# タイムスタンプ: YYYY年M月D日（DOW） HH:MM  (年は省略される場合あり)
TIMESTAMP_RE = re.compile(
    r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日（[^）]+）\s*(\d{1,2}):(\d{2})"
)

# 日付セパレータ: YYYY年M月D日 (「（」が続かないもの = タイムスタンプではない)
DATE_SEP_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日(?!（)")

# Chatwork Web UIのクラフト文字列
UI_CRUFT_RE = re.compile(r"返信リアクション引用ブックマークタスクリンク")

# セクションマーカー 【...】
SECTION_RE = re.compile(r"【([^】]+)】")

# 返信パターン
REPLY_RE = re.compile(r"\[返信\s+aid=(\d+)\s+to=([^\]]+)\]")


def build_name_to_id():
    """config.pyのメンバー情報から名前→account_idマッピングを構築。"""
    mapping = {}
    all_members = {**ROOKIES, **MANAGERS}
    for aid, info in all_members.items():
        name = info["name"]
        mapping[name] = aid
        # スペース入りのバリエーションも登録
        for i in range(1, len(name)):
            mapping[name[:i] + " " + name[i:]] = aid
            mapping[name[:i] + "\u3000" + name[i:]] = aid
    # 表記ゆれ対応
    mapping["白柳愛菜"] = 9206000
    mapping["白柳 愛菜"] = 9206000
    mapping["白栁 愛菜"] = 9206000
    return mapping


def normalize_name(name):
    """名前の正規化（スペース除去）。"""
    return name.replace(" ", "").replace("\u3000", "").strip()


def extract_sender_and_body(text):
    """メッセージテキストから送信者名と本文を分離する。"""
    text = text.strip()
    if not text:
        return None, "", False

    # [toall] で分割
    toall_match = re.search(r"\[toall\]", text)
    # [返信 aid=...] で分割
    reply_match = REPLY_RE.search(text)

    is_reply = False

    if toall_match and (not reply_match or toall_match.start() < reply_match.start()):
        sender_part = text[: toall_match.start()].strip()
        body_part = text[toall_match.start() :]
    elif reply_match:
        sender_part = text[: reply_match.start()].strip()
        # [返信 aid=X to=Y]name → [rp aid=X to=Y]name に変換
        body_part = "[rp aid={} to={}]{}".format(
            reply_match.group(1),
            reply_match.group(2),
            text[reply_match.end() :],
        )
        is_reply = True
    else:
        # マーカーなし → 最初の行を送信者とみなす
        lines = text.split("\n", 1)
        sender_part = lines[0].strip()
        body_part = lines[1].strip() if len(lines) > 1 else ""

    # 送信者名を抽出（【、（、株式会社、[ より前の部分）
    name_match = re.match(r"([^【（(\[株\n]+)", sender_part)
    name = name_match.group(1).strip() if name_match else sender_part.strip()

    # account_name には元の表示名（メタデータ含む）を使う
    account_name = sender_part if sender_part else name

    return name, body_part, is_reply


def convert_body_to_chatwork_format(body):
    """【セクション名】形式を [info][title]...[/title]...[/info] 形式に変換。"""
    if "[info]" in body:
        return body  # 既にChatwork形式

    sections = SECTION_RE.split(body)
    if len(sections) <= 1:
        return body  # セクションマーカーなし

    # [toall] を先頭に確保
    has_toall = "[toall]" in body
    prefix = sections[0].strip()
    if has_toall:
        prefix = prefix.replace("[toall]", "").strip()

    result_parts = []
    if has_toall:
        result_parts.append("[toall]")
    if prefix:
        result_parts.append(prefix)

    for i in range(1, len(sections), 2):
        title = sections[i]
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        result_parts.append(f"[info][title]{title}[/title]{content}[/info]")

    return "\n".join(result_parts)


def clean_trailing_numbers(text):
    """末尾のリアクション数等の余計な数字を除去。"""
    # 末尾の1〜4桁の数字（文末の句読点・括弧の後）を除去
    return re.sub(r"[\s]*\d{1,4}\s*$", "", text)


def main():
    # ファイルパス
    if len(sys.argv) >= 2:
        log_path = sys.argv[1]
    else:
        log_path = os.path.join(PROJECT_ROOT, "過去のチャット日報ログ.txt")

    if not os.path.exists(log_path):
        print(f"ERROR: ファイルが見つかりません: {log_path}")
        sys.exit(1)

    print(f"テキストログ読み込み: {log_path}")
    with open(log_path, "r", encoding="utf-8") as f:
        text = f.read()

    print(f"  ファイルサイズ: {len(text):,} bytes / {text.count(chr(10)):,} lines")

    name_map = build_name_to_id()

    # --- タイムスタンプ検出 ---
    ts_matches = list(TIMESTAMP_RE.finditer(text))
    print(f"  タイムスタンプ検出: {len(ts_matches)} 件")

    # 年推定用の日付セパレータ一覧
    date_seps = []
    for m in DATE_SEP_RE.finditer(text):
        # タイムスタンプの一部として既に含まれているものを除外
        is_part_of_timestamp = False
        for ts in ts_matches:
            if ts.start() <= m.start() <= ts.end():
                is_part_of_timestamp = True
                break
        if not is_part_of_timestamp:
            date_seps.append((m.start(), int(m.group(1))))

    def get_year_for_position(pos, ts_year_group):
        """タイムスタンプに年がない場合、直近の日付セパレータから年を推定。"""
        if ts_year_group:
            return int(ts_year_group)
        year = 2023  # デフォルト
        for sep_pos, sep_year in date_seps:
            if sep_pos < pos:
                year = sep_year
            else:
                break
        return year

    # --- メッセージ分割 ---
    messages = []
    skipped = 0

    for i, ts_match in enumerate(ts_matches):
        # このタイムスタンプの前にあるテキスト = メッセージ内容
        if i == 0:
            content = text[: ts_match.start()]
        else:
            content = text[ts_matches[i - 1].end() : ts_match.start()]

        # UIクラフト・日付セパレータを除去
        content = UI_CRUFT_RE.sub("", content)
        content = DATE_SEP_RE.sub("", content)
        content = content.strip()

        if not content:
            skipped += 1
            continue

        # 末尾の余計な数字を除去
        content = clean_trailing_numbers(content)

        # --- タイムスタンプ解析 ---
        year = get_year_for_position(ts_match.start(), ts_match.group(1))
        month = int(ts_match.group(2))
        day = int(ts_match.group(3))
        hour = int(ts_match.group(4))
        minute = int(ts_match.group(5))

        try:
            dt = datetime(year, month, day, hour, minute)
        except ValueError:
            skipped += 1
            continue

        unix_ts = int(dt.timestamp())
        send_time = dt.strftime("%Y/%m/%d %H:%M:%S")

        # --- 送信者・本文の分離 ---
        sender_name, body, is_reply = extract_sender_and_body(content)

        if not body.strip():
            skipped += 1
            continue

        # 本文をChatwork互換形式に変換（返信以外）
        if not is_reply:
            body = convert_body_to_chatwork_format(body)

        # --- account_id マッピング ---
        account_id = 0
        if sender_name:
            norm = normalize_name(sender_name)
            for name, aid in name_map.items():
                if norm == normalize_name(name):
                    account_id = aid
                    break
            if account_id == 0:
                # 未知の名前 → ハッシュから安定的に生成
                account_id = int(md5(norm.encode()).hexdigest()[:8], 16) % 10**8

        account_name = sender_name or "unknown"

        msg_id = f"textlog_{unix_ts}_{account_id}_{abs(hash(body)) % 10**8}"

        messages.append(
            {
                "message_id": msg_id,
                "account_id": account_id,
                "account_name": account_name,
                "body": body,
                "send_time": send_time,
                "send_time_unix": unix_ts,
            }
        )

    print(f"  パース成功: {len(messages)} 件 (スキップ: {skipped} 件)")

    # --- 名前別の件数 ---
    name_counts = {}
    for m in messages:
        n = m["account_name"]
        name_counts[n] = name_counts.get(n, 0) + 1
    print("\n  送信者別件数:")
    for name, count in sorted(name_counts.items(), key=lambda x: -x[1]):
        print(f"    {name}: {count} 件")

    # --- 既存データとマージ ---
    output_path = os.path.join(DATA_DIR, "raw_messages.json")
    existing = []
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    print(f"\n  既存 raw_messages.json: {len(existing)} 件")

    # 重複排除: send_time_unix + account_id
    existing_keys = set()
    for m in existing:
        existing_keys.add(f"{m['send_time_unix']}_{m['account_id']}")

    new_count = 0
    for m in messages:
        key = f"{m['send_time_unix']}_{m['account_id']}"
        if key not in existing_keys:
            existing.append(m)
            existing_keys.add(key)
            new_count += 1

    existing.sort(key=lambda x: x["send_time_unix"])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"  新規追加: {new_count} 件")
    print(f"  合計: {len(existing)} 件")

    if existing:
        dates = [m["send_time"][:10] for m in existing]
        print(f"  期間: {dates[0]} ~ {dates[-1]}")

    print(f"\n  保存先: {output_path}")


if __name__ == "__main__":
    main()
