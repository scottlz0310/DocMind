"""
Phase7 DocumentProcessorの強化テストモジュール

ドキュメント処理機能の包括的なテストを提供します。
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.document_processor import DocumentProcessor
from src.data.models import FileType
from src.utils.exceptions import DocumentProcessingError


class TestDocumentProcessorPhase7:
    """Phase7 DocumentProcessorの強化テストクラス"""

    @pytest.fixture
    def processor(self):
        """DocumentProcessorインスタンスを作成"""
        return DocumentProcessor()

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_initialization(self, processor):
        """初期化テスト"""
        assert processor is not None

    def test_extract_pdf_text_accuracy(self, processor, temp_dir):
        """PDF テキスト抽出精度テスト"""
        # テスト用PDFファイルを作成
        pdf_path = os.path.join(temp_dir, "test.pdf")
        Path(pdf_path).touch()

        with patch('src.core.document_processor.fitz') as mock_fitz:
            # モックPDFドキュメントを設定
            mock_doc = Mock()
            mock_page = Mock()
            mock_page.get_text.return_value = "これはPDFのテストテキストです。"
            mock_doc.__iter__ = Mock(return_value=iter([mock_page]))
            mock_doc.close = Mock()
            mock_fitz.open.return_value = mock_doc

            result = processor.extract_pdf_text(pdf_path)

            assert result.success is True
            assert "PDFのテストテキスト" in result.text
            assert result.metadata['file_type'] == 'pdf'
            mock_fitz.open.assert_called_once_with(pdf_path)

    def test_extract_pdf_text_no_library(self, processor, temp_dir):
        """PDFライブラリ未インストール時のテスト"""
        pdf_path = os.path.join(temp_dir, "test.pdf")
        Path(pdf_path).touch()

        with patch('src.core.document_processor.fitz', None):
            result = processor.extract_pdf_text(pdf_path)

            # ライブラリがない場合は警告ログが出力され、空の結果が返される
            assert result.success is False or result.text == ""

    def test_extract_word_text_accuracy(self, processor, temp_dir):
        """Word文書テキスト抽出精度テスト"""
        docx_path = os.path.join(temp_dir, "test.docx")
        Path(docx_path).touch()

        with patch('src.core.document_processor.docx') as mock_docx:
            # モックWordドキュメントを設定
            mock_doc = Mock()
            mock_paragraph = Mock()
            mock_paragraph.text = "これはWordドキュメントのテストテキストです。"
            mock_doc.paragraphs = [mock_paragraph]
            mock_docx.Document.return_value = mock_doc

            result = processor.extract_word_text(docx_path)

            assert result.success is True
            assert "Wordドキュメントのテストテキスト" in result.text
            assert result.metadata['file_type'] == 'word'

    def test_extract_excel_data_accuracy(self, processor, temp_dir):
        """Excel データ抽出精度テスト"""
        xlsx_path = os.path.join(temp_dir, "test.xlsx")
        Path(xlsx_path).touch()

        with patch('src.core.document_processor.openpyxl') as mock_openpyxl:
            # モックExcelワークブックを設定
            mock_workbook = Mock()
            mock_worksheet = Mock()
            mock_worksheet.title = "Sheet1"
            mock_worksheet.iter_rows.return_value = [
                [Mock(value="ヘッダー1"), Mock(value="ヘッダー2")],
                [Mock(value="データ1"), Mock(value="データ2")]
            ]
            mock_workbook.worksheets = [mock_worksheet]
            mock_openpyxl.load_workbook.return_value = mock_workbook

            result = processor.extract_excel_data(xlsx_path)

            assert result.success is True
            assert "ヘッダー1" in result.text
            assert "データ1" in result.text
            assert result.metadata['file_type'] == 'excel'
            assert result.metadata['sheet_count'] == 1

    def test_extract_markdown_text_accuracy(self, processor, temp_dir):
        """Markdown テキスト抽出精度テスト"""
        md_path = os.path.join(temp_dir, "test.md")

        markdown_content = """# テストドキュメント

これはMarkdownのテストです。

## セクション1

- リスト項目1
- リスト項目2

