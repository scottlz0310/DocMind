#!/usr/bin/env python3
"""
互換性・移植性検証実行スクリプト

DocMindアプリケーションの環境互換性を包括的に検証します。
Windows 10/11環境での全機能動作、異なる画面解像度とファイルシステムでの動作、
異なる文字エンコーディングファイルの処理、限定リソース環境での動作を検証します。

使用方法:
    python run_compatibility_validation.py [オプション]

オプション:
    --output-dir: 結果出力ディレクトリ（デフォルト: validation_results/compatibility）
    --log-level: ログレベル（DEBUG, INFO, WARNING, ERROR）
    --enable-performance-monitoring: パフォーマンス監視を有効化
    --enable-memory-monitoring: メモリ監視を有効化
    --test-methods: 実行するテストメソッド（カンマ区切り）
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from tests.validation_framework.base_validator import ValidationConfig
    from tests.validation_framework.compatibility_validator import (
        CompatibilityValidator,
    )
    from tests.validation_framework.validation_reporter import ValidationReporter
except ImportError as e:
    print(f"インポートエラー: {e}")
    print("プロジェクトルートから実行してください")
    sys.exit(1)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """ログ設定のセットアップ"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                f'compatibility_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
                encoding='utf-8'
            )
        ]
    )
    return logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """コマンドライン引数の解析"""
    parser = argparse.ArgumentParser(
        description="DocMind互換性・移植性検証ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
検証項目:
  1. Windows 10/11環境での全機能動作検証
  2. 異なる画面解像度とファイルシステムでの動作検証
  3. 異なる文字エンコーディングファイルの処理検証
  4. 限定リソース環境での動作検証
  5. 包括的互換性監査

例:
  # 基本的な互換性検証
  python run_compatibility_validation.py

  # 特定のテストのみ実行
  python run_compatibility_validation.py --test-methods test_windows_environment_compatibility

  # 詳細ログで実行
  python run_compatibility_validation.py --log-level DEBUG
        """
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='validation_results/compatibility',
        help='結果出力ディレクトリ（デフォルト: validation_results/compatibility）'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='ログレベル（デフォルト: INFO）'
    )

    parser.add_argument(
        '--enable-performance-monitoring',
        action='store_true',
        help='パフォーマンス監視を有効化'
    )

    parser.add_argument(
        '--enable-memory-monitoring',
        action='store_true',
        help='メモリ監視を有効化'
    )

    parser.add_argument(
        '--test-methods',
        type=str,
        help='実行するテストメソッド（カンマ区切り）'
    )

    parser.add_argument(
        '--max-execution-time',
        type=float,
        default=600.0,
        help='最大実行時間（秒、デフォルト: 600）'
    )

    parser.add_argument(
        '--max-memory-usage',
        type=float,
        default=4096.0,
        help='最大メモリ使用量（MB、デフォルト: 4096）'
    )

    return parser.parse_args()


def create_validation_config(args: argparse.Namespace) -> ValidationConfig:
    """検証設定の作成"""
    return ValidationConfig(
        enable_performance_monitoring=args.enable_performance_monitoring,
        enable_memory_monitoring=args.enable_memory_monitoring,
        max_execution_time=args.max_execution_time,
        max_memory_usage=args.max_memory_usage,
        log_level=args.log_level,
        output_directory=args.output_dir
    )


def run_compatibility_validation(args: argparse.Namespace) -> bool:
    """互換性検証の実行"""
    logger = setup_logging(args.log_level)
    logger.info("DocMind互換性・移植性検証を開始します")

    try:
        # 出力ディレクトリの作成
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 検証設定の作成
        config = create_validation_config(args)

        # 互換性検証クラスの初期化
        validator = CompatibilityValidator(config)

        # テスト環境のセットアップ
        logger.info("テスト環境をセットアップします")
        validator.setup_test_environment()

        # 実行するテストメソッドの決定
        test_methods = None
        if args.test_methods:
            test_methods = [method.strip() for method in args.test_methods.split(',')]
            logger.info(f"指定されたテストメソッド: {test_methods}")

        # 検証の実行
        logger.info("互換性検証を実行します")
        start_time = datetime.now()

        validation_results = validator.run_validation(test_methods)

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        # 結果の分析
        successful_tests = sum(1 for result in validation_results if result.success)
        total_tests = len(validation_results)
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0

        logger.info("互換性検証が完了しました")
        logger.info(f"実行時間: {execution_time:.2f}秒")
        logger.info(f"テスト結果: {successful_tests}/{total_tests} ({success_rate:.1f}%)")

        # 互換性メトリクスの取得
        compatibility_metrics = validator.compatibility_metrics

        # 統計情報の取得
        statistics_raw = validator.get_statistics_summary()

        # 統計情報をJSON serializable形式に変換
        statistics = {}
        for key, value in statistics_raw.items():
            if hasattr(value, 'to_dict'):
                statistics[key] = value.to_dict()
            elif isinstance(value, list | tuple):
                statistics[key] = [
                    item.to_dict() if hasattr(item, 'to_dict') else item
                    for item in value
                ]
            else:
                statistics[key] = value

        # 結果の保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON形式での結果保存
        results_data = {
            'timestamp': timestamp,
            'execution_time_seconds': execution_time,
            'test_summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': success_rate
            },
            'validation_results': [
                {
                    'test_name': result.test_name,
                    'success': result.success,
                    'execution_time': result.execution_time,
                    'memory_usage': result.memory_usage,
                    'error_message': result.error_message,
                    'details': result.details
                }
                for result in validation_results
            ],
            'compatibility_metrics': [
                {
                    'test_name': metric.test_name,
                    'compatibility_level': metric.compatibility_level,
                    'os_version': metric.os_version,
                    'python_version': metric.python_version,
                    'memory_available_mb': metric.memory_available_mb,
                    'disk_space_available_mb': metric.disk_space_available_mb,
                    'screen_resolution': metric.screen_resolution,
                    'filesystem_type': metric.filesystem_type,
                    'encoding_support': metric.encoding_support,
                    'feature_compatibility': metric.feature_compatibility,
                    'performance_metrics': metric.performance_metrics,
                    'limitations': metric.limitations,
                    'recommendations': metric.recommendations,
                    'additional_details': metric.additional_details
                }
                for metric in compatibility_metrics
            ],
            'statistics': statistics,
            'configuration': {
                'performance_monitoring': config.enable_performance_monitoring,
                'memory_monitoring': config.enable_memory_monitoring,
                'max_execution_time': config.max_execution_time,
                'max_memory_usage': config.max_memory_usage
            }
        }

        results_file = output_dir / f"compatibility_validation_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)

        logger.info(f"結果をJSONファイルに保存しました: {results_file}")

        # HTMLレポートの生成
        try:
            reporter = ValidationReporter()
            html_report = reporter.generate_compatibility_report(
                validation_results,
                compatibility_metrics,
                statistics
            )

            report_file = output_dir / f"compatibility_report_{timestamp}.html"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_report)

            logger.info(f"HTMLレポートを生成しました: {report_file}")

        except Exception as e:
            logger.warning(f"HTMLレポート生成に失敗しました: {e}")

        # テスト環境のクリーンアップ
        logger.info("テスト環境をクリーンアップします")
        validator.teardown_test_environment()
        validator.cleanup()

        # 結果の判定
        overall_success = success_rate >= 80.0  # 80%以上で成功とする

        if overall_success:
            logger.info("✅ 互換性検証が成功しました")
        else:
            logger.error("❌ 互換性検証で問題が検出されました")

        # 互換性レベルの表示
        compatibility_levels = [metric.compatibility_level for metric in compatibility_metrics]
        if compatibility_levels:
            level_counts = {
                'COMPATIBLE': compatibility_levels.count('COMPATIBLE'),
                'LIMITED': compatibility_levels.count('LIMITED'),
                'INCOMPATIBLE': compatibility_levels.count('INCOMPATIBLE')
            }

            logger.info("互換性レベル分布:")
            for level, count in level_counts.items():
                if count > 0:
                    logger.info(f"  {level}: {count}件")

        # 推奨事項の表示
        all_recommendations = []
        for metric in compatibility_metrics:
            all_recommendations.extend(metric.recommendations)

        if all_recommendations:
            logger.info("推奨事項:")
            unique_recommendations = list(set(all_recommendations))[:5]
            for i, recommendation in enumerate(unique_recommendations, 1):
                logger.info(f"  {i}. {recommendation}")

        return overall_success

    except Exception as e:
        logger.error(f"互換性検証中にエラーが発生しました: {e}")
        logger.exception("詳細なエラー情報:")
        return False


def main():
    """メイン関数"""
    args = parse_arguments()

    try:
        success = run_compatibility_validation(args)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n検証が中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
