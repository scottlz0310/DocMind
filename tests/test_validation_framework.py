"""
基盤検証フレームワークのテスト

基盤検証フレームワークの各コンポーネントが正しく動作することを確認します。
"""

import os
import shutil

# テスト対象のインポート
import sys
import tempfile
import time
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'validation_framework'))

from base_validator import BaseValidator, ValidationConfig, ValidationResult
from error_injector import ErrorInjector
from memory_monitor import MemoryMonitor
from performance_monitor import PerformanceMonitor
from statistics_collector import StatisticsCollector
from test_data_generator import TestDataGenerator


class TestBaseValidator(BaseValidator):
    """テスト用の基盤検証クラス"""

    def setup_test_environment(self):
        """テスト環境のセットアップ"""
        self.test_data = {"setup": True}

    def teardown_test_environment(self):
        """テスト環境のクリーンアップ"""
        self.test_data = {"setup": False}

    def test_sample_validation(self):
        """サンプル検証テスト"""
        time.sleep(0.1)  # 短い処理時間をシミュレート
        self.assert_condition(True, "サンプル検証が成功しました")

    def test_failing_validation(self):
        """失敗する検証テスト"""
        self.assert_condition(False, "意図的に失敗させるテスト")


class ValidationFrameworkTestCase(unittest.TestCase):
    """基盤検証フレームワークのテストケース"""

    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ValidationConfig(
            enable_performance_monitoring=True,
            enable_memory_monitoring=True,
            enable_error_injection=False,
            output_directory=self.temp_dir
        )

    def tearDown(self):
        """テストクリーンアップ"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_base_validator_initialization(self):
        """基盤検証クラスの初期化テスト"""
        validator = TestBaseValidator(self.config)

        self.assertIsNotNone(validator.performance_monitor)
        self.assertIsNotNone(validator.memory_monitor)
        self.assertIsNotNone(validator.error_injector)
        self.assertIsNotNone(validator.statistics_collector)
        self.assertEqual(len(validator.validation_results), 0)

    def test_validation_execution(self):
        """検証実行のテスト"""
        validator = TestBaseValidator(self.config)

        # 成功するテストの実行
        results = validator.run_validation(['test_sample_validation'])

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertGreater(results[0].execution_time, 0)
        self.assertEqual(results[0].test_name, 'test_sample_validation')

    def test_validation_failure_handling(self):
        """検証失敗の処理テスト"""
        validator = TestBaseValidator(self.config)

        # 失敗するテストの実行
        results = validator.run_validation(['test_failing_validation'])

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertIsNotNone(results[0].error_message)
        self.assertIn('意図的に失敗', results[0].error_message)

    def test_performance_requirements_validation(self):
        """パフォーマンス要件検証のテスト"""
        validator = TestBaseValidator(self.config)

        # 短時間で完了するテストを実行
        validator.run_validation(['test_sample_validation'])

        # パフォーマンス要件をチェック
        is_valid = validator.validate_performance_requirements(max_time=1.0, max_memory=100.0)
        self.assertTrue(is_valid)

        # 厳しい要件でのチェック
        is_valid_strict = validator.validate_performance_requirements(max_time=0.01, max_memory=1.0)
        self.assertFalse(is_valid_strict)


class PerformanceMonitorTestCase(unittest.TestCase):
    """パフォーマンス監視のテストケース"""

    def test_performance_monitor_initialization(self):
        """パフォーマンス監視の初期化テスト"""
        monitor = PerformanceMonitor(sampling_interval=0.1)

        self.assertFalse(monitor.is_monitoring)
        self.assertEqual(len(monitor.metrics_history), 0)

    def test_performance_monitoring_lifecycle(self):
        """パフォーマンス監視のライフサイクルテスト"""
        monitor = PerformanceMonitor(sampling_interval=0.1)

        # 監視開始
        monitor.start_monitoring()
        self.assertTrue(monitor.is_monitoring)

        # 短時間待機してデータ収集
        time.sleep(0.3)

        # 監視停止
        monitor.stop_monitoring()
        self.assertFalse(monitor.is_monitoring)

        # データが収集されていることを確認
        self.assertGreater(len(monitor.metrics_history), 0)

        # 統計情報の取得
        summary = monitor.get_performance_summary()
        self.assertIn('monitoring_duration_seconds', summary)
        self.assertIn('cpu_usage', summary)
        self.assertIn('memory_usage', summary)

    def test_performance_thresholds(self):
        """パフォーマンス閾値チェックのテスト"""
        monitor = PerformanceMonitor(sampling_interval=0.1)

        monitor.start_monitoring()
        time.sleep(0.2)
        monitor.stop_monitoring()

        # 閾値チェック
        results = monitor.check_performance_thresholds(max_cpu_percent=100.0, max_memory_mb=4096.0)

        self.assertIn('cpu_within_threshold', results)
        self.assertIn('memory_within_threshold', results)
        self.assertIn('peak_cpu_percent', results)
        self.assertIn('peak_memory_mb', results)


class MemoryMonitorTestCase(unittest.TestCase):
    """メモリ監視のテストケース"""

    def test_memory_monitor_initialization(self):
        """メモリ監視の初期化テスト"""
        monitor = MemoryMonitor(sampling_interval=0.1)

        self.assertFalse(monitor.is_monitoring)
        self.assertEqual(len(monitor.memory_snapshots), 0)

    def test_memory_monitoring_lifecycle(self):
        """メモリ監視のライフサイクルテスト"""
        monitor = MemoryMonitor(sampling_interval=0.1)

        # 監視開始
        monitor.start_monitoring()
        self.assertTrue(monitor.is_monitoring)

        # 短時間待機してデータ収集
        time.sleep(0.3)

        # 監視停止
        monitor.stop_monitoring()
        self.assertFalse(monitor.is_monitoring)

        # データが収集されていることを確認
        self.assertGreater(len(monitor.memory_snapshots), 0)

        # 統計情報の取得
        stats = monitor.get_memory_statistics()
        self.assertIn('monitoring_duration_seconds', stats)
        self.assertIn('rss_memory', stats)

    def test_memory_leak_detection(self):
        """メモリリーク検出のテスト"""
        monitor = MemoryMonitor(sampling_interval=0.1)

        monitor.start_monitoring()
        time.sleep(0.2)
        monitor.stop_monitoring()

        # メモリリーク検出（通常は検出されないはず）
        is_leak = monitor.detect_memory_leak(threshold_mb_per_minute=1000.0)
        self.assertFalse(is_leak)


class ErrorInjectorTestCase(unittest.TestCase):
    """エラー注入のテストケース"""

    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.injector = ErrorInjector()

    def tearDown(self):
        """テストクリーンアップ"""
        self.injector.cleanup()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_error_injector_initialization(self):
        """エラー注入クラスの初期化テスト"""
        self.assertEqual(len(self.injector.injected_errors), 0)
        self.assertEqual(len(self.injector.active_injections), 0)
        self.assertIn('file_not_found', self.injector.injection_methods)

    def test_file_not_found_injection(self):
        """ファイル不存在エラー注入のテスト"""
        test_file = os.path.join(self.temp_dir, 'test_file.txt')

        # テストファイルを作成
        with open(test_file, 'w') as f:
            f.write('test content')

        self.assertTrue(os.path.exists(test_file))

        # エラー注入
        success = self.injector.inject_error(
            'file_not_found',
            parameters={'target_file': test_file}
        )

        self.assertTrue(success)
        self.assertFalse(os.path.exists(test_file))  # ファイルが移動されている

        # 注入履歴の確認
        history = self.injector.get_injection_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].error_type, 'file_not_found')

    def test_corrupted_file_injection(self):
        """ファイル破損エラー注入のテスト"""
        success = self.injector.inject_error(
            'corrupted_file',
            parameters={'target_file': os.path.join(self.temp_dir, 'corrupted.txt')}
        )

        self.assertTrue(success)

        # 破損ファイルが作成されていることを確認
        corrupted_file = os.path.join(self.temp_dir, 'corrupted.txt')
        self.assertTrue(os.path.exists(corrupted_file))

    def test_injection_statistics(self):
        """エラー注入統計のテスト"""
        # 複数のエラーを注入
        self.injector.inject_error('corrupted_file', parameters={'target_file': 'test1.txt'})
        self.injector.inject_error('encoding_error', parameters={'target_file': 'test2.txt'})

        # 統計情報の取得
        stats = self.injector.get_injection_statistics()

        self.assertEqual(stats['total_injections'], 2)
        self.assertEqual(stats['successful_injections'], 2)
        self.assertEqual(stats['success_rate'], 1.0)
        self.assertIn('corrupted_file', stats['error_types'])
        self.assertIn('encoding_error', stats['error_types'])


class TestDataGeneratorTestCase(unittest.TestCase):
    """テストデータ生成のテストケース"""

    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = TestDataGenerator()

    def tearDown(self):
        """テストクリーンアップ"""
        self.generator.cleanup()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_test_data_generator_initialization(self):
        """テストデータ生成クラスの初期化テスト"""
        self.assertEqual(len(self.generator.generated_files), 0)
        self.assertIn('txt', self.generator.supported_formats)
        self.assertIn('ja', self.generator.sample_texts)

    def test_small_dataset_generation(self):
        """小規模データセット生成のテスト"""
        from test_data_generator import TestDatasetConfig

        config = TestDatasetConfig(
            dataset_name="test_small",
            output_directory=self.temp_dir,
            file_count=5,
            file_types=['txt', 'json'],
            size_range_kb=(1, 10)
        )

        result = self.generator.generate_dataset(config)

        self.assertEqual(result['statistics']['total_files'], 5)
        self.assertGreater(result['statistics']['total_size_mb'], 0)
        self.assertTrue(os.path.exists(result['metadata_path']))

        # 生成されたファイルの確認
        generated_files = result['generated_files']
        self.assertEqual(len(generated_files), 5)

        for file_path in generated_files:
            self.assertTrue(os.path.exists(file_path))


class StatisticsCollectorTestCase(unittest.TestCase):
    """統計情報収集のテストケース"""

    def setUp(self):
        """テストセットアップ"""
        self.collector = StatisticsCollector()

    def test_statistics_collector_initialization(self):
        """統計情報収集クラスの初期化テスト"""
        self.assertEqual(len(self.collector.validation_results), 0)
        self.assertEqual(len(self.collector.performance_metrics), 0)
        self.assertEqual(len(self.collector.memory_metrics), 0)

    def test_result_addition_and_statistics(self):
        """結果追加と統計計算のテスト"""
        # サンプル結果の追加
        for i in range(10):
            result = ValidationResult(
                test_name=f"test_{i}",
                success=i % 2 == 0,  # 偶数番号は成功
                execution_time=0.1 + (i * 0.01),
                memory_usage=100.0 + (i * 10.0),
                timestamp=datetime.now()
            )
            self.collector.add_result(result)

        # 統計情報の取得
        summary = self.collector.get_summary()

        self.assertIn('basic_statistics', summary)
        basic_stats = summary['basic_statistics']

        self.assertEqual(basic_stats['total_tests'], 10)
        self.assertEqual(basic_stats['successful_tests'], 5)
        self.assertEqual(basic_stats['overall_success_rate'], 50.0)

    def test_performance_metrics_addition(self):
        """パフォーマンス指標追加のテスト"""
        metrics = {
            'cpu_percent': 25.5,
            'memory_percent': 45.2,
            'disk_io_read_mb': 10.0,
            'disk_io_write_mb': 5.0
        }

        self.collector.add_performance_metrics(metrics)

        self.assertEqual(len(self.collector.performance_metrics), 1)
        self.assertEqual(self.collector.performance_metrics[0]['cpu_percent'], 25.5)


if __name__ == '__main__':
    # テストスイートの実行
    unittest.main(verbosity=2)
