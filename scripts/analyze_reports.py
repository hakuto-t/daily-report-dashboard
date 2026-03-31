"""
parsed_reports.json を読み込み、Claude APIで4種類の分析を実行し、
data/analysis_results.json に保存する。

分析内容:
1. 日次センチメント分析（Haiku）
2. 週次サマリー（Haiku）
3. 個人プロファイル + マイルストーン抽出（Sonnet）
4. アラート検知（ルールベース + AI補助）
"""

import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

# プロジェクトルートをパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import (
    ALERT_ACHIEVEMENT_DECLINE_DAYS,
    ALERT_KEYWORDS,
    ALERT_MISSING_REPORT_DAYS,
    ALERT_SENTIMENT_THRESHOLD,
    ANTHROPIC_API_KEY,
    DATA_DIR,
    ROOKIES,
    SKILL_CATEGORIES,
)

# モデル設定
MODEL_HAIKU = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-6"

# APIモード判定
USE_API = bool(ANTHROPIC_API_KEY) and Anthropic is not None
if USE_API:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None
    print("[INFO] ANTHROPIC_API_KEY 未設定またはSDK未インストール → ルールベース分析モードで実行")

# API呼び出し間隔（秒）
API_SLEEP = 0.5


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def load_json(filepath: str) -> any:
    """JSONファイルを読み込む。存在しなければNoneを返す。"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath: str, data: any) -> None:
    """JSONファイルに保存する。"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def iso_week(date_str: str) -> str:
    """日付文字列からISO週番号を返す（例: '2026-W13'）。"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    iso_cal = dt.isocalendar()
    return f"{iso_cal[0]}-W{iso_cal[1]:02d}"


def is_business_day(date_str: str) -> bool:
    """営業日かどうかを判定する（土日を除外。祝日は簡易判定）。"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.weekday() < 5  # 月〜金


def call_api(model: str, system_prompt: str, user_prompt: str) -> dict | None:
    """Claude APIを呼び出し、JSONレスポンスを返す。"""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text
        # JSONをパース
        return json.loads(text)
    except json.JSONDecodeError:
        # JSON部分だけ抽出を試みる
        text = response.content[0].text
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        print(f"  [警告] JSONパース失敗: {text[:200]}")
        return None
    except Exception as e:
        print(f"  [エラー] API呼び出し失敗: {e}")
        return None


# ---------------------------------------------------------------------------
# 1. 日次センチメント分析
# ---------------------------------------------------------------------------

DAILY_SYSTEM_PROMPT = """\
あなたは営業組織の新人育成を支援するコンディション分析AIです。
営業新人の日報テキストを分析し、書き手のコンディション（メンタル、モチベーション、エネルギー）を数値化してください。

テキストの表面的なポジティブ表現だけでなく、行間の疲労感や無理している感じも読み取ってください。

必ず以下のJSON形式で回答してください（他のテキストは不要）:
{
  "sentiment_score": <-1.0〜+1.0の小数。ネガティブ〜ポジティブ>,
  "energy_level": <1〜5の整数。低〜高>,
  "emotion_label": "<前向き|不安|疲労|充実|焦り|成長実感|停滞感 等>",
  "brief_note": "<1行の要約コメント>"
}"""


