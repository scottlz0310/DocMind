#!/usr/bin/env python3
"""
検索機能包括検証実行スクリプト

SearchFunctionalityValidatorを使用して検索機能の包括的な検証を実行します。
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .base_validator import ValidationConfig
from .search_functionality_validator import SearchFunctionalityValidator
from .validation_reporter import ValidationReporter


def setup_logging():
    """ログ設定のセットアップ"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                f'search_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            ),
        ],
    )


def main():
    """メイン実行関数"""
    print("=" * 80)
    print("DocMind 検索機能包括検証")
    print("=" * 80)

    # ログ設定
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # 検証設定
        config = ValidationConfig(
            enable_performance_monitoring=True,
            enable_memory_monitoring=True,
            enable_error_injection=False,
            max_execution_time=300.0,  # 5分
            max_memory_usage=2048.0,  # 2GB
            log_level="INFO",
        )

        # 検証クラスの初期化
        logger.info("SearchFunctionalityValidatorを初期化中...")
        validator = SearchFunctionalityValidator(config)

        # テスト環境のセットアップ
        logger.info("テスト環境をセットアップ中...")
        validator.setup_test_environment()

        try:
            # 検証の実行
            logger.info("検索機能の包括検証を開始します...")

            # 実行するテストメソッドを指定
            test_methods = [
                "test_full_text_search_accuracy",
                "test_semantic_search_accuracy",
                "test_hybrid_search_accuracy",
                "test_search_performance_requirements",
                "test_large_dataset_scalability",
                "test_search_filters",
                "test_concurrent_search",
                "test_search_suggestions",
            ]

            # 検証実行
            results = validator.run_validation(test_methods)

            # 結果の表示
            print("\n" + "=" * 80)
            print("検証結果サマリー")
            print("=" * 80)

            success_count = sum(1 for r in results if r.success)
            total_count = len(results)

            print(f"実行テスト数: {total_count}")
            print(f"成功: {success_count}")
            print(f"失敗: {total_count - success_count}")
            print(f"成功率: {success_count / total_count * 100:.1f}%")

            # 詳細結果の表示
            print("\n詳細結果:")
            print("-" * 80)
            for result in results:
                status = "✓" if result.success else "✗"
                print(f"{status} {result.test_name}")
                print(f"   実行時間: {result.execution_time:.2f}秒")
                print(f"   メモリ使用量: {result.memory_usage:.2f}MB")
                if not result.success:
                    print(f"   エラー: {result.error_message}")
                print()

            # 検索メトリクスサマリーの表示
            metrics_summary = validator.get_search_metrics_summary()
            if metrics_summary:
                print("検索パフォーマンスサマリー:")
                print("-" * 80)
                print(f"総検索回数: {metrics_summary['total_searches']}")
                print(f"平均実行時間: {metrics_summary['overall_avg_time']:.2f}秒")
                print(f"最大実行時間: {metrics_summary['overall_max_time']:.2f}秒")
                print(
                    f"パフォーマンス要件達成: {'✓' if metrics_summary['performance_requirement_met'] else '✗'}"
                )
                print(
                    f"メモリ要件達成: {'✓' if metrics_summary['memory_requirement_met'] else '✗'}"
                )

                # 検索タイプ別統計
                for search_type, stats in metrics_summary["by_type"].items():
                    print(f"\n{search_type}検索:")
                    print(f"  検索回数: {stats['count']}")
                    print(f"  平均実行時間: {stats['avg_execution_time']:.2f}秒")
                    print(f"  平均結果数: {stats['avg_result_count']:.1f}")
                    if stats["avg_precision"] is not None:
                        print(f"  平均精度: {stats['avg_precision']:.2f}")
                    if stats["avg_recall"] is not None:
                        print(f"  平均再現率: {stats['avg_recall']:.2f}")

            # 統計情報の表示
            stats_summary = validator.get_statistics_summary()
            if stats_summary:
                print("\n統計情報:")
                print("-" * 80)
                for key, value in stats_summary.items():
                    print(f"{key}: {value}")

            # レポート生成
            reporter = ValidationReporter()
            report_path = f"search_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            reporter.generate_html_report(
                results, report_path, "検索機能包括検証レポート"
            )
            print(f"\n詳細レポートが生成されました: {report_path}")

            # 全体的な成功/失敗の判定
            overall_success = success_count == total_count
            if overall_success:
                print("\n🎉 すべての検証が成功しました！")
                return 0
            else:
                print(f"\n❌ {total_count - success_count}個の検証が失敗しました。")
                return 1

        finally:
            # テスト環境のクリーンアップ
            logger.info("テスト環境をクリーンアップ中...")
            validator.teardown_test_environment()
            validator.cleanup()

    except Exception as e:
        logger.error(f"検証実行中にエラーが発生しました: {e}")
        print(f"\n❌ 検証実行中にエラーが発生しました: {e}")
        return 1

    finally:
        print("\n検索機能包括検証が完了しました。")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
