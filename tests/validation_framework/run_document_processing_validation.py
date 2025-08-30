#!/usr/bin/env python3
"""
ドキュメント処理機能包括検証の実行スクリプト

DocMindアプリケーションのドキュメント処理機能について
包括的な検証を実行します。
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from validation_framework.base_validator import ValidationConfig
from validation_framework.document_processing_validator import (
    DocumentProcessingValidator,
)
from validation_framework.validation_reporter import ValidationReporter


def setup_logging():
    """ログ設定のセットアップ"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'document_processing_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )


def main():
    """メイン実行関数"""
    print("=" * 80)
    print("DocMind ドキュメント処理機能包括検証")
    print("=" * 80)

    # ログ設定
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # 検証設定の作成
        config = ValidationConfig(
            enable_performance_monitoring=True,
            enable_memory_monitoring=True,
            enable_error_injection=False,
            max_execution_time=300.0,  # 5分
            max_memory_usage=2048.0,   # 2GB
            log_level="INFO",
            output_directory="validation_results"
        )

        logger.info("ドキュメント処理検証を開始します")

        # バリデーターの初期化
        validator = DocumentProcessingValidator(config)

        # テスト環境のセットアップ
        logger.info("テスト環境をセットアップしています...")
        validator.setup_test_environment()

        # 検証の実行
        logger.info("検証を実行しています...")

        # 実行するテストメソッドを指定
        test_methods = [
            'test_pdf_processing_accuracy',
            'test_word_processing_accuracy',
            'test_excel_processing_accuracy',
            'test_text_processing_accuracy',
            'test_markdown_processing_accuracy',
            'test_encoding_detection_accuracy',
            'test_large_file_processing',
            'test_error_handling_robustness',
            'test_processing_performance_requirements',
            'test_concurrent_processing_safety'
        ]

        # 検証実行
        results = validator.run_validation(test_methods)

        # 結果の表示
        print("\n" + "=" * 80)
        print("検証結果サマリー")
        print("=" * 80)

        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - successful_tests

        print(f"総テスト数: {total_tests}")
        print(f"成功: {successful_tests}")
        print(f"失敗: {failed_tests}")
        print(f"成功率: {(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "N/A")

        # 詳細結果の表示
        print("\n詳細結果:")
        print("-" * 80)

        for result in results:
            status = "✓ 成功" if result.success else "✗ 失敗"
            print(f"{status} | {result.test_name}")
            print(f"    実行時間: {result.execution_time:.2f}秒")
            print(f"    メモリ使用量: {result.memory_usage:.2f}MB")

            if not result.success and result.error_message:
                print(f"    エラー: {result.error_message}")

            print()

        # 処理統計の表示
        processing_stats = validator.get_processing_statistics()
        print("処理統計:")
        print("-" * 80)
        print(f"処理ファイル数: {processing_stats['overall_stats']['files_processed']}")
        print(f"成功率: {processing_stats['success_rate']:.2%}")
        print(f"平均処理時間: {processing_stats['average_processing_time']:.2f}秒")
        print(f"平均コンテンツ長: {processing_stats['average_content_length']:.0f}文字")

        # ファイル形式別統計
        if processing_stats['overall_stats']['file_type_stats']:
            print("\nファイル形式別統計:")
            for file_type, stats in processing_stats['overall_stats']['file_type_stats'].items():
                success_rate = (stats['successful'] / stats['processed']) * 100 if stats['processed'] > 0 else 0
                print(f"  {file_type.upper()}: {stats['successful']}/{stats['processed']} ({success_rate:.1f}%)")

        # エラー統計
        if processing_stats['overall_stats']['error_types']:
            print("\nエラー統計:")
            for error_type, count in processing_stats['overall_stats']['error_types'].items():
                print(f"  {error_type}: {count}件")

        # レポート生成
        logger.info("検証レポートを生成しています...")

        reporter = ValidationReporter()
        report_data = {
            'validation_type': 'document_processing',
            'timestamp': datetime.now(),
            'config': config.__dict__,
            'results': results,
            'statistics': processing_stats,
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'success_rate': (successful_tests/total_tests) if total_tests > 0 else 0
            }
        }

        # レポートファイルの生成
        os.makedirs(config.output_directory, exist_ok=True)

        # HTMLレポート
        html_report_path = os.path.join(
            config.output_directory,
            f"document_processing_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        reporter.generate_html_report(report_data, html_report_path)

        # JSONレポート
        json_report_path = os.path.join(
            config.output_directory,
            f"document_processing_validation_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        reporter.generate_json_report(report_data, json_report_path)

        print("\nレポートが生成されました:")
        print(f"  HTML: {html_report_path}")
        print(f"  JSON: {json_report_path}")

        # 全体的な結果判定
        overall_success = failed_tests == 0 and processing_stats['success_rate'] >= 0.8

        if overall_success:
            print("\n🎉 ドキュメント処理機能検証が正常に完了しました！")
            logger.info("ドキュメント処理機能検証が正常に完了しました")
            exit_code = 0
        else:
            print("\n⚠️  ドキュメント処理機能検証で問題が検出されました。")
            logger.warning("ドキュメント処理機能検証で問題が検出されました")
            exit_code = 1

    except Exception as e:
        logger.error(f"検証実行中にエラーが発生しました: {e}")
        print(f"\n❌ 検証実行中にエラーが発生しました: {e}")
        exit_code = 2

    finally:
        # クリーンアップ
        try:
            if 'validator' in locals():
                validator.teardown_test_environment()
                validator.cleanup()
        except Exception as e:
            logger.warning(f"クリーンアップ中にエラーが発生しました: {e}")

    print("\n" + "=" * 80)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
