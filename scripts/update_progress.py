#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase4進捗更新スクリプト

作業終了時に進捗を自動更新し、次回セッション用の情報を準備します。
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional

class ProgressUpdater:
    """進捗更新クラス"""
    
    def __init__(self):
        self.tracker_file = "PHASE4_PROGRESS_TRACKER.md"
        self.status_file = "REFACTORING_STATUS.md"
        
    def update_progress(self, session_data: Dict) -> None:
        """進捗を更新"""
        print("📊 Phase4進捗を更新中...")
        
        # 進捗トラッカーを更新
        self._update_tracker(session_data)
        
        # ステータスファイルを更新
        self._update_status(session_data)
        
        print("✅ 進捗更新完了")
    
    def _update_tracker(self, session_data: Dict) -> None:
        """進捗トラッカーファイルを更新"""
        if not os.path.exists(self.tracker_file):
            print(f"❌ {self.tracker_file} が見つかりません")
            return
        
        with open(self.tracker_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 現在の進捗状況を更新
        content = self._update_current_progress(content, session_data)
        
        # 作業ログを追加
        content = self._add_work_log(content, session_data)
        
        # 次回作業項目を更新
        content = self._update_next_tasks(content, session_data)
        
        with open(self.tracker_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _update_current_progress(self, content: str, session_data: Dict) -> str:
        """現在の進捗状況を更新"""
        # Week進捗を更新
        if 'week_progress' in session_data:
            week_num = session_data['week_progress']['week']
            day_num = session_data['week_progress']['day']
            completed_hours = session_data['week_progress']['completed_hours']
            total_hours = session_data['week_progress']['total_hours']
            
            # Week X Day Y の進捗を更新
            pattern = f"- \[ \] \*\*Day {day_num}\*\*:"
            replacement = f"- [{'x' if completed_hours >= total_hours else ' '}] **Day {day_num}**:"
            content = re.sub(pattern, replacement, content)
        
        # 全体進捗率を更新
        if 'overall_progress' in session_data:
            progress_percent = session_data['overall_progress']['percent']
            completed_weeks = session_data['overall_progress']['completed_weeks']
            
            pattern = r"- \*\*完了率\*\*: \d+% \(\d+/7週間\)"
            replacement = f"- **完了率**: {progress_percent}% ({completed_weeks}/7週間)"
            content = re.sub(pattern, replacement, content)
        
        return content
    
    def _add_work_log(self, content: str, session_data: Dict) -> str:
        """作業ログを追加"""
        today = datetime.now().strftime("%Y-%m-%d")
        session_num = session_data.get('session_number', 'X')
        
        log_entry = f"""
### **{today} (セッション{session_num})**
**作業内容**:
{self._format_work_items(session_data.get('work_done', []))}

**成果物**:
{self._format_deliverables(session_data.get('deliverables', []))}

**進捗更新**:
{self._format_progress_update(session_data)}

**次回作業**:
{self._format_next_tasks(session_data.get('next_tasks', []))}

**問題・課題**:
{self._format_issues(session_data.get('issues', []))}

---
"""
        
        # 作業ログセクションの最後に追加
        log_section_end = "### **次回セッション用テンプレート**"
        content = content.replace(log_section_end, log_entry + log_section_end)
        
        return content
    
    def _update_next_tasks(self, content: str, session_data: Dict) -> str:
        """次回作業項目を更新"""
        if 'next_tasks' not in session_data:
            return content
        
        next_tasks_text = self._format_next_tasks(session_data['next_tasks'])
        
        # 次回セッション時の最優先作業セクションを更新
        pattern = r"### \*\*次回セッション時の最優先作業\*\*\n.*?(?=\n### |\n## |\Z)"
        replacement = f"### **次回セッション時の最優先作業**\n{next_tasks_text}\n"
        
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        return content
    
    def _format_work_items(self, work_items: List[str]) -> str:
        """作業項目をフォーマット"""
        if not work_items:
            return "- 作業なし"
        return "\n".join(f"- {item}" for item in work_items)
    
    def _format_deliverables(self, deliverables: List[str]) -> str:
        """成果物をフォーマット"""
        if not deliverables:
            return "- なし"
        return "\n".join(f"- `{item}`" for item in deliverables)
    
    def _format_progress_update(self, session_data: Dict) -> str:
        """進捗更新をフォーマット"""
        if 'week_progress' in session_data:
            week = session_data['week_progress']['week']
            day = session_data['week_progress']['day']
            status = session_data['week_progress']['status']
            return f"- Week {week} Day {day}: {status}"
        return "- 進捗更新なし"
    
    def _format_next_tasks(self, next_tasks: List[str]) -> str:
        """次回作業をフォーマット"""
        if not next_tasks:
            return "- 次回作業項目未定"
        return "\n".join(f"- {task}" for task in next_tasks)
    
    def _format_issues(self, issues: List[str]) -> str:
        """問題・課題をフォーマット"""
        if not issues:
            return "- なし"
        return "\n".join(f"- {issue}" for issue in issues)
    
    def _update_status(self, session_data: Dict) -> None:
        """ステータスファイルを更新"""
        if not os.path.exists(self.status_file):
            return
        
        with open(self.status_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Phase4の進捗状況を更新
        if 'overall_progress' in session_data:
            progress_percent = session_data['overall_progress']['percent']
            
            # Phase4セクションの進捗を更新
            pattern = r"## ✅ Phase 4: folder_tree\.py 完全リファクタリング \(.*?\)"
            if progress_percent == 100:
                replacement = "## ✅ Phase 4: folder_tree.py 完全リファクタリング (完了)"
            else:
                replacement = f"## 🔄 Phase 4: folder_tree.py 完全リファクタリング ({progress_percent}%進行中)"
            
            content = re.sub(pattern, replacement, content)
        
        with open(self.status_file, 'w', encoding='utf-8') as f:
            f.write(content)

def create_session_template() -> Dict:
    """セッションデータのテンプレートを作成"""
    return {
        'session_number': 1,
        'work_done': [
            "依存関係分析スクリプト実行",
            "folder_tree.py完全分析"
        ],
        'deliverables': [
            "folder_tree_dependencies.json",
            "FOLDER_TREE_ANALYSIS.md"
        ],
        'week_progress': {
            'week': 0,
            'day': 1,
            'completed_hours': 6,
            'total_hours': 6,
            'status': '完了'
        },
        'overall_progress': {
            'percent': 5,
            'completed_weeks': 0
        },
        'next_tasks': [
            "Week 0 Day 2: テスト環境構築",
            "現在動作の完全記録",
            "パフォーマンス基準値測定"
        ],
        'issues': [
            "なし"
        ]
    }

def main():
    """メイン実行関数"""
    print("📊 Phase4進捗更新ツール")
    print("=" * 40)
    
    # テンプレート表示
    template = create_session_template()
    print("\n📝 セッションデータテンプレート:")
    print("以下の形式でデータを準備してください:")
    print(f"""
session_data = {{
    'session_number': {template['session_number']},
    'work_done': {template['work_done']},
    'deliverables': {template['deliverables']},
    'week_progress': {template['week_progress']},
    'overall_progress': {template['overall_progress']},
    'next_tasks': {template['next_tasks']},
    'issues': {template['issues']}
}}
""")
    
    print("\n💡 使用方法:")
    print("1. 上記テンプレートを実際のデータで更新")
    print("2. update_progress(session_data) を呼び出し")
    print("3. 進捗ファイルが自動更新されます")
    
    # 実際の更新は手動で行う
    print("\n⚠️ 注意: 実際の更新は作業完了時に手動で実行してください")

if __name__ == "__main__":
    main()