#!/usr/bin/env python3
"""
DocMind ドキュメントプレビューウィジェット

QTextEditを拡張したプレビューウィジェットクラスを実装します。
シンタックスハイライト、検索語ハイライト、ズーム機能、
ドキュメント要約生成機能を提供します。
"""

import logging
import re

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.data.models import Document, FileType


class DocumentSyntaxHighlighter(QSyntaxHighlighter):
    """
    ドキュメント用シンタックスハイライター

    ファイルタイプに応じて適切なシンタックスハイライトを適用します。
    """

    def __init__(self, document: QTextDocument, file_type: FileType):
        """
        ハイライターの初期化

        Args:
            document: ハイライト対象のドキュメント
            file_type: ファイルタイプ
        """
        super().__init__(document)
        self.file_type = file_type
        self._setup_highlighting_rules()

    def _setup_highlighting_rules(self):
        """ハイライトルールを設定"""
        self.highlighting_rules = []

        if self.file_type == FileType.MARKDOWN:
            self._setup_markdown_rules()
        elif self.file_type == FileType.TEXT:
            self._setup_text_rules()
        # 他のファイルタイプは基本的なハイライトのみ

    def _setup_markdown_rules(self):
        """Markdownファイル用のハイライトルールを設定"""
        # ヘッダー
        header_format = QTextCharFormat()
        header_format.setForeground(QColor("#2E86AB"))
        header_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r"^#{1,6}\s.*$", header_format))

        # 太字
        bold_format = QTextCharFormat()
        bold_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r"\*\*.*?\*\*", bold_format))

        # 斜体
        italic_format = QTextCharFormat()
        italic_format.setFontItalic(True)
        self.highlighting_rules.append((r"\*.*?\*", italic_format))

        # コードブロック
        code_format = QTextCharFormat()
        code_format.setForeground(QColor("#A23B72"))
        code_format.setBackground(QColor("#F5F5F5"))
        code_font = QFont("Consolas, Monaco, monospace")
        code_format.setFont(code_font)
        self.highlighting_rules.append((r"`.*?`", code_format))

        # リンク
        link_format = QTextCharFormat()
        link_format.setForeground(QColor("#F18F01"))
        link_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
        self.highlighting_rules.append((r"\[.*?\]\(.*?\)", link_format))

    def _setup_text_rules(self):
        """テキストファイル用の基本ハイライトルールを設定"""
        # URL
        url_format = QTextCharFormat()
        url_format.setForeground(QColor("#0066CC"))
        url_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
        self.highlighting_rules.append((r"https?://[^\s]+", url_format))

        # メールアドレス
        email_format = QTextCharFormat()
        email_format.setForeground(QColor("#0066CC"))
        self.highlighting_rules.append(
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", email_format)
        )

    def highlightBlock(self, text: str):
        """テキストブロックのハイライト処理"""
        for pattern, format_obj in self.highlighting_rules:
            expression = re.compile(pattern, re.MULTILINE)
            for match in expression.finditer(text):
                start = match.start()
                length = match.end() - match.start()
                self.setFormat(start, length, format_obj)


class SearchHighlighter:
    """
    検索語ハイライト機能

    プレビューテキスト内の検索語をハイライト表示します。
    """

    def __init__(self, text_edit: QTextEdit):
        """
        ハイライターの初期化

        Args:
            text_edit: ハイライト対象のテキストエディット
        """
        self.text_edit = text_edit
        self.search_terms = []
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(QColor("#FFFF00"))  # 黄色背景
        self.highlight_format.setForeground(QColor("#000000"))  # 黒文字

    def set_search_terms(self, terms: list[str]):
        """
        ハイライト対象の検索語を設定

        Args:
            terms: ハイライト対象の用語リスト
        """
        self.search_terms = [term.strip() for term in terms if term.strip()]
        self.apply_highlights()

    def apply_highlights(self):
        """ハイライトを適用"""
        if not self.search_terms:
            return

        document = self.text_edit.document()
        cursor = QTextCursor(document)

        # 既存のハイライトをクリア
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())
        cursor.clearSelection()

        # 各検索語をハイライト
        for term in self.search_terms:
            cursor.movePosition(QTextCursor.Start)

            while True:
                cursor = document.find(term, cursor, QTextDocument.FindCaseSensitively)
                if cursor.isNull():
                    break

                cursor.mergeCharFormat(self.highlight_format)

    def clear_highlights(self):
        """すべてのハイライトをクリア"""
        document = self.text_edit.document()
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())
        cursor.clearSelection()


