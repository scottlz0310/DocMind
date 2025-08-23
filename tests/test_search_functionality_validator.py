# -*- coding: utf-8 -*-
"""
SearchFunctionalityValidatorのテストケース

検索機能包括検証クラスの動作を検証するテストケースです。
"""

import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.validation_framework.search_functionality_validator import SearchFunctionalityValidator
from tests.validation_framework.base_validator import ValidationConfig
from src.data.models import SearchQuery, SearchType, FileType


class TestSearchFunctionalityValidator(unittest.TestCase):
    """SearchFunctionalityValidatorのテストクラス"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config = ValidationConfig(
            enable_performance_monitoring=True,
            enable_memory_monitoring=True,
            enable_error_injection=False,
            log_level="DEBUG"
        )
        
        self.validator = SearchFunctionalityValidator(self.config)
        
        # テスト用の一時ディレクトリ
        self.test_dir = tempfile.mkdtemp(prefix="search_validator_test_")
    
    def tearDown(self):
        """テストクリーンアップ"""
        try:
            self.validator.cleanup()
            if os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
        except Exception as e:
            print(f"クリーンアップ中にエラーが発生しました: {e}")
    
    def test_validator_initialization(self):
        """バリデーターの初期化テスト"""
        self.assertIsNotNone(self.validator)
        self.assertIsNotNone(self.validator.data_generator)
        self.assertEqual(self.validator.max_search_time, 5.0)
        self.assertEqual(self.validator.max_memory_usage, 2048.0)
        self.assertEqual(self.validator.min_precision, 0.7)
        self.assertEqual(self.validator.min_recall, 0.6)
        self.assertEqual(self.validator.min_f1_score, 0.65)
    
    @patch('src.core.search_manager.SearchManager')
    @patch('src.core.document_processor.DocumentProcessor')
    @patch('src.core.embedding_manager.EmbeddingManager')
    @patch('src.core.index_manager.IndexManager')
    def test_setup_test_environment(self, mock_index_manager, mock_embedding_manager,
                                  mock_doc_processor, mock_search_manager):
        """テスト環境セットアップのテスト"""
        # モックの設定
        mock_index_manager.return_value = Mock()
        mock_embedding_manager.return_value = Mock()
        mock_doc_processor.return_value = Mock()
        mock_search_manager.return_value = Mock()
        
        # テスト実行
        self.validator.setup_test_environment()
        
        # 検証
        self.assertIsNotNone(self.validator.test_data_dir)
        self.assertIsNotNone(self.validator.search_manager)
        self.assertIsNotNone(self.validator.index_manager)
        self.assertIsNotNone(self.validator.embedding_manager)
        self.assertIsNotNone(self.validator.document_processor)
        
        # モックが呼ばれたことを確認
        mock_index_manager.assert_called_once()
        mock_embedding_manager.assert_called_once()
        mock_doc_processor.assert_called_once()
        mock_search_manager.assert_called_once()
    
    def test_teardown_test_environment(self):
        """テスト環境クリーンアップのテスト"""
        # モックオブジェクトを設定
        self.validator.search_manager = Mock()
        self.validator.embedding_manager = Mock()
        self.validator.test_data_dir = self.test_dir
        
        # テスト実行
        self.validator.teardown_test_environment()
        
        # 検証
        self.validator.search_manager.clear_suggestion_cache.assert_called_once()
        self.validator.embedding_manager.clear_cache.assert_called_once()
    
    def test_calculate_search_accuracy(self):
        """検索精度計算のテスト"""
        # テストデータの準備
        test_documents = [
            {
                'filename': 'test_doc_001.txt',
                'content': 'これはテストドキュメントです。',
                'keywords': ['テスト', 'ドキュメント']
            },
            {
                'filename': 'test_doc_002.txt', 
                'content': '検索機能のテストです。',
                'keywords': ['検索', '機能', 'テスト']
            }
        ]
        
        # モック検索結果の作成
        mock_result1 = Mock()
        mock_result1.document.file_path = '/path/to/test_doc_001.txt'
        
        mock_result2 = Mock()
        mock_result2.document.file_path = '/path/to/test_doc_002.txt'
        
        results = [mock_result1, mock_result2]
        
        # テスト実行
        precision, recall, f1_score = self.validator._calculate_search_accuracy(
            "テスト", results, test_documents
        )
        
        # 検証
        self.assertGreaterEqual(precision, 0.0)
        self.assertLessEqual(precision, 1.0)
        self.assertGreaterEqual(recall, 0.0)
        self.assertLessEqual(recall, 1.0)
        self.assertGreaterEqual(f1_score, 0.0)
        self.assertLessEqual(f1_score, 1.0)
    
    def test_calculate_semantic_search_accuracy(self):
        """セマンティック検索精度計算のテスト"""
        # テストデータの準備
        test_documents = [
            {
                'filename': 'doc1.txt',
                'keywords': ['ドキュメント', '検索']
            }
        ]
        
        # モック検索結果
        mock_result = Mock()
        mock_result.document.file_path = '/path/to/doc1.txt'
        results = [mock_result]
        
        # テスト実行
        precision, recall, f1_score = self.validator._calculate_semantic_search_accuracy(
            "文書の検索", results, test_documents
        )
        
        # 検証
        self.assertGreaterEqual(precision, 0.0)
        self.assertLessEqual(precision, 1.0)
        self.assertGreaterEqual(recall, 0.0)
        self.assertLessEqual(recall, 1.0)
    
    def test_get_search_metrics_summary_empty(self):
        """空の検索メトリクスサマリーのテスト"""
        summary = self.validator.get_search_metrics_summary()
        self.assertEqual(summary, {})
    
    def test_get_search_metrics_summary_with_data(self):
        """データありの検索メトリクスサマリーのテスト"""
        from tests.validation_framework.search_functionality_validator import SearchTestMetrics
        
        # テストメトリクスの追加
        metrics1 = SearchTestMetrics(
            query_text="テスト",
            search_type=SearchType.FULL_TEXT,
            execution_time=1.5,
            result_count=10,
            memory_usage=100.0,
            precision=0.8,
            recall=0.7,
            f1_score=0.75
        )
        
        metrics2 = SearchTestMetrics(
            query_text="検索",
            search_type=SearchType.SEMANTIC,
            execution_time=2.0,
            result_count=15,
            memory_usage=150.0,
            precision=0.7,
            recall=0.6,
            f1_score=0.65
        )
        
        self.validator.search_metrics = [metrics1, metrics2]
        
        # テスト実行
        summary = self.validator.get_search_metrics_summary()
        
        # 検証
        self.assertEqual(summary['total_searches'], 2)
        self.assertIn('by_type', summary)
        self.assertIn('overall_avg_time', summary)
        self.assertIn('performance_requirement_met', summary)
        self.assertIn('memory_requirement_met', summary)
        
        # 平均実行時間の検証
        expected_avg_time = (1.5 + 2.0) / 2
        self.assertEqual(summary['overall_avg_time'], expected_avg_time)
    
    @patch('tests.validation_framework.test_data_generator.TestDataGenerator')
    def test_data_generator_integration(self, mock_generator_class):
        """データ生成器統合のテスト"""
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        # 新しいバリデーターインスタンスを作成
        validator = SearchFunctionalityValidator(self.config)
        
        # 検証
        self.assertIsNotNone(validator.data_generator)
        mock_generator_class.assert_called_once()


class TestSearchFunctionalityValidatorIntegration(unittest.TestCase):
    """SearchFunctionalityValidatorの統合テストクラス"""
    
    def setUp(self):
        """統合テストセットアップ"""
        self.config = ValidationConfig(
            enable_performance_monitoring=False,  # 統合テストでは無効化
            enable_memory_monitoring=False,
            enable_error_injection=False,
            log_level="WARNING"  # ログレベルを上げてノイズを減らす
        )
    
    @unittest.skipIf(
        not os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'src')),
        "DocMindソースコードが見つかりません"
    )
    def test_full_validation_workflow(self):
        """完全な検証ワークフローのテスト"""
        validator = SearchFunctionalityValidator(self.config)
        
        try:
            # 基本的なワークフローをテスト
            validator.setup_test_environment()
            
            # 簡単なテストデータを作成
            test_dir = validator.test_data_dir
            test_file = os.path.join(test_dir, "test.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("これはテストドキュメントです。")
            
            # 基本的な機能が動作することを確認
            self.assertIsNotNone(validator.search_manager)
            self.assertIsNotNone(validator.index_manager)
            self.assertIsNotNone(validator.embedding_manager)
            
        finally:
            validator.teardown_test_environment()
            validator.cleanup()


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)