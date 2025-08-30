#!/usr/bin/env python3
"""
実環境シミュレーション実行スクリプト

DocMindアプリケーションの実環境シミュレーション機能を実行し、
典型的な使用パターン、エッジケース、ユーザーシナリオを検証します。
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
    from tests.validation_framework.real_world_simulator import RealWorldSimulator
    from tests.validation_framework.validation_reporter import ValidationReporter
except ImportError as e:
    print(f"モジュールのインポートに失敗しました: {e}")
    sys.exit(1)


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """ログ設定のセットアップ"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # ログレベルの設定
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'無効なログレベル: {log_level}')

    # ログ設定
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # ファイル出力の追加
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)


def create_validation_config(args) -> ValidationConfig:
    """検証設定の作成"""
    return ValidationConfig(
        enable_performance_monitoring=args.enable_performance,
        enable_memory_monitoring=args.enable_memory,
        enable_error_injection=args.enable_error_injection,
        max_execution_time=args.max_execution_time,
        max_memory_usage=args.max_memory_usage,
        log_level=args.log_level,
        output_directory=args.output_dir
    )


def run_usage_pattern_tests(simulator: RealWorldSimulator, patterns: list) -> dict:
    """使用パターンテストの実行"""
    results = {}

    if not patterns or 'daily' in patterns:
        print("\n=== 日次使用パターンテスト ===")
        try:
            simulator.test_daily_usage_pattern()
            results['daily'] = {'status': 'success', 'message': '日次使用パターンテスト完了'}
        except Exception as e:
            results['daily'] = {'status': 'failed', 'message': str(e)}
            print(f"日次使用パターンテスト失敗: {e}")

    if not patterns or 'weekly' in patterns:
        print("\n=== 週次使用パターンテスト ===")
        try:
            simulator.test_weekly_usage_pattern()
            results['weekly'] = {'status': 'success', 'message': '週次使用パターンテスト完了'}
        except Exception as e:
            results['weekly'] = {'status': 'failed', 'message': str(e)}
            print(f"週次使用パターンテスト失敗: {e}")

    if not patterns or 'monthly' in patterns:
        print("\n=== 月次使用パターンテスト ===")
        try:
            simulator.test_monthly_usage_pattern()
            results['monthly'] = {'status': 'success', 'message': '月次使用パターンテスト完了'}
        except Exception as e:
            results['monthly'] = {'status': 'failed', 'message': str(e)}
            print(f"月次使用パターンテスト失敗: {e}")

    return results


def run_edge_case_tests(simulator: RealWorldSimulator, edge_cases: list) -> dict:
    """エッジケーステストの実行"""
    results = {}

    if not edge_cases or 'large_files' in edge_cases:
        print("\n=== 大容量ファイルエッジケーステスト ===")
        try:
            simulator.test_large_files_edge_case()
            results['large_files'] = {'status': 'success', 'message': '大容量ファイルテスト完了'}
        except Exception as e:
            results['large_files'] = {'status': 'failed', 'message': str(e)}
            print(f"大容量ファイルテスト失敗: {e}")

    if not edge_cases or 'many_files' in edge_cases:
        print("\n=== 多数ファイルエッジケーステスト ===")
        try:
            simulator.test_many_files_edge_case()
            results['many_files'] = {'status': 'success', 'message': '多数ファイルテスト完了'}
        except Exception as e:
            results['many_files'] = {'status': 'failed', 'message': str(e)}
            print(f"多数ファイルテスト失敗: {e}")

    if not edge_cases or 'special_chars' in edge_cases:
        print("\n=== 特殊文字エッジケーステスト ===")
        try:
            simulator.test_special_characters_edge_case()
            results['special_chars'] = {'status': 'success', 'message': '特殊文字テスト完了'}
        except Exception as e:
            results['special_chars'] = {'status': 'failed', 'message': str(e)}
            print(f"特殊文字テスト失敗: {e}")

    return results


def run_user_scenario_tests(simulator: RealWorldSimulator, scenarios: list) -> dict:
    """ユーザーシナリオテストの実行"""
    results = {}

    if not scenarios or 'new_user' in scenarios:
        print("\n=== 新規ユーザーシナリオテスト ===")
        try:
            simulator.test_new_user_scenario()
            results['new_user'] = {'status': 'success', 'message': '新規ユーザーシナリオテスト完了'}
        except Exception as e:
            results['new_user'] = {'status': 'failed', 'message': str(e)}
            print(f"新規ユーザーシナリオテスト失敗: {e}")

    if not scenarios or 'existing_user' in scenarios:
        print("\n=== 既存ユーザーシナリオテスト ===")
        try:
            simulator.test_existing_user_scenario()
            results['existing_user'] = {'status': 'success', 'message': '既存ユーザーシナリオテスト完了'}
        except Exception as e:
            results['existing_user'] = {'status': 'failed', 'message': str(e)}
            print(f"既存ユーザーシナリオテスト失敗: {e}")

    if not scenarios or 'bulk_processing' in scenarios:
        print("\n=== 大量データ処理シナリオテスト ===")
        try:
            simulator.test_bulk_processing_scenario()
            results['bulk_processing'] = {'status': 'success', 'message': '大量データ処理シナリオテスト完了'}
        except Exception as e:
            results['bulk_processing'] = {'status': 'failed', 'message': str(e)}
            print(f"大量データ処理シナリオテスト失敗: {e}")

    return results


def save_results(results: dict, output_file: str) -> None:
    """結果の保存"""
    try:
        # 出力ディレクトリの作成
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 結果の保存
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n検証結果を保存しました: {output_file}")

    except Exception as e:
        print(f"結果保存エラー: {e}")


