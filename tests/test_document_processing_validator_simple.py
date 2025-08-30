"""
ドキュメント処理検証クラスの簡単なテスト

DocumentProcessingValidatorクラスの基本動作を検証します。
"""

import os
import shutil
import sys
import tempfile
import unittest

# テスト対象のインポート
sys.path.append(os.path.join(os.path.dirname(__file__), 'validation_framework'))

try:
    from base_validator import ValidationConfig
    from document_processing_validator import DocumentProcessingValidator
except ImportError as e:
    print(f"インポートエラー: {e}")
    sys.exit(1)


class TestDocumentProcessingValidatorSimple(unittest.TestCase):
    """DocumentProcessingValidatorの簡単なテストクラス"""

    def setUp(self):
        """テストセットアップ"""
        self.config = ValidationConfig(
            enable_performance_monitoring=False,  # パフォーマンス監視を無効化
            enable_memory_monitoring=False,       # メモリ監視を無効化
            max_execution_time=30.0,
            max_memory_usage=512.0,
            log_level="ERROR"  # ログレベルを下げる
        )

        self.validator = DocumentProcessingValidator(self.config)
        self.temp_dir = tempfile.mkdtemp(prefix="test_doc_validator_simple_")

    def tearDown(self):
        """テストクリーンアップ"""
        try:
            if hasattr(self.validator, 'teardown_test_environment'):
                self.validator.teardown_test_environment()
        except:
            pass

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_validator_initialization(self):
        """バリデーターの初期化テスト"""
        self.assertIsNotNone(self.validator)
        self.assertIsNotNone(self.validator.document_processor)
        self.assertIsNotNone(self.validator.test_data_generator)
        self.assertEqual(self.validator.processing_stats['files_processed'], 0)
        print("✓ バリデーター初期化テスト成功")

    def test_get_test_files_by_type(self):
        """ファイル形式別取得テスト"""
        # テストファイルの作成
        txt_file1 = os.path.join(self.temp_dir, "test1.txt")
        txt_file2 = os.path.join(self.temp_dir, "test2.txt")
        pdf_file = os.path.join(self.temp_dir, "test.pdf")

        with open(txt_file1, 'w') as f:
            f.write("content1")
        with open(txt_file2, 'w') as f:
            f.write("content2")
        with open(pdf_file, 'w') as f:
            f.write("pdf content")

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

        print("✓ ファイル形式別取得テスト成功")

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

        print("✓ 処理統計更新テスト成功")

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

        print("✓ 処理統計取得テスト成功")

    def test_create_empty_file(self):
        """空ファイル作成テスト"""
        self.validator.test_data_dir = self.temp_dir

        empty_file = self.validator._create_empty_file()

        self.assertTrue(os.path.exists(empty_file))
        self.assertEqual(os.path.getsize(empty_file), 0)

        print("✓ 空ファイル作成テスト成功")


if __name__ == '__main__':
    print("DocumentProcessingValidator 簡単なテストを開始します...")
    unittest.main(verbosity=2)
