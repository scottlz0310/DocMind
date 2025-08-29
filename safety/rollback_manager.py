#!/usr/bin/env python3
"""
ロールバック管理システム
Phase4リファクタリング用の緊急復旧機能
"""

import os
import shutil
import tarfile
from pathlib import Path

class RollbackManager:
    """ロールバック管理クラス"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups"
    
    def list_backups(self) -> list:
        """利用可能なバックアップ一覧を取得"""
        if not self.backup_dir.exists():
            return []
        
        backups = list(self.backup_dir.glob("*.tar.gz"))
        return sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def rollback_from_backup(self, backup_file: str) -> bool:
        """指定されたバックアップからロールバック"""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            print(f"❌ バックアップファイルが見つかりません: {backup_file}")
            return False
        
        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(self.project_root)
            
            print(f"✅ ロールバック完了: {backup_file}")
            return True
        except Exception as e:
            print(f"❌ ロールバック失敗: {e}")
            return False
    
    def emergency_rollback(self) -> bool:
        """最新バックアップからの緊急ロールバック"""
        backups = self.list_backups()
        if not backups:
            print("❌ 利用可能なバックアップがありません")
            return False
        
        latest_backup = backups[0]
        print(f"🚨 緊急ロールバック実行: {latest_backup.name}")
        return self.rollback_from_backup(str(latest_backup))

def main():
    """ロールバック管理のメイン関数"""
    manager = RollbackManager()
    backups = manager.list_backups()
    
    if backups:
        print("📋 利用可能なバックアップ:")
        for i, backup in enumerate(backups):
            print(f"  {i+1}. {backup.name}")
    else:
        print("⚠️ 利用可能なバックアップがありません")

if __name__ == "__main__":
    main()