#!/usr/bin/env python3
"""
セキュリティ・プライバシー検証実行スクリプト

DocMindアプリケーションのセキュリティ要件を包括的に検証します。
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from tests.validation_framework.base_validator import ValidationConfig
    from tests.validation_framework.security_validator import SecurityValidator
    from tests.validation_framework.validation_reporter import ValidationReporter
except ImportError as e:
    print(f"インポートエラー: {e}")
    print("プロジェクトルートから実行してください")
    sys.exit(1)


def setup_logging() -> logging.Logger:
    """ログ設定のセットアップ"""
    logger = logging.getLogger("security_validation")
    logger.setLevel(logging.INFO)

    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # ファイルハンドラー
    log_dir = project_root / "validation_results" / "security"
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"security_validation_{timestamp}.log"

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


def run_security_validation(quick_mode: bool = False) -> bool:
    """
    セキュリティ検証の実行

    Args:
        quick_mode: クイックモード（短時間での実行）

    Returns:
        検証成功の場合True
    """
    logger = setup_logging()
    logger.info("=== DocMind セキュリティ・プライバシー検証開始 ===")

    try:
        # 検証設定
        config = ValidationConfig(
            enable_performance_monitoring=True,
            enable_memory_monitoring=True,
            enable_error_injection=False,
            max_execution_time=600.0 if not quick_mode else 180.0,  # 10分 or 3分
            max_memory_usage=2048.0,
            log_level="INFO",
            output_directory=str(project_root / "validation_results" / "security")
        )

        # セキュリティ検証器の初期化
        validator = SecurityValidator(config)

        # テスト環境のセットアップ
        logger.info("テスト環境をセットアップしています...")
        validator.setup_test_environment()

        # 検証の実行
        logger.info("セキュリティ検証を実行しています...")

        if quick_mode:
            # クイックモード: 基本的なセキュリティテストのみ
            test_methods = [
                'test_local_processing_verification',
                'test_file_access_permissions_verification',
                'test_data_encryption_verification'
            ]
        else:
            # フルモード: 全セキュリティテスト
            test_methods = [
                'test_local_processing_verification',
                'test_file_access_permissions_verification',
                'test_data_encryption_verification',
                'test_privacy_protection_verification',
                'test_comprehensive_security_audit'
            ]

        validation_results = validator.run_validation(test_methods)

        # 結果の分析
        logger.info("検証結果を分析しています...")
        security_summary = validator.get_security_summary()

        # 結果の表示
        logger.info("=== セキュリティ検証結果サマリー ===")
        logger.info(f"実行テスト数: {security_summary['test_summary']['total_tests']}")
        logger.info(f"セキュアなテスト: {security_summary['test_summary']['secure_tests']}")
        logger.info(f"警告レベル: {security_summary['test_summary']['warning_tests']}")
        logger.info(f"重大レベル: {security_summary['test_summary']['critical_tests']}")
        logger.info(f"総合セキュリティレベル: {security_summary['test_summary']['overall_security_level']}")
        logger.info(f"平均コンプライアンススコア: {security_summary['compliance_statistics']['average_compliance_score']:.2f}")

        # 脆弱性の表示
        if security_summary['vulnerability_analysis']['total_vulnerabilities'] > 0:
            logger.warning("=== 検出された脆弱性 ===")
            for vuln in security_summary['vulnerability_analysis']['vulnerability_list']:
                logger.warning(f"- {vuln}")
        else:
            logger.info("脆弱性は検出されませんでした")

        # レポート生成
        logger.info("検証レポートを生成しています...")
        reporter = ValidationReporter()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_data = {
            'validation_type': 'security',
            'timestamp': timestamp,
            'results': validation_results,
            'summary': security_summary,
            'validator_config': {
                'quick_mode': quick_mode,
                'test_methods': test_methods
            }
        }

        # HTMLレポートの生成
        output_dir = project_root / "validation_results" / "security"
        html_report_path = reporter.generate_html_report(
            report_data,
            str(output_dir / f"security_report_{timestamp}.html")
        )

        # JSONレポートの生成
        json_report_path = reporter.generate_json_report(
            report_data,
            str(output_dir / f"security_validation_results_{timestamp}.json")
        )

        logger.info(f"HTMLレポート: {html_report_path}")
        logger.info(f"JSONレポート: {json_report_path}")

        # 成功判定
        overall_security_level = security_summary['test_summary']['overall_security_level']
        success = overall_security_level in ['SECURE', 'WARNING']

        if success:
            logger.info("=== セキュリティ検証完了: 合格 ===")
        else:
            logger.error("=== セキュリティ検証完了: 不合格 ===")

        return success

    except Exception as e:
        logger.error(f"セキュリティ検証中にエラーが発生しました: {e}")
        logger.exception("詳細なエラー情報:")
        return False

    finally:
        # クリーンアップ
        try:
            validator.teardown_test_environment()
            validator.cleanup()
        except:
            pass


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="DocMind セキュリティ・プライバシー検証",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python run_security_validation.py                    # フル検証
  python run_security_validation.py --quick           # クイック検証
  python run_security_validation.py --help            # ヘルプ表示
        """
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='クイックモードで実行（基本テストのみ、短時間）'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細ログを表示'
    )

    args = parser.parse_args()

    # ログレベルの設定
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 検証の実行
    success = run_security_validation(quick_mode=args.quick)

    # 終了コード
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
