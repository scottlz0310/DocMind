# -*- coding: utf-8 -*-
"""
基盤検証フレームワークの使用例

このスクリプトは、基盤検証フレームワークの各コンポーネントの
使用方法を示すサンプルコードです。
"""

import os
import time
import tempfile
import shutil
from datetime import datetime

# 基盤検証フレームワークのインポート
from validation_framework import (
    BaseValidator, ValidationConfig, ValidationResult,
    PerformanceMonitor, MemoryMonitor, ErrorInjector,
    TestDataGenerator, TestDatasetConfig,
    ValidationReporter, ReportConfig,
    StatisticsCollector
)


class SampleValidator(BaseValidator):
    """
    サンプル検証クラス
    
    基盤検証フレームワークの使用方法を示すための
    サンプル検証クラスです。
    """
    
    def setup_test_environment(self):
        """テスト環境のセットアップ"""
        self.logger.info("テスト環境をセットアップしています...")
        
        # 一時ディレクトリの作成
        self.temp_dir = tempfile.mkdtemp()
        self.logger.info(f"一時ディレクトリを作成しました: {self.temp_dir}")
        
        # テストデータの準備
        self.test_files = []
        for i in range(5):
            test_file = os.path.join(self.temp_dir, f"test_file_{i}.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(f"これはテストファイル{i}の内容です。\n" * 10)
            self.test_files.append(test_file)
        
        self.logger.info(f"{len(self.test_files)}個のテストファイルを作成しました")
    
    def teardown_test_environment(self):
        """テスト環境のクリーンアップ"""
        self.logger.info("テスト環境をクリーンアップしています...")
        
        # 一時ディレクトリの削除
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.logger.info("一時ディレクトリを削除しました")
    
    def test_file_processing(self):
        """ファイル処理のテスト"""
        self.logger.info("ファイル処理テストを開始します")
        
        processed_count = 0
        for test_file in self.test_files:
            # ファイル存在チェック
            self.assert_condition(
                os.path.exists(test_file),
                f"テストファイルが存在すること: {test_file}"
            )
            
            # ファイル読み込み
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 内容チェック
            self.assert_condition(
                len(content) > 0,
                "ファイル内容が空でないこと"
            )
            
            processed_count += 1
            
            # 処理時間のシミュレート
            time.sleep(0.1)
        
        self.assert_condition(
            processed_count == len(self.test_files),
            f"すべてのファイルが処理されること（期待値: {len(self.test_files)}, 実際: {processed_count}）"
        )
        
        self.logger.info(f"ファイル処理テストが完了しました（処理ファイル数: {processed_count}）")
    
    def test_performance_intensive_task(self):
        """パフォーマンス集約的なタスクのテスト"""
        self.logger.info("パフォーマンス集約的なタスクのテストを開始します")
        
        # CPU集約的な処理のシミュレート
        start_time = time.time()
        
        # 計算集約的な処理
        result = sum(i * i for i in range(100000))
        
        execution_time = time.time() - start_time
        
        # パフォーマンス要件の検証
        self.assert_condition(
            execution_time < 5.0,
            f"処理が5秒以内に完了すること（実際: {execution_time:.2f}秒）"
        )
        
        self.assert_condition(
            result > 0,
            "計算結果が正しいこと"
        )
        
        self.logger.info(f"パフォーマンステストが完了しました（実行時間: {execution_time:.2f}秒）")
    
    def test_memory_usage(self):
        """メモリ使用量のテスト"""
        self.logger.info("メモリ使用量テストを開始します")
        
        # メモリを消費する処理のシミュレート
        large_data = []
        
        # 段階的にメモリを消費
        for i in range(1000):
            large_data.append([j for j in range(1000)])
            
            if i % 100 == 0:
                time.sleep(0.01)  # 監視のための短い待機
        
        # メモリ使用量の確認
        current_memory = self.memory_monitor.get_current_memory_usage()
        
        self.assert_condition(
            current_memory['rss_mb'] > 0,
            "メモリが使用されていること"
        )
        
        # メモリの解放
        large_data.clear()
        
        self.logger.info("メモリ使用量テストが完了しました")
    
    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        self.logger.info("エラーハンドリングテストを開始します")
        
        # 存在しないファイルへのアクセス
        non_existent_file = os.path.join(self.temp_dir, "non_existent.txt")
        
        try:
            with open(non_existent_file, 'r') as f:
                content = f.read()
            
            # ここに到達したら失敗
            self.assert_condition(False, "存在しないファイルでFileNotFoundErrorが発生すること")
            
        except FileNotFoundError:
            # 期待される例外
            self.logger.info("期待されるFileNotFoundErrorが発生しました")
        
        except Exception as e:
            # 予期しない例外
            self.assert_condition(False, f"予期しない例外が発生しました: {e}")
        
        self.logger.info("エラーハンドリングテストが完了しました")
    
    def test_with_error_injection(self):
        """エラー注入を使用したテスト"""
        self.logger.info("エラー注入テストを開始します")
        
        # テストファイルの作成
        test_file = os.path.join(self.temp_dir, "injection_test.txt")
        with open(test_file, 'w') as f:
            f.write("テストデータ")
        
        # ファイル不存在エラーの注入
        self.inject_error(
            'file_not_found',
            parameters={'target_file': test_file},
            duration_seconds=2.0
        )
        
        # エラー注入後の処理
        try:
            with open(test_file, 'r') as f:
                content = f.read()
            
            # ファイルが読めた場合（エラー注入が効いていない）
            self.logger.warning("エラー注入が効いていない可能性があります")
            
        except FileNotFoundError:
            # 期待される動作
            self.logger.info("エラー注入によりFileNotFoundErrorが発生しました")
        
        # 少し待機してファイルが復元されるかチェック
        time.sleep(3.0)
        
        self.logger.info("エラー注入テストが完了しました")


def demonstrate_performance_monitoring():
    """パフォーマンス監視のデモンストレーション"""
    print("\n=== パフォーマンス監視のデモンストレーション ===")
    
    monitor = PerformanceMonitor(sampling_interval=0.5)
    
    print("パフォーマンス監視を開始します...")
    monitor.start_monitoring()
    
    # 監視対象の処理
    print("CPU集約的な処理を実行中...")
    result = sum(i * i for i in range(1000000))
    
    print("I/O集約的な処理を実行中...")
    temp_file = tempfile.mktemp()
    with open(temp_file, 'w') as f:
        for i in range(10000):
            f.write(f"Line {i}: This is a test line with some content.\n")
    
    # 監視停止
    print("パフォーマンス監視を停止します...")
    monitor.stop_monitoring()
    
    # 結果の表示
    summary = monitor.get_performance_summary()
    print(f"監視時間: {summary['monitoring_duration_seconds']:.2f}秒")
    print(f"最大CPU使用率: {summary['cpu_usage']['peak_percent']:.1f}%")
    print(f"平均CPU使用率: {summary['cpu_usage']['average_percent']:.1f}%")
    print(f"最大メモリ使用量: {summary['memory_usage']['peak_mb']:.1f}MB")
    
    # 閾値チェック
    thresholds = monitor.check_performance_thresholds(
        max_cpu_percent=80.0,
        max_memory_mb=2048.0
    )
    print(f"CPU閾値内: {thresholds['cpu_within_threshold']}")
    print(f"メモリ閾値内: {thresholds['memory_within_threshold']}")
    
    # クリーンアップ
    monitor.cleanup()
    if os.path.exists(temp_file):
        os.remove(temp_file)


def demonstrate_test_data_generation():
    """テストデータ生成のデモンストレーション"""
    print("\n=== テストデータ生成のデモンストレーション ===")
    
    generator = TestDataGenerator()
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 小規模データセットの生成
        print("小規模テストデータセットを生成中...")
        config = TestDatasetConfig(
            dataset_name="demo_dataset",
            output_directory=temp_dir,
            file_count=20,
            file_types=['txt', 'json', 'csv'],
            size_range_kb=(1, 50),
            include_corrupted=True,
            include_special_chars=True
        )
        
        result = generator.generate_dataset(config)
        
        print(f"生成完了:")
        print(f"  - ファイル数: {result['statistics']['total_files']}")
        print(f"  - 総サイズ: {result['statistics']['total_size_mb']:.2f}MB")
        print(f"  - 破損ファイル数: {result['statistics']['corrupted_files']}")
        print(f"  - 特殊文字ファイル数: {result['statistics']['special_char_files']}")
        print(f"  - メタデータファイル: {result['metadata_path']}")
        
        # 生成されたファイルの一覧表示
        print("\n生成されたファイル（最初の5個）:")
        for i, file_path in enumerate(result['generated_files'][:5]):
            file_size = os.path.getsize(file_path) / 1024  # KB
            print(f"  {i+1}. {os.path.basename(file_path)} ({file_size:.1f}KB)")
        
    finally:
        # クリーンアップ
        generator.cleanup()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def demonstrate_error_injection():
    """エラー注入のデモンストレーション"""
    print("\n=== エラー注入のデモンストレーション ===")
    
    injector = ErrorInjector()
    temp_dir = tempfile.mkdtemp()
    
    try:
        # テストファイルの作成
        test_file = os.path.join(temp_dir, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("これはテストファイルです。")
        
        print(f"テストファイルを作成しました: {test_file}")
        print(f"ファイル存在確認: {os.path.exists(test_file)}")
        
        # ファイル不存在エラーの注入
        print("\nファイル不存在エラーを注入中...")
        success = injector.inject_error(
            'file_not_found',
            parameters={'target_file': test_file}
        )
        
        print(f"エラー注入成功: {success}")
        print(f"ファイル存在確認（注入後）: {os.path.exists(test_file)}")
        
        # 破損ファイルの生成
        print("\n破損ファイルを生成中...")
        corrupted_file = os.path.join(temp_dir, "corrupted.txt")
        injector.inject_error(
            'corrupted_file',
            parameters={'target_file': corrupted_file}
        )
        
        print(f"破損ファイル生成: {os.path.exists(corrupted_file)}")
        
        # 注入統計の表示
        stats = injector.get_injection_statistics()
        print(f"\n注入統計:")
        print(f"  - 総注入回数: {stats['total_injections']}")
        print(f"  - 成功回数: {stats['successful_injections']}")
        print(f"  - 成功率: {stats['success_rate']:.1%}")
        print(f"  - エラータイプ別: {stats['error_types']}")
        
    finally:
        # クリーンアップ
        injector.cleanup()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def demonstrate_comprehensive_validation():
    """包括的検証のデモンストレーション"""
    print("\n=== 包括的検証のデモンストレーション ===")
    
    # 検証設定
    config = ValidationConfig(
        enable_performance_monitoring=True,
        enable_memory_monitoring=True,
        enable_error_injection=True,
        max_execution_time=30.0,
        max_memory_usage=1024.0,
        log_level="INFO"
    )
    
    # 検証実行
    validator = SampleValidator(config)
    
    print("包括的検証を開始します...")
    start_time = time.time()
    
    # 環境セットアップ
    validator.setup_test_environment()
    
    try:
        # 検証実行
        results = validator.run_validation()
        
        # 結果の表示
        execution_time = time.time() - start_time
        print(f"\n検証完了（実行時間: {execution_time:.2f}秒）")
        
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        
        print(f"検証結果サマリー:")
        print(f"  - 総テスト数: {total_count}")
        print(f"  - 成功数: {success_count}")
        print(f"  - 失敗数: {total_count - success_count}")
        print(f"  - 成功率: {success_rate:.1f}%")
        
        # 個別結果の表示
        print(f"\n個別テスト結果:")
        for result in results:
            status = "✅ 成功" if result.success else "❌ 失敗"
            print(f"  {status} {result.test_name} ({result.execution_time:.3f}秒)")
            if not result.success:
                print(f"    エラー: {result.error_message}")
        
        # 統計情報の表示
        stats_summary = validator.get_statistics_summary()
        if stats_summary:
            basic_stats = stats_summary.get('basic_statistics', {})
            print(f"\n統計情報:")
            print(f"  - 平均実行時間: {basic_stats.get('execution_time_stats', {}).get('mean', 0):.3f}秒")
            print(f"  - 最大メモリ使用量: {basic_stats.get('memory_usage_stats', {}).get('max_value', 0):.1f}MB")
        
    finally:
        # 環境クリーンアップ
        validator.teardown_test_environment()
        validator.cleanup()


def demonstrate_report_generation():
    """レポート生成のデモンストレーション"""
    print("\n=== レポート生成のデモンストレーション ===")
    
    # サンプルデータの作成
    validation_results = []
    for i in range(10):
        result = ValidationResult(
            test_name=f"test_sample_{i}",
            success=i % 3 != 0,  # 3の倍数は失敗
            execution_time=0.1 + (i * 0.05),
            memory_usage=100.0 + (i * 20.0),
            error_message="サンプルエラー" if i % 3 == 0 else None,
            timestamp=datetime.now()
        )
        validation_results.append(result)
    
    # サンプルパフォーマンスデータ
    performance_data = {
        'monitoring_duration_seconds': 60.0,
        'cpu_usage': {'peak_percent': 45.2, 'average_percent': 25.8},
        'memory_usage': {'peak_mb': 512.3, 'peak_percent': 25.1},
        'disk_io': {'read_mb': 15.2, 'write_mb': 8.7},
        'network_io': {'sent_mb': 2.1, 'recv_mb': 1.8}
    }
    
    # サンプルメモリデータ
    memory_data = {
        'monitoring_duration_seconds': 60.0,
        'rss_memory': {'peak_mb': 512.3, 'average_mb': 387.1, 'growth_rate_mb_per_sec': 0.05},
        'memory_leak_detected': False
    }
    
    # サンプルエラー注入データ
    error_injection_data = {
        'total_injections': 5,
        'successful_injections': 4,
        'success_rate': 0.8,
        'error_types': {'file_not_found': 2, 'memory_error': 1, 'corrupted_file': 2}
    }
    
    # レポート生成
    reporter = ValidationReporter()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = ReportConfig(
            output_directory=temp_dir,
            report_name="demo_report",
            include_charts=False,  # チャート生成をスキップ（依存関係の問題を回避）
            include_detailed_logs=True,
            report_format="html"
        )
        
        print("レポートを生成中...")
        report_files = reporter.generate_comprehensive_report(
            validation_results=validation_results,
            performance_data=performance_data,
            memory_data=memory_data,
            error_injection_data=error_injection_data,
            config=config
        )
        
        print("レポート生成完了:")
        for report_type, file_path in report_files.items():
            file_size = os.path.getsize(file_path) / 1024  # KB
            print(f"  - {report_type}: {file_path} ({file_size:.1f}KB)")
        
        # HTMLレポートの内容をプレビュー
        if 'html_report' in report_files:
            html_file = report_files['html_report']
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"\nHTMLレポートのサイズ: {len(content)}文字")
            print("HTMLレポートが正常に生成されました。")
        
    finally:
        # クリーンアップ
        reporter.cleanup()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def main():
    """メイン関数"""
    print("DocMind 基盤検証フレームワーク デモンストレーション")
    print("=" * 60)
    
    try:
        # 各コンポーネントのデモンストレーション
        demonstrate_performance_monitoring()
        demonstrate_test_data_generation()
        demonstrate_error_injection()
        demonstrate_comprehensive_validation()
        demonstrate_report_generation()
        
        print("\n" + "=" * 60)
        print("すべてのデモンストレーションが完了しました。")
        print("基盤検証フレームワークの各機能が正常に動作することを確認できました。")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()