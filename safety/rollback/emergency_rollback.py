#!/usr/bin/env python3
"""
緊急ロールバックスクリプト
問題発生時の安全な状態復旧
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

class EmergencyRollback:
    """緊急ロールバック管理クラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.backup_dir = self.project_root / "backups"
        
    def list_available_backups(self):
        """利用可能なバックアップ一覧表示"""
        print("📋 利用可能なバックアップ:")
        print("-" * 40)
        
        daily_backups = []
        weekly_backups = []
        
        # 日次バックアップ
        daily_dir = self.backup_dir / "daily"
        if daily_dir.exists():
            for backup in sorted(daily_dir.iterdir(), reverse=True):
                if backup.is_dir():
                    daily_backups.append(backup)
        
        # 週次バックアップ
        weekly_dir = self.backup_dir / "weekly"
        if weekly_dir.exists():
            for backup in sorted(weekly_dir.iterdir(), reverse=True):
                if backup.is_dir():
                    weekly_backups.append(backup)
        
        print("日次バックアップ:")
        for i, backup in enumerate(daily_backups[:5]):  # 最新5件
            print(f"  {i+1}. {backup.name}")
        
        print("\n週次バックアップ:")
        for i, backup in enumerate(weekly_backups[:3]):  # 最新3件
            print(f"  {i+1}. {backup.name}")
        
        return daily_backups, weekly_backups
    
    def git_rollback(self, target_branch="main"):
        """Gitを使用した緊急ロールバック"""
        print(f"🔄 Git緊急ロールバック実行: {target_branch}")
        
        try:
            # 現在の変更を退避
            subprocess.run(["git", "stash"], check=True)
            print("✅ 現在の変更を退避")
            
            # 対象ブランチにチェックアウト
            subprocess.run(["git", "checkout", target_branch], check=True)
            print(f"✅ {target_branch}ブランチにチェックアウト")
            
            # 作業ブランチを削除（存在する場合）
            try:
                subprocess.run(["git", "branch", "-D", "refactor/folder-tree-phase4"], 
                             check=True, capture_output=True)
                print("✅ 作業ブランチを削除")
            except subprocess.CalledProcessError:
                print("ℹ️ 作業ブランチは存在しませんでした")
            
            # クリーンアップ
            subprocess.run(["git", "clean", "-fd"], check=True)
            print("✅ 未追跡ファイルをクリーンアップ")
            
            print("🎉 Git緊急ロールバック完了")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git緊急ロールバック失敗: {e}")
            return False
    
    def file_rollback(self, backup_path):
        """ファイルバックアップからの復旧"""
        print(f"📁 ファイルロールバック実行: {backup_path}")
        
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                print(f"❌ バックアップが見つかりません: {backup_path}")
                return False
            
            # バックアップ情報読み込み
            info_file = backup_dir / "backup_info.json"
            if info_file.exists():
                import json
                backup_info = json.loads(info_file.read_text())
                files_to_restore = backup_info.get("files", [])
            else:
                # 全ファイルを復旧対象とする
                files_to_restore = []
                for file_path in backup_dir.rglob("*.py"):
                    rel_path = file_path.relative_to(backup_dir)
                    files_to_restore.append(str(rel_path))
            
            # ファイル復旧
            for file_path in files_to_restore:
                source = backup_dir / file_path
                dest = self.project_root / file_path
                
                if source.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    print(f"✅ 復旧完了: {file_path}")
            
            print("🎉 ファイルロールバック完了")
            return True
            
        except Exception as e:
            print(f"❌ ファイルロールバック失敗: {e}")
            return False

def main():
    """メイン処理"""
    print("🚨 緊急ロールバックシステム")
    print("=" * 40)
    
    rollback = EmergencyRollback()
    
    print("選択してください:")
    print("1. Git緊急ロールバック (推奨)")
    print("2. ファイルバックアップからの復旧")
    print("3. 利用可能なバックアップ一覧表示")
    print("4. 終了")
    
    try:
        choice = input("\n選択 (1-4): ").strip()
        
        if choice == "1":
            rollback.git_rollback()
        elif choice == "2":
            daily_backups, weekly_backups = rollback.list_available_backups()
            # 簡単のため最新の日次バックアップを使用
            if daily_backups:
                rollback.file_rollback(daily_backups[0])
            else:
                print("❌ 利用可能なバックアップがありません")
        elif choice == "3":
            rollback.list_available_backups()
        elif choice == "4":
            print("終了します")
        else:
            print("❌ 無効な選択です")
            
    except KeyboardInterrupt:
        print("\n操作がキャンセルされました")
    except Exception as e:
        print(f"❌ エラー発生: {e}")

if __name__ == "__main__":
    main()
