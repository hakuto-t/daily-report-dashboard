"""
data/raw_messages.json を読み込み、ルーキーの日報のみをパースして
data/parsed_reports.json に保存する。
"""

import json
import os
import re
import sys
from datetime import datetime

# プロジェクトルートをパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import DATA_DIR, ROOKIES


def is_daily_report(body: str) -> bool:
    """日報メッセージかどうかを判定する。"""
    # 返信メッセージはスキップ
    if re.match(r"\[rp\s+aid=", body.strip()):
        return False
    # [toall] を含み、かつ [info][title] を含むものが日報
    return "[toall]" in body and "[info][title]" in body


def extract_section(body: str, keyword: str) -> str | None:
    """
    [info][title]...keyword...[/title] と [/info] の間のテキストを抽出する。
    部分一致で検索。
    """
    pattern = (
        r"\[info\]\[title\][^\[]*"
        + re.escape(keyword)
        + r"[^\[]*\[/title\](.*?)\[/info\]"
    )
    match = re.search(pattern, body, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def extract_achievement_rate(text: str | None) -> int | None:
    """達成度のパーセンテージを抽出する。"""
    if text is None:
        return None
    match = re.search(r"達成度[：:]\s*(\d+)\s*[%％]", text)
    if match:
        return int(match.group(1))
    return None


def extract_date_from_send_time(send_time: str) -> str:
    """send_time (YYYY/M/D H:M:S) から YYYY-MM-DD 形式の日付を抽出する。"""
    dt = datetime.strptime(send_time, "%Y/%m/%d %H:%M:%S")
    return dt.strftime("%Y-%m-%d")


def parse_report(msg: dict) -> dict | None:
    """1件のメッセージをパースして日報レコードを返す。日報でなければNone。"""
    account_id = msg["account_id"]

    # ルーキーのメッセージのみ対象
    if account_id not in ROOKIES:
        return None

    body = msg["body"]

    if not is_daily_report(body):
        return None

    # セクション抽出（部分一致キーワード）
    goal_section = extract_section(body, "今日の目標")
    if goal_section is None:
        goal_section = extract_section(body, "目標")
    if goal_section is None:
        goal_section = extract_section(body, "達成度")

    learning_section = extract_section(body, "学んだこと")

    tomorrow_section = extract_section(body, "明日の目標")
    if tomorrow_section is None:
        tomorrow_section = extract_section(body, "明日")

    achievement_rate = extract_achievement_rate(goal_section)

    return {
        "message_id": msg["message_id"],
        "account_id": account_id,
        "name": ROOKIES[account_id]["name"],
        "date": extract_date_from_send_time(msg["send_time"]),
        "goal_and_achievement": goal_section,
        "achievement_rate": achievement_rate,
        "learning": learning_section,
        "tomorrow_plan": tomorrow_section,
        "full_text": body,
    }


def deduplicate_by_person_date(reports: list[dict]) -> list[dict]:
    """同一人物の同日複数投稿は最後のものを採用する。"""
    seen = {}
    for report in reports:
        key = (report["account_id"], report["date"])
        seen[key] = report  # 後のものが上書き
    return list(seen.values())


def main():
    input_path = os.path.join(DATA_DIR, "raw_messages.json")

    if not os.path.exists(input_path):
        print(f"エラー: {input_path} が見つかりません。")
        print("先に fetch_reports.py を実行してください。")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        raw_messages = json.load(f)

    print(f"raw_messages.json: {len(raw_messages)} 件読み込み")

    # パース
    parsed = []
    for msg in raw_messages:
        report = parse_report(msg)
        if report is not None:
            parsed.append(report)

    print(f"  日報として認識: {len(parsed)} 件")

    # 同一人物・同日の重複排除
    deduplicated = deduplicate_by_person_date(parsed)
    print(f"  重複排除後: {len(deduplicated)} 件")

    # 日付昇順でソート
    deduplicated.sort(key=lambda r: (r["date"], r["name"]))

    # 保存
    output_path = os.path.join(DATA_DIR, "parsed_reports.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(deduplicated, f, ensure_ascii=False, indent=2)

    print(f"保存完了: {output_path}")

    # サマリー表示
    names = set(r["name"] for r in deduplicated)
    dates = set(r["date"] for r in deduplicated)
    print(f"  対象者: {', '.join(sorted(names))}")
    print(f"  日付範囲: {min(dates) if dates else 'N/A'} ~ {max(dates) if dates else 'N/A'}")


if __name__ == "__main__":
    main()
