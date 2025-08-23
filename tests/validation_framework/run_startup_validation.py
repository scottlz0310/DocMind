#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アプリケーション起動検証の実行スクリプト

ApplicationStartupValidatorを使用して、DocMindアプリケーションの
起動プロセスを包括的に検証します。
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from application_startup_validator import ApplicationStartupValidator
from base_validator import ValidationConfig


def generate_simple_report(results, stats, total_tests, successful_tests, failed_tests):
    """簡単なMarkdownレポートを生成"""
    report = f"""# DocMind アプリケーション起動検証レポート

## 実行概要
- 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 総テスト数: {total_tests}
- 成功: {successful_tests}
- 失敗: {failed_tests}
- 成功率: {(successful_tests/total_tests)*100:.1f}%

## テスト結果詳細

"""
    
    for result in results:
        status = "✅ 成功" if result.success else "❌ 失敗"
        report += f"### {result.test_name}\n"
        report += f"- ステータス: {status}\n"
        report += f"- 実行時間: {result.execution_time:.3f}秒\n"
        report += f"- メモリ使用量: {result.memory_usage:.1f}MB\n"
        
        if not result.success and result.error_message:
            report += f"- エラー: {result.error_message}\n"
        
        report += "\n"
    
    if stats:
        report += "## パフォーマンス統計\n\n"
        for key, value in stats.items():
            if isinstance(value, float):
                report += f"- {key}: {value:.3f}\n"
            else:
                report += f"- {key}: {value}\n"
    
    return report


def main():
    """メイン実行関数"""
    print("=" * 60)
    print("DocMind アプリケーション起動検証")
    print("=" * 60)
    print(f"実行開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 検証設定
    config = ValidationConfig(
        enable_performance_monitoring=True,
        enable_memory_monitoring=True,
        enable_error_injection=True,
        max_execution_time=30.0,
        max_memory_usage=1024.0,
        log_level="INFO"
    )
    
    # バリデーターの初期化
    validator = ApplicationStartupValidator(config)
    
    try:
        # テスト環境のセットアップ
        print("テスト環境をセットアップしています...")
        validator.setup_test_environment()
        print(f"テストディレクトリ: {validator.temp_dir}")
        print()
        
        # 検証の実行
        print("アプリケーション起動検証を実行しています...")
        print("-" * 40)
        
        # 実行するテストメソッドを定義
        test_methods = [
            'test_startup_time_requirement',
            'test_directory_creation', 
            'test_config_initialization',
            'test_logging_system_initialization',
            'test_database_initialization',
            'test_startup_error_recovery',
            'test_startup_error_injection'
        ]
        
        # 検証実行
        results = validator.run_validation(test_methods)
        
        # 結果の表示
        print("\n" + "=" * 60)
        print("検証結果サマリー")
        print("=" * 60)
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - successful_tests
        
        print(f"総テスト数: {total_tests}")
        print(f"成功: {successful_tests}")
        print(f"失敗: {failed_tests}")
        print(f"成功率: {(successful_tests/total_tests)*100:.1f}%")
        print()
        
        # 個別テスト結果の表示
        print("個別テスト結果:")
        print("-" * 40)
        
        for result in results:
            status = "✓ 成功" if result.success else "✗ 失敗"
            print(f"{status} | {result.test_name}")
            print(f"    実行時間: {result.execution_time:.3f}秒")
            print(f"    メモリ使用量: {result.memory_usage:.1f}MB")
            
            if not result.success and result.error_message:
                print(f"    エラー: {result.error_message}")
            print()
        
        # パフォーマンス統計の表示
        stats = validator.get_statistics_summary()
        if stats:
            print("パフォーマンス統計:")
            print("-" * 40)
            for key, value in stats.items():
                if isinstance(value, float):
                    print(f"{key}: {value:.3f}")
                else:
                    print(f"{key}: {value}")
            print()
        
        # 要件適合性の確認
        print("要件適合性チェック:")
        print("-" * 40)
        
        # 起動時間要件（10秒以内）
        startup_result = next((r for r in results if 'startup_time' in r.test_name), None)
        if startup_result:
            startup_ok = startup_result.execution_time <= 10.0
            print(f"起動時間要件 (≤10秒): {'✓' if startup_ok else '✗'} {startup_result.execution_time:.2f}秒")
        
        # メモリ使用量要件（2GB以下）
        max_memory = max((r.memory_usage for r in results), default=0)
        memory_ok = max_memory <= 2048.0
        print(f"メモリ使用量要件 (≤2GB): {'✓' if memory_ok else '✗'} {max_memory:.1f}MB")
        
        # 全体的な成功率要件（90%以上）
        success_rate_ok = (successful_tests / total_tests) >= 0.9
        print(f"成功率要件 (≥90%): {'✓' if success_rate_ok else '✗'} {(successful_tests/total_tests)*100:.1f}%")
        
        print()
        
        # レポート生成
        print("検証レポートを生成しています...")
        
        # 簡単なMarkdownレポートを生成
        report_content = generate_simple_report(results, stats, total_tests, successful_tests, failed_tests)
        report_file = validator.temp_dir / "startup_validation_report.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"レポートを保存しました: {report_file}")
        
        # 最終判定
        print("\n" + "=" * 60)
        overall_success = failed_tests == 0 and startup_ok and memory_ok and success_rate_ok
        
        if overall_success:
            print("🎉 アプリケーション起動検証: 合格")
            print("すべての要件を満たしています。")
            exit_code = 0
        else:
            print("❌ アプリケーション起動検証: 不合格")
            print("一部の要件を満たしていません。詳細は上記の結果を確認してください。")
            exit_code = 1
        
        print("=" * 60)
        
        return exit_code
        
    except Exception as e:
        print(f"\n❌ 検証実行中にエラーが発生しました: {e}")
        logging.exception("検証実行エラー")
        return 1
        
    finally:
        # クリーンアップ
        try:
            validator.teardown_test_environment()
            validator.cleanup()
            print("\nクリーンアップが完了しました。")
        except Exception as e:
            print(f"クリーンアップ中にエラー: {e}")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)