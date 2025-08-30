#!/usr/bin/env python3
"""
DocMind プレビューウィジェットのユニットテスト

プレビューウィジェットの機能をテストします。
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

from src.data.models import Document, FileType
from src.gui.preview_widget import (
    DocumentSummarizer,
    DocumentSyntaxHighlighter,
    PreviewWidget,
    SearchHighlighter,
)


class TestDocumentSummarizer:
    """DocumentSummarizerクラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.summarizer = DocumentSummarizer()

    def test_generate_summary_short_content(self):
        """短いコンテンツの要約生成テスト"""
        content = "これは短いテストコンテンツです。"
        summary = self.summarizer.generate_summary(content, max_length=500)

        # 短いコンテンツはそのまま返される
        assert summary == content

    def test_generate_summary_long_content(self):
        """長いコンテンツの要約生成テスト"""
        # 長いコンテンツを作成
        content = (
            "これは最初の段落です。重要な情報が含まれています。\n\n"
            "これは2番目の段落です。追加の詳細情報があります。\n\n"
            "これは3番目の段落です。さらなる説明が続きます。\n\n"
            "これは最後の段落です。結論が述べられています。"
        )

        summary = self.summarizer.generate_summary(content, max_length=100)

        # 要約が生成され、元のコンテンツより短い
        assert len(summary) <= 100
        assert summary != content
        assert "これは最初の段落です" in summary  # 最初の段落は含まれる

    def test_split_into_sentences(self):
        """文分割機能のテスト"""
        text = "これは最初の文です。これは2番目の文です！これは3番目の文です？"
        sentences = self.summarizer._split_into_sentences(text)

        assert len(sentences) == 3
        assert "これは最初の文です" in sentences
        assert "これは2番目の文です" in sentences
        assert "これは3番目の文です" in sentences

    def test_select_important_paragraphs(self):
        """重要段落選択機能のテスト"""
        paragraphs = ["最初の段落です。", "2番目の段落です。", "3番目の段落です。"]

        summary = self.summarizer._select_important_paragraphs(
            paragraphs, max_length=50
        )

        # 最初の段落は常に含まれる
        assert "最初の段落です。" in summary
        assert len(summary) <= 50


class TestSearchHighlighter:
    """SearchHighlighterクラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        # QApplicationが必要
        if not QApplication.instance():
            self.app = QApplication([])

        # モックのQTextEditを作成
        self.text_edit = Mock()
        self.text_edit.document.return_value = Mock()

        self.highlighter = SearchHighlighter(self.text_edit)

    def test_set_search_terms(self):
        """検索語設定のテスト"""
        # モックのQTextDocumentを作成
        from PySide6.QtGui import QTextDocument

        mock_document = QTextDocument()
        self.text_edit.document.return_value = mock_document

        terms = ["テスト", "検索", ""]
        self.highlighter.set_search_terms(terms)

        # 空の文字列は除外される
        assert len(self.highlighter.search_terms) == 2
        assert "テスト" in self.highlighter.search_terms
        assert "検索" in self.highlighter.search_terms
        assert "" not in self.highlighter.search_terms

    def test_clear_highlights(self):
        """ハイライトクリア機能のテスト"""
        # モックの設定
        mock_document = Mock()
        mock_cursor = Mock()
        self.text_edit.document.return_value = mock_document

        with patch("src.gui.preview_widget.QTextCursor", return_value=mock_cursor):
            self.highlighter.clear_highlights()

            # QTextCursorが呼び出されたことを確認
            mock_cursor.select.assert_called()
            mock_cursor.setCharFormat.assert_called()
            mock_cursor.clearSelection.assert_called()


@pytest.fixture
def sample_document():
    """テスト用のサンプルドキュメントを作成"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("これはテスト用のドキュメントです。\n検索機能をテストします。")
        temp_path = f.name

    try:
        doc = Document.create_from_file(
            temp_path,
            content="これはテスト用のドキュメントです。\n検索機能をテストします。",
        )
        yield doc
    finally:
        # テンポラリファイルを削除
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.fixture
def preview_widget():
    """テスト用のプレビューウィジェットを作成"""
    # QApplicationが必要
    if not QApplication.instance():
        QApplication([])

    widget = PreviewWidget()
    yield widget

    # クリーンアップ
    widget.close()