def analyze_daily_sentiment_rulebased(report: dict) -> dict:
    """ルールベースでセンチメント分析を行う（API不要）。"""
    text = (report.get("full_text") or "") + (report.get("goal_and_achievement") or "") + (report.get("learning") or "")
    achievement = report.get("achievement_rate")

    # --- キーワードスコアリング ---
    positive_words = ["成長", "学べ", "達成", "合格", "できた", "嬉しい", "楽しい", "充実",
                      "成功", "自信", "頑張", "良い", "いい", "ナイス", "素晴", "実感",
                      "理解でき", "把握でき", "身につ", "感謝", "ありがとう", "100％", "100%"]
    negative_words = ["できなかった", "不合格", "失敗", "不安", "辛い", "つらい", "しんどい",
                      "難しい", "課題", "反省", "焦り", "緊張", "ミス", "苦手", "0％", "0%",
                      "達成度合いは０", "達成度：0", "できていない", "合格できな"]
    fatigue_words = ["疲", "眠", "体調", "休み", "限界", "きつい"]

    pos_count = sum(1 for w in positive_words if w in text)
    neg_count = sum(1 for w in negative_words if w in text)
    fat_count = sum(1 for w in fatigue_words if w in text)

    # ベーススコア（-1.0〜+1.0）
    word_score = (pos_count - neg_count * 1.5 - fat_count * 1.2) / max(pos_count + neg_count + fat_count, 1)
    word_score = max(-1.0, min(1.0, word_score * 0.6))

    # 達成率による補正
    if achievement is not None:
        if achievement >= 80:
            word_score += 0.2
        elif achievement >= 50:
            word_score += 0.05
        elif achievement >= 20:
            word_score -= 0.1
        else:
            word_score -= 0.3

    sentiment_score = max(-1.0, min(1.0, round(word_score, 2)))

    # エネルギーレベル
    energy = 3
    if sentiment_score > 0.3:
        energy = 4
    if sentiment_score > 0.6:
        energy = 5
    if sentiment_score < -0.1:
        energy = 2
    if sentiment_score < -0.4:
        energy = 1

    # 感情ラベル
    if fat_count >= 2:
        label = "疲労"
    elif sentiment_score >= 0.4:
        label = "充実" if pos_count >= 3 else "前向き"
    elif sentiment_score >= 0.1:
        label = "成長実感" if "学" in text or "成長" in text else "安定"
    elif sentiment_score >= -0.2:
        label = "焦り" if "焦" in text else "普通"
    elif sentiment_score >= -0.5:
        label = "不安" if neg_count > pos_count else "停滞感"
    else:
        label = "不安"

    # 要約コメント
    if achievement is not None:
        note = f"達成率{achievement}%。"
    else:
        note = ""
    if pos_count > neg_count:
        note += "前向きな取り組みが見られる。"
    elif neg_count > pos_count:
        note += "課題意識が強く、やや苦戦気味。"
    else:
        note += "淡々と取り組んでいる。"

    return {
        "sentiment_score": sentiment_score,
        "energy_level": energy,
        "emotion_label": label,
        "brief_note": note,
    }


def analyze_daily_sentiment(report: dict) -> dict | None:
    """1件の日報に対してセンチメント分析を実行する。"""
    if not USE_API:
        return analyze_daily_sentiment_rulebased(report)

    user_prompt = f"""以下の営業新人の日報を分析してください。

【名前】{report['name']}
【日付】{report['date']}
【目標と達成度】{report.get('goal_and_achievement', '記載なし')}
【達成率】{report.get('achievement_rate', '不明')}%
【今日学んだこと】{report.get('learning', '記載なし')}
【明日の目標】{report.get('tomorrow_plan', '記載なし')}

【日報全文】
{report.get('full_text', '記載なし')}"""

    result = call_api(MODEL_HAIKU, DAILY_SYSTEM_PROMPT, user_prompt)
    if result:
        # 値の範囲を正規化
        result["sentiment_score"] = max(-1.0, min(1.0, float(result.get("sentiment_score", 0))))
        result["energy_level"] = max(1, min(5, int(result.get("energy_level", 3))))
    return result


# ---------------------------------------------------------------------------
# 2. 週次サマリー
# ---------------------------------------------------------------------------

WEEKLY_SYSTEM_PROMPT = """\
あなたは営業組織の新人育成を支援する分析AIです。
1週間分の日報データをまとめて分析し、その週のトレンドと要約を生成してください。

必ず以下のJSON形式で回答してください（他のテキストは不要）:
{
  "trend": "<上昇|安定|下降|波あり>",
  "summary": "<3-4行の要約テキスト>",
  "challenges": ["課題1", "課題2", ...],
  "growth_points": ["成長点1", "成長点2", ...]
}"""


