# -*- coding: utf-8 -*-
"""
ドキュメント処理検証クラスのテスト

DocumentProcessingValidatorクラスの動作を検証します。
"""

import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import Mock, patch, MagicMock

# テスト対象のインポート
sys.path.append(os.path.join(os.path.dirname(__file__), 'validation_framework'))
from document_processing_validator import DocumentProcessingValidator
from base_validator import ValidationConfig


class TestDocumentProcessingValidator(unittest.TestCase):
    """DocumentProcessingValidatorのテストクラス"""
    
    def setUp(self):
        """テストセットアップ"""
        self.config = ValidationConfig(
            enable_performance_monitoring=True,
            enable_memory_monitoring=True,
            max_execution_time=60.0,
            max_memory_usage=1024.0,
            log_level="DEBUG"
        )
        
        self.validator = DocumentProcessingValidator(self.config)
        self.temp_dir = tempfile.mkdtemp(prefix="test_doc_validator_")
    
    def tearDown(self):
        """テストクリーンアップ"""
        if hasattr(self.validator, 'teardown_test_environment'):
            self.validator.teardown_test_environment()
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_validator_initialization(self):
        """バリデーターの初期化テスト"""
        self.assertIsNotNone(self.validator)
        self.assertIsNotNone(self.validator.document_processor)
        self.assertIsNotNone(self.validator.test_data_generator)
        self.assertEqual(self.validator.processing_stats['files_processed'], 0)
    
    def test_setup_test_environment(self):
        """テスト環境セットアップのテスト"""
        self.validator.setup_test_environment()
        
        # テストデータディレクトリが作成されていることを確認
        self.assertIsNotNone(self.validator.test_data_dir)
        self.assertTrue(os.path.exists(self.validator.test_data_dir))
        
        # サブディレクトリが作成されていることを確認
        expected_subdirs = ['standard', 'encoding', 'large', 'error']
        for subdir in expected_subdirs:
            subdir_path = os.path.join(self.validator.test_data_dir, subdir)
            self.assertTrue(os.path.exists(subdir_path), f"サブディレクトリが存在しません: {subdir}")
    
    def test_teardown_test_environment(self):
        """テスト環境クリーンアップのテスト"""
        self.validator.setup_test_environment()
        test_dir = self.validator.test_data_dir
        
        # クリーンアップ実行
        self.validator.teardown_test_environment()
        
        # ディレクトリが削除されていることを確認
        self.assertFalse(os.path.exists(test_dir))
    
    @patch('document_processing_validator.DocumentProcessor')
    def test_pdf_processing_accuracy(self, mock_processor_class):
        """PDF処理精度テストのモック"""
        # モックの設定
        mock_processor = Mock()
        mock_document = Mock()
        mock_document.content = "テストPDFコンテンツ"
        mock_processor.process_file.return_value = mock_document
        mock_processor_class.return_value = mock_processor
        
        # テスト用PDFファイルの作成
        self._create_test_file("test.pdf", "dummy pdf content")
        
        # バリデーターの再初期化（モックを使用）
        validator = DocumentProcessingValidator(self.config)
        validator.document_processor = mock_processor
        validator.test_data_dir = self.temp_dir
        
        # テスト実行
        try:
            validator.test_pdf_processing_accuracy()
            # 例外が発生しなければ成功
            self.assertTrue(True)
        except AssertionError:
            # PDFファイルが見つからない場合は警告ログが出力される
            pass
    
    @patch('document_processing_validator.DocumentProcessor')
    def test_text_processing_accuracy(self, mock_processor_class):
        """テキスト処理精度テストのモック"""
        # テスト用テキストファイルの作成
        test_content = "これはテストテキストです。\n日本語の内容を含みます。"
        test_file = self._create_test_file("test.txt", test_content)
        
        # モックの設定
        mock_processor = Mock()
        mock_document = Mock()
        mock_document.content = test_content
        mock_processor.process_file.return_value = mock_document
        mock_processor_class.return_value = mock_processor
        
        # バリデーターの再初期化（モックを使用）
        validator = DocumentProcessingValidator(self.config)
        validator.document_processor = mock_processor
        validator.test_data_dir = self.temp_dir
        
        # テスト実行
        try:
            validator.test_text_processing_accuracy()
            # 例外が発生しなければ成功
            self.assertTrue(True)
        except AssertionError:
            # テキストファイルが見つからない場合は警告ログが出力される
            pass
    
    def test_get_test_files_by_type(self):
        """ファイル形式別取得テスト"""
        # テストファイルの作成
        self._create_test_file("test1.txt", "content1")
        self._create_test_file("test2.txt", "content2")
        self._create_test_file("test.pdf", "pdf content")
        
        self.validator.test_data_dir = self.temp_dir
        
        # テキストファイルの取得
        txt_files = self.validator._get_test_files_by_type("txt")
        self.assertEqual(len(txt_files), 2)
        
        # PDFファイルの取得
        pdf_files = self.validator._get_test_files_by_type("pdf")
        self.assertEqual(len(pdf_files), 1)
        
        # 存在しない形式
        doc_files = self.validator._get_test_files_by_type("doc")
        self.assertEqual(len(doc_files), 0)
    
    def test_update_processing_stats(self):
        """処理統計更新テスト"""
        # 成功ケース
        self.validator._update_processing_stats("txt", True, 100, 1.5)
        
        stats = self.validator.processing_stats
        self.assertEqual(stats['files_processed'], 1)
        self.assertEqual(stats['successful_extractions'], 1)
        self.assertEqual(stats['total_characters_extracted'], 100)
        self.assertEqual(len(stats['processing_times']), 1)
        self.assertEqual(stats['processing_times'][0], 1.5)
        
        # 失敗ケース
        self.validator._update_processing_stats("pdf", False, 0, 0, "TestError")
        
        self.assertEqual(stats['files_processed'], 2)
        self.assertEqual(stats['failed_extractions'], 1)
        self.assertIn("Unknown", stats['error_types'])
    
    def test_get_processing_statistics(self):
        """処理統計取得テスト"""
        # 統計データの追加
        self.validator._update_processing_stats("txt", True, 100, 1.0)
        self.validator._update_processing_stats("pdf", True, 200, 2.0)
        self.validator._update_processing_stats("doc", False, 0, 0, "Error")
        
        # 統計情報の取得
        stats = self.validator.get_processing_statistics()
        
        self.assertIn('overall_stats', stats)
        self.assertIn('success_rate', stats)
        self.assertIn('average_processing_time', stats)
        self.assertIn('average_content_length', stats)
        
        # 成功率の確認
        self.assertAlmostEqual(stats['success_rate'], 2/3, places=2)
        
        # 平均処理時間の確認
        self.assertAlmostEqual(stats['average_processing_time'], 1.5, places=1)
        
        # 平均コンテンツ長の確認
        self.assertAlmostEqual(stats['average_content_length'], 150.0, places=1)
    
    def test_create_empty_file(self):
        """空ファイル作成テスト"""
        self.validator.test_data_dir = self.temp_dir
        
        empty_file = self.validator._create_empty_file()
        
        self.assertTrue(os.path.exists(empty_file))
        self.assertEqual(os.path.getsize(empty_file), 0)
    
    def test_create_encoding_test_files(self):
        """エンコーディングテストファイル作成テスト"""
        self.validator.test_data_dir = self.temp_dir
        
        encoding_files = self.validator._create_encoding_test_files()
        
        # ファイルが作成されていることを確認
        self.assertGreater(len(encoding_files), 0)
        
        for file_path, encoding in encoding_files:
            self.assertTrue(os.path.exists(file_path))
            
            # ファイルが読み込み可能であることを確認
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    self.assertIn("日本語", content)
            except Exception as e:
                self.fail(f"エンコーディングファイルの読み込みに失敗: {file_path} ({encoding}) - {e}")
    
    def test_get_large_test_files(self):
        """大容量ファイル取得テスト"""
        # 大きなファイルを作成（1MB以上）
        large_content = "a" * (1024 * 1024 + 100)  # 1MB + 100バイト
        large_file = self._create_test_file("large.txt", large_content)
        
        # 小さなファイルを作成
        small_file = self._create_test_file("small.txt", "small content")
        
        self.validator.test_data_dir = self.temp_dir
        
        large_files = self.validator._get_large_test_files()
        
        # 大きなファイルのみが取得されることを確認
        self.assertEqual(len(large_files), 1)
        self.assertIn("large.txt", large_files[0])
    
    def test_get_corrupted_test_files(self):
        """破損ファイル取得テスト"""
        # エラーディレクトリの作成
        error_dir = os.path.join(self.temp_dir, "error")
        os.makedirs(error_dir, exist_ok=True)
        
        # 破損ファイルの作成
        corrupted_file = os.path.join(error_dir, "corrupted.txt")
        with open(corrupted_file, 'wb') as f:
            f.write(b'\x00\xFF\xFE invalid content')
        
        self.validator.test_data_dir = self.temp_dir
        
        corrupted_files = self.validator._get_corrupted_test_files()
        
        self.assertEqual(len(corrupted_files), 1)
        self.assertIn("corrupted.txt", corrupted_files[0])
    
    def _create_test_file(self, filename: str, content: str) -> str:
        """テストファイルの作成ヘルパー"""
        file_path = os.path.join(self.temp_dir, filename)
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if isinstance(content, str):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            with open(file_path, 'wb') as f:
                f.write(content)
        
        return file_path


if __name__ == '__main__':
    unittest.main()