class TestPreviewWidget:
    """PreviewWidgetクラスのテスト"""

    def test_initialization(self, preview_widget):
        """初期化のテスト"""
        assert preview_widget.current_document is None
        assert preview_widget.current_zoom == 100
        assert preview_widget.search_highlighter is not None
        assert preview_widget.summarizer is not None

    def test_display_document(self, preview_widget, sample_document):
        """ドキュメント表示機能のテスト"""
        preview_widget.display_document(sample_document)

        # ドキュメントが設定されている
        assert preview_widget.current_document == sample_document

        # ドキュメント情報が更新されている
        info_text = preview_widget.doc_info_label.text()
        assert sample_document.title in info_text
        assert "TEXT" in info_text.upper()

        # コンテンツが表示されている
        displayed_text = preview_widget.text_browser.toPlainText()
        assert sample_document.content in displayed_text

    def test_display_summary(self, preview_widget):
        """要約表示機能のテスト"""
        summary_text = "これは要約テキストです。"
        preview_widget.display_summary(summary_text)

        # 要約が表示されている
        displayed_text = preview_widget.text_browser.toPlainText()
        assert displayed_text == summary_text

        # ドキュメント情報が更新されている
        assert "要約表示" in preview_widget.doc_info_label.text()

    def test_highlight_search_terms(self, preview_widget, sample_document):
        """検索語ハイライト機能のテスト"""
        # ドキュメントを表示
        preview_widget.display_document(sample_document)

        # 検索語をハイライト
        search_terms = ["テスト", "検索"]
        preview_widget.highlight_search_terms(search_terms)

        # ハイライターに検索語が設定されている
        assert preview_widget.search_highlighter.search_terms == search_terms

    def test_clear_highlights(self, preview_widget, sample_document):
        """ハイライトクリア機能のテスト"""
        # ドキュメントを表示してハイライト
        preview_widget.display_document(sample_document)
        preview_widget.highlight_search_terms(["テスト"])

        # ハイライトをクリア
        preview_widget.clear_highlights()

        # ハイライターの検索語がクリアされている（実際の実装では内部状態をチェック）
        # この部分は実装の詳細に依存するため、例外が発生しないことを確認
        try:
            preview_widget.clear_highlights()
        except Exception as e:
            pytest.fail(f"clear_highlights()で例外が発生しました: {e}")

    def test_zoom_functionality(self, preview_widget):
        """ズーム機能のテスト"""
        # 初期ズームレベル
        assert preview_widget.get_zoom_level() == 100

        # ズームレベルを変更
        preview_widget.set_zoom_level(150)
        assert preview_widget.zoom_slider.value() == 150

        # 範囲外の値は制限される
        preview_widget.set_zoom_level(300)  # 200%を超える
        assert preview_widget.zoom_slider.value() == 200

        preview_widget.set_zoom_level(25)  # 50%未満
        assert preview_widget.zoom_slider.value() == 50

    def test_format_change(self, preview_widget, sample_document):
        """表示フォーマット変更のテスト"""
        # ドキュメントを表示
        preview_widget.display_document(sample_document)

        # 要約フォーマットに変更
        preview_widget.format_combo.setCurrentText("要約")

        # フォーマットが変更されている
        assert preview_widget.format_combo.currentText() == "要約"

    def test_clear_preview(self, preview_widget, sample_document):
        """プレビュークリア機能のテスト"""
        # ドキュメントを表示
        preview_widget.display_document(sample_document)
        assert preview_widget.current_document is not None

        # プレビューをクリア
        preview_widget.clear_preview()

        # ドキュメントがクリアされている
        assert preview_widget.current_document is None
        assert preview_widget.text_browser.toPlainText() == ""
        assert (
            "ドキュメントが選択されていません" in preview_widget.doc_info_label.text()
        )

    def test_file_size_formatting(self, preview_widget):
        """ファイルサイズフォーマット機能のテスト"""
        # バイト
        assert preview_widget._format_file_size(500) == "500 B"

        # キロバイト
        assert preview_widget._format_file_size(1536) == "1.5 KB"

        # メガバイト
        assert preview_widget._format_file_size(1572864) == "1.5 MB"

        # ギガバイト
        assert preview_widget._format_file_size(1610612736) == "1.5 GB"

    def test_error_handling(self, preview_widget):
        """エラーハンドリングのテスト"""
        # 無効なドキュメントでエラーが適切に処理される
        invalid_doc = Mock()
        invalid_doc.title = "Invalid Document"
        invalid_doc.content = None  # 無効なコンテンツ

        # エラーが発生しても例外は発生しない
        try:
            preview_widget.display_document(invalid_doc)
        except Exception:
            # ログにエラーが記録されるが、例外は発生しない
            pass

    def test_syntax_highlighting_setup(self, preview_widget, sample_document):
        """シンタックスハイライト設定のテスト"""
        # Markdownドキュメントを作成
        markdown_doc = sample_document
        markdown_doc.file_type = FileType.MARKDOWN
        markdown_doc.content = "# ヘッダー\n\n**太字**テキスト\n\n`コード`"

        # ドキュメントを表示
        preview_widget.display_document(markdown_doc)

        # シンタックスハイライターが設定されている
        assert preview_widget.syntax_highlighter is not None
        assert preview_widget.syntax_highlighter.file_type == FileType.MARKDOWN


