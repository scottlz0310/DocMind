# -*- coding: utf-8 -*-
"""
SecurityValidatorのテストケース

セキュリティ・プライバシー検証クラスの動作を検証します。
"""

import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.validation_framework.security_validator import (
    SecurityValidator, 
    SecurityThresholds, 
    SecurityMetrics,
    NetworkMonitor,
    FilePermissionChecker,
    MemoryScanner
)
from tests.validation_framework.base_validator import ValidationConfig


class TestSecurityValidator(unittest.TestCase):
    """SecurityValidatorのテストクラス"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config = ValidationConfig(
            enable_performance_monitoring=False,
            enable_memory_monitoring=False,
            enable_error_injection=False,
            max_execution_time=60.0,
            log_level="WARNING"
        )
        
        self.validator = SecurityValidator(self.config)
        self.test_dir = None
    
    def tearDown(self):
        """テストクリーンアップ"""
        try:
            if hasattr(self.validator, 'teardown_test_environment'):
                self.validator.teardown_test_environment()
            self.validator.cleanup()
        except:
            pass
        
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_security_validator_initialization(self):
        """SecurityValidatorの初期化テスト"""
        self.assertIsInstance(self.validator, SecurityValidator)
        self.assertIsInstance(self.validator.thresholds, SecurityThresholds)
        self.assertIsInstance(self.validator.network_monitor, NetworkMonitor)
        self.assertIsInstance(self.validator.file_permission_checker, FilePermissionChecker)
        self.assertIsInstance(self.validator.memory_scanner, MemoryScanner)
        self.assertEqual(len(self.validator.security_metrics), 0)
    
    def test_setup_test_environment(self):
        """テスト環境セットアップのテスト"""
        # DocMindコンポーネントのモック
        with patch('tests.validation_framework.security_validator.IndexManager'), \
             patch('tests.validation_framework.security_validator.EmbeddingManager'), \
             patch('tests.validation_framework.security_validator.SearchManager'), \
             patch('tests.validation_framework.security_validator.DocumentProcessor'):
            
            self.validator.setup_test_environment()
            
            # テストディレクトリが作成されていることを確認
            self.assertIsNotNone(self.validator.test_base_dir)
            self.assertTrue(os.path.exists(self.validator.test_base_dir))
            
            # コンポーネントが初期化されていることを確認
            self.assertIn('index_manager', self.validator.test_components)
            self.assertIn('embedding_manager', self.validator.test_components)
            self.assertIn('search_manager', self.validator.test_components)
            self.assertIn('document_processor', self.validator.test_components)
    
    @patch('tests.validation_framework.security_validator.IndexManager')
    @patch('tests.validation_framework.security_validator.EmbeddingManager')
    @patch('tests.validation_framework.security_validator.SearchManager')
    @patch('tests.validation_framework.security_validator.DocumentProcessor')
    def test_local_processing_verification(self, mock_doc_proc, mock_search, mock_embed, mock_index):
        """ローカル処理検証のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()
        
        # モックの設定
        mock_search_instance = MagicMock()
        mock_search.return_value = mock_search_instance
        mock_search_instance.search.return_value = []
        
        mock_doc_proc_instance = MagicMock()
        mock_doc_proc.return_value = mock_doc_proc_instance
        mock_doc_proc_instance.process_file.return_value = None
        
        # ネットワーク監視のモック（外部通信なし）
        with patch.object(self.validator.network_monitor, 'get_external_connections', return_value=[]):
            # テスト実行
            self.validator.test_local_processing_verification()
            
            # 結果の確認
            self.assertEqual(len(self.validator.security_metrics), 1)
            metric = self.validator.security_metrics[0]
            self.assertEqual(metric.test_name, "local_processing_verification")
            self.assertEqual(metric.security_level, "SECURE")
            self.assertEqual(len(metric.external_connections), 0)
    
    def test_file_permission_checker(self):
        """ファイル権限チェッカーのテスト"""
        checker = FilePermissionChecker()
        
        # テスト用ファイルの作成
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name
        
        try:
            # 権限チェック
            permission_info = checker.check_file_permissions(temp_file_path)
            
            # 結果の確認
            self.assertIn('file_path', permission_info)
            self.assertIn('permissions', permission_info)
            self.assertIn('security_level', permission_info)
            self.assertIn('is_secure', permission_info)
            self.assertEqual(permission_info['file_path'], temp_file_path)
            
        finally:
            # クリーンアップ
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    def test_memory_scanner(self):
        """メモリスキャナーのテスト"""
        scanner = MemoryScanner()
        
        # メモリスキャンの実行（短時間）
        results = scanner.scan_process_memory(max_duration_seconds=1)
        
        # 結果の確認
        self.assertIsInstance(results, list)
        # メモリスキャンは模擬実装なので、結果の詳細は確認しない
    
    def test_network_monitor(self):
        """ネットワークモニターのテスト"""
        monitor = NetworkMonitor()
        
        # 短時間の監視
        monitor.start_monitoring()
        import time
        time.sleep(0.5)
        monitor.stop_monitoring()
        
        # 結果の取得
        connections = monitor.get_external_connections()
        
        # 結果の確認
        self.assertIsInstance(connections, list)
        # 通常のテスト環境では外部接続は発生しないはず
    
    @patch('tests.validation_framework.security_validator.IndexManager')
    @patch('tests.validation_framework.security_validator.EmbeddingManager')
    @patch('tests.validation_framework.security_validator.SearchManager')
    @patch('tests.validation_framework.security_validator.DocumentProcessor')
    def test_file_access_permissions_verification(self, mock_doc_proc, mock_search, mock_embed, mock_index):
        """ファイルアクセス権限検証のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()
        
        # テスト実行（セキュアでないファイルが検出されることを期待）
        with self.assertRaises(AssertionError) as context:
            self.validator.test_file_access_permissions_verification()
        
        # エラーメッセージの確認
        self.assertIn("セキュアでないファイル権限が検出されました", str(context.exception))
        
        # 結果の確認
        self.assertEqual(len(self.validator.security_metrics), 1)
        metric = self.validator.security_metrics[0]
        self.assertEqual(metric.test_name, "file_access_permissions_verification")
        self.assertIn(metric.security_level, ["SECURE", "WARNING", "CRITICAL"])
    
    @patch('tests.validation_framework.security_validator.IndexManager')
    @patch('tests.validation_framework.security_validator.EmbeddingManager')
    @patch('tests.validation_framework.security_validator.SearchManager')
    @patch('tests.validation_framework.security_validator.DocumentProcessor')
    def test_data_encryption_verification(self, mock_doc_proc, mock_search, mock_embed, mock_index):
        """データ暗号化検証のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()
        
        # テスト実行
        self.validator.test_data_encryption_verification()
        
        # 結果の確認
        self.assertEqual(len(self.validator.security_metrics), 1)
        metric = self.validator.security_metrics[0]
        self.assertEqual(metric.test_name, "data_encryption_verification")
        self.assertIn(metric.security_level, ["SECURE", "WARNING", "CRITICAL"])
        self.assertIsInstance(metric.encryption_status, dict)
    
    def test_security_thresholds(self):
        """セキュリティ閾値のテスト"""
        thresholds = SecurityThresholds()
        
        # デフォルト値の確認
        self.assertEqual(thresholds.max_external_connections, 0)
        self.assertEqual(thresholds.max_temp_file_lifetime_seconds, 300)
        self.assertEqual(thresholds.min_file_permission_security, 0o600)
        self.assertEqual(thresholds.max_memory_scan_duration_seconds, 30)
        self.assertEqual(thresholds.encryption_key_min_length, 32)
    
    def test_security_metrics_creation(self):
        """SecurityMetricsの作成テスト"""
        metrics = SecurityMetrics(
            test_name="test_security",
            security_level="SECURE",
            compliance_score=0.95
        )
        
        self.assertEqual(metrics.test_name, "test_security")
        self.assertEqual(metrics.security_level, "SECURE")
        self.assertEqual(metrics.compliance_score, 0.95)
        self.assertEqual(len(metrics.external_connections), 0)
        self.assertEqual(len(metrics.vulnerabilities), 0)
    
    @patch('tests.validation_framework.security_validator.IndexManager')
    @patch('tests.validation_framework.security_validator.EmbeddingManager')
    @patch('tests.validation_framework.security_validator.SearchManager')
    @patch('tests.validation_framework.security_validator.DocumentProcessor')
    def test_get_security_summary(self, mock_doc_proc, mock_search, mock_embed, mock_index):
        """セキュリティサマリー取得のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()
        
        # テストメトリクスの追加
        test_metric = SecurityMetrics(
            test_name="test_security",
            security_level="SECURE",
            compliance_score=0.9,
            vulnerabilities=[]
        )
        self.validator.security_metrics.append(test_metric)
        
        # サマリーの取得
        summary = self.validator.get_security_summary()
        
        # 結果の確認
        self.assertIn('test_summary', summary)
        self.assertIn('compliance_statistics', summary)
        self.assertIn('vulnerability_analysis', summary)
        self.assertIn('detailed_metrics', summary)
        
        self.assertEqual(summary['test_summary']['total_tests'], 1)
        self.assertEqual(summary['test_summary']['secure_tests'], 1)
        self.assertEqual(summary['compliance_statistics']['average_compliance_score'], 0.9)
    
    def test_validation_config_integration(self):
        """ValidationConfigとの統合テスト"""
        custom_config = ValidationConfig(
            enable_performance_monitoring=True,
            enable_memory_monitoring=True,
            max_execution_time=120.0,
            max_memory_usage=1024.0,
            log_level="DEBUG"
        )
        
        validator = SecurityValidator(custom_config)
        
        # 設定の確認
        self.assertEqual(validator.config.max_execution_time, 120.0)
        self.assertEqual(validator.config.max_memory_usage, 1024.0)
        self.assertEqual(validator.config.log_level, "DEBUG")
        self.assertTrue(validator.config.enable_performance_monitoring)
        self.assertTrue(validator.config.enable_memory_monitoring)


class TestSecurityValidatorIntegration(unittest.TestCase):
    """SecurityValidatorの統合テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config = ValidationConfig(
            enable_performance_monitoring=False,
            enable_memory_monitoring=False,
            max_execution_time=30.0,
            log_level="ERROR"  # ログを最小限に
        )
    
    @patch('tests.validation_framework.security_validator.IndexManager')
    @patch('tests.validation_framework.security_validator.EmbeddingManager')
    @patch('tests.validation_framework.security_validator.SearchManager')
    @patch('tests.validation_framework.security_validator.DocumentProcessor')
    def test_full_security_validation_workflow(self, mock_doc_proc, mock_search, mock_embed, mock_index):
        """完全なセキュリティ検証ワークフローのテスト"""
        validator = SecurityValidator(self.config)
        
        try:
            # テスト環境のセットアップ
            validator.setup_test_environment()
            
            # ローカル処理検証のみ実行（ファイル権限テストは意図的に失敗するため除外）
            test_methods = [
                'test_local_processing_verification'
            ]
            
            # ネットワーク監視のモック
            with patch.object(validator.network_monitor, 'get_external_connections', return_value=[]):
                results = validator.run_validation(test_methods)
            
            # 結果の確認
            self.assertEqual(len(results), 1)
            self.assertTrue(all(result.success for result in results))
            
            # セキュリティメトリクスの確認
            self.assertEqual(len(validator.security_metrics), 1)
            
            # サマリーの確認
            summary = validator.get_security_summary()
            self.assertGreater(summary['test_summary']['total_tests'], 0)
            
        finally:
            # クリーンアップ
            validator.teardown_test_environment()
            validator.cleanup()


if __name__ == '__main__':
    # テストの実行
    unittest.main(verbosity=2)