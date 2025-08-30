#!/usr/bin/env python3
"""
エラーハンドリング・回復機能検証実行スクリプト

DocMindアプリケーションのエラーハンドリング機能と回復機能を
包括的に検証するためのスクリプトです。
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tests.validation_framework.base_validator import ValidationConfig
from tests.validation_framework.error_handling_validator import ErrorHandlingValidator
from tests.validation_framework.validation_reporter import ValidationReporter


def setup_logging() -> logging.Logger:
    """ログ設定のセットアップ"""
    # ログディレクトリの作成
    log_dir = Path("validation_results/error_handling")
    log_dir.mkdir(parents=True, exist_ok=True)

    # ログファイル名（タイムスタンプ付き）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"error_handling_validation_{timestamp}.log"

    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"エラーハンドリング検証ログを開始: {log_file}")

    return logger


def create_validation_config() -> ValidationConfig:
    """検証設定の作成"""
    return ValidationConfig(
        enable_performance_monitoring=True,
        enable_memory_monitoring=True,
        enable_error_injection=True,
        max_execution_time=600.0,  # 10分
        max_memory_usage=2048.0,  # 2GB
        log_level="INFO",
        output_directory="validation_results/error_handling",
    )


def run_error_handling_validation() -> dict[str, Any]:
    """エラーハンドリング検証の実行"""
    logger = setup_logging()
    logger.info("=== DocMind エラーハンドリング・回復機能検証を開始 ===")

    # 検証設定の作成
    config = create_validation_config()

    # 検証結果の初期化
    validation_results = {
        "start_time": datetime.now().isoformat(),
        "validation_type": "error_handling_recovery",
        "config": {
            "performance_monitoring": config.enable_performance_monitoring,
            "memory_monitoring": config.enable_memory_monitoring,
            "error_injection": config.enable_error_injection,
            "max_execution_time": config.max_execution_time,
            "max_memory_usage": config.max_memory_usage,
        },
        "results": {},
        "summary": {},
        "errors": [],
    }

    try:
        # エラーハンドリング検証の実行
        logger.info("エラーハンドリング検証クラスを初期化します")
        validator = ErrorHandlingValidator(config)

        # テスト環境のセットアップ
        logger.info("テスト環境をセットアップします")
        validator.setup_test_environment()

        # 検証の実行
        logger.info("エラーハンドリング検証を実行します")
        test_results = validator.run_validation()

        # 詳細結果の取得
        detailed_summary = validator.get_validation_summary()

        # 結果の整理
        validation_results["results"] = {
            "test_results": [
                {
                    "test_name": result.test_name,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "memory_usage": result.memory_usage,
                    "error_message": result.error_message,
                    "details": result.details,
                }
                for result in test_results
            ],
            "detailed_summary": detailed_summary,
        }

        # サマリーの作成
        total_tests = len(test_results)
        successful_tests = sum(1 for result in test_results if result.success)
        failed_tests = total_tests - successful_tests

        validation_results["summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0.0,
            "average_execution_time": (
                sum(r.execution_time for r in test_results) / total_tests
                if total_tests > 0
                else 0.0
            ),
            "peak_memory_usage": max(
                (r.memory_usage for r in test_results), default=0.0
            ),
            "exception_handling": detailed_summary.get("exception_handling", {}),
            "recovery_mechanisms": detailed_summary.get("recovery_mechanisms", {}),
            "graceful_degradation": detailed_summary.get("graceful_degradation", {}),
            "system_health": detailed_summary.get("system_health", {}),
        }

        # パフォーマンス要件の検証
        performance_issues = []
        for result in test_results:
            if result.execution_time > config.max_execution_time:
                performance_issues.append(
                    {
                        "test_name": result.test_name,
                        "issue": "execution_time_exceeded",
                        "actual": result.execution_time,
                        "limit": config.max_execution_time,
                    }
                )

            if result.memory_usage > config.max_memory_usage:
                performance_issues.append(
                    {
                        "test_name": result.test_name,
                        "issue": "memory_usage_exceeded",
                        "actual": result.memory_usage,
                        "limit": config.max_memory_usage,
                    }
                )

        validation_results["performance_issues"] = performance_issues

        # 検証結果の評価
        overall_success = (
            failed_tests == 0
            and len(performance_issues) == 0
            and validation_results["summary"]["success_rate"] >= 0.95
        )

        validation_results["overall_success"] = overall_success

        # 結果の出力
        logger.info("=== エラーハンドリング検証結果サマリー ===")
        logger.info(f"総テスト数: {total_tests}")
        logger.info(f"成功: {successful_tests}")
        logger.info(f"失敗: {failed_tests}")
        logger.info(f"成功率: {validation_results['summary']['success_rate']:.1%}")
        logger.info(
            f"平均実行時間: {validation_results['summary']['average_execution_time']:.2f}秒"
        )
        logger.info(
            f"最大メモリ使用量: {validation_results['summary']['peak_memory_usage']:.2f}MB"
        )

        # 例外処理結果
        exception_summary = detailed_summary.get("exception_handling", {})
        logger.info(
            f"例外処理テスト: {exception_summary.get('successful_handling', 0)}/{exception_summary.get('total_tests', 0)}"
        )

        # 回復機能結果
        recovery_summary = detailed_summary.get("recovery_mechanisms", {})
        logger.info(
            f"回復機能テスト: {recovery_summary.get('successful_recovery', 0)}/{recovery_summary.get('total_tests', 0)}"
        )

        # 劣化機能結果
        degradation_summary = detailed_summary.get("graceful_degradation", {})
        logger.info(
            f"劣化機能テスト: {degradation_summary.get('successful_degradation', 0)}/{degradation_summary.get('total_tests', 0)}"
        )

        # パフォーマンス問題の報告
        if performance_issues:
            logger.warning(
                f"パフォーマンス問題が検出されました: {len(performance_issues)}件"
            )
            for issue in performance_issues:
                logger.warning(
                    f"  - {issue['test_name']}: {issue['issue']} (実際: {issue['actual']}, 制限: {issue['limit']})"
                )

        # 全体的な成功/失敗の判定
        if overall_success:
            logger.info("✓ エラーハンドリング検証が成功しました")
        else:
            logger.error("✗ エラーハンドリング検証で問題が検出されました")

    except Exception as e:
        logger.error(f"エラーハンドリング検証中にエラーが発生: {e}")
        validation_results["errors"].append(
            {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat(),
            }
        )
        validation_results["overall_success"] = False

    finally:
        # クリーンアップ
        try:
            if "validator" in locals():
                validator.teardown_test_environment()
                validator.cleanup()
        except Exception as cleanup_error:
            logger.warning(f"クリーンアップ中にエラー: {cleanup_error}")

    # 終了時刻の記録
    validation_results["end_time"] = datetime.now().isoformat()

    return validation_results


def save_validation_results(results: dict[str, Any]) -> Path:
    """検証結果をファイルに保存"""
    # 結果ディレクトリの作成
    results_dir = Path("validation_results/error_handling")
    results_dir.mkdir(parents=True, exist_ok=True)

    # 結果ファイル名（タイムスタンプ付き）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"error_handling_validation_results_{timestamp}.json"

    # JSON形式で保存
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    return results_file


def generate_validation_report(results: dict[str, Any]) -> Path:
    """検証レポートの生成"""
    try:
        reporter = ValidationReporter()
        report_path = reporter.generate_error_handling_report(results)
        return report_path
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"レポート生成中にエラー: {e}")
        return None


def main():
    """メイン実行関数"""
    print("DocMind エラーハンドリング・回復機能検証を開始します...")

    try:
        # 検証の実行
        results = run_error_handling_validation()

        # 結果の保存
        results_file = save_validation_results(results)
        print(f"検証結果を保存しました: {results_file}")

        # レポートの生成
        report_path = generate_validation_report(results)
        if report_path:
            print(f"検証レポートを生成しました: {report_path}")

        # 終了コードの決定
        if results.get("overall_success", False):
            print("✓ エラーハンドリング検証が成功しました")
            sys.exit(0)
        else:
            print("✗ エラーハンドリング検証で問題が検出されました")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n検証が中断されました")
        sys.exit(130)
    except Exception as e:
        print(f"検証実行中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