**太字テキスト**と*斜体テキスト*があります。
"""

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        result = processor.extract_text_file(md_path)

        assert result.success is True
        assert "テストドキュメント" in result.text
        assert "リスト項目1" in result.text
        assert result.metadata['file_type'] == 'markdown'

    def test_extract_text_file_accuracy(self, processor, temp_dir):
        """テキストファイル抽出精度テスト"""
        txt_path = os.path.join(temp_dir, "test.txt")

        text_content = "これはテキストファイルのテストです。\n日本語の文字も含まれています。"

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text_content)

        result = processor.extract_text_file(txt_path)

        assert result.success is True
        assert "テキストファイルのテスト" in result.text
        assert "日本語の文字" in result.text
        assert result.metadata['file_type'] == 'text'

    def test_process_document_comprehensive(self, processor, temp_dir):
        """包括的ドキュメント処理テスト"""
        # 複数のファイルタイプをテスト
        files_to_test = [
            ("test.txt", "これはテキストファイルです。"),
            ("test.md", "# Markdownファイル\n\nこれはMarkdownです。"),
        ]

        for filename, content in files_to_test:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            result = processor.process_document(file_path)

            assert result.success is True
            assert len(result.text) > 0
            assert 'file_type' in result.metadata
            assert 'word_count' in result.metadata
            assert result.metadata['word_count'] > 0

    def test_large_file_processing_performance(self, processor, temp_dir):
        """大規模ファイル処理パフォーマンステスト"""
        import time

        # 大きなテキストファイルを作成
        large_txt_path = os.path.join(temp_dir, "large_test.txt")
        large_content = "これは大きなファイルのテストです。" * 10000  # 約300KB

        with open(large_txt_path, 'w', encoding='utf-8') as f:
            f.write(large_content)

        start_time = time.time()
        result = processor.process_document(large_txt_path)
        end_time = time.time()

        # 処理時間が5秒以内であることを確認
        assert (end_time - start_time) < 5.0
        assert result.success is True
        assert len(result.text) > 0

    def test_batch_document_processing(self, processor, temp_dir):
        """バッチドキュメント処理テスト"""
        import time

        # 複数のファイルを作成
        file_paths = []
        for i in range(10):
            file_path = os.path.join(temp_dir, f"batch_test_{i}.txt")
            content = f"これは{i}番目のバッチテストファイルです。"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            file_paths.append(file_path)

        start_time = time.time()
        results = []
        for file_path in file_paths:
            result = processor.process_document(file_path)
            results.append(result)
        end_time = time.time()

        # バッチ処理が10秒以内に完了することを確認
        assert (end_time - start_time) < 10.0
        assert len(results) == 10
        assert all(result.success for result in results)

    def test_encoding_detection_accuracy(self, processor, temp_dir):
        """文字エンコーディング検出精度テスト"""
        # 異なるエンコーディングのファイルを作成
        encodings_to_test = ['utf-8', 'shift_jis', 'euc-jp']

        for encoding in encodings_to_test:
            try:
                file_path = os.path.join(temp_dir, f"test_{encoding}.txt")
                content = "これは日本語のテストファイルです。"

                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(content)

                result = processor.extract_text_file(file_path)

                assert result.success is True
                assert "日本語のテストファイル" in result.text

            except (UnicodeEncodeError, LookupError):
                # エンコーディングがサポートされていない場合はスキップ
                continue

    def test_error_handling_corrupted_files(self, processor, temp_dir):
        """破損ファイルのエラーハンドリングテスト"""
        # 破損したファイルを作成
        corrupted_path = os.path.join(temp_dir, "corrupted.pdf")
        with open(corrupted_path, 'wb') as f:
            f.write(b"Invalid PDF data")  # 無効なPDFデータ

        result = processor.extract_pdf_text(corrupted_path)

        # エラーが適切にハンドリングされることを確認
        assert result.success is False or result.text == ""

    def test_error_handling_nonexistent_files(self, processor):
        """存在しないファイルのエラーハンドリングテスト"""
        nonexistent_path = "/nonexistent/file.txt"

        with pytest.raises(DocumentProcessingError):
            processor.process_document(nonexistent_path)

    def test_error_handling_permission_denied(self, processor, temp_dir):
        """アクセス権限エラーのハンドリングテスト"""
        restricted_path = os.path.join(temp_dir, "restricted.txt")

        # ファイルを作成
        with open(restricted_path, 'w') as f:
            f.write("制限されたファイル")

        # 読み取り権限を削除
        os.chmod(restricted_path, 0o000)

        try:
            with pytest.raises(DocumentProcessingError):
                processor.process_document(restricted_path)
        finally:
            # テスト後に権限を復元
            os.chmod(restricted_path, 0o644)

    def test_metadata_extraction_accuracy(self, processor, temp_dir):
        """メタデータ抽出精度テスト"""
        txt_path = os.path.join(temp_dir, "metadata_test.txt")
        content = "これはメタデータテスト用のファイルです。\n複数行のテキストが含まれています。"

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)

        result = processor.process_document(txt_path)

        assert result.success is True
        assert 'file_size' in result.metadata
        assert 'word_count' in result.metadata
        assert 'line_count' in result.metadata
        assert 'character_count' in result.metadata

        # メタデータの値が妥当であることを確認
        assert result.metadata['word_count'] > 0
        assert result.metadata['line_count'] >= 2
        assert result.metadata['character_count'] > 0

    def test_memory_usage_during_processing(self, processor, temp_dir):
        """処理中のメモリ使用量テスト"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 複数のファイルを処理
        for i in range(20):
            file_path = os.path.join(temp_dir, f"memory_test_{i}.txt")
            content = f"メモリテスト用ファイル{i}です。" * 1000  # 約30KB

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            result = processor.process_document(file_path)
            assert result.success is True

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # メモリ増加量が合理的な範囲内であることを確認（50MB以下）
        assert memory_increase < 50 * 1024 * 1024

    def test_concurrent_document_processing(self, processor, temp_dir):
        """並行ドキュメント処理テスト"""
        import time
        from concurrent.futures import ThreadPoolExecutor

        # 複数のファイルを作成
        file_paths = []
        for i in range(10):
            file_path = os.path.join(temp_dir, f"concurrent_test_{i}.txt")
            content = f"並行処理テスト用ファイル{i}です。"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            file_paths.append(file_path)

        def process_file(file_path):
            return processor.process_document(file_path)

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_file, path) for path in file_paths]
            results = [future.result() for future in futures]

        end_time = time.time()

        # 並行処理でも15秒以内に完了することを確認
        assert (end_time - start_time) < 15.0
        assert len(results) == 10
        assert all(result.success for result in results)

    def test_file_type_detection_accuracy(self, processor, temp_dir):
        """ファイルタイプ検出精度テスト"""
        test_files = [
            ("test.txt", "テキストファイル", FileType.TEXT),
            ("test.md", "# Markdownファイル", FileType.MARKDOWN),
        ]

        for filename, content, expected_type in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            result = processor.process_document(file_path)

            assert result.success is True
            assert result.metadata['file_type'] == expected_type.value

    def test_text_cleaning_and_normalization(self, processor, temp_dir):
        """テキストクリーニング・正規化テスト"""
        txt_path = os.path.join(temp_dir, "cleaning_test.txt")

        # 特殊文字や空白を含むテキスト
        content = """  これは　　テスト用の　　　ファイルです。


        複数の空行があります。


        タブ文字\t\tも含まれています。
        """

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)

        result = processor.process_document(txt_path)

        assert result.success is True
        # 余分な空白や空行が適切に処理されていることを確認
        assert result.text.strip() != ""
        assert "テスト用のファイル" in result.text

    def test_processing_result_consistency(self, processor, temp_dir):
        """処理結果の一貫性テスト"""
        txt_path = os.path.join(temp_dir, "consistency_test.txt")
        content = "一貫性テスト用のファイルです。"

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 同じファイルを複数回処理
        results = []
        for _ in range(5):
            result = processor.process_document(txt_path)
            results.append(result)

        # 全ての結果が同じであることを確認
        assert all(result.success for result in results)
        assert all(result.text == results[0].text for result in results)
        assert all(result.metadata['word_count'] == results[0].metadata['word_count'] for result in results)
