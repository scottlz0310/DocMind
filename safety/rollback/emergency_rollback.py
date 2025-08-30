#!/usr/bin/env python3
"""
緊急ロールバックスクリプト
問題発生時の安全な状態復旧
"""

import shutil
import subprocess
from pathlib import Path


class EmergencyRollback:
    """緊急ロールバック管理クラス"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.backup_dir = self.project_root / "backups"

    def list_available_backups(self):
        """利用可能なバックアップ一覧表示"""

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

        for _i, backup in enumerate(daily_backups[:5]):  # 最新5件
            pass

        for _i, backup in enumerate(weekly_backups[:3]):  # 最新3件
            pass

        return daily_backups, weekly_backups

    def git_rollback(self, target_branch="main"):
        """Gitを使用した緊急ロールバック"""

        try:
            # 現在の変更を退避
            subprocess.run(["git", "stash"], check=True)

            # 対象ブランチにチェックアウト
            subprocess.run(["git", "checkout", target_branch], check=True)

            # 作業ブランチを削除（存在する場合）
            try:
                subprocess.run(["git", "branch", "-D", "refactor/folder-tree-phase4"],
                             check=True, capture_output=True)
            except subprocess.CalledProcessError:
                pass

            # クリーンアップ
            subprocess.run(["git", "clean", "-fd"], check=True)

            return True

        except subprocess.CalledProcessError:
            return False

    def file_rollback(self, backup_path):
        """ファイルバックアップからの復旧"""

        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
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

            return True

        except Exception:
            return False

def main():
    """メイン処理"""

    rollback = EmergencyRollback()


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
                pass
        elif choice == "3":
            rollback.list_available_backups()
        elif choice == "4":
            pass
        else:
            pass

    except KeyboardInterrupt:
        pass
    except Exception:
        pass

if __name__ == "__main__":
    main()
