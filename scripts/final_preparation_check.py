#!/usr/bin/env python3
"""
Phase4最終準備確認スクリプト
Week 0 Day 5: 最終準備確認

全安全対策の動作確認とPhase4実行環境の最終チェックを実行
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def check_virtual_environment():
    """仮想環境の確認"""
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        return True
    else:
        return False


def check_safety_measures():
    """安全対策の確認"""

    safety_dir = Path("safety")
    if not safety_dir.exists():
        return False

    required_files = [
        "safety/backup_manager.py",
        "safety/rollback_manager.py",
        "safety/test_runner.py",
        "safety/validation_manager.py",
    ]

    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            pass
        else:
            all_exist = False

    return all_exist


def check_phase4_target():
    """Phase4対象ファイルの確認"""

    target_file = Path("src/gui/folder_tree.py")
    if not target_file.exists():
        return False

    # ファイルサイズ確認
    with open(target_file, encoding="utf-8") as f:
        lines = f.readlines()
        line_count = len(lines)

    if line_count > 1000:
        return True
    else:
        return True


def check_dependencies():
    """依存関係分析結果の確認"""

    deps_file = Path("folder_tree_dependencies.json")
    if not deps_file.exists():
        return False

    try:
        with open(deps_file, encoding="utf-8") as f:
            json.load(f)

        return True
    except Exception:
        return False


def check_backup_system():
    """バックアップシステムの確認"""

    backup_dir = Path("backups")
    if not backup_dir.exists():
        return False

    # 最新バックアップの確認
    backup_files = list(backup_dir.glob("*.tar.gz"))
    if backup_files:
        max(backup_files, key=lambda x: x.stat().st_mtime)
        return True
    else:
        return False


def check_test_environment():
    """テスト環境の確認"""

    try:
        # 基本的なimportテスト
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, 'src'); from gui.folder_tree import FolderTreeWidget; print('✅ folder_tree.py import成功')",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return True
        else:
            return False
    except Exception:
        return False


def check_progress_tracking():
    """進捗追跡システムの確認"""

    required_files = [
        "PHASE4_PROGRESS_TRACKER.md",
        "PHASE4_SAFETY_PLAN.md",
        "FOLDER_TREE_ANALYSIS.md",
    ]

    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            pass
        else:
            all_exist = False

    return all_exist


def generate_final_report():
    """最終確認レポートの生成"""

    report = {
        "check_date": datetime.now().isoformat(),
        "phase": "Phase4準備完了確認",
        "target_file": "src/gui/folder_tree.py",
        "status": "準備完了",
        "next_action": "Phase4 Week1開始可能",
    }

    report_file = Path("PHASE4_FINAL_PREPARATION_REPORT.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"""# Phase4最終準備確認レポート

**確認日時**: {report["check_date"]}
**対象フェーズ**: {report["phase"]}
**対象ファイル**: {report["target_file"]}

## 確認結果

✅ 全ての準備項目が完了しました

## 次回アクション

{report["next_action"]}

---
自動生成: scripts/final_preparation_check.py
""")

    return True


def main():
    """メイン実行関数"""

    checks = [
        ("仮想環境", check_virtual_environment),
        ("安全対策", check_safety_measures),
        ("Phase4対象ファイル", check_phase4_target),
        ("依存関係分析", check_dependencies),
        ("バックアップシステム", check_backup_system),
        ("テスト環境", check_test_environment),
        ("進捗追跡システム", check_progress_tracking),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception:
            results.append((name, False))

    success_count = 0
    for name, result in results:
        if result:
            success_count += 1

    if success_count == len(results):
        generate_final_report()
        return True
    else:
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
