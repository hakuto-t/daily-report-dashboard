@echo off
REM 新人日報コンディション見える化アプリ - 自動更新パイプライン
REM Chatwork取得 → パース → ダッシュボード再生成
REM (AI分析はAPIキー設定時のみ実行)

cd /d "%~dp0"
echo [%date% %time%] Pipeline start >> auto_collect.log

py scripts\fetch_reports.py >> auto_collect.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] FAILED: fetch_reports >> auto_collect.log
    exit /b 1
)

py scripts\parse_reports.py >> auto_collect.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] FAILED: parse_reports >> auto_collect.log
    exit /b 1
)

py scripts\generate_dashboard.py >> auto_collect.log 2>&1

echo [%date% %time%] Pipeline complete >> auto_collect.log
