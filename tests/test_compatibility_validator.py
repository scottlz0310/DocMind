# -*- coding: utf-8 -*-
"""
互換性・移植性検証クラスのテスト

CompatibilityValidatorクラスの動作を検証するテストケースです。
"""

import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.validation_framework.compatibility_validator import (
    CompatibilityValidator,
    CompatibilityThresholds,
    CompatibilityMetrics,
    SystemInfoCollector,
    EncodingTester,
    ResourceLimiter
)
from tests.validation_framework.base_validator import ValidationConfig


class TestSystemInfoCollector(unittest.TestCase):
    """SystemInfoCollectorクラスのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.collector = SystemInfoCollector()
    
    def test_collect_system_info(self):
        """システム情報収集のテスト"""
        system_info = self.collector.collect_system_info()
        
        # 基本的なシステム情報が含まれているかチェック
        self.assertIn('os_name', system_info)
        self.assertIn('python_version', system_info)
        self.assertIn('total_memory_mb', system_info)
        self.assertIn('cpu_count', system_info)
    
    def test_get_windows_version(self):
        """Windows版本取得のテスト"""
        version, is_supported = self.collector.get_windows_version()
        
        # 戻り値の型チェック
        self.assertIsInstance(version, str)
        self.assertIsInstance(is_supported, bool)
    
    @patch('platform.system')
    def test_get_windows_version_non_windows(self, mock_system):
        """非Windows環境でのテスト"""
        mock_system.return_value = 'Linux'
        
        version, is_supported = self.collector.get_windows_version()
        
        self.assertEqual(version, "非Windows")
        self.assertFalse(is_supported)
    
    def test_get_filesystem_type(self):
        """ファイルシステムタイプ取得のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            filesystem_type = self.collector.get_filesystem_type(temp_dir)
            
            # 戻り値が文字列であることを確認
            self.assertIsInstance(filesystem_type, str)


class TestEncodingTester(unittest.TestCase):
    """EncodingTesterクラスのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.tester = EncodingTester()
    
    def test_test_encoding_support(self):
        """エンコーディングサポートテストのテスト"""
        encodings = ['utf-8', 'shift_jis', 'euc-jp']
        results = self.tester.test_encoding_support(encodings)
        
        # 結果の構造チェック
        self.assertIsInstance(results, dict)
        for encoding in encodings:
            if encoding in results:  # サポートされているエンコーディングのみチェック
                self.assertIsInstance(results[encoding], dict)
                for test_name, result in results[encoding].items():
                    self.assertIsInstance(result, bool)
    
    def test_create_test_files_with_encodings(self):
        """エンコーディングテストファイル作成のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            encodings = ['utf-8', 'shift_jis']
            test_files = self.tester.create_test_files_with_encodings(temp_dir, encodings)
            
            # ファイルが作成されているかチェック
            self.assertIsInstance(test_files, list)
            
            for file_path in test_files:
                self.assertTrue(os.path.exists(file_path))
                
                # ファイル内容の確認
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.assertIn('エンコーディング', content)
                except UnicodeDecodeError:
                    # UTF-8以外のエンコーディングの場合は正常
                    pass


class TestResourceLimiter(unittest.TestCase):
    """ResourceLimiterクラスのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.limiter = ResourceLimiter()
    
    def test_simulate_limited_memory(self):
        """メモリ制限シミュレーションのテスト"""
        # メモリ制限の設定
        self.limiter.simulate_limited_memory(512)
        
        # 制限が設定されているかチェック
        self.assertEqual(self.limiter.memory_limit_mb, 512)
        self.assertTrue(self.limiter.memory_monitor_active)
        
        # クリーンアップ
        self.limiter.cleanup_resource_limits()
    
    def test_simulate_limited_disk_space(self):
        """ディスク容量制限シミュレーションのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            dummy_file = self.limiter.simulate_limited_disk_space(temp_dir, 50)
            
            # ダミーファイルが作成されているかチェック（容量に依存）
            if dummy_file:
                self.assertTrue(os.path.exists(dummy_file))
                
                # クリーンアップ
                try:
                    os.remove(dummy_file)
                except OSError:
                    pass
    
    def test_cleanup_resource_limits(self):
        """リソース制限クリーンアップのテスト"""
        # メモリ制限を設定してからクリーンアップ
        self.limiter.simulate_limited_memory(256)
        self.limiter.cleanup_resource_limits()
        
        # クリーンアップが実行されることを確認
        self.assertFalse(self.limiter.memory_monitor_active)


