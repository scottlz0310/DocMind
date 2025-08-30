#!/usr/bin/env python3
"""
データ永続化・整合性検証実行スクリプト

このスクリプトは、DocMindアプリケーションのデータ永続化機能と
データ整合性を包括的に検証します。
"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.validation_framework.base_validator import ValidationConfig
from tests.validation_framework.data_persistence_validator import (
    DataPersistenceValidator,
)
from tests.validation_framework.validation_reporter import ValidationReporter


def parse_arguments():
    """コマンドライン引数の解析"""
    parser = argparse.ArgumentParser(
        description="DocMind データ永続化・整合性検証",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python run_data_persistence_validation.py                    # 全テスト実行
  python run_data_persistence_validation.py --quick           # 高速テスト実行
  python run_data_persistence_validation.py --test acid       # ACID特性のみテスト
  python run_data_persistence_validation.py --output report/  # 結果をreport/に出力
        """
    )

    parser.add_argument(
        '--test',
        choices=['acid', 'concurrent', 'index', 'embedding', 'backup', 'all'],
        default='all',
        help='実行するテストの種類 (デフォルト: all)'
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='高速テストモード（テストデータを削減）'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='validation_results/data_persistence',
        help='結果出力ディレクトリ (デフォルト: validation_results/data_persistence)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=600,
        help='テストタイムアウト（秒） (デフォルト: 600)'
    )

    parser.add_argument(
        '--memory-limit',
        type=int,
        default=4096,
        help='メモリ制限（MB） (デフォルト: 4096)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='詳細ログ出力'
    )

    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='テスト後のクリーンアップをスキップ（デバッグ用）'
    )

    return parser.parse_args()


def create_validation_config(args):
    """検証設定の作成"""
    return ValidationConfig(
        enable_performance_monitoring=True,
        enable_memory_monitoring=True,
        enable_error_injection=False,  # データ永続化テストでは無効
        max_execution_time=float(args.timeout),
        max_memory_usage=float(args.memory_limit),
        log_level="DEBUG" if args.verbose else "INFO",
        output_directory=args.output
    )


def get_test_methods(test_type):
    """テストタイプに応じた実行メソッドリストを取得"""
    test_mapping = {
        'acid': ['test_database_acid_properties'],
        'concurrent': ['test_concurrent_access_validation'],
        'index': ['test_index_integrity_validation'],
        'embedding': ['test_embedding_cache_validation'],
        'backup': ['test_backup_recovery_validation'],
        'all': None  # 全テストメソッドを実行
    }

    return test_mapping.get(test_type, None)


def run_validation(args):
    """検証の実行"""
    print("=" * 60)
    print("DocMind データ永続化・整合性検証")
    print("=" * 60)
    print(f"テストタイプ: {args.test}")
    print(f"出力ディレクトリ: {args.output}")
    print(f"タイムアウト: {args.timeout}秒")
    print(f"メモリ制限: {args.memory_limit}MB")
    print(f"高速モード: {'有効' if args.quick else '無効'}")
    print("-" * 60)

    # 出力ディレクトリの作成
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 検証設定の作成
    config = create_validation_config(args)

    # 検証実行
    validator = DataPersistenceValidator(config)

    try:
        # テスト環境のセットアップ
        print("テスト環境をセットアップ中...")
        validator.setup_test_environment()

        # 高速モードの場合、テストデータ生成器の設定を調整
        if args.quick:
            validator.test_data_generator.set_quick_mode(True)

        # 実行するテストメソッドの決定
        test_methods = get_test_methods(args.test)

        # 検証実行
        print("検証を実行中...")
        results = validator.run_validation(test_methods)

        # 結果の分析
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - passed_tests

        # 基本統計の表示
        print("\n" + "=" * 60)
        print("検証結果サマリー")
        print("=" * 60)
        print(f"総テスト数: {total_tests}")
        print(f"成功: {passed_tests}")
        print(f"失敗: {failed_tests}")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "成功率: N/A")

        # パフォーマンス統計
        stats = validator.get_statistics_summary()
        if stats:
            print("\nパフォーマンス統計:")
            print(f"  平均実行時間: {stats.get('avg_execution_time', 0):.2f}秒")
            print(f"  最大実行時間: {stats.get('max_execution_time', 0):.2f}秒")
            print(f"  平均メモリ使用量: {stats.get('avg_memory_usage', 0):.2f}MB")
            print(f"  最大メモリ使用量: {stats.get('max_memory_usage', 0):.2f}MB")

        # 失敗したテストの詳細
        if failed_tests > 0:
            print("\n失敗したテスト:")
            for result in results:
                if not result.success:
                    print(f"  ❌ {result.test_name}")
                    print(f"     エラー: {result.error_message}")
                    print(f"     実行時間: {result.execution_time:.2f}秒")

        # 成功したテストの一覧
        if passed_tests > 0:
            print("\n成功したテスト:")
            for result in results:
                if result.success:
                    print(f"  ✅ {result.test_name} ({result.execution_time:.2f}秒)")

        # 詳細レポートの生成
        try:
            reporter = ValidationReporter(output_dir)
            report_files = reporter.generate_reports(
                validator_name="DataPersistenceValidator",
                results=results,
                statistics=stats,
                config=config
            )

            print("\n詳細レポートを生成しました:")
            for report_file in report_files:
                print(f"  📄 {report_file}")

        except Exception as e:
            print(f"\n⚠️  レポート生成でエラーが発生しました: {e}")

        # 終了コードの決定
        exit_code = 0 if failed_tests == 0 else 1

        print(f"\n検証が完了しました。終了コード: {exit_code}")
        return exit_code

    except KeyboardInterrupt:
        print("\n\n検証が中断されました。")
        return 130

    except Exception as e:
        print(f"\n❌ 検証実行中にエラーが発生しました: {e}")
        import traceback
        if args.verbose:
            print("\nスタックトレース:")
            traceback.print_exc()
        return 1

    finally:
        # クリーンアップ
        if not args.no_cleanup:
            try:
                print("\nテスト環境をクリーンアップ中...")
                validator.teardown_test_environment()
                validator.cleanup()
            except Exception as e:
                print(f"⚠️  クリーンアップでエラーが発生しました: {e}")
        else:
            print("\nクリーンアップをスキップしました（--no-cleanup指定）")


def main():
    """メイン関数"""
    try:
        args = parse_arguments()
        exit_code = run_validation(args)
        sys.exit(exit_code)

    except Exception as e:
        print(f"❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
