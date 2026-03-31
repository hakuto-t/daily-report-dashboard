#!/usr/bin/env python3
"""
新人日報コンディション見える化ダッシュボード生成スクリプト

data/analysis_results.json を読み込み、単一の index.html を生成する。
CSS/JS はすべてインライン。Chart.js は CDN 読み込み。
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config


def load_data():
    """analysis_results.json と member_profiles.json を読み込む"""
    analysis_path = os.path.join(config.DATA_DIR, 'analysis_results.json')
    profiles_path = os.path.join(config.DATA_DIR, 'member_profiles.json')

    with open(analysis_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    profiles = {}
    if os.path.exists(profiles_path):
        with open(profiles_path, 'r', encoding='utf-8') as f:
            profiles = json.load(f)

    # プロフィール情報をanalysisにマージ（join_date, status, graduated_date等）
    for mid, member in analysis.get('members', {}).items():
        if mid in profiles:
            p = profiles[mid]
            if 'join_date' not in member:
                member['join_date'] = p.get('join_date', '')
            member['status'] = p.get('status', member.get('status', 'active'))
            if 'graduated_date' in p:
                member['graduated_date'] = p['graduated_date']
            if 'resigned_date' in p:
                member['resigned_date'] = p['resigned_date']

    return analysis


def generate_html(data):
    """HTMLテンプレート文字列にデータを埋め込んで返す"""

    html_template = r'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>新人コンディションダッシュボード</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --primary: #2563eb;
  --primary-light: #eff6ff;
  --primary-dark: #1e40af;
  --success: #059669;
  --success-light: #ecfdf5;
  --warning: #d97706;
  --warning-light: #fffbeb;
  --danger: #dc2626;
  --danger-light: #fef2f2;
  --bg: #f1f5f9;
  --card: #ffffff;
  --text: #0f172a;
  --subtext: #64748b;
  --border: #e2e8f0;
  --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
  --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.04);
  --radius: 10px;
  --radius-lg: 16px;
}

body {
  font-family: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

/* Header */
.header {
  background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
  color: #fff;
  padding: 18px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header h1 {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.3px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.header h1::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 22px;
  background: #60a5fa;
  border-radius: 2px;
}
.header-sub {
  font-size: 12px;
  opacity: 0.6;
  font-weight: 400;
}

/* Tab Navigation */
.tab-nav {
  display: flex;
  background: var(--card);
  border-bottom: 1px solid var(--border);
  padding: 0 32px;
  gap: 0;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.tab-btn {
  padding: 14px 28px;
  font-size: 13px;
  font-weight: 600;
  color: var(--subtext);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
  margin-bottom: -1px;
  letter-spacing: 0.3px;
}
.tab-btn:hover {
  color: var(--text);
}
.tab-btn.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 700;
}

/* Main content */
.main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px 32px 60px;
}
.tab-content { display: none; }
.tab-content.active { display: block; }

/* KPI Cards */
.kpi-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.kpi-card {
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: 22px 24px;
  box-shadow: var(--shadow);
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.2s;
  border: 1px solid var(--border);
}
.kpi-card:hover { box-shadow: var(--shadow-md); border-color: #cbd5e1; }
.kpi-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.kpi-icon.blue { background: var(--primary-light); color: var(--primary); }
.kpi-icon.green { background: var(--success-light); color: var(--success); }
.kpi-icon.yellow { background: var(--warning-light); color: var(--warning); }
.kpi-icon.red { background: var(--danger-light); color: var(--danger); }
.kpi-info { flex: 1; }
.kpi-label { font-size: 11px; color: var(--subtext); font-weight: 600; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-value { font-size: 26px; font-weight: 700; line-height: 1.1; }
.kpi-sub { font-size: 11px; color: var(--subtext); margin-top: 4px; }

/* Gauge */
.gauge-container { display: inline-flex; align-items: center; gap: 8px; }
.gauge-bar {
  width: 60px; height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
  display: inline-block;
  vertical-align: middle;
}
.gauge-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }

/* Alert Panel */
.alert-panel {
  margin-bottom: 24px;
}
.alert-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.alert-toggle-read {
  font-size: 12px;
  color: var(--subtext);
  cursor: pointer;
  user-select: none;
  padding: 4px 10px;
  border-radius: var(--radius);
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}
.alert-toggle-read:hover { background: #e2e8f0; }
.alert-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius);
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  position: relative;
}
.alert-item.danger {
  background: var(--danger-light);
  color: #991b1b;
  border-left: 4px solid var(--danger);
}
.alert-item.warning {
  background: var(--warning-light);
  color: #92400e;
  border-left: 4px solid var(--warning);
}
.alert-item.read {
  opacity: 0.4;
  display: none;
}
.alert-item.read.show-read {
  display: flex;
}
.alert-icon { font-size: 18px; flex-shrink: 0; }
.alert-read-btn {
  margin-left: auto;
  font-size: 11px;
  color: var(--subtext);
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  background: #fff;
  white-space: nowrap;
  flex-shrink: 0;
}
.alert-read-btn:hover { background: #f1f5f9; }

/* Section title */
.section-title {
  font-size: 15px;
  font-weight: 700;
  margin: 28px 0 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text);
  letter-spacing: 0.2px;
}
.section-title .icon { font-size: 18px; }

/* Member Cards Grid */
.member-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.member-card {
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow);
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid var(--border);
}
.member-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-3px);
  border-color: var(--primary);
}
.member-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.member-name {
  font-size: 16px;
  font-weight: 700;
}
.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}
.status-active { background: var(--success-light); color: var(--success); }
.status-graduated { background: var(--primary-light); color: var(--primary); }
.status-resigned { background: #f1f5f9; color: #94a3b8; }

.status-filter {
  display: flex;
  gap: 4px;
}
.status-filter-btn {
  display: flex;
  align-items: center;
  padding: 6px 14px;
  font-size: 13px;
  font-family: inherit;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: var(--card);
  color: var(--subtext);
  cursor: pointer;
  transition: all 0.15s;
}
.status-filter-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.status-filter-btn.active {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.member-card.status-dimmed {
  opacity: 0.5;
  filter: grayscale(0.4);
}
.member-card.status-dimmed:hover {
  opacity: 0.75;
  filter: grayscale(0.1);
}

.member-card-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}
.member-stat {
  flex: 1;
}
.member-stat-label {
  font-size: 11px;
  color: var(--subtext);
  margin-bottom: 2px;
}
.member-stat-value {
  font-size: 20px;
  font-weight: 700;
}
.trend-up { color: var(--success); }
.trend-down { color: var(--danger); }
.trend-flat { color: var(--subtext); }

.member-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.training-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  background: #f0f9ff;
  color: #0369a1;
}
.sparkline-container {
  width: 100px;
  height: 32px;
}

/* Chart containers */
.chart-section {
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow);
  margin-bottom: 20px;
  border: 1px solid var(--border);
}
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.chart-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}
.period-filter {
  display: flex;
  gap: 3px;
}
.period-btn {
  padding: 5px 12px;
  font-size: 11px;
  border: 1px solid var(--border);
  background: var(--card);
  border-radius: 6px;
  cursor: pointer;
  font-family: inherit;
  color: var(--subtext);
  font-weight: 500;
  transition: all 0.15s;
}
.period-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.period-btn.active {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.chart-wrapper {
  position: relative;
  height: 300px;
}
.chart-wrapper-radar {
  position: relative;
  height: 400px;
  max-width: 600px;
  margin: 0 auto;
}

/* ===== Individual View ===== */
.member-selector {
  margin-bottom: 24px;
}
.member-selector select {
  display: none;
}
.member-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.member-tag {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  border: 2px solid var(--border);
  border-radius: 20px;
  background: var(--card);
  color: var(--text);
  cursor: pointer;
  transition: all 0.15s;
}
.member-tag:hover { border-color: var(--primary); background: var(--primary-light); }
.member-tag.active { border-color: var(--primary); background: var(--primary); color: #fff; }
.member-tag.status-graduated { opacity: 0.6; }
.member-tag.status-graduated.active { opacity: 1; background: var(--primary); }
.member-tag.status-resigned { opacity: 0.4; }
.member-tag.status-resigned.active { opacity: 1; background: #94a3b8; border-color: #94a3b8; }
.member-tag-separator {
  width: 100%;
  font-size: 11px;
  color: var(--subtext);
  padding: 4px 0 0;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}
.member-tag-separator:hover { color: var(--text); }
.member-tag-group { display: flex; flex-wrap: wrap; gap: 8px; }
.member-tag-group.collapsed { display: none; }

/* Profile Header */
.profile-header {
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: 28px;
  box-shadow: var(--shadow);
  margin-bottom: 20px;
  border: 1px solid var(--border);
}
.profile-top {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.profile-avatar {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(37,99,235,0.25);
}
.profile-info { flex: 1; }
.profile-name {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.profile-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 13px;
  color: var(--subtext);
}
.profile-meta span { display: flex; align-items: center; gap: 4px; }

.trait-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.trait-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  background: #ede9fe;
  color: #6d28d9;
}

.progress-bar-container {
  margin-top: 16px;
}
.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 6px;
}
.progress-bar {
  width: 100%;
  height: 10px;
  background: var(--border);
  border-radius: 5px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 5px;
  background: linear-gradient(90deg, var(--primary), #60a5fa);
  transition: width 0.5s;
}

/* Two column layout */
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

/* Three column cards */
.three-col {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.info-card {
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow);
}
.info-card h3 {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.info-card ul {
  list-style: none;
  padding: 0;
}
.info-card li {
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 4px;
}
.info-card.strengths li { background: var(--success-light); color: #166534; }
.info-card.challenges li { background: var(--warning-light); color: #92400e; }
.info-card.recommendation {
  border-left: 4px solid var(--primary);
}
.info-card.recommendation p {
  font-size: 13px;
  line-height: 1.8;
}

/* 1on1 Sheet */
.oneonone-sheet {
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow);
  margin-bottom: 24px;
  border: 2px dashed var(--primary-light);
}
.oneonone-sheet h3 {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 16px;
  color: var(--primary);
}
.oneonone-topics {
  list-style: none;
  padding: 0;
}
.oneonone-topics li {
  padding: 8px 12px;
  border-left: 3px solid var(--primary);
  margin-bottom: 8px;
  font-size: 14px;
  background: var(--primary-light);
  border-radius: 0 6px 6px 0;
}
.print-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  font-size: 13px;
  font-family: inherit;
  font-weight: 500;
  cursor: pointer;
  margin-top: 12px;
  transition: background 0.15s;
}
.print-btn:hover { background: var(--primary-dark); }

/* Timeline */
.timeline {
  position: relative;
  padding-left: 32px;
  margin-bottom: 24px;
}
.timeline::before {
  content: '';
  position: absolute;
  left: 12px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--border);
}
.timeline-item {
  position: relative;
  margin-bottom: 20px;
}
.timeline-dot {
  position: absolute;
  left: -27px;
  top: 4px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--primary);
  border: 3px solid var(--primary-light);
}
.timeline-date {
  font-size: 12px;
  color: var(--subtext);
  font-weight: 500;
  margin-bottom: 2px;
}
.timeline-label {
  font-size: 14px;
  font-weight: 700;
}
.timeline-desc {
  font-size: 13px;
  color: var(--subtext);
  margin-top: 2px;
}

/* Heatmap */
.heatmap-container {
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow);
  margin-bottom: 20px;
  overflow-x: auto;
  border: 1px solid var(--border);
}
.heatmap-grid {
  display: flex;
  gap: 3px;
  flex-wrap: wrap;
}
.heatmap-cell {
  width: 13px;
  height: 13px;
  border-radius: 3px;
  background: #ebedf0;
}
.heatmap-cell.level-0 { background: #f0f0f0; }
.heatmap-cell.level-1 { background: #bbdefb; }
.heatmap-cell.level-2 { background: #64b5f6; }
.heatmap-cell.level-3 { background: #2196f3; }
.heatmap-cell.level-4 { background: #1565c0; }
.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--subtext);
}
.heatmap-month-labels {
  display: flex;
  gap: 3px;
  margin-bottom: 4px;
  font-size: 10px;
  color: var(--subtext);
}
.heatmap-weeks {
  display: flex;
  gap: 3px;
}
.heatmap-week {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

/* Accordion */
.accordion {
  background: var(--card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  margin-bottom: 8px;
  overflow: hidden;
}
.accordion-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.15s;
  user-select: none;
}
.accordion-header:hover {
  background: #f8fafc;
}
.accordion-arrow {
  transition: transform 0.2s;
  font-size: 12px;
  color: var(--subtext);
}
.accordion.open .accordion-arrow {
  transform: rotate(180deg);
}
.accordion-body {
  display: none;
  padding: 0 20px 16px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text);
}
.accordion.open .accordion-body {
  display: block;
}
.accordion-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.accordion-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.accordion-tag.trend-up-tag { background: var(--success-light); color: var(--success); }
.accordion-tag.trend-down-tag { background: var(--danger-light); color: var(--danger); }
.accordion-tag.trend-flat-tag { background: #f1f5f9; color: var(--subtext); }

/* Sentiment badge */
.sentiment-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
}
.sentiment-pos { background: var(--success-light); color: var(--success); }
.sentiment-neu { background: var(--warning-light); color: var(--warning); }
.sentiment-neg { background: var(--danger-light); color: var(--danger); }

/* Footer */
.footer {
  text-align: center;
  padding: 32px 24px;
  font-size: 11px;
  color: #94a3b8;
  letter-spacing: 0.3px;
  border-top: 1px solid var(--border);
  margin-top: 40px;
}

/* Responsive */
@media (max-width: 1024px) {
  .kpi-bar { grid-template-columns: repeat(2, 1fr); }
  .three-col { grid-template-columns: 1fr; }
  .two-col { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .kpi-bar { grid-template-columns: 1fr; }
  .main { padding: 16px; }
  .header { padding: 12px 16px; }
  .tab-nav { padding: 0 16px; }
  .tab-btn { padding: 10px 16px; font-size: 13px; }
  .member-grid { grid-template-columns: 1fr; }
}

/* Print */
@media print {
  body * { visibility: hidden; }
  .oneonone-sheet, .oneonone-sheet * { visibility: visible; }
  .oneonone-sheet {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    border: none;
    box-shadow: none;
    padding: 20px;
  }
  .print-btn { display: none; }
}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>新人コンディションダッシュボード</h1>
    <div class="header-sub">Rookie Condition Dashboard</div>
  </div>
  <div class="header-sub" id="header-updated"></div>
</div>

<div class="tab-nav">
  <button class="tab-btn active" data-tab="team" onclick="switchTab('team')">チーム全体</button>
  <button class="tab-btn" data-tab="member" onclick="switchTab('member')">個人詳細</button>
</div>

<div class="main">
  <!-- ===== TAB 1: Team View ===== -->
  <div class="tab-content active" id="tab-team">

    <!-- KPI Summary -->
    <div class="kpi-bar" id="kpi-bar"></div>

    <!-- Alert Panel -->
    <div class="alert-header">
      <span></span>
      <span class="alert-toggle-read" id="alert-toggle-read" onclick="toggleShowRead()">既読も表示</span>
    </div>
    <div class="alert-panel" id="alert-panel"></div>

    <!-- Member Cards -->
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:8px;">
      <div class="section-title" style="margin-bottom:0;"><span class="icon">&#128101;</span> メンバー一覧</div>
      <div class="status-filter" id="status-filter">
        <button class="status-filter-btn" data-filter="all" onclick="filterByStatus('all')">全員</button>
        <button class="status-filter-btn active" data-filter="active" onclick="filterByStatus('active')">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--success);margin-right:4px;"></span>Active
        </button>
        <button class="status-filter-btn" data-filter="graduated" onclick="filterByStatus('graduated')">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--primary);margin-right:4px;"></span>卒業
        </button>
        <button class="status-filter-btn" data-filter="resigned" onclick="filterByStatus('resigned')">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#94a3b8;margin-right:4px;"></span>退職
        </button>
      </div>
    </div>
    <div class="member-grid" id="member-grid"></div>

    <!-- Condition Chart -->
    <div class="section-title"><span class="icon">&#128200;</span> 全員コンディション推移</div>
    <div class="chart-section">
      <div class="chart-header">
        <div class="chart-title">センチメントスコア推移</div>
        <div class="period-filter">
          <button class="period-btn" onclick="setConditionPeriod('1w', this)">1週間</button>
          <button class="period-btn active" onclick="setConditionPeriod('1m', this)">1ヶ月</button>
          <button class="period-btn" onclick="setConditionPeriod('all', this)">全期間</button>
        </div>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;align-items:center;">
        <span style="font-size:12px;color:var(--subtext);font-weight:500;">表示:</span>
        <label style="font-size:13px;color:var(--subtext);display:flex;align-items:center;gap:4px;">
          <input type="checkbox" id="ma-toggle-raw" checked onchange="updateConditionChart()"> 日次データ
        </label>
        <label style="font-size:13px;color:var(--subtext);display:flex;align-items:center;gap:4px;">
          <input type="checkbox" id="ma-toggle-trend" onchange="updateConditionChart()"> トレンドライン
        </label>
        <label style="font-size:13px;color:var(--subtext);display:flex;align-items:center;gap:4px;">
          <input type="checkbox" id="ma-toggle-1m" onchange="updateConditionChart()"> 1M移動平均
        </label>
        <label style="font-size:13px;color:var(--subtext);display:flex;align-items:center;gap:4px;">
          <input type="checkbox" id="ma-toggle-3m" onchange="updateConditionChart()"> 3M移動平均
        </label>
      </div>
      <div class="chart-wrapper"><canvas id="chart-condition"></canvas></div>
    </div>

    <!-- Achievement Chart -->
    <div class="section-title"><span class="icon">&#127942;</span> 全員達成度推移</div>
    <div class="chart-section">
      <div class="chart-header">
        <div class="chart-title">達成度 (%) 推移</div>
        <div class="period-filter">
          <button class="period-btn" onclick="setAchievementPeriod('1w', this)">1週間</button>
          <button class="period-btn active" onclick="setAchievementPeriod('1m', this)">1ヶ月</button>
          <button class="period-btn" onclick="setAchievementPeriod('all', this)">全期間</button>
        </div>
      </div>
      <div class="chart-wrapper"><canvas id="chart-achievement"></canvas></div>
    </div>

    <!-- Team Radar -->
    <div class="section-title"><span class="icon">&#128302;</span> チーム比較レーダーチャート</div>
    <div class="chart-section">
      <div class="chart-header">
        <div class="chart-title">スキルスコア比較</div>
      </div>
      <div class="chart-wrapper-radar"><canvas id="chart-team-radar"></canvas></div>
    </div>

  </div>

  <!-- ===== TAB 2: Individual View ===== -->
  <div class="tab-content" id="tab-member">

    <div class="member-selector">
      <select id="member-select" onchange="renderMemberDetail(this.value)"></select>
      <div class="member-tags" id="member-tags"></div>
    </div>

    <div id="member-detail"></div>
  </div>

</div>

<div class="footer" id="footer"></div>

<script>
const DASHBOARD_DATA = __DASHBOARD_DATA__;

// ===== Utilities =====
const COLORS = ['#2563eb','#16a34a','#f59e0b','#dc2626','#8b5cf6','#06b6d4','#ec4899','#84cc16'];

function sentimentClass(s) {
  if (s > 0.3) return 'sentiment-pos';
  if (s < -0.3) return 'sentiment-neg';
  return 'sentiment-neu';
}
function sentimentColor(s) {
  if (s > 0.3) return 'var(--success)';
  if (s < -0.3) return 'var(--danger)';
  return 'var(--warning)';
}
function trendArrow(trend) {
  if (!trend) return {arrow:'&#8594;', cls:'trend-flat'};
  if (trend === '上昇') return {arrow:'&#8593;', cls:'trend-up'};
  if (trend === '下降') return {arrow:'&#8595;', cls:'trend-down'};
  return {arrow:'&#8594;', cls:'trend-flat'};
}
function statusBadge(status) {
  if (status === 'graduated') return '<span class="status-badge status-graduated">卒業</span>';
  if (status === 'resigned') return '<span class="status-badge status-resigned">退職</span>';
  return '<span class="status-badge status-active">Active</span>';
}
let currentStatusFilter = 'active';
function filterByStatus(filter) {
  currentStatusFilter = filter;
  document.querySelectorAll('.status-filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === filter);
  });
  document.querySelectorAll('.member-card').forEach(card => {
    const st = card.dataset.status;
    if (filter === 'all') {
      card.style.display = '';
    } else {
      card.style.display = (st === filter) ? '' : 'none';
    }
  });
}
function daysBetween(d1, d2) {
  return Math.floor((new Date(d2) - new Date(d1)) / 86400000);
}
function formatDate(d) {
  if (!d) return '';
  const parts = d.split('-');
  return parts[1] + '/' + parts[2];
}
function filterByPeriod(dates, period) {
  if (period === 'all' || !dates.length) return dates;
  const latest = new Date(dates[dates.length - 1]);
  let cutoff;
  if (period === '1w') { cutoff = new Date(latest); cutoff.setDate(cutoff.getDate() - 7); }
  else { cutoff = new Date(latest); cutoff.setDate(cutoff.getDate() - 30); }
  return dates.filter(d => new Date(d) >= cutoff);
}

// ===== Data helpers =====
const members = DASHBOARD_DATA.members || {};
const memberIds = Object.keys(members);

function getMemberLatest(mid) {
  const m = members[mid];
  const daily = m.daily_analysis || [];
  if (!daily.length) return {sentiment: 0, achievement: 0, energy: 0, emotion: '', date: ''};
  const last = daily[daily.length - 1];
  return {
    sentiment: last.sentiment_score || 0,
    achievement: last.achievement_rate || 0,
    energy: last.energy_level || 0,
    emotion: last.emotion_label || '',
    date: last.date || ''
  };
}

function getMemberTrend(mid) {
  const ws = (members[mid].weekly_summaries || []);
  if (!ws.length) return '';
  return ws[ws.length - 1].trend || '';
}

// ===== Tab switching =====
function switchTab(tabName) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  const tabEl = document.getElementById('tab-' + tabName);
  if (tabEl) tabEl.classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(el => {
    if (el.dataset.tab === tabName) el.classList.add('active');
  });
  if (tabName === 'member') {
    const sel = document.getElementById('member-select');
    if (sel.value) renderMemberDetail(sel.value);
  }
  history.replaceState(null, '', '#' + tabName + (tabName === 'member' ? '-' + document.getElementById('member-select').value : ''));
}

// ===== Render KPI =====
function renderKPI() {
  const activeCount = memberIds.filter(id => members[id].status === 'active').length;
  let totalSentiment = 0, totalAchievement = 0, sentimentCount = 0, achievementCount = 0;
  let alertCount = 0;
  const readAlerts = getReadAlerts();
  memberIds.forEach(id => {
    const m = members[id];
    if (m.status !== 'active') return;
    const latest = getMemberLatest(id);
    if (latest.date) { totalSentiment += latest.sentiment; sentimentCount++; }
    if (latest.date && latest.achievement !== undefined) { totalAchievement += latest.achievement; achievementCount++; }
    (m.alerts || []).forEach(a => {
      if (!isRecentAlert(a.date, 7)) return;
      if (!readAlerts[alertKey(id, a)]) alertCount++;
    });
  });
  const avgSentiment = sentimentCount ? (totalSentiment / sentimentCount) : 0;
  const avgAchievement = achievementCount ? (totalAchievement / achievementCount) : 0;
  const gaugePercent = ((avgSentiment + 1) / 2 * 100).toFixed(0);
  const gaugeColor = avgSentiment > 0.3 ? 'var(--success)' : (avgSentiment < -0.3 ? 'var(--danger)' : 'var(--warning)');

  document.getElementById('kpi-bar').innerHTML = `
    <div class="kpi-card">
      <div class="kpi-icon blue">&#128100;</div>
      <div class="kpi-info">
        <div class="kpi-label">アクティブメンバー</div>
        <div class="kpi-value">${activeCount}<span style="font-size:14px;font-weight:400;color:var(--subtext)"> / ${memberIds.length}名</span></div>
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-icon green">&#128578;</div>
      <div class="kpi-info">
        <div class="kpi-label">平均コンディション</div>
        <div class="kpi-value gauge-container">
          ${avgSentiment.toFixed(2)}
          <div class="gauge-bar"><div class="gauge-fill" style="width:${gaugePercent}%;background:${gaugeColor}"></div></div>
        </div>
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-icon yellow">&#127919;</div>
      <div class="kpi-info">
        <div class="kpi-label">平均達成度</div>
        <div class="kpi-value">${avgAchievement.toFixed(0)}<span style="font-size:16px">%</span></div>
      </div>
    </div>
    <div class="kpi-card">
      <div class="kpi-icon red">&#9888;</div>
      <div class="kpi-info">
        <div class="kpi-label">アラート</div>
        <div class="kpi-value">${alertCount}<span style="font-size:14px;font-weight:400;color:var(--subtext)"> 件</span></div>
      </div>
    </div>
  `;
}

// ===== Alert Read State (localStorage) =====
const ALERT_READ_KEY = 'dashboardAlertRead';
let showReadAlerts = false;

function getReadAlerts() {
  try { return JSON.parse(localStorage.getItem(ALERT_READ_KEY) || '{}'); } catch { return {}; }
}
function setAlertRead(alertKey) {
  const read = getReadAlerts();
  read[alertKey] = Date.now();
  localStorage.setItem(ALERT_READ_KEY, JSON.stringify(read));
  renderAlerts();
  renderKPI();
}
function toggleShowRead() {
  showReadAlerts = !showReadAlerts;
  document.getElementById('alert-toggle-read').textContent = showReadAlerts ? '既読を隠す' : '既読も表示';
  document.querySelectorAll('.alert-item.read').forEach(el => {
    el.classList.toggle('show-read', showReadAlerts);
  });
}
function alertKey(id, a) {
  return `${id}_${a.type}_${a.date}_${(a.message||'').slice(0,30)}`;
}

// ===== Render Alerts =====
function isRecentAlert(alertDate, daysBack) {
  if (!alertDate) return false;
  const now = new Date();
  const ad = new Date(alertDate);
  const diff = (now - ad) / 86400000;
  return diff <= daysBack;
}

function renderAlerts() {
  const readAlerts = getReadAlerts();
  let html = '';
  let unreadCount = 0;
  memberIds.forEach(id => {
    const m = members[id];
    if (m.status !== 'active') return;
    (m.alerts || []).forEach(a => {
      if (!isRecentAlert(a.date, 7)) return;
      const cls = a.severity === 'danger' || a.severity === 'critical' ? 'danger' : 'warning';
      const icon = cls === 'danger' ? '&#128680;' : '&#9888;&#65039;';
      const key = alertKey(id, a);
      const isRead = !!readAlerts[key];
      if (!isRead) unreadCount++;
      const readCls = isRead ? ' read' + (showReadAlerts ? ' show-read' : '') : '';
      const btnLabel = isRead ? '既読' : '既読にする';
      html += `<div class="alert-item ${cls}${readCls}"><span class="alert-icon">${icon}</span><span style="flex:1">${m.name}: ${a.message} (${formatDate(a.date)})</span><span class="alert-read-btn" onclick="event.stopPropagation();setAlertRead('${key.replace(/'/g, "\\'")}')">${btnLabel}</span></div>`;
    });
  });
  if (!html) html = '<div style="color:var(--subtext);font-size:14px;padding:12px;">直近1週間のアラートはありません</div>';
  document.getElementById('alert-panel').innerHTML = html;
  return unreadCount;
}

// ===== Render Member Cards =====
function renderMemberCards() {
  let html = '';
  memberIds.forEach((id, idx) => {
    const m = members[id];
    const latest = getMemberLatest(id);
    const trend = getMemberTrend(id);
    const t = trendArrow(trend);
    const profile = m.profile || {};
    const daily = m.daily_analysis || [];
    const recentDays = daily.slice(-7);

    // Sparkline SVG — auto-scale to actual data range for visible trend
    let sparkSvg = '';
    if (recentDays.length > 1) {
      const vals = recentDays.map(d => d.sentiment_score || 0);
      const dataMin = Math.min(...vals);
      const dataMax = Math.max(...vals);
      const range = dataMax - dataMin || 0.1;
      const minV = dataMin - range * 0.15;
      const maxV = dataMax + range * 0.15;
      const w = 100, h = 32, pad = 2;
      const points = vals.map((v, i) => {
        const x = pad + (i / (vals.length - 1)) * (w - pad * 2);
        const y = pad + (1 - (v - minV) / (maxV - minV)) * (h - pad * 2);
        return `${x},${y}`;
      }).join(' ');
      const lineColor = vals[vals.length-1] > 0.3 ? '#16a34a' : (vals[vals.length-1] < -0.3 ? '#dc2626' : '#f59e0b');
      sparkSvg = `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${points}" fill="none" stroke="${lineColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    }

    const dimmed = (m.status === 'graduated' || m.status === 'resigned') ? ' status-dimmed' : '';
    const alertCount = (m.alerts || []).length;
    const hasCritical = (m.alerts || []).some(a => a.severity === 'critical' || a.severity === 'danger');
    const dangerStyle = hasCritical ? 'border-left:4px solid var(--danger);background:linear-gradient(90deg,rgba(254,226,226,0.6) 0%,#fff 10%);' : (alertCount > 0 ? 'border-left:4px solid var(--warning);' : '');
    html += `
    <div class="member-card${dimmed}" data-status="${m.status}" style="${dangerStyle}" onclick="goToMember('${id}')">
      <div class="member-card-header">
        <span class="member-name">${m.name}</span>
        ${hasCritical ? '<span style="color:var(--danger);font-size:16px;margin-left:4px;">&#128680;</span>' : ''}
        ${statusBadge(m.status)}
      </div>
      <div class="member-card-stats">
        <div class="member-stat">
          <div class="member-stat-label">コンディション</div>
          <div class="member-stat-value" style="color:${sentimentColor(latest.sentiment)}">${latest.sentiment.toFixed(2)}</div>
        </div>
        <div class="member-stat">
          <div class="member-stat-label">達成度</div>
          <div class="member-stat-value">${latest.achievement}%</div>
        </div>
        <div class="member-stat">
          <div class="member-stat-label">トレンド</div>
          <div class="member-stat-value ${t.cls}">${t.arrow}</div>
        </div>
      </div>
      <div class="member-card-bottom">
        <span class="training-badge">${profile.training_stage || '-'}</span>
        <div class="sparkline-container">${sparkSvg}</div>
      </div>
    </div>`;
  });
  document.getElementById('member-grid').innerHTML = html;
}

function toggleTagGroup(groupId) {
  const el = document.getElementById(groupId);
  if (el) el.classList.toggle('collapsed');
}
function selectMemberTag(mid, skipRender) {
  document.getElementById('member-select').value = mid;
  document.querySelectorAll('.member-tag').forEach(t => {
    t.classList.toggle('active', t.dataset.mid === mid);
  });
  if (!skipRender) renderMemberDetail(mid);
  history.replaceState(null, '', '#member-' + mid);
}
function goToMember(mid) {
  switchTab('member');
  selectMemberTag(mid);
}

// ===== Charts (Team) =====
let conditionChart = null, achievementChart = null, teamRadarChart = null;
let conditionPeriod = '1m', achievementPeriod = '1m';

function getAllDates(statusFilter) {
  const dateSet = new Set();
  const ids = statusFilter ? memberIds.filter(id => members[id].status === statusFilter) : memberIds;
  ids.forEach(id => {
    (members[id].daily_analysis || []).forEach(d => dateSet.add(d.date));
  });
  return [...dateSet].sort();
}

// Moving average calculation
function movingAverage(data, window) {
  return data.map((val, i) => {
    if (val === null) return null;
    const start = Math.max(0, i - window + 1);
    const slice = data.slice(start, i + 1).filter(v => v !== null);
    return slice.length > 0 ? slice.reduce((a, b) => a + b, 0) / slice.length : null;
  });
}

// Auto-scale Y axis to data range with padding for visible fluctuation
function autoScale(datasets, padding) {
  let allVals = [];
  datasets.forEach(ds => { ds.data.forEach(v => { if (v !== null && v !== undefined) allVals.push(v); }); });
  if (!allVals.length) return { min: 0, max: 1 };
  const dataMin = Math.min(...allVals);
  const dataMax = Math.max(...allVals);
  const range = dataMax - dataMin || 0.1;
  const pad = range * (padding || 0.15);
  return { min: Math.floor((dataMin - pad) * 100) / 100, max: Math.ceil((dataMax + pad) * 100) / 100 };
}

// Linear regression trendline — shows clear up/down/flat direction
function trendline(data) {
  const points = [];
  data.forEach((v, i) => { if (v !== null) points.push({x: i, y: v}); });
  if (points.length < 2) return data.map(() => null);
  const n = points.length;
  const sumX = points.reduce((a, p) => a + p.x, 0);
  const sumY = points.reduce((a, p) => a + p.y, 0);
  const sumXY = points.reduce((a, p) => a + p.x * p.y, 0);
  const sumXX = points.reduce((a, p) => a + p.x * p.x, 0);
  const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;
  return data.map((v, i) => slope * i + intercept);
}

function buildTeamConditionChart(period) {
  const allDates = getAllDates('active');
  const filteredDates = filterByPeriod(allDates, period);
  const showRaw = document.getElementById('ma-toggle-raw').checked;
  const showTrend = document.getElementById('ma-toggle-trend').checked;
  const showMA1m = document.getElementById('ma-toggle-1m').checked;
  const showMA3m = document.getElementById('ma-toggle-3m').checked;

  const activeMembers = memberIds.filter(id => members[id].status === 'active');
  const datasets = [];

  activeMembers.forEach((id, i) => {
    const m = members[id];
    const dailyMap = {};
    (m.daily_analysis || []).forEach(d => { dailyMap[d.date] = d.sentiment_score; });
    const rawData = filteredDates.map(d => dailyMap[d] !== undefined ? dailyMap[d] : null);
    const color = COLORS[i % COLORS.length];

    if (showRaw) {
      datasets.push({
        label: m.name,
        data: rawData,
        borderColor: color,
        backgroundColor: color + '20',
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 6,
        spanGaps: true,
        borderWidth: 1.5,
        borderDash: []
      });
    }
    if (showTrend) {
      const trendData = trendline(rawData);
      const trendDirection = trendData.length >= 2 ? (trendData[trendData.length-1] > trendData[0] ? ' ↑' : trendData[trendData.length-1] < trendData[0] ? ' ↓' : ' →') : '';
      datasets.push({
        label: m.name + ' トレンド' + trendDirection,
        data: trendData,
        borderColor: color,
        backgroundColor: 'transparent',
        tension: 0,
        pointRadius: 0,
        spanGaps: true,
        borderWidth: 3,
        borderDash: [12, 4]
      });
    }
    if (showMA1m) {
      datasets.push({
        label: m.name + ' (1M平均)',
        data: movingAverage(rawData, 22),
        borderColor: color,
        backgroundColor: 'transparent',
        tension: 0.4,
        pointRadius: 0,
        spanGaps: true,
        borderWidth: 2.5,
        borderDash: [6, 3]
      });
    }
    if (showMA3m) {
      datasets.push({
        label: m.name + ' (3M平均)',
        data: movingAverage(rawData, 66),
        borderColor: color,
        backgroundColor: 'transparent',
        tension: 0.4,
        pointRadius: 0,
        spanGaps: true,
        borderWidth: 3.5,
        borderDash: [2, 2]
      });
    }
  });

  if (conditionChart) conditionChart.destroy();
  const condScale = autoScale(datasets, 0.2);
  conditionChart = new Chart(document.getElementById('chart-condition'), {
    type: 'line',
    data: { labels: filteredDates.map(formatDate), datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y: { min: condScale.min, max: condScale.max, grid: { color: '#e2e8f0' } }, x: { grid: { display: false } } },
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16, font: { size: 11 } } },
        tooltip: { mode: 'index', intersect: false },
        annotation: {
          annotations: {
            dangerZone: { type: 'box', yMin: condScale.min, yMax: -0.3, backgroundColor: 'rgba(220,38,38,0.08)', borderWidth: 0, label: { display: true, content: 'DANGER', position: { x: 'start', y: 'start' }, font: { size: 10, weight: 'bold' }, color: 'rgba(220,38,38,0.4)', padding: 4 } },
            warningZone: { type: 'box', yMin: -0.3, yMax: 0.3, backgroundColor: 'rgba(245,158,11,0.05)', borderWidth: 0 },
            goodZone: { type: 'box', yMin: 0.3, yMax: condScale.max, backgroundColor: 'rgba(22,163,74,0.05)', borderWidth: 0 },
            dangerLine: { type: 'line', yMin: -0.3, yMax: -0.3, borderColor: 'rgba(220,38,38,0.3)', borderWidth: 1, borderDash: [4, 4] },
            goodLine: { type: 'line', yMin: 0.3, yMax: 0.3, borderColor: 'rgba(22,163,74,0.3)', borderWidth: 1, borderDash: [4, 4] }
          }
        }
      },
      interaction: { mode: 'nearest', axis: 'x', intersect: false }
    }
  });
}

function updateConditionChart() {
  buildTeamConditionChart(conditionPeriod);
}

function buildTeamAchievementChart(period) {
  const allDates = getAllDates('active');
  const filteredDates = filterByPeriod(allDates, period);
  const activeMembers = memberIds.filter(id => members[id].status === 'active');
  const datasets = activeMembers.map((id, i) => {
    const m = members[id];
    const dailyMap = {};
    (m.daily_analysis || []).forEach(d => { dailyMap[d.date] = d.achievement_rate; });
    return {
      label: m.name,
      data: filteredDates.map(d => dailyMap[d] !== undefined ? dailyMap[d] : null),
      borderColor: COLORS[i % COLORS.length],
      backgroundColor: COLORS[i % COLORS.length] + '20',
      tension: 0.3,
      pointRadius: 3,
      pointHoverRadius: 6,
      spanGaps: true,
      borderWidth: 2
    };
  });
  if (achievementChart) achievementChart.destroy();
  const achScale = autoScale(datasets, 0.2);
  achievementChart = new Chart(document.getElementById('chart-achievement'), {
    type: 'line',
    data: { labels: filteredDates.map(formatDate), datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y: { min: achScale.min, max: achScale.max, grid: { color: '#e2e8f0' } }, x: { grid: { display: false } } },
      plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } }, tooltip: { mode: 'index', intersect: false } },
      interaction: { mode: 'nearest', axis: 'x', intersect: false }
    }
  });
}

function buildTeamRadarChart() {
  const labels = ['接客','ヒアリング','提案','クロージング','知識','報連相'];
  const activeMembers = memberIds.filter(id => members[id].status === 'active');
  const datasets = activeMembers.map((id, i) => {
    const skills = (members[id].profile || {}).skill_scores || {};
    return {
      label: members[id].name,
      data: labels.map(l => skills[l] || 0),
      borderColor: COLORS[i % COLORS.length],
      backgroundColor: COLORS[i % COLORS.length] + '20',
      pointBackgroundColor: COLORS[i % COLORS.length],
      borderWidth: 2,
      pointRadius: 3
    };
  });
  if (teamRadarChart) teamRadarChart.destroy();
  teamRadarChart = new Chart(document.getElementById('chart-team-radar'), {
    type: 'radar',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { r: { min: 0, max: 5, ticks: { stepSize: 1 }, grid: { color: '#e2e8f0' }, angleLines: { color: '#e2e8f0' } } },
      plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } } }
    }
  });
}

function setConditionPeriod(p, btn) {
  conditionPeriod = p;
  btn.parentElement.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  buildTeamConditionChart(p);
}
function setAchievementPeriod(p, btn) {
  achievementPeriod = p;
  btn.parentElement.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  buildTeamAchievementChart(p);
}

// ===== Member Detail =====
let memberCondChart = null, memberAchChart = null, memberRadarChart = null;

function renderMemberDetail(mid) {
  if (!mid || !members[mid]) return;
  try {
  const m = members[mid];
  const profile = m.profile || {};
  const daily = m.daily_analysis || [];
  const latest = getMemberLatest(mid);
  const trend = getMemberTrend(mid);
  const t = trendArrow(trend);
  const joinDate = m.join_date || '';
  const graduatedDate = m.graduated_date || '';
  const resignedDate = m.resigned_date || '';
  const endDate = graduatedDate || resignedDate || '';
  const elapsed = joinDate ? daysBetween(joinDate, endDate || new Date().toISOString().split('T')[0]) : '';

  let html = '';

  // Pre-declare verdict (used in both archive banner and manager section)
  const verdict = profile.one_line_verdict || '';

  // Archive Summary Banner (graduated / resigned)
  if (m.status === 'graduated' || m.status === 'resigned') {
    const archiveIcon = m.status === 'graduated' ? '&#127942;' : '&#128220;';
    const archiveLabel = m.status === 'graduated' ? '卒業（独り立ち済み）' : '退職';
    const archiveColor = m.status === 'graduated' ? 'var(--primary)' : '#94a3b8';
    const archiveBg = m.status === 'graduated' ? 'var(--primary-light)' : '#f1f5f9';
    const archiveReportCount = daily.length;
    const archiveRates = daily.filter(function(d){ return d.achievement_rate != null; }).map(function(d){ return d.achievement_rate; });
    const archiveAvgRate = archiveRates.length ? (archiveRates.reduce(function(a,b){ return a+b; }, 0) / archiveRates.length).toFixed(0) : '-';
    const archiveAvgSent = daily.length ? (daily.reduce(function(a,d){ return a + (d.sentiment_score||0); }, 0) / daily.length).toFixed(2) : '-';
    const archiveFirstDate = daily.length ? daily[0].date : '-';
    const archiveLastDate = daily.length ? daily[daily.length-1].date : '-';
    const archiveDuration = joinDate && endDate ? daysBetween(joinDate, endDate) : (joinDate && archiveLastDate !== '-' ? daysBetween(joinDate, archiveLastDate) : '-');
    const archiveStage = profile.training_stage || '-';
    const archiveProgress = profile.training_progress_pct || 0;

    html += '<div style="background:' + archiveBg + ';border:2px solid ' + archiveColor + ';border-radius:var(--radius-lg);padding:24px;margin-bottom:24px;">';
    html += '<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">';
    html += '<span style="font-size:28px;">' + archiveIcon + '</span>';
    html += '<span style="font-size:20px;font-weight:700;color:' + archiveColor + ';">' + m.name + ' - ' + archiveLabel + '</span>';
    html += '</div>';
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:16px;">';
    html += '<div style="background:#fff;border-radius:var(--radius);padding:12px;text-align:center;"><div style="font-size:11px;color:var(--subtext);margin-bottom:4px;">在籍期間</div><div style="font-size:18px;font-weight:700;">' + (archiveDuration !== '-' ? archiveDuration + '日' : '-') + '</div></div>';
    html += '<div style="background:#fff;border-radius:var(--radius);padding:12px;text-align:center;"><div style="font-size:11px;color:var(--subtext);margin-bottom:4px;">日報提出数</div><div style="font-size:18px;font-weight:700;">' + archiveReportCount + '件</div></div>';
    html += '<div style="background:#fff;border-radius:var(--radius);padding:12px;text-align:center;"><div style="font-size:11px;color:var(--subtext);margin-bottom:4px;">平均達成率</div><div style="font-size:18px;font-weight:700;">' + archiveAvgRate + '%</div></div>';
    html += '<div style="background:#fff;border-radius:var(--radius);padding:12px;text-align:center;"><div style="font-size:11px;color:var(--subtext);margin-bottom:4px;">平均コンディション</div><div style="font-size:18px;font-weight:700;">' + archiveAvgSent + '</div></div>';
    html += '<div style="background:#fff;border-radius:var(--radius);padding:12px;text-align:center;"><div style="font-size:11px;color:var(--subtext);margin-bottom:4px;">最終ステージ</div><div style="font-size:14px;font-weight:700;">' + archiveStage + ' (' + archiveProgress + '%)</div></div>';
    html += '<div style="background:#fff;border-radius:var(--radius);padding:12px;text-align:center;"><div style="font-size:11px;color:var(--subtext);margin-bottom:4px;">活動期間</div><div style="font-size:13px;font-weight:600;">' + archiveFirstDate + ' ~ ' + archiveLastDate + '</div></div>';
    html += '</div>';
    if (verdict) {
      html += '<div style="background:#fff;border-left:4px solid ' + archiveColor + ';padding:12px 16px;border-radius:var(--radius);font-size:15px;font-weight:600;color:var(--text);">' + verdict + '</div>';
    }
    html += '</div>';
  }

  // Profile Header
  const nameInitial = m.name ? m.name.charAt(0) : '?';
  const traits = (profile.personality_traits || []).map(tr => `<span class="trait-tag">${tr}</span>`).join('');
  const progressPct = profile.training_progress_pct || 0;

  html += `
  <div class="profile-header">
    <div class="profile-top">
      <div class="profile-avatar">${nameInitial}</div>
      <div class="profile-info">
        <div class="profile-name">${m.name} ${statusBadge(m.status)}</div>
        <div class="profile-meta">
          <span>&#127891; ${profile.training_stage || '-'}</span>
          ${joinDate ? `<span>&#128197; 入社: ${joinDate}</span>` : ''}
          ${graduatedDate ? `<span>&#127942; 卒業: ${graduatedDate}</span>` : ''}
          ${resignedDate ? `<span>退職: ${resignedDate}</span>` : ''}
          ${elapsed ? `<span>&#128336; ${endDate ? '在籍' : '経過'}${elapsed}日</span>` : ''}
        </div>
      </div>
    </div>
    ${traits ? `<div class="trait-tags">${traits}</div>` : ''}
    <div class="progress-bar-container">
      <div class="progress-label"><span>研修進捗</span><span>${progressPct}%</span></div>
      <div class="progress-bar"><div class="progress-fill" style="width:${progressPct}%"></div></div>
    </div>
  </div>`;

  // Two charts: condition + achievement
  html += `
  <div class="two-col">
    <div class="chart-section">
      <div class="chart-header">
        <div class="chart-title">コンディション推移</div>
        <div class="period-filter">
          <button class="period-btn" onclick="setMemberCondPeriod('1w','${mid}',this)">1週間</button>
          <button class="period-btn active" onclick="setMemberCondPeriod('1m','${mid}',this)">1ヶ月</button>
          <button class="period-btn" onclick="setMemberCondPeriod('all','${mid}',this)">全期間</button>
        </div>
      </div>
      <div class="chart-wrapper"><canvas id="chart-member-condition"></canvas></div>
    </div>
    <div class="chart-section">
      <div class="chart-header">
        <div class="chart-title">達成度推移</div>
        <div class="period-filter">
          <button class="period-btn" onclick="setMemberAchPeriod('1w','${mid}',this)">1週間</button>
          <button class="period-btn active" onclick="setMemberAchPeriod('1m','${mid}',this)">1ヶ月</button>
          <button class="period-btn" onclick="setMemberAchPeriod('all','${mid}',this)">全期間</button>
        </div>
      </div>
      <div class="chart-wrapper"><canvas id="chart-member-achievement"></canvas></div>
    </div>
  </div>`;

  // Skill Radar
  html += `
  <div class="chart-section">
    <div class="chart-header"><div class="chart-title">スキルレーダーチャート</div></div>
    <div class="chart-wrapper-radar"><canvas id="chart-member-radar"></canvas></div>
  </div>`;

  // --- Manager Assessment Section (active members only) ---
  if (m.status === 'active') {
  const personalitySummary = profile.personality_summary || '';
  const salesAptitude = profile.sales_aptitude || '';
  const salesAptitudeScore = profile.sales_aptitude_score || 3;
  const emotionalStability = profile.emotional_stability || '';
  const emotionalStabilityScore = profile.emotional_stability_score || 3;
  const growthSpeed = profile.growth_speed || '';
  const growthSpeedScore = profile.growth_speed_score || 3;
  const retentionRisk = profile.retention_risk || '';
  const retentionRiskScore = profile.retention_risk_score || 1;
  const mgmtEffort = profile.management_effort || '';
  const mgmtEffortScore = profile.management_effort_score || 3;
  const growthEfficiency = profile.growth_efficiency || '';
  const growthEfficiencyScore = profile.growth_efficiency_score || 3;
  const mgmtStyle = profile.management_style_recommendation || '';
  const mgmtDos = (profile.management_dos || []).map(s => `<li>${s}</li>`).join('');
  const mgmtDonts = (profile.management_donts || []).map(s => `<li>${s}</li>`).join('');
  const strengths = (profile.strengths || []).map(s => `<li>${s}</li>`).join('');
  const weaknesses = (profile.weaknesses || []).map(s => `<li>${s}</li>`).join('');
  const challenges = (profile.challenges || []).map(c => `<li>${c}</li>`).join('');
  const riskFactors = (profile.risk_factors || []).map(r => `<li>${r}</li>`).join('');

  function scoreBar(score, max, color) {
    const pct = (score / max * 100);
    return `<div style="display:flex;align-items:center;gap:8px;">
      <div style="flex:1;height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
        <div style="width:${pct}%;height:100%;background:${color};border-radius:4px;"></div>
      </div>
      <span style="font-weight:700;font-size:14px;min-width:24px;color:${color}">${score}/5</span>
    </div>`;
  }

  // Critical alert banner — retention risk + management warnings
  if (retentionRiskScore >= 4) {
    html += `
    <div style="background:linear-gradient(135deg,#fee2e2,#fecaca);border:2px solid var(--danger);border-radius:var(--radius-lg);padding:24px;margin-bottom:20px;position:relative;overflow:hidden;">
      <div style="position:absolute;top:12px;right:16px;font-size:48px;opacity:0.15;">&#128680;</div>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
        <span style="font-size:24px;">&#128680;</span>
        <span style="font-size:18px;font-weight:700;color:var(--danger);">退職リスク: ${retentionRiskScore === 5 ? '非常に高い' : '高い'}</span>
        <span style="background:var(--danger);color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:10px;">${retentionRiskScore}/5</span>
      </div>
      <p style="font-size:14px;line-height:1.7;color:var(--text);margin-bottom:16px;">${retentionRisk}</p>
      ${riskFactors ? `
      <div style="margin-top:8px;padding-top:12px;border-top:1px solid rgba(220,38,38,0.2);">
        <div style="font-size:12px;font-weight:700;color:var(--danger);margin-bottom:8px;">&#9888; マネジメント注意点</div>
        <ul style="list-style:none;display:flex;flex-direction:column;gap:4px;">${riskFactors}</ul>
      </div>` : ''}
    </div>`;
  }

  // Verdict banner
  if (verdict) {
    const verdictBg = retentionRiskScore >= 4 ? 'var(--danger-light)' : 'var(--primary-light)';
    const verdictBorder = retentionRiskScore >= 4 ? 'var(--danger)' : 'var(--primary)';
    const verdictColor = retentionRiskScore >= 4 ? 'var(--danger)' : 'var(--primary)';
    html += `<div style="background:${verdictBg};border-left:4px solid ${verdictBorder};padding:16px 20px;border-radius:var(--radius);margin-bottom:20px;">
      <div style="font-size:11px;color:${verdictColor};font-weight:700;text-transform:uppercase;margin-bottom:4px;">One-Line Verdict</div>
      <div style="font-size:16px;font-weight:700;color:var(--text);">${verdict}</div>
    </div>`;
  }

  // Personality & Assessment Scores
  html += `
  <div class="section-title"><span class="icon">&#128100;</span> 人物評価</div>
  <div style="background:var(--card);border-radius:var(--radius-lg);padding:24px;box-shadow:var(--shadow);margin-bottom:20px;">
    ${personalitySummary ? `<p style="font-size:15px;line-height:1.7;margin-bottom:20px;color:var(--text);">${personalitySummary}</p>` : ''}
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;">
      <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);">
        <div style="font-size:12px;color:var(--subtext);font-weight:500;margin-bottom:8px;">営業適性</div>
        ${scoreBar(salesAptitudeScore, 5, salesAptitudeScore >= 4 ? '#16a34a' : salesAptitudeScore >= 3 ? '#f59e0b' : '#dc2626')}
        <p style="font-size:13px;color:var(--subtext);margin-top:8px;">${salesAptitude}</p>
      </div>
      <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);">
        <div style="font-size:12px;color:var(--subtext);font-weight:500;margin-bottom:8px;">感情安定性</div>
        ${scoreBar(emotionalStabilityScore, 5, emotionalStabilityScore >= 4 ? '#16a34a' : emotionalStabilityScore >= 3 ? '#f59e0b' : '#dc2626')}
        <p style="font-size:13px;color:var(--subtext);margin-top:8px;">${emotionalStability}</p>
      </div>
      <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);">
        <div style="font-size:12px;color:var(--subtext);font-weight:500;margin-bottom:8px;">成長スピード</div>
        ${scoreBar(growthSpeedScore, 5, growthSpeedScore >= 4 ? '#16a34a' : growthSpeedScore >= 3 ? '#f59e0b' : '#dc2626')}
        <p style="font-size:13px;color:var(--subtext);margin-top:8px;">${growthSpeed}</p>
      </div>
      <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);">
        <div style="font-size:12px;color:var(--subtext);font-weight:500;margin-bottom:8px;">退職リスク</div>
        ${scoreBar(retentionRiskScore, 5, retentionRiskScore <= 2 ? '#16a34a' : retentionRiskScore <= 3 ? '#f59e0b' : '#dc2626')}
        <p style="font-size:13px;color:var(--subtext);margin-top:8px;">${retentionRisk}</p>
      </div>
      <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);">
        <div style="font-size:12px;color:var(--subtext);font-weight:500;margin-bottom:8px;">マネジメント工数</div>
        ${scoreBar(mgmtEffortScore, 5, mgmtEffortScore <= 2 ? '#16a34a' : mgmtEffortScore <= 3 ? '#f59e0b' : '#dc2626')}
        <p style="font-size:13px;color:var(--subtext);margin-top:8px;">${mgmtEffort}</p>
      </div>
      <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);">
        <div style="font-size:12px;color:var(--subtext);font-weight:500;margin-bottom:8px;">成長効率</div>
        ${scoreBar(growthEfficiencyScore, 5, growthEfficiencyScore >= 4 ? '#16a34a' : growthEfficiencyScore >= 3 ? '#f59e0b' : '#dc2626')}
        <p style="font-size:13px;color:var(--subtext);margin-top:8px;">${growthEfficiency}</p>
      </div>
    </div>
  </div>`;

  // Strengths vs Weaknesses
  html += `
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
    <div class="info-card strengths">
      <h3>&#128170; 強み</h3>
      <ul>${strengths || '<li>データなし</li>'}</ul>
    </div>
    <div class="info-card" style="background:#fff5f5;border-left:4px solid var(--danger);padding:20px;border-radius:var(--radius);">
      <h3 style="color:var(--danger);font-size:14px;font-weight:700;margin-bottom:12px;">&#9888; 弱点</h3>
      <ul style="list-style:none;display:flex;flex-direction:column;gap:6px;">${weaknesses || '<li>データなし</li>'}</ul>
    </div>
  </div>`;

  // Risk Factors & Challenges
  html += `
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
    <div class="info-card challenges">
      <h3>&#128203; 現在の課題</h3>
      <ul>${challenges || '<li>データなし</li>'}</ul>
    </div>
    <div class="info-card" style="background:#fef3c7;border-left:4px solid var(--warning);padding:20px;border-radius:var(--radius);">
      <h3 style="color:#92400e;font-size:14px;font-weight:700;margin-bottom:12px;">&#128680; マネジメント注意点</h3>
      <ul style="list-style:none;display:flex;flex-direction:column;gap:6px;">${riskFactors || '<li>データなし</li>'}</ul>
    </div>
  </div>`;

  // Management Playbook
  html += `
  <div class="section-title"><span class="icon">&#128218;</span> マネジメント方針</div>
  <div style="background:var(--card);border-radius:var(--radius-lg);padding:24px;box-shadow:var(--shadow);margin-bottom:20px;">
    ${mgmtStyle ? `<p style="font-size:15px;line-height:1.7;margin-bottom:20px;padding:12px 16px;background:var(--primary-light);border-radius:var(--radius);color:var(--text);">${mgmtStyle}</p>` : ''}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
      <div>
        <h4 style="color:var(--success);font-size:13px;font-weight:700;margin-bottom:10px;">&#9989; DO（やるべき）</h4>
        <ul style="list-style:none;display:flex;flex-direction:column;gap:6px;">${mgmtDos || '<li>データなし</li>'}</ul>
      </div>
      <div>
        <h4 style="color:var(--danger);font-size:13px;font-weight:700;margin-bottom:10px;">&#10060; DON'T（やってはいけない）</h4>
        <ul style="list-style:none;display:flex;flex-direction:column;gap:6px;">${mgmtDonts || '<li>データなし</li>'}</ul>
      </div>
    </div>
  </div>`;

  // 1on1 Sheet removed per user request
  } // end if active — Manager Assessment Section

  // Milestones Timeline
  const milestones = m.milestones || [];
  if (milestones.length) {
    html += `<div class="section-title"><span class="icon">&#127942;</span> 成長マイルストーン</div><div class="timeline">`;
    milestones.forEach(ms => {
      html += `
      <div class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-date">${ms.date}</div>
        <div class="timeline-label">${ms.label}</div>
        <div class="timeline-desc">${ms.description || ''}</div>
      </div>`;
    });
    html += `</div>`;
  }

  // Heatmap
  html += `
  <div class="section-title"><span class="icon">&#128197;</span> 日報提出ヒートマップ</div>
  <div class="heatmap-container">
    <div id="heatmap-${mid}"></div>
  </div>`;

  // Weekly Summaries & Daily Timeline removed per user request

  document.getElementById('member-detail').innerHTML = html;

  // Build charts after DOM update
  setTimeout(() => {
    buildMemberConditionChart(mid, '1m');
    buildMemberAchievementChart(mid, '1m');
    buildMemberRadarChart(mid);
    buildHeatmap(mid);
  }, 50);
  } catch(e) { console.error('renderMemberDetail error:', e); }
}

function buildMemberConditionChart(mid, period) {
  const daily = members[mid].daily_analysis || [];
  const dates = daily.map(d => d.date);
  const filtered = filterByPeriod(dates, period);
  const dailyMap = {};
  daily.forEach(d => { dailyMap[d.date] = d.sentiment_score; });
  const data = filtered.map(d => dailyMap[d] !== undefined ? dailyMap[d] : null);
  const canvas = document.getElementById('chart-member-condition');
  if (!canvas) return;
  if (memberCondChart) memberCondChart.destroy();
  memberCondChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: filtered.map(formatDate),
      datasets: [{
        label: 'センチメント',
        data: data,
        borderColor: '#2563eb',
        backgroundColor: '#2563eb20',
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 7,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y: (function(){ const s = autoScale([{data}], 0.2); return { min: s.min, max: s.max, grid: { color: '#e2e8f0' } }; })(), x: { grid: { display: false } } },
      plugins: {
        legend: { display: false },
        annotation: {
          annotations: (function() {
            const s = autoScale([{data}], 0.2);
            return {
              dangerZone: { type: 'box', yMin: s.min, yMax: -0.3, backgroundColor: 'rgba(220,38,38,0.08)', borderWidth: 0 },
              warningZone: { type: 'box', yMin: -0.3, yMax: 0.3, backgroundColor: 'rgba(245,158,11,0.05)', borderWidth: 0 },
              goodZone: { type: 'box', yMin: 0.3, yMax: s.max, backgroundColor: 'rgba(22,163,74,0.05)', borderWidth: 0 },
              dangerLine: { type: 'line', yMin: -0.3, yMax: -0.3, borderColor: 'rgba(220,38,38,0.3)', borderWidth: 1, borderDash: [4, 4] },
              goodLine: { type: 'line', yMin: 0.3, yMax: 0.3, borderColor: 'rgba(22,163,74,0.3)', borderWidth: 1, borderDash: [4, 4] }
            };
          })()
        }
      }
    }
  });
}

function buildMemberAchievementChart(mid, period) {
  const daily = members[mid].daily_analysis || [];
  const dates = daily.map(d => d.date);
  const filtered = filterByPeriod(dates, period);
  const dailyMap = {};
  daily.forEach(d => { dailyMap[d.date] = d.achievement_rate; });
  const data = filtered.map(d => dailyMap[d] !== undefined ? dailyMap[d] : null);
  const canvas = document.getElementById('chart-member-achievement');
  if (!canvas) return;
  if (memberAchChart) memberAchChart.destroy();
  memberAchChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: filtered.map(formatDate),
      datasets: [{
        label: '達成度',
        data: data,
        borderColor: '#16a34a',
        backgroundColor: '#16a34a20',
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 7,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y: (function(){ const s = autoScale([{data}], 0.2); return { min: s.min, max: s.max, grid: { color: '#e2e8f0' } }; })(), x: { grid: { display: false } } },
      plugins: { legend: { display: false } }
    }
  });
}

function buildMemberRadarChart(mid) {
  const labels = ['接客','ヒアリング','提案','クロージング','知識','報連相'];
  const skills = (members[mid].profile || {}).skill_scores || {};
  const canvas = document.getElementById('chart-member-radar');
  if (!canvas) return;
  if (memberRadarChart) memberRadarChart.destroy();
  memberRadarChart = new Chart(canvas, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: members[mid].name,
        data: labels.map(l => skills[l] || 0),
        borderColor: '#2563eb',
        backgroundColor: '#2563eb30',
        pointBackgroundColor: '#2563eb',
        borderWidth: 2,
        pointRadius: 4
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { r: { min: 0, max: 5, ticks: { stepSize: 1 }, grid: { color: '#e2e8f0' }, angleLines: { color: '#e2e8f0' } } },
      plugins: { legend: { display: false } }
    }
  });
}

function setMemberCondPeriod(p, mid, btn) {
  btn.parentElement.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  buildMemberConditionChart(mid, p);
}
function setMemberAchPeriod(p, mid, btn) {
  btn.parentElement.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  buildMemberAchievementChart(mid, p);
}

// ===== Heatmap =====
function buildHeatmap(mid) {
  const daily = members[mid].daily_analysis || [];
  const dateSet = new Set(daily.map(d => d.date));
  const container = document.getElementById('heatmap-' + mid);
  if (!container) return;

  // Determine range: join_date or earliest daily to today
  const joinDate = members[mid].join_date || '';
  const allDates = daily.map(d => d.date).sort();
  const start = joinDate || (allDates.length ? allDates[0] : new Date().toISOString().split('T')[0]);
  const end = new Date().toISOString().split('T')[0];

  const startDate = new Date(start);
  const endDate = new Date(end);

  // Align to start of week (Sunday)
  const weekStart = new Date(startDate);
  weekStart.setDate(weekStart.getDate() - weekStart.getDay());

  // Build weeks
  let weeks = [];
  let current = new Date(weekStart);
  while (current <= endDate) {
    let week = [];
    for (let d = 0; d < 7; d++) {
      const dateStr = current.toISOString().split('T')[0];
      const dayOfWeek = current.getDay();
      const isSunday = dayOfWeek === 0;
      const isSaturday = dayOfWeek === 6;
      let level = 0;
      if (dateSet.has(dateStr)) {
        // Find sentiment to determine intensity
        const entry = daily.find(e => e.date === dateStr);
        const score = entry ? (entry.sentiment_score + 1) / 2 : 0.5;
        level = Math.min(4, Math.max(1, Math.ceil(score * 4)));
      } else if (isSunday || isSaturday) {
        level = -1; // weekend placeholder
      }
      week.push({ date: dateStr, level, isWeekend: isSunday || isSaturday });
      current.setDate(current.getDate() + 1);
    }
    weeks.push(week);
  }

  // Month labels
  const monthNames = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
  let monthHtml = '<div class="heatmap-month-labels" style="margin-left:32px;">';
  let lastMonth = -1;
  weeks.forEach((week, wi) => {
    const firstDay = week[0];
    const m = new Date(firstDay.date).getMonth();
    if (m !== lastMonth) {
      monthHtml += `<span style="min-width:${wi === 0 ? 0 : 0}px">${monthNames[m]}</span>`;
      lastMonth = m;
    } else {
      monthHtml += '<span style="width:17px"></span>';
    }
  });
  monthHtml += '</div>';

  // Day labels + grid
  const dayLabels = ['','月','','水','','金',''];
  let heatHtml = monthHtml + '<div style="display:flex;gap:3px;">';
  heatHtml += '<div style="display:flex;flex-direction:column;gap:3px;margin-right:4px;">';
  dayLabels.forEach(l => { heatHtml += `<div style="height:14px;font-size:10px;color:var(--subtext);line-height:14px;text-align:right;">${l}</div>`; });
  heatHtml += '</div>';
  heatHtml += '<div class="heatmap-weeks">';
  weeks.forEach(week => {
    heatHtml += '<div class="heatmap-week">';
    week.forEach(cell => {
      let cls = 'heatmap-cell';
      const style = cell.isWeekend ? 'opacity:0.3;' : '';
      if (cell.level === -1) cls += ' level-0';
      else cls += ' level-' + cell.level;
      heatHtml += `<div class="${cls}" style="${style}" title="${cell.date}${cell.level > 0 ? ' (提出済)' : ''}"></div>`;
    });
    heatHtml += '</div>';
  });
  heatHtml += '</div></div>';
  heatHtml += `
  <div class="heatmap-legend" style="margin-top:8px;">
    <span>未提出</span>
    <div class="heatmap-cell level-0"></div>
    <div class="heatmap-cell level-1" title="ネガティブ"></div>
    <div class="heatmap-cell level-2" title="やや低め"></div>
    <div class="heatmap-cell level-3" title="良好"></div>
    <div class="heatmap-cell level-4" title="非常に良好"></div>
    <span>ポジティブ</span>
  </div>`;
  container.innerHTML = heatHtml;
}

// ===== Accordion =====
function toggleAccordion(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle('open');
}

// ===== Init =====
function init() {
  // Header updated time
  document.getElementById('header-updated').textContent = '最終更新: ' + (DASHBOARD_DATA.generated_at || '-');
  document.getElementById('footer').textContent = '最終更新: ' + (DASHBOARD_DATA.generated_at || '-') + ' | 新人コンディションダッシュボード';

  // Member select (hidden select for compatibility) + tag UI
  const sel = document.getElementById('member-select');
  const tagsContainer = document.getElementById('member-tags');
  const activeIds = memberIds.filter(id => members[id].status === 'active');
  const graduatedIds = memberIds.filter(id => members[id].status === 'graduated');
  const resignedIds = memberIds.filter(id => members[id].status === 'resigned');

  // Build hidden select
  memberIds.forEach(id => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = members[id].name;
    sel.appendChild(opt);
  });

  // Build tag UI
  let tagsHtml = '';
  activeIds.forEach(id => {
    tagsHtml += `<div class="member-tag" data-mid="${id}" onclick="selectMemberTag('${id}')">${members[id].name}</div>`;
  });
  if (graduatedIds.length) {
    tagsHtml += `<div class="member-tag-separator" onclick="toggleTagGroup('tag-group-graduated')">&#127942; 卒業 <span style="font-size:10px;">&#9660;</span></div>`;
    tagsHtml += `<div class="member-tag-group collapsed" id="tag-group-graduated">`;
    graduatedIds.forEach(id => {
      tagsHtml += `<div class="member-tag status-graduated" data-mid="${id}" onclick="selectMemberTag('${id}')">${members[id].name}</div>`;
    });
    tagsHtml += `</div>`;
  }
  if (resignedIds.length) {
    tagsHtml += `<div class="member-tag-separator" onclick="toggleTagGroup('tag-group-resigned')">&#128220; 退職（学習データ） <span style="font-size:10px;">&#9660;</span></div>`;
    tagsHtml += `<div class="member-tag-group collapsed" id="tag-group-resigned">`;
    resignedIds.forEach(id => {
      tagsHtml += `<div class="member-tag status-resigned" data-mid="${id}" onclick="selectMemberTag('${id}')">${members[id].name}</div>`;
    });
    tagsHtml += `</div>`;
  }
  tagsContainer.innerHTML = tagsHtml;

  // Select first active member by default
  if (activeIds.length) {
    selectMemberTag(activeIds[0], true);
  }

  // Render team view
  renderKPI();
  renderAlerts();
  renderMemberCards();
  filterByStatus('active');
  buildTeamConditionChart('1m');
  buildTeamAchievementChart('1m');
  buildTeamRadarChart();

  // Handle URL hash
  const hash = location.hash.replace('#', '');
  if (hash.startsWith('member-')) {
    const mid = hash.replace('member-', '');
    if (members[mid]) {
      sel.value = mid;
      switchTab('member');
      renderMemberDetail(mid);
    }
  } else if (hash === 'member' && memberIds.length) {
    switchTab('member');
    renderMemberDetail(memberIds[0]);
  }
}

document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>'''

    # Embed data
    data_json = json.dumps(data, ensure_ascii=False, default=str)
    html = html_template.replace('__DASHBOARD_DATA__', data_json)
    return html


def main():
    data = load_data()
    html = generate_html(data)
    output_path = os.path.join(config.BASE_DIR, 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Dashboard generated: {output_path}")
    print(f"Members: {len(data.get('members', {}))}")


if __name__ == '__main__':
    main()