def analyze_weekly_summary_rulebased(name: str, week: str, reports: list[dict]) -> dict:
    """ルールベースで週次サマリーを生成する（API不要）。"""
    rates = [r.get("achievement_rate") for r in reports if r.get("achievement_rate") is not None]
    avg_rate = sum(rates) / len(rates) if rates else None

    # トレンド判定
    if len(rates) >= 2:
        first_half = sum(rates[: len(rates) // 2]) / max(len(rates) // 2, 1)
        second_half = sum(rates[len(rates) // 2 :]) / max(len(rates) - len(rates) // 2, 1)
        diff = second_half - first_half
        if diff > 10:
            trend = "上昇"
        elif diff < -10:
            trend = "下降"
        elif abs(diff) <= 5:
            trend = "安定"
        else:
            trend = "波あり"
    else:
        trend = "安定"

    summary = f"{name}の{week}の日報{len(reports)}件。"
    if avg_rate is not None:
        summary += f"平均達成率{avg_rate:.0f}%。"
    summary += f"トレンド: {trend}。"

    return {
        "trend": trend,
        "summary": summary,
        "challenges": [],
        "growth_points": [],
    }


def analyze_weekly_summary(name: str, week: str, reports: list[dict]) -> dict | None:
    """1週間分の日報から週次サマリーを生成する。"""
    if not USE_API:
        return analyze_weekly_summary_rulebased(name, week, reports)

    reports_text = ""
    for r in sorted(reports, key=lambda x: x["date"]):
        reports_text += f"\n--- {r['date']} ---\n"
        reports_text += f"達成率: {r.get('achievement_rate', '不明')}%\n"
        reports_text += f"目標と達成: {r.get('goal_and_achievement', '記載なし')}\n"
        reports_text += f"学び: {r.get('learning', '記載なし')}\n"
        reports_text += f"明日の目標: {r.get('tomorrow_plan', '記載なし')}\n"

    user_prompt = f"""以下は {name} さんの {week} の日報データです。1週間のトレンドを分析してください。

{reports_text}"""

    return call_api(MODEL_HAIKU, WEEKLY_SYSTEM_PROMPT, user_prompt)


# ---------------------------------------------------------------------------
# 3. 個人プロファイル + マイルストーン抽出
# ---------------------------------------------------------------------------

PROFILE_SYSTEM_PROMPT = """\
あなたは営業組織の新人育成を支援するプロファイリングAIです。
このツールはマネージャー専用です。本人は一切見ません。
したがって、遠慮や配慮は不要です。良い部分は良い、悪い部分は悪いと、フェアかつストレートに評価してください。
マネージャーが「この人をどうマネジメントすべきか」を判断するために必要な情報を全て出してください。

メンバーの全日報データを分析し、以下を生成してください。

必ず以下のJSON形式で回答してください（他のテキストは不要）:
{
  "personality_traits": ["特性1", "特性2", ...],
  "personality_summary": "<この人はどういう人間か。性格、思考パターン、行動傾向を2-3文で。忖度不要>",
  "sales_aptitude": "<営業適性についての率直な評価。向いている点・向いていない点を具体的に。1-2文>",
  "sales_aptitude_score": <1-5の数値。1=営業に不向き、3=普通、5=天性の営業マン>,
  "emotional_stability": "<感情の浮き沈みの傾向。安定型か波型か。どういう時に落ちるか>",
  "emotional_stability_score": <1-5。1=非常に不安定、3=普通、5=非常に安定>,
  "strengths": ["強み1（具体的エピソード付き）", "強み2", ...],
  "weaknesses": ["弱点1（具体的に。改善見込みも）", "弱点2", ...],
  "challenges": ["現在の課題1", "課題2", ...],
  "risk_factors": ["マネジメント上の注意点やリスク。例:叱責に弱い、放置すると腐る、調子に乗りやすい等"],
  "retention_risk": "<退職リスク評価。低/中/高 + 根拠>",
  "retention_risk_score": <1-5。1=辞めなさそう、5=危険信号あり>,
  "growth_speed": "<成長スピードの評価。速い/普通/遅い + 何が伸びていて何が停滞しているか>",
  "growth_speed_score": <1-5。1=遅い、3=普通、5=速い>,
  "management_style_recommendation": "<この人に最適なマネジメントスタイル。褒めて伸びるタイプか、厳しく言った方がいいか、放任でいいか等>",
  "management_dos": ["やるべきこと1", "やるべきこと2", ...],
  "management_donts": ["やってはいけないこと1", "やってはいけないこと2", ...],
  "skill_scores": {"接客": <1-5>, "ヒアリング": <1-5>, "提案": <1-5>, "クロージング": <1-5>, "知識": <1-5>, "報連相": <1-5>},
  "oneonone_topics": ["次の1on1で話すべきトピック1", "トピック2", ...],
  "training_stage": "<初期研修|基礎固め|実践デビュー|応用|独り立ち準備>",
  "training_progress_pct": <0-100>,
  "management_effort": "<この人にかかるマネジメント工数の評価。手がかかるか、放置でも育つか>",
  "management_effort_score": <1-5。1=ほぼ手がかからない、5=非常に手がかかる>,
  "growth_efficiency": "<少ない指導で大きく伸びるか、手をかけても伸びが遅いか>",
  "growth_efficiency_score": <1-5。1=手をかけても伸びない、3=相応、5=少しの指導で大きく伸びる>,
  "one_line_verdict": "<この人を一言で表すと？マネージャー目線で>",
  "milestones": [
    {"date": "YYYY-MM-DD", "label": "短いラベル", "description": "詳細説明"},
    ...
  ]
}"""


def score_skill_from_reports(reports: list[dict], category: str) -> int:
    """日報テキストからカテゴリ別のスキルスコア(1-5)をキーワード出現頻度で推定。"""
    SKILL_KEYWORDS = {
        "接客": ["接客", "お客様", "お客さま", "来店", "来客", "対応", "笑顔", "身だしなみ", "挨拶", "マナー"],
        "ヒアリング": ["ヒアリング", "聞き取り", "ニーズ", "要望", "深掘り", "質問", "傾聴", "聞く", "確認"],
        "提案": ["提案", "プレゼン", "説明", "紹介", "おすすめ", "プラン", "見積", "資料", "商品説明"],
        "クロージング": ["クロージング", "契約", "成約", "受注", "申込", "決定", "クローズ", "成果", "売上"],
        "知識": ["知識", "勉強", "学習", "資格", "試験", "テスト", "合格", "暗記", "理解", "覚え"],
        "報連相": ["報告", "連絡", "相談", "報連相", "共有", "フィードバック", "日報", "振り返り", "反省"],
    }
    keywords = SKILL_KEYWORDS.get(category, [])
    if not keywords or not reports:
        return 2

    total_hits = 0
    for r in reports:
        text = (r.get("full_text") or "") + (r.get("goal_and_achievement") or "") + (r.get("learning") or "")
        total_hits += sum(1 for kw in keywords if kw in text)

    avg_hits = total_hits / len(reports)
    # avg_hits → score: 0-0.3=1, 0.3-0.8=2, 0.8-1.5=3, 1.5-2.5=4, 2.5+=5
    if avg_hits >= 2.5:
        return 5
    elif avg_hits >= 1.5:
        return 4
    elif avg_hits >= 0.8:
        return 3
    elif avg_hits >= 0.3:
        return 2
    else:
        return 1


def analyze_profile_rulebased(name: str, account_id: int, reports: list[dict]) -> dict:
    """ルールベースでプロファイルを生成する（API不要）。"""
    status = ROOKIES.get(account_id, {}).get("status", "unknown")
    rates = [r.get("achievement_rate") for r in reports if r.get("achievement_rate") is not None]
    avg_rate = sum(rates) / len(rates) if rates else 0
    dates = sorted(r["date"] for r in reports)
    report_count = len(reports)

    # カテゴリ別スキルスコア（日報テキストのキーワード出現頻度ベース）
    skill_scores = {cat: score_skill_from_reports(reports, cat) for cat in SKILL_CATEGORIES}
    base_skill = min(5, max(1, round(avg_rate / 25)))

    return {
        "personality_traits": [],
        "personality_summary": f"日報{report_count}件の分析（ルールベース）。平均達成率{avg_rate:.0f}%。",
        "sales_aptitude": "API未使用のためルールベース分析。詳細はAPI有効化後に生成。",
        "sales_aptitude_score": base_skill,
        "emotional_stability": "",
        "emotional_stability_score": 3,
        "strengths": [],
        "weaknesses": [],
        "challenges": [],
        "risk_factors": [],
        "retention_risk": f"{'高（退職済み）' if status == 'resigned' else '低' if status == 'graduated' else '不明'}",
        "retention_risk_score": 5 if status == "resigned" else 1 if status == "graduated" else 3,
        "growth_speed": "",
        "growth_speed_score": 3,
        "management_style_recommendation": "",
        "management_dos": [],
        "management_donts": [],
        "skill_scores": skill_scores,
        "oneonone_topics": [],
        "training_stage": "独り立ち準備" if status == "graduated" else "基礎固め",
        "training_progress_pct": 100 if status == "graduated" else 50,
        "management_effort": "",
        "management_effort_score": 3,
        "growth_efficiency": "",
        "growth_efficiency_score": 3,
        "one_line_verdict": f"{'独り立ち済み' if status == 'graduated' else '退職済み' if status == 'resigned' else '分析中'}（日報{report_count}件, 平均達成率{avg_rate:.0f}%）",
        "milestones": [],
    }


def analyze_profile(name: str, account_id: int, reports: list[dict]) -> dict | None:
    """メンバーの全日報からプロファイルを生成する。"""
    if not USE_API:
        return analyze_profile_rulebased(name, account_id, reports)

    join_date = ROOKIES.get(account_id, {}).get("join_date", "不明")
    skill_cats = ", ".join(SKILL_CATEGORIES)

    # 日報が多い場合は要約して送る（トークン節約）
    reports_text = ""
    for r in sorted(reports, key=lambda x: x["date"]):
        reports_text += f"\n--- {r['date']} (達成率: {r.get('achievement_rate', '不明')}%) ---\n"
        reports_text += f"{r.get('full_text', r.get('goal_and_achievement', '記載なし'))}\n"

    # テキストが長すぎる場合は切り詰め（約30000文字まで）
    if len(reports_text) > 30000:
        reports_text = reports_text[:30000] + "\n\n...（以降省略）"

    user_prompt = f"""以下は {name} さん（入社日: {join_date}）の全日報データです。
スキルカテゴリ: {skill_cats}
日報件数: {len(reports)}件

マネージャーがこの人をマネジメントするために必要な情報を全て出してください。
- 忖度不要。良い点は良い、悪い点は悪いとストレートに
- 日報の文章の書き方、内容の具体性、振り返りの深さ、感情の波、成長の軌跡から人間性を読み取ること
- 「この人は営業に向いているか」「どう扱えばいいか」「何に注意すべきか」を明確に
- スキルスコアは甘くつけない。実際の実力を反映すること
- マイルストーンも日報の内容から具体的に抽出すること
- 強みと弱みに矛盾する項目を書かないこと。もし同じ領域が強みでも弱みでもある場合は、なぜ両立するのか具体的に説明を書くこと（例:「聞く力はあるが自分から発信する力が弱い」など、同じ「コミュニケーション」でも別の側面であることを明記）

{reports_text}"""

    return call_api(MODEL_SONNET, PROFILE_SYSTEM_PROMPT, user_prompt)


# ---------------------------------------------------------------------------
# 4. アラート検知
# ---------------------------------------------------------------------------

AI_CONCERN_SYSTEM_PROMPT = """\
あなたは営業新人のメンタルヘルスを見守るAIです。
直近の日報データを確認し、「要注意」かどうかを判断してください。

必ず以下のJSON形式で回答してください（他のテキストは不要）:
{
  "is_concern": <true|false>,
  "reason": "<要注意と判断した理由、もしくは問題なしの場合は空文字>",
  "severity": "<critical|warning|info>"
}"""


def detect_alerts(
    account_id: int,
    name: str,
    reports: list[dict],
    daily_analyses: list[dict],
) -> list[dict]:
    """ルールベース + AI補助でアラートを検知する。"""
    alerts = []

    # --- ルールベース ---

    # 1. sentiment_drop: 直近3日のsentiment平均が閾値以下
    if len(daily_analyses) >= 3:
        recent_3 = sorted(daily_analyses, key=lambda x: x["date"])[-3:]
        avg_sentiment = sum(d["sentiment_score"] for d in recent_3) / 3
        if avg_sentiment <= ALERT_SENTIMENT_THRESHOLD:
            alerts.append({
                "type": "sentiment_drop",
                "date": recent_3[-1]["date"],
                "message": f"直近3日のセンチメント平均が{avg_sentiment:.2f}（閾値: {ALERT_SENTIMENT_THRESHOLD}）",
                "severity": "warning",
            })

    # 2. achievement_decline: 達成度がN日連続低下
    sorted_reports = sorted(reports, key=lambda x: x["date"])
    if len(sorted_reports) >= ALERT_ACHIEVEMENT_DECLINE_DAYS:
        recent_n = sorted_reports[-ALERT_ACHIEVEMENT_DECLINE_DAYS:]
        rates = [r.get("achievement_rate") for r in recent_n if r.get("achievement_rate") is not None]
        if len(rates) == ALERT_ACHIEVEMENT_DECLINE_DAYS:
            declining = all(rates[i] > rates[i + 1] for i in range(len(rates) - 1))
            if declining:
                alerts.append({
                    "type": "achievement_decline",
                    "date": recent_n[-1]["date"],
                    "message": f"達成度が{ALERT_ACHIEVEMENT_DECLINE_DAYS}日連続低下: {' → '.join(str(r) for r in rates)}",
                    "severity": "warning",
                })

    # 3. missing_report: 営業日で2日以上未提出
    if sorted_reports:
        report_dates = {r["date"] for r in sorted_reports}
        last_date = datetime.strptime(sorted_reports[-1]["date"], "%Y-%m-%d")
        today = datetime.now()
        check_end = min(last_date + timedelta(days=14), today)

        missing_dates = []
        current = last_date + timedelta(days=1)
        while current <= check_end:
            date_str = current.strftime("%Y-%m-%d")
            if is_business_day(date_str) and date_str not in report_dates:
                missing_dates.append(date_str)
            current += timedelta(days=1)

        if len(missing_dates) >= ALERT_MISSING_REPORT_DAYS:
            alerts.append({
                "type": "missing_report",
                "date": missing_dates[-1],
                "message": f"営業日で{len(missing_dates)}日間未提出: {', '.join(missing_dates[:5])}",
                "severity": "warning" if len(missing_dates) < 4 else "critical",
            })

    # 4. keyword_alert: 特定キーワードマッチ
    for r in sorted_reports:
        text = (r.get("full_text") or "") + (r.get("goal_and_achievement") or "") + (r.get("learning") or "")
        matched = [kw for kw in ALERT_KEYWORDS if kw in text]
        if matched:
            alerts.append({
                "type": "keyword_alert",
                "date": r["date"],
                "message": f"注意キーワード検出: {', '.join(matched)}",
                "severity": "critical" if any(kw in ["辞めたい", "退職", "辞める", "限界"] for kw in matched) else "warning",
            })

    # 5. ai_concern: AIが要注意と判断（API利用時のみ）
    if USE_API and len(sorted_reports) >= 3:
        recent_reports = sorted_reports[-5:]  # 直近5件
        reports_text = ""
        for r in recent_reports:
            reports_text += f"\n--- {r['date']} ---\n"
            reports_text += f"{r.get('full_text', r.get('goal_and_achievement', '記載なし'))}\n"

        user_prompt = f"""以下は {name} さんの直近の日報です。メンタル面で要注意かどうか判断してください。

{reports_text}"""

        time.sleep(API_SLEEP)
        result = call_api(MODEL_HAIKU, AI_CONCERN_SYSTEM_PROMPT, user_prompt)
        if result and result.get("is_concern"):
            alerts.append({
                "type": "ai_concern",
                "date": sorted_reports[-1]["date"],
                "message": result.get("reason", "AIが要注意と判断"),
                "severity": result.get("severity", "warning"),
            })

    return alerts


# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------

def group_reports_by_member(reports: list[dict]) -> dict[int, list[dict]]:
    """日報データをメンバーごとにグルーピングする。"""
    grouped = defaultdict(list)
    for r in reports:
        grouped[r["account_id"]].append(r)
    return dict(grouped)


def group_reports_by_week(reports: list[dict]) -> dict[str, list[dict]]:
    """日報データを週ごとにグルーピングする。"""
    grouped = defaultdict(list)
    for r in reports:
        week = iso_week(r["date"])
        grouped[week].append(r)
    return dict(grouped)


def get_existing_daily_dates(existing_results: dict, account_id: int) -> set[str]:
    """既存の分析結果から、分析済みの日付セットを取得する。"""
    member_key = str(account_id)
    if not existing_results or "members" not in existing_results:
        return set()
    member = existing_results.get("members", {}).get(member_key, {})
    return {d["date"] for d in member.get("daily_analysis", [])}


def get_existing_weeks(existing_results: dict, account_id: int) -> set[str]:
    """既存の分析結果から、分析済みの週セットを取得する。"""
    member_key = str(account_id)
    if not existing_results or "members" not in existing_results:
        return set()
    member = existing_results.get("members", {}).get(member_key, {})
    return {w["week"] for w in member.get("weekly_summaries", [])}


def main():
    # 入力データ読み込み
    parsed_path = os.path.join(DATA_DIR, "parsed_reports.json")
    reports = load_json(parsed_path)

    if not reports:
        print("parsed_reports.json が空または存在しません。スキップします。")
        return

    print(f"日報データ読み込み完了: {len(reports)} 件")

    # 既存の分析結果を読み込み（差分分析用）
    results_path = os.path.join(DATA_DIR, "analysis_results.json")
    existing_results = load_json(results_path)

    # 結果格納用（既存があればベースにする）
    if existing_results and "members" in existing_results:
        results = existing_results
    else:
        results = {"generated_at": None, "members": {}}

    # メンバーごとにグルーピング
    grouped = group_reports_by_member(reports)

    for account_id, member_reports in grouped.items():
        # ROOKIESに含まれるメンバーのみ分析
        if account_id not in ROOKIES:
            continue

        member_info = ROOKIES[account_id]
        name = member_info["name"]
        member_key = str(account_id)

        print(f"\n{'='*50}")
        print(f"分析開始: {name} ({account_id})")
        print(f"{'='*50}")

        # メンバーのエントリを初期化
        if member_key not in results["members"]:
            results["members"][member_key] = {
                "name": name,
                "status": member_info["status"],
                "daily_analysis": [],
                "weekly_summaries": [],
                "profile": {},
                "alerts": [],
                "milestones": [],
            }

        member_result = results["members"][member_key]
        member_result["name"] = name
        member_result["status"] = member_info["status"]

        # ---------------------------------------------------------------
        # 1. 日次センチメント分析（差分のみ）
        # ---------------------------------------------------------------
        existing_dates = get_existing_daily_dates(existing_results, account_id)
        new_reports = [r for r in member_reports if r["date"] not in existing_dates]

        if new_reports:
            print(f"\n  [日次分析] 新規 {len(new_reports)} 件を分析中...")
            for r in sorted(new_reports, key=lambda x: x["date"]):
                print(f"    {r['date']}...", end=" ")
                result = analyze_daily_sentiment(r)
                time.sleep(API_SLEEP)

                if result:
                    daily_entry = {
                        "date": r["date"],
                        "sentiment_score": result["sentiment_score"],
                        "energy_level": result["energy_level"],
                        "emotion_label": result.get("emotion_label", "不明"),
                        "brief_note": result.get("brief_note", ""),
                        "achievement_rate": r.get("achievement_rate"),
                    }
                    member_result["daily_analysis"].append(daily_entry)
                    print(f"OK (sentiment: {result['sentiment_score']:.2f})")
                else:
                    print("SKIP（API失敗）")

            # 日付順にソート
            member_result["daily_analysis"].sort(key=lambda x: x["date"])
        else:
            print(f"\n  [日次分析] 新規日報なし、スキップ")

        # ---------------------------------------------------------------
        # 2. 週次サマリー（差分のみ）
        # ---------------------------------------------------------------
        weekly_grouped = group_reports_by_week(member_reports)
        existing_weeks = get_existing_weeks(existing_results, account_id)

        # 新規の週だけ分析（ただし現在進行中の週も再分析）
        current_week = iso_week(datetime.now().strftime("%Y-%m-%d"))
        new_weeks = {w for w in weekly_grouped if w not in existing_weeks or w == current_week}

        if new_weeks:
            print(f"\n  [週次分析] {len(new_weeks)} 週分を分析中...")
            # 現在週を再分析する場合、既存の週次サマリーからその週を除外
            member_result["weekly_summaries"] = [
                ws for ws in member_result["weekly_summaries"]
                if ws["week"] not in new_weeks
            ]

            for week in sorted(new_weeks):
                week_reports = weekly_grouped[week]
                print(f"    {week} ({len(week_reports)}件)...", end=" ")
                result = analyze_weekly_summary(name, week, week_reports)
                time.sleep(API_SLEEP)

                if result:
                    weekly_entry = {
                        "week": week,
                        "trend": result.get("trend", "不明"),
                        "summary": result.get("summary", ""),
                        "challenges": result.get("challenges", []),
                        "growth_points": result.get("growth_points", []),
                    }
                    member_result["weekly_summaries"].append(weekly_entry)
                    print(f"OK (trend: {result.get('trend', '不明')})")
                else:
                    print("SKIP（API失敗）")

            # 週順にソート
            member_result["weekly_summaries"].sort(key=lambda x: x["week"])
        else:
            print(f"\n  [週次分析] 新規週なし、スキップ")

        # ---------------------------------------------------------------
        # 3. 個人プロファイル（毎回再生成）
        # ---------------------------------------------------------------
        print(f"\n  [プロファイル分析] 全日報からプロファイル生成中...")
        profile_result = analyze_profile(name, account_id, member_reports)
        time.sleep(API_SLEEP)

        if profile_result:
            # マイルストーンを分離して保存
            milestones = profile_result.pop("milestones", [])
            member_result["profile"] = {
                "personality_traits": profile_result.get("personality_traits", []),
                "personality_summary": profile_result.get("personality_summary", ""),
                "sales_aptitude": profile_result.get("sales_aptitude", ""),
                "sales_aptitude_score": profile_result.get("sales_aptitude_score", 3),
                "emotional_stability": profile_result.get("emotional_stability", ""),
                "emotional_stability_score": profile_result.get("emotional_stability_score", 3),
                "strengths": profile_result.get("strengths", []),
                "weaknesses": profile_result.get("weaknesses", []),
                "challenges": profile_result.get("challenges", []),
                "risk_factors": profile_result.get("risk_factors", []),
                "retention_risk": profile_result.get("retention_risk", ""),
                "retention_risk_score": profile_result.get("retention_risk_score", 1),
                "growth_speed": profile_result.get("growth_speed", ""),
                "growth_speed_score": profile_result.get("growth_speed_score", 3),
                "management_style_recommendation": profile_result.get("management_style_recommendation", ""),
                "management_dos": profile_result.get("management_dos", []),
                "management_donts": profile_result.get("management_donts", []),
                "skill_scores": profile_result.get("skill_scores", {}),
                "oneonone_topics": profile_result.get("oneonone_topics", []),
                "training_stage": profile_result.get("training_stage", "基礎固め"),
                "training_progress_pct": profile_result.get("training_progress_pct", 0),
                "management_effort": profile_result.get("management_effort", ""),
                "management_effort_score": profile_result.get("management_effort_score", 3),
                "growth_efficiency": profile_result.get("growth_efficiency", ""),
                "growth_efficiency_score": profile_result.get("growth_efficiency_score", 3),
                "one_line_verdict": profile_result.get("one_line_verdict", ""),
            }
            member_result["milestones"] = milestones
            print(f"    OK (stage: {member_result['profile']['training_stage']})")
        else:
            print("    SKIP（API失敗）")

        # ---------------------------------------------------------------
        # 4. アラート検知
        # ---------------------------------------------------------------
        print(f"\n  [アラート検知] ルールベース + AI判定中...")
        alerts = detect_alerts(
            account_id,
            name,
            member_reports,
            member_result["daily_analysis"],
        )
        member_result["alerts"] = alerts
        if alerts:
            for a in alerts:
                severity_mark = "🔴" if a["severity"] == "critical" else "🟡"
                print(f"    {severity_mark} [{a['type']}] {a['message']}")
        else:
            print("    アラートなし")

    # タイムスタンプ更新
    results["generated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # 保存
    save_json(results_path, results)
    print(f"\n{'='*50}")
    print(f"分析結果を保存しました: {results_path}")
    print(f"生成日時: {results['generated_at']}")
    print(f"メンバー数: {len(results['members'])}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