class TestCompatibilityValidator(unittest.TestCase):
    """CompatibilityValidatorクラスのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config = ValidationConfig(
            enable_performance_monitoring=False,
            enable_memory_monitoring=False,
            log_level="WARNING"  # テスト時はログを抑制
        )
        self.validator = CompatibilityValidator(self.config)
    
    def tearDown(self):
        """テストクリーンアップ"""
        try:
            self.validator.teardown_test_environment()
            self.validator.cleanup()
        except Exception:
            pass
    
    def test_initialization(self):
        """初期化のテスト"""
        # 基本的な属性が設定されているかチェック
        self.assertIsInstance(self.validator.thresholds, CompatibilityThresholds)
        self.assertIsInstance(self.validator.system_info_collector, SystemInfoCollector)
        self.assertIsInstance(self.validator.encoding_tester, EncodingTester)
        self.assertIsInstance(self.validator.resource_limiter, ResourceLimiter)
        self.assertEqual(self.validator.compatibility_metrics, [])
    
    def test_setup_test_environment(self):
        """テスト環境セットアップのテスト"""
        self.validator.setup_test_environment()
        
        # テスト環境が正しく設定されているかチェック
        self.assertIsNotNone(self.validator.test_base_dir)
        self.assertTrue(os.path.exists(self.validator.test_base_dir))
        self.assertIn('index_manager', self.validator.test_components)
        self.assertIn('search_manager', self.validator.test_components)
    
    @patch.object(CompatibilityValidator, '_test_all_docmind_features')
    @patch.object(CompatibilityValidator, '_test_windows_performance')
    def test_windows_environment_compatibility(self, mock_performance, mock_features):
        """Windows環境互換性テストのテスト"""
        # モックの設定
        mock_features.return_value = {
            'document_processing': True,
            'indexing': True,
            'search': True,
            'embedding': True,
            'gui': True
        }
        mock_performance.return_value = {
            'startup_time_seconds': 5.0,
            'search_time_seconds': 2.0,
            'memory_usage_mb': 512
        }
        
        # テスト環境のセットアップ
        self.validator.setup_test_environment()
        
        # テストの実行
        self.validator.test_windows_environment_compatibility()
        
        # 結果の確認
        self.assertEqual(len(self.validator.compatibility_metrics), 1)
        metric = self.validator.compatibility_metrics[0]
        self.assertEqual(metric.test_name, "windows_environment_compatibility")
        self.assertIn(metric.compatibility_level, ["COMPATIBLE", "LIMITED", "INCOMPATIBLE"])
    
    @patch.object(CompatibilityValidator, '_get_screen_resolution')
    @patch.object(CompatibilityValidator, '_test_resolution_compatibility')
    @patch.object(CompatibilityValidator, '_test_filesystem_compatibility')
    @patch.object(CompatibilityValidator, '_test_gui_display_compatibility')
    def test_screen_resolution_filesystem_compatibility(
        self, mock_gui, mock_filesystem, mock_resolution, mock_get_resolution
    ):
        """画面解像度・ファイルシステム互換性テストのテスト"""
        # モックの設定
        mock_get_resolution.return_value = (1920, 1080)
        mock_resolution.return_value = {'ui_scaling': True}
        mock_filesystem.return_value = {'file_operations': True}
        mock_gui.return_value = {'display_accuracy': True}
        
        # テスト環境のセットアップ
        self.validator.setup_test_environment()
        
        # テストの実行
        self.validator.test_screen_resolution_filesystem_compatibility()
        
        # 結果の確認
        self.assertEqual(len(self.validator.compatibility_metrics), 1)
        metric = self.validator.compatibility_metrics[0]
        self.assertEqual(metric.test_name, "screen_resolution_filesystem_compatibility")
        self.assertEqual(metric.screen_resolution, (1920, 1080))
    
    @patch.object(CompatibilityValidator, '_test_encoding_file_processing')
    @patch.object(CompatibilityValidator, '_test_encoding_search_functionality')
    def test_character_encoding_compatibility(self, mock_search, mock_processing):
        """文字エンコーディング互換性テストのテスト"""
        # モックの設定
        mock_processing.return_value = {
            'utf-8': {'japanese_hiragana': True, 'japanese_kanji': True},
            'shift_jis': {'japanese_hiragana': True, 'japanese_kanji': True}
        }
        mock_search.return_value = {
            'utf-8': {'basic_search': True, 'japanese_search': True},
            'shift_jis': {'basic_search': True, 'japanese_search': True}
        }
        
        # テスト環境のセットアップ
        self.validator.setup_test_environment()
        
        # テストの実行
        self.validator.test_character_encoding_compatibility()
        
        # 結果の確認
        self.assertEqual(len(self.validator.compatibility_metrics), 1)
        metric = self.validator.compatibility_metrics[0]
        self.assertEqual(metric.test_name, "character_encoding_compatibility")
        self.assertIsInstance(metric.encoding_support, dict)
    
    @patch.object(CompatibilityValidator, '_test_low_memory_environment')
    @patch.object(CompatibilityValidator, '_test_low_disk_environment')
    @patch.object(CompatibilityValidator, '_test_low_cpu_environment')
    @patch.object(CompatibilityValidator, '_test_combined_resource_limits')
    def test_limited_resource_environment_compatibility(
        self, mock_combined, mock_cpu, mock_disk, mock_memory
    ):
        """限定リソース環境互換性テストのテスト"""
        # モックの設定
        mock_memory.return_value = {
            'basic_functionality': True,
            'acceptable_performance': True,
            'critical_errors': [],
            'performance_metrics': {'execution_time': 5.0}
        }
        mock_disk.return_value = {
            'basic_functionality': True,
            'acceptable_performance': True,
            'critical_errors': [],
            'performance_metrics': {'execution_time': 3.0}
        }
        mock_cpu.return_value = {
            'basic_functionality': True,
            'acceptable_performance': True,
            'critical_errors': [],
            'performance_metrics': {'execution_time': 7.0}
        }
        mock_combined.return_value = {
            'basic_functionality': True,
            'acceptable_performance': False,
            'critical_errors': [],
            'performance_metrics': {'execution_time': 10.0}
        }
        
        # テスト環境のセットアップ
        self.validator.setup_test_environment()
        
        # テストの実行
        self.validator.test_limited_resource_environment_compatibility()
        
        # 結果の確認
        self.assertEqual(len(self.validator.compatibility_metrics), 1)
        metric = self.validator.compatibility_metrics[0]
        self.assertEqual(metric.test_name, "limited_resource_environment_compatibility")
        self.assertIsInstance(metric.performance_metrics, dict)
    
    def test_helper_methods(self):
        """ヘルパーメソッドのテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()
        
        # _test_document_processing_feature のテスト
        result = self.validator._test_document_processing_feature()
        self.assertIsInstance(result, bool)
        
        # _test_search_feature のテスト
        result = self.validator._test_search_feature()
        self.assertIsInstance(result, bool)
        
        # _get_screen_resolution のテスト
        resolution = self.validator._get_screen_resolution()
        self.assertIsInstance(resolution, tuple)
        self.assertEqual(len(resolution), 2)
        self.assertIsInstance(resolution[0], int)
        self.assertIsInstance(resolution[1], int)
    
    def test_recommendation_generation(self):
        """推奨事項生成のテスト"""
        # Windows推奨事項
        issues = ["サポートされていないWindows版本", "メモリ不足"]
        recommendations = self.validator._generate_windows_recommendations(issues)
        self.assertIsInstance(recommendations, list)
        self.assertTrue(len(recommendations) > 0)
        
        # エンコーディング推奨事項
        issues = ["shift_jis のサポート不完全"]
        recommendations = self.validator._generate_encoding_recommendations(issues)
        self.assertIsInstance(recommendations, list)
        self.assertTrue(len(recommendations) > 0)
    
    def test_audit_methods(self):
        """監査メソッドのテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()
        
        # システム互換性監査
        result = self.validator._audit_system_compatibility()
        self.assertIsInstance(result, dict)
        self.assertIn('score', result)
        self.assertIn('critical_issues', result)
        
        # リソース互換性監査
        result = self.validator._audit_resource_compatibility()
        self.assertIsInstance(result, dict)
        self.assertIn('score', result)
        self.assertIn('critical_issues', result)


class TestCompatibilityThresholds(unittest.TestCase):
    """CompatibilityThresholdsクラスのテスト"""
    
    def test_default_values(self):
        """デフォルト値のテスト"""
        thresholds = CompatibilityThresholds()
        
        # デフォルト値の確認
        self.assertEqual(thresholds.min_windows_version, "10.0")
        self.assertEqual(thresholds.max_startup_time_seconds, 15.0)
        self.assertEqual(thresholds.min_memory_mb, 512)
        self.assertEqual(thresholds.max_memory_usage_mb, 2048)
        self.assertEqual(thresholds.min_disk_space_mb, 1024)
        self.assertEqual(thresholds.max_search_time_seconds, 10.0)
        self.assertIn('utf-8', thresholds.supported_encodings)
        self.assertIn('shift_jis', thresholds.supported_encodings)
        self.assertEqual(thresholds.min_screen_resolution, (1024, 768))
        self.assertIn('NTFS', thresholds.supported_filesystems)


class TestCompatibilityMetrics(unittest.TestCase):
    """CompatibilityMetricsクラスのテスト"""
    
    def test_initialization(self):
        """初期化のテスト"""
        metrics = CompatibilityMetrics(
            test_name="test_compatibility",
            compatibility_level="COMPATIBLE"
        )
        
        # 基本属性の確認
        self.assertEqual(metrics.test_name, "test_compatibility")
        self.assertEqual(metrics.compatibility_level, "COMPATIBLE")
        self.assertEqual(metrics.os_version, "")
        self.assertEqual(metrics.python_version, "")
        self.assertEqual(metrics.memory_available_mb, 0)
        self.assertEqual(metrics.disk_space_available_mb, 0)
        self.assertEqual(metrics.screen_resolution, (0, 0))
        self.assertEqual(metrics.filesystem_type, "")
        self.assertEqual(metrics.encoding_support, {})
        self.assertEqual(metrics.feature_compatibility, {})
        self.assertEqual(metrics.performance_metrics, {})
        self.assertEqual(metrics.limitations, [])
        self.assertEqual(metrics.recommendations, [])
        self.assertEqual(metrics.additional_details, {})


if __name__ == '__main__':
    # テストの実行
    unittest.main(verbosity=2)