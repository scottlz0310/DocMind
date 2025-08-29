#!/usr/bin/env python3
"""
バックアップ作成スクリプト
重要ファイルの安全なバックアップを作成
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path

class BackupManager:
    """バックアップ管理クラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.backup_dir = self.project_root / "backups"
        
    def create_daily_backup(self):
        """日次バックアップ作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / "daily" / f"backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # バックアップ対象ファイル
        target_files = [
            "src/gui/folder_tree.py",
            "src/gui/main_window.py",
            "src/gui/search_interface.py"
        ]
        
        backup_info = {
            "timestamp": timestamp,
            "files": [],
            "status": "success"
        }
        
        try:
            for file_path in target_files:
                source = self.project_root / file_path
                if source.exists():
                    dest = backup_path / file_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    backup_info["files"].append(file_path)
                    print(f"✅ バックアップ完了: {file_path}")
            
            # バックアップ情報保存
            info_file = backup_path / "backup_info.json"
            info_file.write_text(json.dumps(backup_info, indent=2, ensure_ascii=False))
            
            print(f"🎉 日次バックアップ完了: {backup_path.name}")
            return str(backup_path)
            
        except Exception as e:
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            print(f"❌ バックアップ失敗: {e}")
            return None
    
    def create_weekly_backup(self):
        """週次バックアップ作成"""
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_path = self.backup_dir / "weekly" / f"week_backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # プロジェクト全体をバックアップ
        try:
            # 重要ディレクトリのバックアップ
            important_dirs = ["src", "docs", "scripts", "safety"]
            
            for dir_name in important_dirs:
                source_dir = self.project_root / dir_name
                if source_dir.exists():
                    dest_dir = backup_path / dir_name
                    shutil.copytree(source_dir, dest_dir, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                    print(f"✅ ディレクトリバックアップ完了: {dir_name}")
            
            print(f"🎉 週次バックアップ完了: {backup_path.name}")
            return str(backup_path)
            
        except Exception as e:
            print(f"❌ 週次バックアップ失敗: {e}")
            return None

def main():
    """メイン処理"""
    print("💾 バックアップシステム実行")
    print("=" * 40)
    
    manager = BackupManager()
    
    # 日次バックアップ作成
    daily_result = manager.create_daily_backup()
    
    # 週次バックアップ（週末のみ）
    if datetime.now().weekday() == 6:  # 日曜日
        weekly_result = manager.create_weekly_backup()

if __name__ == "__main__":
    main()