def print_summary(results: dict) -> None:
    """結果サマリーの表示"""
    print("\n" + "="*60)
    print("実環境シミュレーション検証結果サマリー")
    print("="*60)

    total_tests = 0
    passed_tests = 0

    for category, tests in results.items():
        if category == 'summary':
            continue

        print(f"\n【{category.upper()}】")
        for test_name, test_result in tests.items():
            status_symbol = "✓" if test_result['status'] == 'success' else "✗"
            print(f"  {status_symbol} {test_name}: {test_result['message']}")

            total_tests += 1
            if test_result['status'] == 'success':
                passed_tests += 1

    # 全体サマリー
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print("\n【全体結果】")
    print(f"  合格: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

    if success_rate >= 90:
        print("  🎉 優秀な結果です！")
    elif success_rate >= 75:
        print("  👍 良好な結果です")
    elif success_rate >= 50:
        print("  ⚠️  改善が必要です")
    else:
        print("  ❌ 重大な問題があります")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="DocMind実環境シミュレーション検証",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 全テスト実行
  python run_real_world_simulation.py

  # 特定の使用パターンのみ実行
  python run_real_world_simulation.py --patterns daily weekly

  # エッジケースのみ実行
  python run_real_world_simulation.py --edge-cases large_files many_files

  # ユーザーシナリオのみ実行
  python run_real_world_simulation.py --scenarios new_user existing_user

  # 詳細ログ出力
  python run_real_world_simulation.py --log-level DEBUG --log-file simulation.log
        """
    )

    # 実行対象の選択
    parser.add_argument(
        '--patterns',
        nargs='*',
        choices=['daily', 'weekly', 'monthly'],
        help='実行する使用パターン（指定なしで全実行）'
    )

    parser.add_argument(
        '--edge-cases',
        nargs='*',
        choices=['large_files', 'many_files', 'special_chars'],
        help='実行するエッジケース（指定なしで全実行）'
    )

    parser.add_argument(
        '--scenarios',
        nargs='*',
        choices=['new_user', 'existing_user', 'bulk_processing'],
        help='実行するユーザーシナリオ（指定なしで全実行）'
    )

    # 検証設定
    parser.add_argument(
        '--enable-performance',
        action='store_true',
        default=True,
        help='パフォーマンス監視を有効化'
    )

    parser.add_argument(
        '--enable-memory',
        action='store_true',
        default=True,
        help='メモリ監視を有効化'
    )

    parser.add_argument(
        '--enable-error-injection',
        action='store_true',
        help='エラー注入を有効化'
    )

    parser.add_argument(
        '--max-execution-time',
        type=float,
        default=600.0,
        help='最大実行時間（秒）'
    )

    parser.add_argument(
        '--max-memory-usage',
        type=float,
        default=3072.0,
        help='最大メモリ使用量（MB）'
    )

    # ログ設定
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='ログレベル'
    )

    parser.add_argument(
        '--log-file',
        help='ログファイルパス'
    )

    # 出力設定
    parser.add_argument(
        '--output-dir',
        default='validation_results/real_world_simulation',
        help='結果出力ディレクトリ'
    )

    parser.add_argument(
        '--output-file',
        help='結果出力ファイル（JSONフォーマット）'
    )

    args = parser.parse_args()

    # ログ設定
    setup_logging(args.log_level, args.log_file)

    # 出力ファイル名の生成
    if not args.output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_file = f"{args.output_dir}/real_world_simulation_results_{timestamp}.json"

    print("DocMind実環境シミュレーション検証を開始します")
    print(f"出力ディレクトリ: {args.output_dir}")
    print(f"ログレベル: {args.log_level}")

    # 検証設定の作成
    config = create_validation_config(args)

    # シミュレーターの初期化
    simulator = RealWorldSimulator(config)

    # 結果格納用辞書
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'patterns': args.patterns,
            'edge_cases': args.edge_cases,
            'scenarios': args.scenarios,
            'max_execution_time': args.max_execution_time,
            'max_memory_usage': args.max_memory_usage
        },
        'usage_patterns': {},
        'edge_cases': {},
        'user_scenarios': {}
    }

    try:
        # テスト環境のセットアップ
        simulator.setup_test_environment()

        # 使用パターンテストの実行
        print("\n" + "="*60)
        print("使用パターンテスト実行中...")
        print("="*60)
        all_results['usage_patterns'] = run_usage_pattern_tests(simulator, args.patterns)

        # エッジケーステストの実行
        print("\n" + "="*60)
        print("エッジケーステスト実行中...")
        print("="*60)
        all_results['edge_cases'] = run_edge_case_tests(simulator, args.edge_cases)

        # ユーザーシナリオテストの実行
        print("\n" + "="*60)
        print("ユーザーシナリオテスト実行中...")
        print("="*60)
        all_results['user_scenarios'] = run_user_scenario_tests(simulator, args.scenarios)

        # 統計情報の取得
        stats = simulator.get_statistics_summary()
        all_results['statistics'] = stats

        # 結果の保存
        save_results(all_results, args.output_file)

        # サマリーの表示
        print_summary(all_results)

    except KeyboardInterrupt:
        print("\n検証が中断されました")
        return 1

    except Exception as e:
        print(f"\n検証中にエラーが発生しました: {e}")
        logging.exception("検証エラー")
        return 1

    finally:
        # クリーンアップ
        try:
            simulator.teardown_test_environment()
            simulator.cleanup()
        except Exception as e:
            print(f"クリーンアップエラー: {e}")

    print("\n実環境シミュレーション検証が完了しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
