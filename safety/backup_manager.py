#!/usr/bin/env python3
"""
バックアップ管理システム
Phase4リファクタリング用の安全対策
"""

import tarfile
from datetime import datetime
from pathlib import Path


class BackupManager:
    """バックアップ管理クラス"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self, name: str = None) -> str:
        """プロジェクト全体のバックアップを作成"""
        if name is None:
            name = f"phase4_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_file = self.backup_dir / f"{name}.tar.gz"

        with tarfile.open(backup_file, "w:gz") as tar:
            # 重要なファイルのみバックアップ
            important_paths = [
                "src/gui/folder_tree.py",
                "src/gui/main_window.py",
                "src/gui/search_interface.py",
                "REFACTORING_STATUS.md",
                "PHASE4_PROGRESS_TRACKER.md"
            ]

            for path in important_paths:
                full_path = self.project_root / path
                if full_path.exists():
                    tar.add(full_path, arcname=path)

        return str(backup_file)

def main():
    """バックアップ作成のメイン関数"""
    manager = BackupManager()
    manager.create_backup()

if __name__ == "__main__":
    main()
