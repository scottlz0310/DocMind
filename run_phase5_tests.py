#!/usr/bin/env python3
"""
Phase5テスト実行スクリプト

新しいテストアーキテクチャでのテスト実行
- ユニットテスト: 各コンポーネントの独立テスト
- 統合テスト: コンポーネント間の接続確認のみ
"""

from pathlib import Path
import subprocess
import sys
import time


def run_command(command: list, description: str) -> bool:
    """コマンドを実行し、結果を表示"""

    start_time = time.time()
    try:
        # 仮想環境のPythonを使用
        if command[0] == "python":
            venv_python = Path(__file__).parent / "venv" / "bin" / "python"
            if venv_python.exists():
                command[0] = str(venv_python)
            else:
                command[0] = "python"

        result = subprocess.run(command, check=False, capture_output=True, text=True, cwd=Path(__file__).parent)

        time.time() - start_time

        if result.returncode == 0:
            if result.stdout:
                pass
            return True
        else:
            if result.stderr:
                pass
            if result.stdout:
                pass
            return False

    except Exception:
        time.time() - start_time
        return False


def main():
    """メイン実行関数"""

    # 仮想環境の確認
    if not Path("venv").exists():
        return False

    # テストディレクトリの確認
    test_dir = Path("tests")
    if not test_dir.exists():
        return False

    success_count = 0
    total_tests = 0

    # 1. ユニットテスト実行

    unit_tests = [
        (
            ["python", "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
            "ユニットテスト全体",
        ),
        (
            ["python", "-m", "pytest", "tests/unit/managers/", "-v"],
            "マネージャー系ユニットテスト",
        ),
        (
            ["python", "-m", "pytest", "tests/unit/controllers/", "-v"],
            "コントローラー系ユニットテスト",
        ),
        (
            ["python", "-m", "pytest", "tests/unit/search/", "-v"],
            "検索機能系ユニットテスト",
        ),
        (
            ["python", "-m", "pytest", "tests/unit/folder_tree/", "-v"],
            "フォルダツリー系ユニットテスト",
        ),
    ]

    for command, description in unit_tests:
        total_tests += 1
        if run_command(command, description):
            success_count += 1

    # 2. 統合テスト実行

    integration_tests = [
        (
            ["python", "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
            "統合テスト全体",
        ),
        (
            [
                "python",
                "-m",
                "pytest",
                "tests/integration/test_main_window_integration.py",
                "-v",
            ],
            "メインウィンドウ統合テスト",
        ),
        (
            [
                "python",
                "-m",
                "pytest",
                "tests/integration/test_search_flow_integration.py",
                "-v",
            ],
            "検索フロー統合テスト",
        ),
    ]

    for command, description in integration_tests:
        total_tests += 1
        if run_command(command, description):
            success_count += 1

    # 3. カバレッジ測定

    coverage_tests = [
        (
            [
                "python",
                "-m",
                "pytest",
                "tests/",
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html",
            ],
            "カバレッジ付きテスト実行",
        ),
    ]

    for command, description in coverage_tests:
        total_tests += 1
        if run_command(command, description):
            success_count += 1

    # 4. テスト品質チェック

    quality_tests = [
        (["python", "-m", "pytest", "tests/", "--collect-only"], "テスト収集確認"),
        (
            ["python", "-c", "import tests; print('テストモジュールのインポート成功')"],
            "テストモジュールインポート確認",
        ),
    ]

    for command, description in quality_tests:
        total_tests += 1
        if run_command(command, description):
            success_count += 1

    # 結果サマリー

    (success_count / total_tests) * 100 if total_tests > 0 else 0

    if success_count == total_tests:
        return True
    else:
        total_tests - success_count
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
