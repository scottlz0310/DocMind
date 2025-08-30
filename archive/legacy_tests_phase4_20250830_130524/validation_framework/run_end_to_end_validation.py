#!/usr/bin/env python3
"""
統合ワークフロー検証実行スクリプト

DocMindアプリケーションの統合ワークフロー検証を実行し、
結果をレポートとして出力します。
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from tests.validation_framework.base_validator import ValidationConfig
    from tests.validation_framework.end_to_end_workflow_validator import (
        EndToEndWorkflowValidator,
    )
    from tests.validation_framework.validation_reporter import ValidationReporter
except ImportError as e:
    print(f"モジュールのインポートに失敗しました: {e}")
    print("プロジェクトルートから実行してください")
    sys.exit(1)


def create_validation_config(args) -> ValidationConfig:
    """
    コマンドライン引数から検証設定を作成

    Args:
        args: コマンドライン引数

    Returns:
        検証設定
    """
    config = ValidationConfig()

    # パフォーマンス監視設定
    config.enable_performance_monitoring = not args.no_performance
    config.enable_memory_monitoring = not args.no_memory
    config.enable_error_injection = args.error_injection

    # 制限設定
    if args.max_time:
        config.max_execution_time = args.max_time
    if args.max_memory:
        config.max_memory_usage = args.max_memory

    # ログレベル設定
    config.log_level = args.log_level.upper()

    # 出力ディレクトリ設定
    if args.output_dir:
        config.output_directory = args.output_dir

    return config


def run_validation(config: ValidationConfig, test_methods: list = None) -> tuple:
    """
    統合ワークフロー検証の実行

    Args:
        config: 検証設定
        test_methods: 実行するテストメソッドのリスト

    Returns:
        (validator, results)のタプル
    """
    print("=== DocMind 統合ワークフロー検証 ===")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # バリデーターの初期化
    validator = EndToEndWorkflowValidator(config)

    try:
        # テスト環境のセットアップ
        print("テスト環境をセットアップ中...")
        validator.setup_test_environment()

        # 検証の実行
        print("統合ワークフロー検証を実行中...")
        results = validator.run_validation(test_methods)

        return validator, results

    except Exception as e:
        print(f"検証実行中にエラーが発生しました: {e}")
        return validator, []


def print_results_summary(results: list) -> None:
    """
    検証結果のサマリーを出力

    Args:
        results: 検証結果のリスト
    """
    if not results:
        print("実行された検証がありません")
        return

    print("\n=== 検証結果サマリー ===")

    # 全体統計
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.success)
    failed_tests = total_tests - passed_tests

    print(f"総テスト数: {total_tests}")
    print(f"成功: {passed_tests}")
    print(f"失敗: {failed_tests}")
    print(f"成功率: {(passed_tests/total_tests*100):.1f}%")

    # 実行時間統計
    total_time = sum(r.execution_time for r in results)
    avg_time = total_time / total_tests
    max_time = max(r.execution_time for r in results)

    print("\n実行時間統計:")
    print(f"総実行時間: {total_time:.2f}秒")
    print(f"平均実行時間: {avg_time:.2f}秒")
    print(f"最大実行時間: {max_time:.2f}秒")

    # メモリ使用量統計
    if any(r.memory_usage > 0 for r in results):
        memory_results = [r.memory_usage for r in results if r.memory_usage > 0]
        avg_memory = sum(memory_results) / len(memory_results)
        max_memory = max(memory_results)

        print("\nメモリ使用量統計:")
        print(f"平均メモリ使用量: {avg_memory:.2f}MB")
        print(f"最大メモリ使用量: {max_memory:.2f}MB")

    # 個別テスト結果
    print("\n=== 個別テスト結果 ===")
    for result in results:
        status = "✓ PASS" if result.success else "✗ FAIL"
        print(f"{status} {result.test_name}")
        print(f"    実行時間: {result.execution_time:.2f}秒")
        if result.memory_usage > 0:
            print(f"    メモリ使用量: {result.memory_usage:.2f}MB")

        if not result.success and result.error_message:
            print(f"    エラー: {result.error_message}")
        print()


def generate_report(validator, results: list, output_dir: str) -> None:
    """
    検証レポートの生成

    Args:
        validator: バリデーターインスタンス
        results: 検証結果
        output_dir: 出力ディレクトリ
    """
    try:
        # 出力ディレクトリの作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # レポーター初期化
        reporter = ValidationReporter(str(output_path))

        # レポート生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON形式の詳細レポート
        json_file = output_path / f"end_to_end_validation_results_{timestamp}.json"
        reporter.generate_json_report(results, str(json_file))

        # HTML形式のサマリーレポート
        html_file = output_path / f"end_to_end_report_{timestamp}.html"
        reporter.generate_html_report(
            results, str(html_file), title="DocMind 統合ワークフロー検証レポート"
        )

        print("\n=== レポート生成完了 ===")
        print(f"JSON詳細レポート: {json_file}")
        print(f"HTMLサマリーレポート: {html_file}")

    except Exception as e:
        print(f"レポート生成中にエラーが発生しました: {e}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="DocMind統合ワークフロー検証を実行します",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な検証実行
  python run_end_to_end_validation.py

  # 特定のテストのみ実行
  python run_end_to_end_validation.py --tests test_complete_application_workflow

  # パフォーマンス監視なしで実行
  python run_end_to_end_validation.py --no-performance --no-memory

  # カスタム制限で実行
  python run_end_to_end_validation.py --max-time 120 --max-memory 4096
        """,
    )

    # テスト選択オプション
    parser.add_argument(
        "--tests", nargs="+", help="実行するテストメソッド名（省略時は全テスト実行）"
    )

    # 監視オプション
    parser.add_argument(
        "--no-performance", action="store_true", help="パフォーマンス監視を無効化"
    )

    parser.add_argument("--no-memory", action="store_true", help="メモリ監視を無効化")

    parser.add_argument(
        "--error-injection", action="store_true", help="エラー注入テストを有効化"
    )

    # 制限オプション
    parser.add_argument("--max-time", type=float, help="最大実行時間（秒）")

    parser.add_argument("--max-memory", type=float, help="最大メモリ使用量（MB）")

    # 出力オプション
    parser.add_argument(
        "--output-dir",
        default="validation_results/end_to_end",
        help="結果出力ディレクトリ（デフォルト: validation_results/end_to_end）",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="ログレベル（デフォルト: INFO）",
    )

    parser.add_argument(
        "--no-report", action="store_true", help="レポート生成をスキップ"
    )

    args = parser.parse_args()

    # 検証設定の作成
    config = create_validation_config(args)

    # 検証の実行
    validator, results = run_validation(config, args.tests)

    try:
        # 結果の表示
        print_results_summary(results)

        # レポートの生成
        if not args.no_report and results:
            generate_report(validator, results, args.output_dir)

        # 終了コードの決定
        if results:
            failed_count = sum(1 for r in results if not r.success)
            if failed_count > 0:
                print(f"\n{failed_count}個のテストが失敗しました")
                sys.exit(1)
            else:
                print("\nすべてのテストが成功しました")
                sys.exit(0)
        else:
            print("\n実行されたテストがありません")
            sys.exit(1)

    finally:
        # クリーンアップ
        try:
            validator.teardown_test_environment()
            validator.cleanup()
        except Exception as e:
            print(f"クリーンアップ中にエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
