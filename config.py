import os

# Chatwork設定
CHATWORK_ROOM_ID = 268865329
# Dropbox同期フォルダ内のMCP設定からトークンを読み込む
def _load_chatwork_token():
    config_path = os.path.expanduser(
        "~/Dropbox/My PC (DESKTOP-2NB6VKP)/Desktop/_claude-global/mcp-servers/chatwork-mcp/config.json"
    )
    try:
        import json
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("CHATWORK_API_TOKEN", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return os.environ.get("CHATWORK_API_TOKEN", "")

CHATWORK_API_TOKEN = _load_chatwork_token()

# Anthropic API設定
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# メンバー定義
ROOKIES = {
    # --- 現役（入社日: HRBrain確認済み）---
    10652422: {"name": "藤田瑛二", "status": "active", "join_date": "2025-09-11"},
    10893844: {"name": "乗松一聖", "status": "active", "join_date": "2025-12-15"},
    11055607: {"name": "藤原由乃", "status": "active", "join_date": "2026-02-16"},
    # --- 独り立ち済み（入社日: HRBrain確認済み）---
    8058515: {"name": "小林直希", "status": "graduated", "join_date": "2023-04-01"},
    9206000: {"name": "白栁愛菜", "status": "graduated", "join_date": "2024-04-01"},
    # --- 退職済み（IDはテキストログ由来の仮ID）---
    78080937: {"name": "澤口誉", "status": "resigned", "join_date": ""},
    21359646: {"name": "永井将太", "status": "resigned", "join_date": ""},
    7865119: {"name": "定村菜笑", "status": "resigned", "join_date": ""},
    42784355: {"name": "倉本望", "status": "resigned", "join_date": ""},
    97839446: {"name": "髙橋七瀬", "status": "resigned", "join_date": ""},
    43802331: {"name": "野尻建", "status": "graduated", "join_date": ""},
    95826131: {"name": "山本圭亮", "status": "resigned", "join_date": ""},
    65284243: {"name": "佃竜平", "status": "resigned", "join_date": ""},
}

MANAGERS = {
    5091071: {"name": "田中康太", "role": "manager"},
    5573448: {"name": "橋本浩平", "role": "manager"},
    6828161: {"name": "寺田結音", "role": "manager"},
    5573504: {"name": "大峰佑月", "role": "manager"},
    7753480: {"name": "三山大智", "role": "manager"},
    9205998: {"name": "市川高裕", "role": "manager"},
}

# ステータス定義
STATUS_ACTIVE = "active"
STATUS_GRADUATED = "graduated"
STATUS_RESIGNED = "resigned"

# アラート閾値
ALERT_SENTIMENT_THRESHOLD = -0.3
ALERT_ACHIEVEMENT_DECLINE_DAYS = 3
ALERT_MISSING_REPORT_DAYS = 2
ALERT_KEYWORDS = ["辛い", "辞めたい", "限界", "しんどい", "退職", "辞める", "きつい", "つらい"]

# スキルカテゴリ
SKILL_CATEGORIES = ["接客", "ヒアリング", "提案", "クロージング", "知識", "報連相"]

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
