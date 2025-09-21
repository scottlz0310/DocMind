"""
DocumentProcessorのテストモジュール

ドキュメント処理機能の包括的なテストを提供します。
Phase7強化版の内容を統合済み。
"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.document_processor import DocumentProcessor
from src.data.models import Document, FileType
from src.utils.exceptions import DocumentProcessingError


class TestDocumentProcessor:
    """DocumentProcessorのテストクラス"""

    @pytest.fixture
    def processor(self):
        """DocumentProcessorインスタンスを作成"""
        return DocumentProcessor()

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def sample_text_file(self, temp_dir):
        """サンプルテキストファイルを作成"""
        file_path = os.path.join(temp_dir, "sample.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                "これはテスト用のテキストファイルです。\n検索機能のテストに使用します。"
            )
        return file_path

    @pytest.fixture
    def sample_markdown_file(self, temp_dir):
        """サンプルMarkdownファイルを作成"""
        file_path = os.path.join(temp_dir, "sample.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                "# テストドキュメント\n\n## 概要\n\nこれはテスト用のMarkdownファイルです。"
            )
        return file_path

    def test_initialization(self, processor):
        """初期化テスト"""
        assert processor is not None
        assert hasattr(processor, "logger")

    def test_process_text_file(self, processor, sample_text_file):
        """テキストファイル処理テスト"""
        document = processor.process_file(sample_text_file)

        assert isinstance(document, Document)
        assert document.file_path == sample_text_file
        assert document.file_type == FileType.TEXT
        assert "テスト用のテキストファイル" in document.content
        assert len(document.content) > 0

    def test_process_markdown_file(self, processor, sample_markdown_file):
        """Markdownファイル処理テスト"""
        document = processor.process_file(sample_markdown_file)

        assert isinstance(document, Document)
        assert document.file_type == FileType.MARKDOWN
        assert "テストドキュメント" in document.content

    def test_process_nonexistent_file(self, processor):
        """存在しないファイルの処理テスト"""
        with pytest.raises(DocumentProcessingError):
            processor.process_file("/nonexistent/file.txt")

    def test_extract_text_file(self, processor, sample_text_file):
        """テキストファイル抽出テスト"""
        content = processor.extract_text_file(sample_text_file)

        assert isinstance(content, str)
        assert "テスト用のテキストファイル" in content

    def test_extract_markdown_text(self, processor, sample_markdown_file):
        """Markdownテキスト抽出テスト"""
        content = processor.extract_markdown_text(sample_markdown_file)

        assert isinstance(content, str)
        assert len(content) > 0

    @patch("src.core.document_processor.fitz")
    def test_extract_pdf_text_no_library(self, mock_fitz, processor, temp_dir):
        """PDFライブラリ未インストール時のテスト"""
        pdf_path = os.path.join(temp_dir, "test.pdf")
        Path(pdf_path).touch()

        # 空のPDFファイルの場合、空文字列が返されることを確認
        result = processor.extract_pdf_text(pdf_path)
        assert result == ""

    def test_get_supported_extensions(self, processor):
        """サポート拡張子取得テスト"""
        extensions = processor.get_supported_extensions()

        assert isinstance(extensions, dict)
        assert ".txt" in extensions
        assert ".md" in extensions
        assert extensions[".txt"] == FileType.TEXT

    def test_is_supported_file(self, processor):
        """ファイルサポート判定テスト"""
        assert processor.is_supported_file("test.txt") is True
        assert processor.is_supported_file("test.md") is True
        assert processor.is_supported_file("test.unknown") is False

    def test_get_file_info(self, processor, sample_text_file):
        """ファイル情報取得テスト"""
        info = processor.get_file_info(sample_text_file)

        assert isinstance(info, dict)
        assert "name" in info
        assert "size" in info
        assert info["file_type"] == FileType.TEXT

    def test_encoding_detection(self, processor, temp_dir):
        """エンコーディング検出テスト"""
        # UTF-8ファイル
        utf8_file = os.path.join(temp_dir, "utf8.txt")
        with open(utf8_file, "w", encoding="utf-8") as f:
            f.write("UTF-8テストファイル")

        encoding = processor._detect_encoding(utf8_file)
        assert encoding in ["utf-8", "UTF-8"]

    def test_process_markdown_content(self, processor):
        """Markdownコンテンツ処理テスト"""
        markdown_content = """
