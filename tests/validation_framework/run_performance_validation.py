#!/usr/bin/env python3
"""
パフォーマンス・スケーラビリティ検証実行スクリプト

DocMindアプリケーションのパフォーマンス要件を包括的に検証します。
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.validation_framework.base_validator import ValidationConfig
from tests.validation_framework.performance_validator import PerformanceValidator
from tests.validation_framework.validation_reporter import ValidationReporter


def setup_logging(log_level: str = "INFO") -> None:
    """ログ設定のセットアップ"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                f'performance_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            ),
        ],
    )


def create_validation_config(quick_mode: bool = False) -> ValidationConfig:
    """検証設定の作成"""
    return ValidationConfig(
        enable_performance_monitoring=True,
        enable_memory_monitoring=True,
        enable_error_injection=False,
        max_execution_time=1800.0 if not quick_mode else 300.0,  # 30分 or 5分
        max_memory_usage=4096.0,  # 4GB
        log_level="INFO",
        output_directory="validation_results/performance",
    )


def run_performance_validation(
    quick_mode: bool = False, custom_thresholds: dict = None
) -> bool:
    """
    パフォーマンス検証の実行

    Args:
        quick_mode: クイックモードで実行するかどうか
        custom_thresholds: カスタム閾値設定

    Returns:
        検証が成功した場合True
    """
    logger = logging.getLogger(__name__)
    logger.info("パフォーマンス・スケーラビリティ検証を開始します")

    # 検証設定の作成
    config = create_validation_config(quick_mode)

    # 出力ディレクトリの作成
    os.makedirs(config.output_directory, exist_ok=True)

    # パフォーマンス検証器の初期化
    validator = PerformanceValidator(config)

    # カスタム閾値の適用
    if custom_thresholds:
        for key, value in custom_thresholds.items():
            if hasattr(validator.thresholds, key):
                setattr(validator.thresholds, key, value)
                logger.info(f"閾値を設定: {key} = {value}")

    # クイックモードの設定
    if quick_mode:
        validator.quick_mode = True
        validator.large_test_enabled = False
        logger.info("クイックモードで実行します")

    try:
        # テスト環境のセットアップ
        validator.setup_test_environment()

        # 検証テストの実行
        test_methods = [
            "test_search_performance_requirements",
            "test_indexing_performance_requirements",
            "test_memory_efficiency_requirements",
            "test_cpu_usage_requirements",
        ]

        # 大規模テストの追加（クイックモードでない場合）
        if not quick_mode:
            test_methods.append("test_large_dataset_scalability")

        # 検証実行
        results = validator.run_validation(test_methods)

        # 結果の分析
        success_count = sum(1 for result in results if result.success)
        total_count = len(results)

        logger.info(f"検証完了: {success_count}/{total_count} テストが成功")

        # 詳細レポートの生成
        reporter = ValidationReporter(config.output_directory)

        # パフォーマンス要約の取得
        performance_summary = validator.get_performance_summary()

        # レポート生成
        report_data = {
            "validation_type": "performance",
            "execution_time": datetime.now().isoformat(),
            "configuration": {
                "quick_mode": quick_mode,
                "thresholds": {
                    "search_time_seconds": validator.thresholds.search_time_seconds,
                    "indexing_time_seconds": validator.thresholds.indexing_time_seconds,
                    "memory_usage_mb": validator.thresholds.memory_usage_mb,
                    "cpu_idle_percent": validator.thresholds.cpu_idle_percent,
                    "large_dataset_documents": validator.thresholds.large_dataset_documents,
                },
            },
            "test_results": [
                {
                    "test_name": result.test_name,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "memory_usage": result.memory_usage,
                    "error_message": result.error_message,
                    "details": result.details,
                }
                for result in results
            ],
            "performance_summary": performance_summary,
            "overall_success": success_count == total_count,
        }

        # HTMLレポートの生成
        html_report_path = reporter.generate_html_report(
            report_data,
            f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
        )

        # JSONレポートの生成
        json_report_path = reporter.generate_json_report(
            report_data,
            f"performance_validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

        logger.info(f"HTMLレポート: {html_report_path}")
        logger.info(f"JSONレポート: {json_report_path}")

        # 統計情報の表示
        logger.info("=== パフォーマンス検証結果サマリー ===")
        logger.info(f"実行テスト数: {total_count}")
        logger.info(f"成功テスト数: {success_count}")
        logger.info(f"成功率: {success_count/total_count*100:.1f}%")

        if performance_summary.get("performance_statistics"):
            stats = performance_summary["performance_statistics"]
            logger.info(f"平均実行時間: {stats['execution_time']['average']:.2f}秒")
            logger.info(f"最大メモリ使用量: {stats['memory_usage_mb']['max']:.1f}MB")
            logger.info(f"平均CPU使用率: {stats['cpu_usage_percent']['average']:.1f}%")

        # 閾値コンプライアンスの表示
        if performance_summary.get("threshold_compliance"):
            compliance = performance_summary["threshold_compliance"]
            logger.info("=== 閾値コンプライアンス ===")
            logger.info(f"検索時間要件: {'✓' if compliance['search_time'] else '✗'}")
            logger.info(
                f"メモリ使用量要件: {'✓' if compliance['memory_usage'] else '✗'}"
            )
            logger.info(f"CPU使用率要件: {'✓' if compliance['cpu_usage'] else '✗'}")

        return success_count == total_count

    except Exception as e:
        logger.error(f"パフォーマンス検証中にエラーが発生しました: {e}")
        return False

    finally:
        # クリーンアップ
        try:
            validator.teardown_test_environment()
            validator.cleanup()
        except Exception as e:
            logger.warning(f"クリーンアップ中にエラーが発生しました: {e}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="DocMind パフォーマンス・スケーラビリティ検証"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="クイックモードで実行（テストデータを削減）",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="ログレベル",
    )

    parser.add_argument(
        "--search-time-threshold", type=float, default=5.0, help="検索時間の閾値（秒）"
    )

    parser.add_argument(
        "--memory-threshold",
        type=float,
        default=2048.0,
        help="メモリ使用量の閾値（MB）",
    )

    parser.add_argument(
        "--cpu-threshold", type=float, default=10.0, help="CPU使用率の閾値（%）"
    )

    args = parser.parse_args()

    # ログ設定
    setup_logging(args.log_level)

    # カスタム閾値の設定
    custom_thresholds = {
        "search_time_seconds": args.search_time_threshold,
        "memory_usage_mb": args.memory_threshold,
        "cpu_idle_percent": args.cpu_threshold,
    }

    # 検証実行
    success = run_performance_validation(
        quick_mode=args.quick, custom_thresholds=custom_thresholds
    )

    # 終了コード
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
