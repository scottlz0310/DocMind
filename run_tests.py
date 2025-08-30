#!/usr/bin/env python3
"""
テスト実行スクリプト

DocMindアプリケーションの包括的なテストスイートを実行するためのスクリプト
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class TestRunner:
    """テスト実行管理クラス"""

    def __init__(self):
        """初期化"""
        self.project_root = Path(__file__).parent
        self.test_dir = self.project_root / "tests"
        self.src_dir = self.project_root / "src"

        # テスト結果ディレクトリ
        self.results_dir = self.project_root / "test_results"
        self.results_dir.mkdir(exist_ok=True)

        # カバレッジディレクトリ
        self.coverage_dir = self.project_root / "htmlcov"

    def run_unit_tests(self, verbose: bool = True) -> dict[str, Any]:
        """ユニットテストを実行"""

        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "-m", "unit",
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            f"--junit-xml={self.results_dir}/unit_tests.xml"
        ]

        if verbose:
            cmd.append("-v")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        execution_time = time.time() - start_time

        return {
            "type": "unit",
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }

    def run_integration_tests(self, verbose: bool = True) -> dict[str, Any]:
        """統合テストを実行"""

        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "-m", "integration",
            f"--junit-xml={self.results_dir}/integration_tests.xml"
        ]

        if verbose:
            cmd.append("-v")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        execution_time = time.time() - start_time

        return {
            "type": "integration",
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }

    def run_performance_tests(self, verbose: bool = True) -> dict[str, Any]:
        """パフォーマンステストを実行"""

        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "-m", "performance",
            "--tb=short",
            f"--junit-xml={self.results_dir}/performance_tests.xml"
        ]

        if verbose:
            cmd.append("-v")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        execution_time = time.time() - start_time

        return {
            "type": "performance",
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }

    def run_gui_tests(self, verbose: bool = True) -> dict[str, Any]:
        """GUIテストを実行"""

        # PySide6が利用可能かチェック
        try:
            import PySide6
        except ImportError:
            return {
                "type": "gui",
                "success": True,
                "execution_time": 0,
                "stdout": "PySide6が利用できないためスキップ",
                "stderr": "",
                "return_code": 0,
                "skipped": True
            }

        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "-m", "gui",
            f"--junit-xml={self.results_dir}/gui_tests.xml"
        ]

        if verbose:
            cmd.append("-v")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        execution_time = time.time() - start_time

        return {
            "type": "gui",
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }

    def run_all_tests(self, verbose: bool = True, skip_slow: bool = False) -> list[dict[str, Any]]:
        """すべてのテストを実行"""

        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            f"--junit-xml={self.results_dir}/all_tests.xml"
        ]

        if verbose:
            cmd.append("-v")

        if skip_slow:
            cmd.extend(["-m", "not slow"])

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        execution_time = time.time() - start_time

        return [{
            "type": "all",
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }]

    def run_specific_tests(self, test_pattern: str, verbose: bool = True) -> dict[str, Any]:
        """特定のテストパターンを実行"""

        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "-k", test_pattern,
            f"--junit-xml={self.results_dir}/specific_tests.xml"
        ]

        if verbose:
            cmd.append("-v")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        execution_time = time.time() - start_time

        return {
            "type": "specific",
            "pattern": test_pattern,
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }

    def generate_coverage_report(self) -> bool:
        """カバレッジレポートを生成"""

        try:
            # HTMLカバレッジレポートが生成されているかチェック
            if self.coverage_dir.exists():
                index_file = self.coverage_dir / "index.html"
                if index_file.exists():
                    return True

            # カバレッジレポートを手動で生成
            cmd = [sys.executable, "-m", "coverage", "html"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return True
            else:
                return False

        except Exception:
            return False

    def save_test_summary(self, results: list[dict[str, Any]]) -> None:
        """テスト結果サマリーを保存"""
        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(results),
            "successful_tests": sum(1 for r in results if r["success"]),
            "failed_tests": sum(1 for r in results if not r["success"]),
            "total_execution_time": sum(r["execution_time"] for r in results),
            "results": results
        }

        summary_file = self.results_dir / "test_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


    def print_summary(self, results: list[dict[str, Any]]) -> None:
        """テスト結果サマリーを表示"""

        total_tests = len(results)
        successful_tests = sum(1 for r in results if r["success"])
        total_tests - successful_tests
        sum(r["execution_time"] for r in results)


        for result in results:
            "✅" if result["success"] else "❌"
            result["type"].upper()
            result["execution_time"]

            if result.get("skipped"):
                pass
            else:

                if not result["success"] and result["stderr"]:
                    pass


        # カバレッジ情報の表示
        coverage_file = self.project_root / "coverage.xml"
        if coverage_file.exists():
            pass


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="DocMind テストスイート実行スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python run_tests.py --all                    # すべてのテストを実行
  python run_tests.py --unit                   # ユニットテストのみ実行
  python run_tests.py --integration            # 統合テストのみ実行
  python run_tests.py --performance            # パフォーマンステストのみ実行
  python run_tests.py --gui                    # GUIテストのみ実行
  python run_tests.py --pattern "search"       # 特定のパターンのテストを実行
  python run_tests.py --all --skip-slow        # 高速テストのみ実行
        """
    )

    # テストタイプオプション
    parser.add_argument("--all", action="store_true", help="すべてのテストを実行")
    parser.add_argument("--unit", action="store_true", help="ユニットテストを実行")
    parser.add_argument("--integration", action="store_true", help="統合テストを実行")
    parser.add_argument("--performance", action="store_true", help="パフォーマンステストを実行")
    parser.add_argument("--gui", action="store_true", help="GUIテストを実行")
    parser.add_argument("--pattern", type=str, help="特定のテストパターンを実行")

    # オプション
    parser.add_argument("--skip-slow", action="store_true", help="時間のかかるテストをスキップ")
    parser.add_argument("--quiet", "-q", action="store_true", help="詳細出力を抑制")
    parser.add_argument("--no-coverage", action="store_true", help="カバレッジレポートを生成しない")

    args = parser.parse_args()

    # 引数チェック
    if not any([args.all, args.unit, args.integration, args.performance, args.gui, args.pattern]):
        parser.print_help()
        sys.exit(1)

    runner = TestRunner()
    results = []
    verbose = not args.quiet

    try:
        # テスト実行
        if args.all:
            results = runner.run_all_tests(verbose=verbose, skip_slow=args.skip_slow)
        else:
            if args.unit:
                results.append(runner.run_unit_tests(verbose=verbose))

            if args.integration:
                results.append(runner.run_integration_tests(verbose=verbose))

            if args.performance:
                results.append(runner.run_performance_tests(verbose=verbose))

            if args.gui:
                results.append(runner.run_gui_tests(verbose=verbose))

            if args.pattern:
                results.append(runner.run_specific_tests(args.pattern, verbose=verbose))

        # カバレッジレポート生成
        if not args.no_coverage:
            runner.generate_coverage_report()

        # 結果保存と表示
        runner.save_test_summary(results)
        runner.print_summary(results)

        # 終了コード決定
        failed_tests = sum(1 for r in results if not r["success"])
        if failed_tests > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
