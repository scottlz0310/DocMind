# -*- coding: utf-8 -*-
"""
TestDatasetManagerクラスのテスト

テストデータセット管理システムの動作を検証します。
"""

import os
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime

# テスト対象のインポート
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tests.validation_framework.test_dataset_manager import (
    TestDatasetManager, DatasetInfo, DatasetMetrics, TestDatasetConfig
)


class TestTestDatasetManager(unittest.TestCase):
    """TestDatasetManagerクラスのテストケース"""
    
    def setUp(self):
        """テストセットアップ"""
        # 一時ディレクトリの作成
        self.temp_dir = tempfile.mkdtemp()
        self.manager = TestDatasetManager(base_directory=self.temp_dir)
    
    def tearDown(self):
        """テストクリーンアップ"""
        # 一時ディレクトリの削除
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """初期化のテスト"""
        # 基本属性の確認
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.base_directory, self.temp_dir)
        self.assertIsInstance(self.manager.datasets, dict)
        self.assertEqual(len(self.manager.datasets), 0)
        
        # ベースディレクトリが作成されているか確認
        self.assertTrue(os.path.exists(self.temp_dir))
        
        print("✓ TestDatasetManager初期化テスト成功")
    
    @patch('tests.validation_framework.test_dataset_manager.TestDataGenerator')
    def test_create_standard_dataset(self, mock_generator_class):
        """標準データセット作成のテスト"""
        # モックの設定
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_dataset.return_value = {
            'statistics': {
                'total_files': 100,
                'total_size_mb': 50.0,
                'by_type': {'txt': 50, 'md': 30, 'json': 20},
                'corrupted_files': 0,
                'large_files': 0,
                'special_char_files': 0
            }
        }
        
        # 新しいマネージャーインスタンスを作成（モックを使用するため）
        manager = TestDatasetManager(base_directory=self.temp_dir)
        
        # 標準データセットの作成
        dataset_info = manager.create_standard_dataset(
            name="test_standard",
            file_count=100
        )
        
        # 結果の検証
        self.assertIsInstance(dataset_info, DatasetInfo)
        self.assertEqual(dataset_info.name, "test_standard")
        self.assertEqual(dataset_info.dataset_type, "standard")
        self.assertEqual(dataset_info.status, "ready")
        self.assertEqual(dataset_info.metrics.total_files, 100)
        self.assertEqual(dataset_info.metrics.total_size_mb, 50.0)
        
        # データセットが管理されているか確認
        self.assertIn("test_standard", manager.datasets)
        
        print("✓ 標準データセット作成テスト成功")
    
    @patch('tests.validation_framework.test_dataset_manager.TestDataGenerator')
    def test_create_large_dataset(self, mock_generator_class):
        """大規模データセット作成のテスト"""
        # モックの設定
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_dataset.return_value = {
            'statistics': {
                'total_files': 50000,
                'total_size_mb': 5000.0,
                'by_type': {'txt': 20000, 'md': 15000, 'json': 10000, 'csv': 5000},
                'corrupted_files': 100,
                'large_files': 250,
                'special_char_files': 500
            }
        }
        
        # 新しいマネージャーインスタンスを作成
        manager = TestDatasetManager(base_directory=self.temp_dir)
        
        # 大規模データセットの作成
        dataset_info = manager.create_large_dataset(
            name="test_large",
            file_count=50000
        )
        
        # 結果の検証
        self.assertIsInstance(dataset_info, DatasetInfo)
        self.assertEqual(dataset_info.name, "test_large")
        self.assertEqual(dataset_info.dataset_type, "large")
        self.assertEqual(dataset_info.status, "ready")
        self.assertEqual(dataset_info.metrics.total_files, 50000)
        self.assertEqual(dataset_info.metrics.total_size_mb, 5000.0)
        self.assertEqual(dataset_info.metrics.corrupted_files, 100)
        self.assertEqual(dataset_info.metrics.large_files, 250)
        
        print("✓ 大規模データセット作成テスト成功")
    
    @patch('tests.validation_framework.test_dataset_manager.TestDataGenerator')
    def test_create_edge_case_dataset(self, mock_generator_class):
        """エッジケースデータセット作成のテスト"""
        # モックの設定
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_dataset.return_value = {
            'statistics': {
                'total_files': 500,
                'total_size_mb': 1000.0,
                'by_type': {'txt': 200, 'pdf': 150, 'docx': 100, 'xlsx': 50},
                'corrupted_files': 50,
                'large_files': 25,
                'special_char_files': 100
            }
        }
        
        # 新しいマネージャーインスタンスを作成
        manager = TestDatasetManager(base_directory=self.temp_dir)
        
        # エッジケースデータセットの作成
        dataset_info = manager.create_edge_case_dataset(
            name="test_edge_case",
            file_count=500
        )
        
        # 結果の検証
        self.assertIsInstance(dataset_info, DatasetInfo)
        self.assertEqual(dataset_info.name, "test_edge_case")
        self.assertEqual(dataset_info.dataset_type, "edge_case")
        self.assertEqual(dataset_info.status, "ready")
        self.assertEqual(dataset_info.metrics.total_files, 500)
        self.assertEqual(dataset_info.metrics.corrupted_files, 50)
        self.assertEqual(dataset_info.metrics.special_char_files, 100)
        
        print("✓ エッジケースデータセット作成テスト成功")
    
    def test_dataset_management(self):
        """データセット管理機能のテスト"""
        # テスト用のデータセット情報を作成
        metrics = DatasetMetrics(
            total_files=100,
            total_size_mb=50.0,
            file_types={'txt': 50, 'md': 50}
        )
        
        config = TestDatasetConfig(
            dataset_name="test_dataset",
            output_directory=os.path.join(self.temp_dir, "test_dataset"),
            file_count=100
        )
        
        dataset_info = DatasetInfo(
            name="test_dataset",
            path=config.output_directory,
            dataset_type="standard",
            created_at=datetime.now(),
            metrics=metrics,
            config=config
        )
        
        # データセットディレクトリを作成
        os.makedirs(dataset_info.path, exist_ok=True)
        
        # データセットを手動で追加
        self.manager.datasets["test_dataset"] = dataset_info
        
        # データセット情報の取得テスト
        retrieved_info = self.manager.get_dataset_info("test_dataset")
        self.assertIsNotNone(retrieved_info)
        self.assertEqual(retrieved_info.name, "test_dataset")
        
        # データセット一覧の取得テスト
        datasets = self.manager.list_datasets()
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].name, "test_dataset")
        
        # データセット削除テスト
        success = self.manager.delete_dataset("test_dataset")
        self.assertTrue(success)
        self.assertNotIn("test_dataset", self.manager.datasets)
        
        print("✓ データセット管理機能テスト成功")
    
    def test_dataset_validation(self):
        """データセット検証機能のテスト"""
        # テスト用のデータセットを作成
        dataset_dir = os.path.join(self.temp_dir, "validation_test")
        os.makedirs(dataset_dir, exist_ok=True)
        
        # テストファイルを作成
        test_files = []
        for i in range(5):
            file_path = os.path.join(dataset_dir, f"test_file_{i}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"テストファイル {i} の内容")
            test_files.append(file_path)
        
        # データセット情報を作成
        metrics = DatasetMetrics(
            total_files=5,
            total_size_mb=0.001,
            file_types={'txt': 5}
        )
        
        config = TestDatasetConfig(
            dataset_name="validation_test",
            output_directory=dataset_dir,
            file_count=5
        )
        
        dataset_info = DatasetInfo(
            name="validation_test",
            path=dataset_dir,
            dataset_type="standard",
            created_at=datetime.now(),
            metrics=metrics,
            config=config
        )
        
        self.manager.datasets["validation_test"] = dataset_info
        
        # 検証の実行
        validation_result = self.manager.validate_dataset("validation_test")
        
        # 結果の確認
        self.assertTrue(validation_result['valid'])
        self.assertEqual(validation_result['file_count'], 5)
        self.assertEqual(len(validation_result['errors']), 0)
        self.assertEqual(len(validation_result['missing_files']), 0)
        
        print("✓ データセット検証機能テスト成功")
    
    def test_config_persistence(self):
        """設定の永続化テスト"""
        # テスト用のデータセット情報を作成
        metrics = DatasetMetrics(
            total_files=10,
            total_size_mb=5.0,
            file_types={'txt': 10}
        )
        
        config = TestDatasetConfig(
            dataset_name="persistence_test",
            output_directory=os.path.join(self.temp_dir, "persistence_test"),
            file_count=10
        )
        
        dataset_info = DatasetInfo(
            name="persistence_test",
            path=config.output_directory,
            dataset_type="standard",
            created_at=datetime.now(),
            metrics=metrics,
            config=config
        )
        
        # データセットディレクトリを作成
        os.makedirs(dataset_info.path, exist_ok=True)
        
        # データセットを追加して保存
        self.manager.datasets["persistence_test"] = dataset_info
        self.manager._save_datasets_config()
        
        # 設定ファイルが作成されているか確認
        config_file = os.path.join(self.temp_dir, "datasets_config.json")
        self.assertTrue(os.path.exists(config_file))
        
        # 新しいマネージャーインスタンスで設定を読み込み
        new_manager = TestDatasetManager(base_directory=self.temp_dir)
        
        # データセットが復元されているか確認
        self.assertIn("persistence_test", new_manager.datasets)
        restored_info = new_manager.get_dataset_info("persistence_test")
        self.assertEqual(restored_info.name, "persistence_test")
        self.assertEqual(restored_info.metrics.total_files, 10)
        
        print("✓ 設定の永続化テスト成功")
    
    @patch('tests.validation_framework.test_dataset_manager.TestDataGenerator')
    def test_comprehensive_test_suite_generation(self, mock_generator_class):
        """包括的テストスイート生成のテスト"""
        # モックの設定
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        
        # 各データセットタイプに対する戻り値を設定
        def mock_generate_dataset(config):
            if "standard" in config.dataset_name:
                return {
                    'statistics': {
                        'total_files': 1000,
                        'total_size_mb': 100.0,
                        'by_type': {'txt': 400, 'md': 300, 'json': 300},
                        'corrupted_files': 0,
                        'large_files': 0,
                        'special_char_files': 0
                    }
                }
            elif "large" in config.dataset_name:
                return {
                    'statistics': {
                        'total_files': 10000,
                        'total_size_mb': 1000.0,
                        'by_type': {'txt': 4000, 'md': 3000, 'json': 3000},
                        'corrupted_files': 200,
                        'large_files': 100,
                        'special_char_files': 500
                    }
                }
            elif "edge_case" in config.dataset_name:
                return {
                    'statistics': {
                        'total_files': 500,
                        'total_size_mb': 500.0,
                        'by_type': {'txt': 200, 'pdf': 150, 'docx': 150},
                        'corrupted_files': 50,
                        'large_files': 25,
                        'special_char_files': 100
                    }
                }
        
        mock_generator.generate_dataset.side_effect = mock_generate_dataset
        
        # 新しいマネージャーインスタンスを作成
        manager = TestDatasetManager(base_directory=self.temp_dir)
        
        # 包括的テストスイートの生成
        datasets = manager.generate_comprehensive_test_suite()
        
        # 結果の検証
        self.assertEqual(len(datasets), 3)
        self.assertIn('standard', datasets)
        self.assertIn('large', datasets)
        self.assertIn('edge_case', datasets)
        
        # 各データセットの詳細確認
        standard_dataset = datasets['standard']
        self.assertEqual(standard_dataset.dataset_type, 'standard')
        self.assertEqual(standard_dataset.metrics.total_files, 1000)
        
        large_dataset = datasets['large']
        self.assertEqual(large_dataset.dataset_type, 'large')
        self.assertEqual(large_dataset.metrics.total_files, 10000)
        
        edge_case_dataset = datasets['edge_case']
        self.assertEqual(edge_case_dataset.dataset_type, 'edge_case')
        self.assertEqual(edge_case_dataset.metrics.total_files, 500)
        
        print("✓ 包括的テストスイート生成テスト成功")
    
    def test_generation_status_tracking(self):
        """生成状況追跡のテスト"""
        # テスト用のデータセット情報を作成
        metrics = DatasetMetrics()
        config = TestDatasetConfig(
            dataset_name="status_test",
            output_directory=os.path.join(self.temp_dir, "status_test"),
            file_count=100
        )
        
        dataset_info = DatasetInfo(
            name="status_test",
            path=config.output_directory,
            dataset_type="standard",
            created_at=datetime.now(),
            metrics=metrics,
            config=config,
            status="generating"
        )
        
        self.manager.datasets["status_test"] = dataset_info
        
        # 生成状況の取得
        status = self.manager.get_generation_status("status_test")
        
        # 結果の確認
        self.assertEqual(status['status'], 'generating')
        self.assertEqual(status['name'], 'status_test')
        self.assertEqual(status['dataset_type'], 'standard')
        self.assertFalse(status['is_generating'])  # 実際のスレッドは動いていない
        
        # 存在しないデータセットの状況確認
        status = self.manager.get_generation_status("nonexistent")
        self.assertEqual(status['status'], 'not_found')
        
        print("✓ 生成状況追跡テスト成功")


if __name__ == '__main__':
    # ログ設定
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # テスト実行
    unittest.main(verbosity=2)