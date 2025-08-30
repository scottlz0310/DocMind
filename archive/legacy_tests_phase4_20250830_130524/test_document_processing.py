"""
DocumentProcessorクラスのユニットテスト

このモジュールは、DocumentProcessorクラスの各メソッドをテストし、
様々なファイル形式の処理が正しく動作することを確認します。
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# テスト対象のモジュール
from src.core.document_processor import DocumentProcessor
from src.data.models import Document, FileType
from src.utils.exceptions import DocumentProcessingError


class TestDocumentProcessor:
    """DocumentProcessorクラスのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.processor = DocumentProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        # 一時ファイルをクリーンアップ
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_temp_file(self, filename: str, content: str = "テストコンテンツ") -> str:
        """テスト用の一時ファイルを作成

        Args:
            filename (str): ファイル名
            content (str): ファイルの内容

        Returns:
            str: 作成されたファイルのパス
        """
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_init(self):
        """DocumentProcessorの初期化テスト"""
        processor = DocumentProcessor()
        assert processor is not None
        assert hasattr(processor, "logger")

    def test_process_file_not_exists(self):
        """存在しないファイルの処理テスト"""
        non_existent_file = "/path/to/non/existent/file.txt"

        with pytest.raises(DocumentProcessingError) as exc_info:
            self.processor.process_file(non_existent_file)

        assert "ファイルが存在しません" in str(exc_info.value)
        assert exc_info.value.file_path == non_existent_file

    def test_extract_text_file_utf8(self):
        """UTF-8テキストファイルの処理テスト"""
        content = "これはテストファイルです。\n日本語のテキストが含まれています。"
        file_path = self.create_temp_file("test.txt", content)

        result = self.processor.extract_text_file(file_path)

        assert result == content

    def test_extract_text_file_empty(self):
        """空のテキストファイルの処理テスト"""
        file_path = self.create_temp_file("empty.txt", "")

        result = self.processor.extract_text_file(file_path)

        assert result == ""

    def test_extract_markdown_text_basic(self):
        """基本的なMarkdownファイルの処理テスト"""
        markdown_content = """# メインタイトル

これは段落です。

## サブタイトル

- リスト項目1
- リスト項目2

1. 番号付きリスト1
2. 番号付きリスト2

**太字のテキスト**と*斜体のテキスト*があります。

`インラインコード`も含まれています。

[リンクテキスト](https://example.com)
"""

        file_path = self.create_temp_file("test.md", markdown_content)

        result = self.processor.extract_markdown_text(file_path)

        # 見出しが正しく処理されているかチェック
        assert "見出し: メインタイトル" in result
        assert "見出し: サブタイトル" in result

        # リストが正しく処理されているかチェック
        assert "リスト項目: リスト項目1" in result
        assert "番号付きリスト: 番号付きリスト1" in result

        # Markdown記法が除去されているかチェック
        assert "太字のテキスト" in result
        assert "**" not in result
        assert "リンクテキスト" in result
        assert "https://example.com" not in result

    @patch("src.core.document_processor.fitz")
    def test_extract_pdf_text_success(self, mock_fitz):
        """PDF処理成功のテスト"""
        # モックの設定
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "PDFページのテキスト"
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None
        mock_fitz.open.return_value = mock_doc

        file_path = self.create_temp_file("test.pdf", "dummy")

        result = self.processor.extract_pdf_text(file_path)

        assert result == "PDFページのテキスト"
        mock_fitz.open.assert_called_once_with(file_path)

    @patch("src.core.document_processor.fitz", None)
    def test_extract_pdf_text_no_dependency(self):
        """PyMuPDFが利用できない場合のテスト"""
        file_path = self.create_temp_file("test.pdf", "dummy")

        with pytest.raises(DocumentProcessingError) as exc_info:
            self.processor.extract_pdf_text(file_path)

        assert "PyMuPDFがインストールされていません" in str(exc_info.value)

    @patch("src.core.document_processor.DocxDocument")
    def test_extract_word_text_success(self, mock_docx_class):
        """Word文書処理成功のテスト"""
        # モックの設定
        mock_doc = MagicMock()

        # 段落のモック
        mock_paragraph1 = MagicMock()
        mock_paragraph1.text = "最初の段落"
        mock_paragraph2 = MagicMock()
        mock_paragraph2.text = "二番目の段落"
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]

        # テーブルのモック
        mock_cell1 = MagicMock()
        mock_cell1.text = "セル1"
        mock_cell2 = MagicMock()
        mock_cell2.text = "セル2"
        mock_row = MagicMock()
        mock_row.cells = [mock_cell1, mock_cell2]
        mock_table = MagicMock()
        mock_table.rows = [mock_row]
        mock_doc.tables = [mock_table]

        mock_docx_class.return_value = mock_doc

        file_path = self.create_temp_file("test.docx", "dummy")

        result = self.processor.extract_word_text(file_path)

        assert "最初の段落" in result
        assert "二番目の段落" in result
        assert "セル1 | セル2" in result

    @patch("src.core.document_processor.DocxDocument", None)
    def test_extract_word_text_no_dependency(self):
        """python-docxが利用できない場合のテスト"""
        file_path = self.create_temp_file("test.docx", "dummy")

        with pytest.raises(DocumentProcessingError) as exc_info:
            self.processor.extract_word_text(file_path)

        assert "python-docxがインストールされていません" in str(exc_info.value)

    @patch("src.core.document_processor.load_workbook")
    def test_extract_excel_text_success(self, mock_load_workbook):
        """Excel処理成功のテスト"""
        # モックの設定
        mock_workbook = MagicMock()
        mock_workbook.sheetnames = ["Sheet1", "Sheet2"]

        # Sheet1のモック
        mock_sheet1 = MagicMock()
        mock_sheet1.iter_rows.return_value = [
            ("ヘッダー1", "ヘッダー2"),
            ("データ1", "データ2"),
            (None, "データ3"),
        ]

        # Sheet2のモック
        mock_sheet2 = MagicMock()
        mock_sheet2.iter_rows.return_value = [("別シートデータ",)]

        mock_workbook.__getitem__.side_effect = lambda name: {
            "Sheet1": mock_sheet1,
            "Sheet2": mock_sheet2,
        }[name]

        mock_load_workbook.return_value = mock_workbook

        file_path = self.create_temp_file("test.xlsx", "dummy")

        result = self.processor.extract_excel_text(file_path)

        assert "=== シート: Sheet1 ===" in result
        assert "ヘッダー1 | ヘッダー2" in result
        assert "データ1 | データ2" in result
        assert "データ3" in result
        assert "=== シート: Sheet2 ===" in result
        assert "別シートデータ" in result

    @patch("src.core.document_processor.load_workbook", None)
    def test_extract_excel_text_no_dependency(self):
        """openpyxlが利用できない場合のテスト"""
        file_path = self.create_temp_file("test.xlsx", "dummy")

        with pytest.raises(DocumentProcessingError) as exc_info:
            self.processor.extract_excel_text(file_path)

        assert "openpyxlがインストールされていません" in str(exc_info.value)

    def test_process_file_text_success(self):
        """テキストファイルの完全な処理テスト"""
        content = "これは完全なテストです。\n複数行のコンテンツが含まれています。"
        file_path = self.create_temp_file("complete_test.txt", content)

        document = self.processor.process_file(file_path)

        assert isinstance(document, Document)
        assert document.content == content
        assert document.file_path == str(Path(file_path).absolute())
        assert document.file_type == FileType.TEXT
        assert document.title == "complete_test"
        assert document.size > 0
        assert isinstance(document.created_date, datetime)
        assert isinstance(document.modified_date, datetime)
        assert isinstance(document.indexed_date, datetime)

    def test_get_supported_extensions(self):
        """サポートされている拡張子の取得テスト"""
        extensions = self.processor.get_supported_extensions()

        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".xlsx" in extensions
        assert ".md" in extensions
        assert ".txt" in extensions

        assert extensions[".pdf"] == FileType.PDF
        assert extensions[".docx"] == FileType.WORD
        assert extensions[".xlsx"] == FileType.EXCEL
        assert extensions[".md"] == FileType.MARKDOWN
        assert extensions[".txt"] == FileType.TEXT

    def test_is_supported_file(self):
        """ファイルサポート判定のテスト"""
        assert self.processor.is_supported_file("test.pdf")
        assert self.processor.is_supported_file("test.docx")
        assert self.processor.is_supported_file("test.xlsx")
        assert self.processor.is_supported_file("test.md")
        assert self.processor.is_supported_file("test.txt")
        assert not self.processor.is_supported_file("test.unknown")
        assert not self.processor.is_supported_file("test")

    def test_get_file_info(self):
        """ファイル情報取得のテスト"""
        content = "テストファイル情報"
        file_path = self.create_temp_file("info_test.txt", content)

        info = self.processor.get_file_info(file_path)

        assert info["name"] == "info_test.txt"
        assert info["stem"] == "info_test"
        assert info["suffix"] == ".txt"
        assert info["size"] > 0
        assert info["file_type"] == FileType.TEXT
        assert info["is_supported"]
        assert "created" in info
        assert "modified" in info

    def test_get_file_info_not_exists(self):
        """存在しないファイルの情報取得テスト"""
        info = self.processor.get_file_info("/path/to/non/existent/file.txt")

        assert info == {}

    @patch("src.core.document_processor.chardet.detect")
    def test_detect_encoding(self, mock_detect):
        """エンコーディング検出のテスト"""
        mock_detect.return_value = {"encoding": "shift_jis", "confidence": 0.9}

        file_path = self.create_temp_file("encoding_test.txt", "テスト")

        encoding = self.processor._detect_encoding(file_path)

        assert encoding == "shift_jis"

    @patch("src.core.document_processor.chardet.detect")
    def test_detect_encoding_low_confidence(self, mock_detect):
        """低信頼度エンコーディング検出のテスト"""
        mock_detect.return_value = {"encoding": "shift_jis", "confidence": 0.3}

        file_path = self.create_temp_file("encoding_test.txt", "テスト")

        encoding = self.processor._detect_encoding(file_path)

        assert encoding == "utf-8"  # 低信頼度の場合はUTF-8を使用

    def test_process_markdown_content(self):
        """Markdownコンテンツ処理のテスト"""
        markdown_content = """# タイトル
## サブタイトル
- リスト1
- リスト2
1. 番号1
2. 番号2
**太字**と*斜体*
`コード`
[リンク](http://example.com)
通常のテキスト"""

        result = self.processor._process_markdown_content(markdown_content)

        assert "見出し: タイトル" in result
        assert "見出し: サブタイトル" in result
        assert "リスト項目: リスト1" in result
        assert "番号付きリスト: 番号1" in result
        assert "太字" in result
        assert "**" not in result
        assert "リンク" in result
        assert "http://example.com" not in result
        assert "通常のテキスト" in result


class TestDocumentProcessorIntegration:
    """DocumentProcessorの統合テストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.processor = DocumentProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_process_multiple_file_types(self):
        """複数のファイルタイプの処理統合テスト"""
        # テストファイルを作成
        files = {
            "test.txt": "テキストファイルの内容",
            "test.md": "# Markdownファイル\n\n内容です。",
        }

        processed_docs = []

        for filename, content in files.items():
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            try:
                doc = self.processor.process_file(file_path)
                processed_docs.append(doc)
            except DocumentProcessingError as e:
                pytest.fail(f"ファイル処理に失敗: {filename} - {str(e)}")

        assert len(processed_docs) == 2

        # テキストファイルの確認
        txt_doc = next(doc for doc in processed_docs if doc.file_type == FileType.TEXT)
        assert txt_doc.content == "テキストファイルの内容"

        # Markdownファイルの確認
        md_doc = next(
            doc for doc in processed_docs if doc.file_type == FileType.MARKDOWN
        )
        assert "見出し: Markdownファイル" in md_doc.content
        assert "内容です。" in md_doc.content