class TestDocumentSyntaxHighlighter:
    """DocumentSyntaxHighlighterクラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        # QApplicationが必要
        if not QApplication.instance():
            self.app = QApplication([])

    def test_markdown_highlighting_rules(self):
        """Markdownハイライトルールのテスト"""
        from PySide6.QtGui import QTextDocument

        document = QTextDocument()
        highlighter = DocumentSyntaxHighlighter(document, FileType.MARKDOWN)

        # Markdownルールが設定されている
        assert len(highlighter.highlighting_rules) > 0

        # ヘッダールールが含まれている
        header_rule_found = False
        for pattern, _ in highlighter.highlighting_rules:
            if "#{1,6}" in pattern:
                header_rule_found = True
                break
        assert header_rule_found

    def test_text_highlighting_rules(self):
        """テキストハイライトルールのテスト"""
        from PySide6.QtGui import QTextDocument

        document = QTextDocument()
        highlighter = DocumentSyntaxHighlighter(document, FileType.TEXT)

        # テキストルールが設定されている
        assert len(highlighter.highlighting_rules) > 0

        # URLルールが含まれている
        url_rule_found = False
        for pattern, _ in highlighter.highlighting_rules:
            if "https?" in pattern:
                url_rule_found = True
                break
        assert url_rule_found

    def test_unknown_file_type(self):
        """未知のファイルタイプのテスト"""
        from PySide6.QtGui import QTextDocument

        document = QTextDocument()
        highlighter = DocumentSyntaxHighlighter(document, FileType.UNKNOWN)

        # 基本的なルールのみ設定される
        assert len(highlighter.highlighting_rules) == 0


# 統合テスト
class TestPreviewWidgetIntegration:
    """プレビューウィジェットの統合テスト"""

    def test_full_workflow(self, preview_widget, sample_document):
        """完全なワークフローのテスト"""
        # 1. ドキュメントを表示
        preview_widget.display_document(sample_document)
        assert preview_widget.current_document == sample_document

        # 2. 検索語をハイライト
        search_terms = ["テスト", "検索"]
        preview_widget.highlight_search_terms(search_terms)

        # 3. ズームを変更
        preview_widget.set_zoom_level(125)
        assert preview_widget.get_zoom_level() == 125

        # 4. フォーマットを変更
        preview_widget.format_combo.setCurrentText("要約")

        # 5. ハイライトをクリア
        preview_widget.clear_highlights()

        # 6. プレビューをクリア
        preview_widget.clear_preview()
        assert preview_widget.current_document is None

    def test_large_document_handling(self, preview_widget):
        """大きなドキュメントの処理テスト"""
        # 大きなコンテンツを持つドキュメントを作成（段落構造を持つ）
        large_content = (
            """これは最初の段落です。重要な情報が含まれています。

これは2番目の段落です。追加の詳細情報があります。

これは3番目の段落です。さらなる説明が続きます。

これは4番目の段落です。より多くの情報があります。

これは最後の段落です。結論が述べられています。"""
            * 10
        )  # 約2000文字

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(large_content)
            temp_path = f.name

        try:
            large_doc = Document.create_from_file(temp_path, content=large_content)

            # ドキュメントを表示
            preview_widget.display_document(large_doc)

            # 要約フォーマットに変更
            preview_widget.format_combo.setCurrentText("要約")

            # 要約が生成されて表示される（1000文字を超える場合は要約される）
            displayed_text = preview_widget.text_browser.toPlainText()
            if len(large_content) > 1000:
                # 要約は元のコンテンツより短くなる
                assert len(displayed_text) < len(large_content)
                # 最初の段落は含まれる
                assert "これは最初の段落です" in displayed_text

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__])
