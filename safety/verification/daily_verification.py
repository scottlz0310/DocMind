#!/usr/bin/env python3
"""
日次検証スクリプト
毎日の作業後に実行する安全性チェック
"""

import subprocess
import sys
from pathlib import Path


def run_syntax_check():
    """構文チェック実行"""
    target_file = Path("src/gui/folder_tree.py")

    if not target_file.exists():
        return False

    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(target_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return True
        else:
            return False
    except Exception:
        return False


def run_import_check():
    """インポートチェック実行"""

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.append('src'); from gui.folder_tree import FolderTreeWidget; print('インポート成功')",
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.returncode == 0:
            return True
        else:
            return False
    except Exception:
        return False


def main():
    """メイン処理"""

    checks = [
        ("構文チェック", run_syntax_check),
        ("インポートチェック", run_import_check),
    ]

    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))

    # 結果サマリー
    all_passed = True
    for name, result in results:
        if not result:
            all_passed = False

    if all_passed:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