class DocumentSummarizer(QObject):
    """
    ドキュメント要約生成クラス

    大きなファイル用のドキュメント要約を生成します。
    """

    summary_ready = Signal(str)  # 要約完了シグナル

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def generate_summary(self, content: str, max_length: int = 500) -> str:
        """
        コンテンツの要約を生成

        Args:
            content: 要約対象のコンテンツ
            max_length: 最大文字数

        Returns:
            str: 生成された要約
        """
        if len(content) <= max_length:
            return content

        try:
            # 段落に分割
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

            if not paragraphs:
                # 段落がない場合は文で分割
                sentences = self._split_into_sentences(content)
                return self._select_important_sentences(sentences, max_length)

            # 重要な段落を選択
            return self._select_important_paragraphs(paragraphs, max_length)

        except Exception as e:
            self.logger.error(f"要約生成エラー: {e}")
            # フォールバック: 単純な切り取り
            return content[:max_length] + "..."

    def _split_into_sentences(self, text: str) -> list[str]:
        """テキストを文に分割"""
        # 日本語と英語の文区切りに対応
        sentence_endings = r"[。！？.!?]"
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]

    def _select_important_sentences(self, sentences: list[str], max_length: int) -> str:
        """重要な文を選択して要約を作成"""
        if not sentences:
            return ""

        # 文の重要度を計算（長さと位置を考慮）
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            # 位置スコア（最初と最後の文を重視）
            position_score = 1.0 if i == 0 or i == len(sentences) - 1 else 0.5

            # 長さスコア（適度な長さの文を重視）
            length_score = min(len(sentence) / 100, 1.0)

            total_score = position_score + length_score
            scored_sentences.append((sentence, total_score))

        # スコア順にソート
        scored_sentences.sort(key=lambda x: x[1], reverse=True)

        # 最大文字数まで文を選択
        selected_sentences = []
        current_length = 0

        for sentence, _ in scored_sentences:
            if current_length + len(sentence) <= max_length:
                selected_sentences.append(sentence)
                current_length += len(sentence)
            else:
                break

        return (
            "。".join(selected_sentences) + "。"
            if selected_sentences
            else sentences[0][:max_length]
        )

    def _select_important_paragraphs(
        self, paragraphs: list[str], max_length: int
    ) -> str:
        """重要な段落を選択して要約を作成"""
        if not paragraphs:
            return ""

        # 最初の段落は常に含める（ただし長すぎる場合は切り取る）
        first_paragraph = paragraphs[0]
        if len(first_paragraph) > max_length // 2:
            first_paragraph = first_paragraph[: max_length // 2] + "..."

        summary_parts = [first_paragraph]
        current_length = len(first_paragraph)

        # 残りの段落から重要なものを選択
        for paragraph in paragraphs[1:]:
            paragraph_length = len(paragraph)

            # 段落全体を追加できる場合
            if current_length + paragraph_length + 2 <= max_length:  # +2 for \n\n
                summary_parts.append(paragraph)
                current_length += paragraph_length + 2
            else:
                # 部分的に追加できるかチェック
                remaining_space = max_length - current_length - 2
                if remaining_space > 50:  # 最低50文字は必要
                    summary_parts.append(paragraph[:remaining_space] + "...")
                break

        result = "\n\n".join(summary_parts)

        # 最終的な長さチェック
        if len(result) > max_length:
            result = result[:max_length] + "..."

        return result


class PreviewWidget(QWidget):
    """
    ドキュメントプレビューウィジェット

    QTextEditを拡張したプレビューウィジェットで、シンタックスハイライト、
    検索語ハイライト、ズーム機能、ドキュメント要約生成機能を提供します。
    """

    # シグナル定義
    zoom_changed = Signal(int)  # ズームレベル変更
    format_changed = Signal(str)  # フォーマット変更

    def __init__(self, parent: QWidget | None = None):
        """
        プレビューウィジェットの初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.current_document: Document | None = None
        self.current_zoom = 100  # デフォルトズーム100%
        self.search_highlighter: SearchHighlighter | None = None
        self.syntax_highlighter: DocumentSyntaxHighlighter | None = None
        self.summarizer = DocumentSummarizer()

        # UIの設定
        self._setup_ui()
        self._setup_connections()
        self._apply_styling()

        self.logger.info("プレビューウィジェットが初期化されました")

    def _setup_ui(self):
        """UIレイアウトを設定"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # ツールバーの作成
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)

        # メインコンテンツエリアの作成
        self.content_area = self._create_content_area()
        layout.addWidget(self.content_area)

    def _create_toolbar(self) -> QFrame:
        """ツールバーを作成"""
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.StyledPanel)
        toolbar.setMaximumHeight(40)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 2, 5, 2)

        # ドキュメント情報ラベル
        self.doc_info_label = QLabel("ドキュメントが選択されていません")
        self.doc_info_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(self.doc_info_label)

        layout.addStretch()

        # ズームコントロール
        zoom_label = QLabel("ズーム:")
        layout.addWidget(zoom_label)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 200)  # 50% - 200%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setMaximumWidth(100)
        self.zoom_slider.setToolTip("ズームレベルを調整")
        layout.addWidget(self.zoom_slider)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(40)
        layout.addWidget(self.zoom_label)

        # フォーマット選択
        format_label = QLabel("表示:")
        layout.addWidget(format_label)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["原文", "要約"])
        self.format_combo.setToolTip("表示形式を選択")
        layout.addWidget(self.format_combo)

        return toolbar

    def _create_content_area(self) -> QWidget:
        """メインコンテンツエリアを作成"""
        # スプリッターで分割（将来的に詳細情報パネルを追加可能）
        splitter = QSplitter(Qt.Vertical)

        # メインプレビューエリア
        self.text_browser = QTextBrowser()
        self.text_browser.setReadOnly(True)
        self.text_browser.setOpenExternalLinks(False)  # 外部リンクは無効

        # フォント設定
        font = QFont("Yu Gothic UI, Meiryo, sans-serif", 10)
        self.text_browser.setFont(font)

        # 検索ハイライターの初期化
        self.search_highlighter = SearchHighlighter(self.text_browser)

        splitter.addWidget(self.text_browser)

        # 詳細情報パネル（折りたたみ可能）
        self.details_panel = self._create_details_panel()
        splitter.addWidget(self.details_panel)

        # 初期サイズ比率（メイン80%, 詳細20%）
        splitter.setSizes([400, 100])
        splitter.setCollapsible(1, True)

        return splitter

    def _create_details_panel(self) -> QFrame:
        """詳細情報パネルを作成"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMaximumHeight(150)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)

        # タイトル
        title_label = QLabel("ドキュメント詳細")
        title_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(title_label)

        # 詳細情報テキスト
        self.details_text = QLabel("詳細情報はありません")
        self.details_text.setWordWrap(True)
        self.details_text.setAlignment(Qt.AlignTop)
        self.details_text.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.details_text)

        return panel

    def _setup_connections(self):
        """シグナル・スロット接続を設定"""
        # ズームスライダー
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)

        # フォーマット選択
        self.format_combo.currentTextChanged.connect(self._on_format_changed)

        # 要約生成完了
        self.summarizer.summary_ready.connect(self._on_summary_ready)

    def _apply_styling(self):
        """スタイリングを適用"""
        style_sheet = """
        QFrame {
            background-color: white;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
        }

        QTextBrowser {
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            padding: 10px;
            background-color: white;
            selection-background-color: #3399ff;
        }

        QLabel {
            color: #333333;
        }

        QSlider::groove:horizontal {
            border: 1px solid #bbb;
            background: white;
            height: 10px;
            border-radius: 4px;
        }

        QSlider::sub-page:horizontal {
            background: #4CAF50;
            border: 1px solid #777;
            height: 10px;
            border-radius: 4px;
        }

        QSlider::add-page:horizontal {
            background: #fff;
            border: 1px solid #777;
            height: 10px;
            border-radius: 4px;
        }

        QSlider::handle:horizontal {
            background: #4CAF50;
            border: 1px solid #5c5c5c;
            width: 18px;
            margin: -2px 0;
            border-radius: 3px;
        }

        QComboBox {
            border: 1px solid #d0d0d0;
            border-radius: 3px;
            padding: 2px 5px;
            background-color: white;
        }

        QComboBox::drop-down {
            border: none;
        }

        QComboBox::down-arrow {
            width: 12px;
            height: 12px;
        }
        """

        self.setStyleSheet(style_sheet)

    def display_document(self, document: Document):
        """
        ドキュメントを表示

        Args:
            document: 表示するドキュメント
        """
        try:
            self.current_document = document

            # ドキュメント情報を更新
            self._update_document_info()

            # 詳細情報を更新
            self._update_details_panel()

            # 現在の表示形式に応じてコンテンツを表示
            if self.format_combo.currentText() == "要約":
                self._display_summary()
            else:
                self._display_full_content()

            # シンタックスハイライトを適用
            self._apply_syntax_highlighting()

            self.logger.info(f"ドキュメントを表示しました: {document.title}")

        except Exception as e:
            self.logger.error(f"ドキュメント表示エラー: {e}")
            self._display_error(f"ドキュメントの表示中にエラーが発生しました: {str(e)}")

    def display_summary(self, text: str):
        """
        要約テキストを表示

        Args:
            text: 表示する要約テキスト
        """
        try:
            self.text_browser.setPlainText(text)
            self.doc_info_label.setText("要約表示")
            self.details_text.setText("カスタム要約が表示されています")

            self.logger.info("要約テキストを表示しました")

        except Exception as e:
            self.logger.error(f"要約表示エラー: {e}")
            self._display_error(f"要約の表示中にエラーが発生しました: {str(e)}")

    def highlight_search_terms(self, terms: list[str]):
        """
        検索語をハイライト表示

        Args:
            terms: ハイライト対象の用語リスト
        """
        try:
            if self.search_highlighter:
                self.search_highlighter.set_search_terms(terms)
                self.logger.debug(f"検索語をハイライトしました: {terms}")

        except Exception as e:
            self.logger.error(f"検索語ハイライトエラー: {e}")

    def clear_highlights(self):
        """すべてのハイライトをクリア"""
        try:
            if self.search_highlighter:
                self.search_highlighter.clear_highlights()
                self.logger.debug("ハイライトをクリアしました")

        except Exception as e:
            self.logger.error(f"ハイライトクリアエラー: {e}")

    def set_zoom_level(self, zoom_percent: int):
        """
        ズームレベルを設定

        Args:
            zoom_percent: ズームレベル（パーセント）
        """
        try:
            zoom_percent = max(50, min(200, zoom_percent))  # 50-200%に制限
            self.zoom_slider.setValue(zoom_percent)

        except Exception as e:
            self.logger.error(f"ズーム設定エラー: {e}")

    def get_zoom_level(self) -> int:
        """
        現在のズームレベルを取得

        Returns:
            int: 現在のズームレベル（パーセント）
        """
        return self.current_zoom

    def clear_preview(self):
        """プレビューをクリア"""
        try:
            self.current_document = None
            self.text_browser.clear()
            self.doc_info_label.setText("ドキュメントが選択されていません")
            self.details_text.setText("詳細情報はありません")

            # ハイライトもクリア
            self.clear_highlights()

            self.logger.debug("プレビューをクリアしました")

        except Exception as e:
            self.logger.error(f"プレビュークリアエラー: {e}")

    def _update_document_info(self):
        """ドキュメント情報を更新"""
        if not self.current_document:
            return

        doc = self.current_document
        info_text = f"{doc.title} ({doc.file_type.value.upper()}, {self._format_file_size(doc.size)})"
        self.doc_info_label.setText(info_text)

    def _update_details_panel(self):
        """詳細情報パネルを更新"""
        if not self.current_document:
            return

        doc = self.current_document
        details = [
            f"ファイルパス: {doc.file_path}",
            f"サイズ: {self._format_file_size(doc.size)}",
            f"作成日: {doc.created_date.strftime('%Y-%m-%d %H:%M:%S')}",
            f"更新日: {doc.modified_date.strftime('%Y-%m-%d %H:%M:%S')}",
            f"インデックス日: {doc.indexed_date.strftime('%Y-%m-%d %H:%M:%S')}",
            f"文字数: {len(doc.content):,} 文字",
        ]

        self.details_text.setText("\n".join(details))

    def _display_full_content(self):
        """完全なコンテンツを表示"""
        if not self.current_document:
            return

        self.text_browser.setPlainText(self.current_document.content)

    def _display_summary(self):
        """要約を表示"""
        if not self.current_document:
            return

        # 大きなファイルの場合は要約を生成
        if len(self.current_document.content) > 1000:
            summary = self.summarizer.generate_summary(
                self.current_document.content, max_length=500
            )
            self.text_browser.setPlainText(summary)
        else:
            # 小さなファイルはそのまま表示
            self.text_browser.setPlainText(self.current_document.content)

    def _apply_syntax_highlighting(self):
        """シンタックスハイライトを適用"""
        if not self.current_document:
            return

        # 既存のハイライターを削除
        if self.syntax_highlighter:
            self.syntax_highlighter.setDocument(None)

        # 新しいハイライターを作成
        self.syntax_highlighter = DocumentSyntaxHighlighter(
            self.text_browser.document(), self.current_document.file_type
        )

    def _display_error(self, error_message: str):
        """エラーメッセージを表示"""
        self.text_browser.setPlainText(f"エラー: {error_message}")
        self.doc_info_label.setText("エラーが発生しました")
        self.details_text.setText(error_message)

    def _format_file_size(self, size_bytes: int) -> str:
        """ファイルサイズを人間が読みやすい形式でフォーマット"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    # スロット関数

    def _on_zoom_changed(self, value: int):
        """ズームレベル変更時の処理"""
        self.current_zoom = value
        self.zoom_label.setText(f"{value}%")

        # フォントサイズを調整
        base_font_size = 10
        new_font_size = int(base_font_size * (value / 100.0))

        font = self.text_browser.font()
        font.setPointSize(new_font_size)
        self.text_browser.setFont(font)

        self.zoom_changed.emit(value)
        self.logger.debug(f"ズームレベルを変更しました: {value}%")

    def _on_format_changed(self, format_name: str):
        """表示フォーマット変更時の処理"""
        if not self.current_document:
            return

        if format_name == "要約":
            self._display_summary()
        else:
            self._display_full_content()

        # シンタックスハイライトを再適用
        self._apply_syntax_highlighting()

        self.format_changed.emit(format_name)
        self.logger.debug(f"表示フォーマットを変更しました: {format_name}")

    def _on_summary_ready(self, summary: str):
        """要約生成完了時の処理"""
        if self.format_combo.currentText() == "要約":
            self.text_browser.setPlainText(summary)
            self.logger.debug("要約を表示しました")