# 見出し1
## 見出し2
- リスト項目1
- リスト項目2
**太字テキスト**
`インラインコード`
        """

        processed = processor._process_markdown_content(markdown_content)

        assert "見出し: 見出し1" in processed
        assert "リスト項目: リスト項目1" in processed
        assert "太字テキスト" in processed

    def test_empty_file_handling(self, processor, temp_dir):
        """空ファイル処理テスト"""
        empty_file = os.path.join(temp_dir, "empty.txt")
        Path(empty_file).touch()

        content = processor.extract_text_file(empty_file)
        assert content == ""

    def test_large_file_handling(self, processor, temp_dir):
        """大きなファイル処理テスト"""
        large_file = os.path.join(temp_dir, "large.txt")
        large_content = "テストデータ" * 10000

        with open(large_file, "w", encoding="utf-8") as f:
            f.write(large_content)

        document = processor.process_file(large_file)
        assert len(document.content) > 50000

    def test_error_handling_corrupted_file(self, processor, temp_dir):
        """破損ファイルのエラーハンドリングテスト"""
        corrupted_file = os.path.join(temp_dir, "corrupted.txt")

        # バイナリデータを書き込んで破損ファイルをシミュレート
        with open(corrupted_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04\x05")

        # エラーが発生しても適切に処理されることを確認
        try:
            document = processor.process_file(corrupted_file)
            # 処理が成功した場合、空でないコンテンツが返されることを確認
            assert isinstance(document.content, str)
        except DocumentProcessingError:
            # エラーが発生した場合、適切な例外が投げられることを確認
            pass

    def test_dependency_check(self, processor):
        """依存関係チェックテスト"""
        # _check_dependencies メソッドが正常に実行されることを確認
        processor._check_dependencies()
        # エラーが発生しないことを確認（ログ出力のみ）
        assert True

    # Phase7統合: PDF処理精度テスト
    def test_extract_pdf_text_accuracy(self, processor, temp_dir):
        """PDF テキスト抽出精度テスト"""
        pdf_path = os.path.join(temp_dir, "test.pdf")
        Path(pdf_path).touch()

        with patch("src.core.document_processor.fitz") as mock_fitz:
            mock_doc = Mock()
            mock_page = Mock()
            mock_page.get_text.return_value = "これはPDFのテストテキストです。"

            mock_doc.__len__ = Mock(return_value=1)
            mock_doc.__getitem__ = Mock(return_value=mock_page)
            mock_doc.__iter__ = Mock(return_value=iter([mock_page]))
            mock_doc.close = Mock()
            mock_doc.__enter__ = Mock(return_value=mock_doc)
            mock_doc.__exit__ = Mock(return_value=None)

            mock_fitz.open.return_value = mock_doc

            result = processor.extract_pdf_text(pdf_path)

            assert result == "これはPDFのテストテキストです。"
            mock_fitz.open.assert_called_once_with(pdf_path)

    # Phase7統合: Word処理精度テスト
    def test_extract_word_text_accuracy(self, processor, temp_dir):
        """Word文書テキスト抽出精度テスト"""
        docx_path = os.path.join(temp_dir, "test.docx")
        Path(docx_path).touch()

        with patch("src.core.document_processor.DocxDocument") as mock_docx_document:
            mock_doc = Mock()
            mock_paragraph = Mock()
            mock_paragraph.text = "これはWordドキュメントのテストテキストです。"
            mock_doc.paragraphs = [mock_paragraph]
            mock_doc.tables = []
            mock_docx_document.return_value = mock_doc

            result = processor.extract_word_text(docx_path)

            assert result == "これはWordドキュメントのテストテキストです。"
            mock_docx_document.assert_called_once_with(docx_path)

    # Phase7統合: Excel処理精度テスト
    def test_extract_excel_data_accuracy(self, processor, temp_dir):
        """Excel データ抽出精度テスト"""
        xlsx_path = os.path.join(temp_dir, "test.xlsx")
        Path(xlsx_path).touch()

        with patch("src.core.document_processor.load_workbook") as mock_load_workbook:
            mock_workbook = Mock()
            mock_worksheet = Mock()
            mock_worksheet.title = "Sheet1"

            mock_workbook.sheetnames = ["Sheet1"]
            mock_workbook.__getitem__ = Mock(return_value=mock_worksheet)
            mock_worksheet.iter_rows.return_value = [
                ("ヘッダー1", "ヘッダー2"),
                ("データ1", "データ2"),
            ]
            mock_workbook.close = Mock()
            mock_load_workbook.return_value = mock_workbook

            result = processor.extract_excel_text(xlsx_path)

            assert "ヘッダー1" in result
            assert "データ1" in result
            mock_load_workbook.assert_called_once_with(
                xlsx_path, read_only=True, data_only=True
            )

    # Phase7統合: パフォーマンステスト
    def test_large_file_processing_performance(self, processor, temp_dir):
        """大規模ファイル処理パフォーマンステスト"""
        large_txt_path = os.path.join(temp_dir, "large_test.txt")
        large_content = "これは大きなファイルのテストです。" * 10000

        with open(large_txt_path, "w", encoding="utf-8") as f:
            f.write(large_content)

        start_time = time.time()
        result = processor.process_file(large_txt_path)
        end_time = time.time()

        assert (end_time - start_time) < 5.0
        assert result is not None
        assert len(result.content) > 0

    # Phase7統合: バッチ処理テスト
    def test_batch_document_processing(self, processor, temp_dir):
        """バッチドキュメント処理テスト"""
        file_paths = []
        for i in range(10):
            file_path = os.path.join(temp_dir, f"batch_test_{i}.txt")
            content = f"これは{i}番目のバッチテストファイルです。"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            file_paths.append(file_path)

        start_time = time.time()
        results = []
        for file_path in file_paths:
            result = processor.process_file(file_path)
            results.append(result)
        end_time = time.time()

        assert (end_time - start_time) < 10.0
        assert len(results) == 10
        assert all(result is not None for result in results)

    # Phase7統合: メモリ使用量テスト
    def test_memory_usage_during_processing(self, processor, temp_dir):
        """処理中のメモリ使用量テスト"""
        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        for i in range(20):
            file_path = os.path.join(temp_dir, f"memory_test_{i}.txt")
            content = f"メモリテスト用ファイル{i}です。" * 1000

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            result = processor.process_file(file_path)
            assert result is not None

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        assert memory_increase < 50 * 1024 * 1024

    # Phase7統合: 並行処理テスト
    def test_concurrent_document_processing(self, processor, temp_dir):
        """並行ドキュメント処理テスト"""
        from concurrent.futures import ThreadPoolExecutor

        file_paths = []
        for i in range(10):
            file_path = os.path.join(temp_dir, f"concurrent_test_{i}.txt")
            content = f"並行処理テスト用ファイル{i}です。"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            file_paths.append(file_path)

        def process_file_wrapper(file_path):
            return processor.process_file(file_path)

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(process_file_wrapper, path) for path in file_paths
            ]
            results = [future.result() for future in futures]

        end_time = time.time()

        assert (end_time - start_time) < 15.0
        assert len(results) == 10
        assert all(result is not None for result in results)
