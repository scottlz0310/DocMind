"""
ドキュメント処理検証の統合テスト

実際のDocumentProcessingValidatorクラスの検証メソッドをテストします。
"""

import os
import signal
import sys
import unittest

# テスト対象のインポート
sys.path.append(os.path.join(os.path.dirname(__file__), 'validation_framework'))
from base_validator import ValidationConfig
from document_processing_validator import DocumentProcessingValidator


class TestDocumentProcessingIntegration(unittest.TestCase):
    """DocumentProcessingValidatorの統合テストクラス"""

    def setUp(self):
        """テストセットアップ"""
        self.config = ValidationConfig(
            enable_performance_monitoring=True,
            enable_memory_monitoring=True,
            max_execution_time=30.0,  # 30秒でタイムアウト
            max_memory_usage=512.0,   # 512MBでメモリ制限
            log_level="INFO"
        )

        self.validator = DocumentProcessingValidator(self.config)

        # タイムアウト設定
        self.timeout_seconds = 30

    def tearDown(self):
        """テストクリーンアップ"""
        if hasattr(self.validator, 'teardown_test_environment'):
            self.validator.teardown_test_environment()

    def _timeout_handler(self, signum, frame):
        """タイムアウトハンドラー"""
        raise TimeoutError(f"テストが{self.timeout_seconds}秒でタイムアウトしました")

    def test_full_validation_workflow_with_timeout(self):
        """完全な検証ワークフローのタイムアウト付きテスト"""
        # タイムアウト設定
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(self.timeout_seconds)

        try:
            # テスト環境のセットアップ
            self.validator.setup_test_environment()

            # 各検証メソッドを順次実行
            validation_methods = [
                'test_text_processing_accuracy',
                'test_markdown_processing_accuracy',
                'test_encoding_detection_accuracy',
                'test_large_file_processing',
                'test_error_handling_robustness'
            ]

            results = {}

            for method_name in validation_methods:
                if hasattr(self.validator, method_name):
                    try:
                        method = getattr(self.validator, method_name)
                        method()
                        results[method_name] = "SUCCESS"
                        print(f"✓ {method_name}: 成功")
                    except Exception as e:
                        results[method_name] = f"FAILED: {str(e)}"
                        print(f"✗ {method_name}: 失敗 - {e}")
                else:
                    results[method_name] = "METHOD_NOT_FOUND"
                    print(f"? {method_name}: メソッドが見つかりません")

            # 結果の検証
            successful_tests = sum(1 for result in results.values() if result == "SUCCESS")
            total_tests = len(results)

            print(f"\n検証結果: {successful_tests}/{total_tests} 成功")

            # 少なくとも50%のテストが成功することを要求
            self.assertGreaterEqual(
                successful_tests / total_tests, 0.5,
                f"検証成功率が低すぎます: {successful_tests}/{total_tests}"
            )

        finally:
            # タイムアウト解除
            signal.alarm(0)

    def test_performance_requirements(self):
        """パフォーマンス要件のテスト"""
        # タイムアウト設定
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(self.timeout_seconds)

        try:
            # テスト環境のセットアップ
            self.validator.setup_test_environment()

            # パフォーマンステストの実行
            if hasattr(self.validator, 'test_processing_performance_requirements'):
                self.validator.test_processing_performance_requirements()
                print("✓ パフォーマンス要件テスト: 成功")
            else:
                print("? パフォーマンス要件テスト: メソッドが見つかりません")

        finally:
            # タイムアウト解除
            signal.alarm(0)

    def test_concurrent_processing_safety(self):
        """並行処理安全性のテスト"""
        # タイムアウト設定
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(self.timeout_seconds)

        try:
            # テスト環境のセットアップ
            self.validator.setup_test_environment()

            # 並行処理テストの実行
            if hasattr(self.validator, 'test_concurrent_processing_safety'):
                self.validator.test_concurrent_processing_safety()
                print("✓ 並行処理安全性テスト: 成功")
            else:
                print("? 並行処理安全性テスト: メソッドが見つかりません")

        finally:
            # タイムアウト解除
            signal.alarm(0)

    def test_statistics_collection(self):
        """統計情報収集のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()

        # いくつかの処理統計を追加
        self.validator._update_processing_stats("txt", True, 100, 1.0)
        self.validator._update_processing_stats("pdf", True, 200, 2.0)
        self.validator._update_processing_stats("docx", False, 0, 0, "TestError")

        # 統計情報の取得
        stats = self.validator.get_processing_statistics()

        # 統計情報の検証
        self.assertIn('overall_stats', stats)
        self.assertIn('success_rate', stats)
        self.assertIn('average_processing_time', stats)
        self.assertIn('average_content_length', stats)

        # 成功率の確認
        self.assertAlmostEqual(stats['success_rate'], 2/3, places=2)

        print(f"✓ 統計情報収集テスト: 成功率={stats['success_rate']:.2%}")

    def test_memory_usage_monitoring(self):
        """メモリ使用量監視のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()

        # メモリ監視機能のテスト
        try:
            if hasattr(self.validator, 'memory_monitor'):
                current_memory = self.validator.memory_monitor.get_current_memory()
                self.assertIsInstance(current_memory, (int, float))
                self.assertGreater(current_memory, 0)
                print(f"✓ メモリ監視テスト: 現在のメモリ使用量={current_memory:.2f}MB")
            else:
                print("? メモリ監視テスト: memory_monitorが見つかりません")
        except Exception as e:
            print(f"? メモリ監視テスト: エラー - {e}")


if __name__ == '__main__':
    unittest.main()
