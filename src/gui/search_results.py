#!/usr/bin/env python3
"""
DocMind 検索結果表示ウィジェット

QListWidgetを拡張した検索結果表示機能を実装します。
タイトル、スニペット、スコア表示付きのカスタム結果アイテムウィジェットと
結果のソート、フィルタリング、ページネーション機能を提供します。
"""

import logging
import math
from enum import Enum
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.data.models import FileType, SearchResult, SearchType


class SortOrder(Enum):
    """ソート順序を定義する列挙型"""

    RELEVANCE_DESC = "relevance_desc"  # 関連度降順（デフォルト）
    RELEVANCE_ASC = "relevance_asc"  # 関連度昇順
    TITLE_ASC = "title_asc"  # タイトル昇順
    TITLE_DESC = "title_desc"  # タイトル降順
    DATE_DESC = "date_desc"  # 日付降順
    DATE_ASC = "date_asc"  # 日付昇順
    SIZE_DESC = "size_desc"  # サイズ降順
    SIZE_ASC = "size_asc"  # サイズ昇順


class SearchResultItemWidget(QFrame):
    """
    検索結果の個別アイテムを表示するカスタムウィジェット

    タイトル、スニペット、スコア、メタデータを含む
    視覚的に魅力的な結果表示を提供します。
    """

    # シグナル定義
    item_clicked = Signal(SearchResult)  # アイテムがクリックされた時
    preview_requested = Signal(SearchResult)  # プレビューが要求された時

    def __init__(self, search_result: SearchResult, parent: QWidget | None = None):
        """
        検索結果アイテムウィジェットの初期化

        Args:
            search_result: 表示する検索結果
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.search_result = search_result
        self.is_selected = False
        self.is_hovered = False

        self._setup_ui()
        self._apply_styling()
        self._setup_interactions()

    def _setup_ui(self) -> None:
        """UIレイアウトを設定します"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setMinimumHeight(120)
        self.setMaximumHeight(150)

        # メインレイアウト
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(6)

        # ヘッダー行（タイトルとスコア）
        header_layout = QHBoxLayout()

        # タイトルラベル
        self.title_label = QLabel(self.search_result.document.title)
        self.title_label.setFont(QFont("", 11, QFont.Bold))
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(50)
        header_layout.addWidget(self.title_label, 1)

        # スコア表示
        self.score_label = QLabel(self.search_result.get_formatted_score())
        self.score_label.setFont(QFont("", 10))
        self.score_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.score_label.setMinimumWidth(60)
        header_layout.addWidget(self.score_label)

        main_layout.addLayout(header_layout)

        # スニペット表示
        self.snippet_label = QLabel(self._format_snippet())
        self.snippet_label.setFont(QFont("", 9))
        self.snippet_label.setWordWrap(True)
        self.snippet_label.setMaximumHeight(40)
        self.snippet_label.setAlignment(Qt.AlignTop)
        main_layout.addWidget(self.snippet_label)

        # メタデータ行
        metadata_layout = QHBoxLayout()

        # ファイルタイプアイコンとパス
        self.file_info_label = QLabel(self._format_file_info())
        self.file_info_label.setFont(QFont("", 8))
        metadata_layout.addWidget(self.file_info_label, 1)

        # 検索タイプ表示
        self.search_type_label = QLabel(self.search_result.get_search_type_display())
        self.search_type_label.setFont(QFont("", 8))
        self.search_type_label.setAlignment(Qt.AlignRight)
        metadata_layout.addWidget(self.search_type_label)

        main_layout.addLayout(metadata_layout)

    def _format_snippet(self) -> str:
        """スニペットをフォーマットします"""
        snippet = self.search_result.snippet
        if not snippet:
            snippet = self.search_result.document.get_summary(150)

        # 長すぎる場合は切り詰める
        if len(snippet) > 150:
            snippet = snippet[:147] + "..."

        return snippet

    def _format_file_info(self) -> str:
        """ファイル情報をフォーマットします"""
        doc = self.search_result.document
        file_type_name = self._get_file_type_display_name(doc.file_type)
        file_size = self._format_file_size(doc.size)

        # ファイルパスを短縮
        file_path = doc.file_path
        if len(file_path) > 50:
            file_path = "..." + file_path[-47:]

        return f"{file_type_name} • {file_size} • {file_path}"

    def _get_file_type_display_name(self, file_type: FileType) -> str:
        """ファイルタイプの表示名を取得"""
        type_names = {
            FileType.PDF: "PDF",
            FileType.WORD: "Word",
            FileType.EXCEL: "Excel",
            FileType.MARKDOWN: "Markdown",
            FileType.TEXT: "テキスト",
            FileType.UNKNOWN: "不明",
        }
        return type_names.get(file_type, "不明")

    def _format_file_size(self, size: int) -> str:
        """ファイルサイズをフォーマットします"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _apply_styling(self) -> None:
        """スタイリングを適用します"""
        self._update_style()

    def _update_style(self) -> None:
        """現在の状態に基づいてスタイルを更新"""
        if self.is_selected:
            background_color = "#e3f2fd"
            border_color = "#2196f3"
            border_width = "2px"
        elif self.is_hovered:
            background_color = "#f5f5f5"
            border_color = "#cccccc"
            border_width = "1px"
        else:
            background_color = "#ffffff"
            border_color = "#e0e0e0"
            border_width = "1px"

        style_sheet = f"""
        QWidget {{
            background-color: {background_color};
            border: {border_width} solid {border_color};
            border-radius: 6px;
            margin: 2px;
        }}

        QLabel {{
            background-color: transparent;
            border: none;
        }}
        """

        self.setStyleSheet(style_sheet)

        # スコアに基づいて色を設定
        score_color = self._get_score_color(self.search_result.score)
        self.score_label.setStyleSheet(f"color: {score_color}; font-weight: bold;")

        # 検索タイプに基づいて色を設定
        type_color = self._get_search_type_color(self.search_result.search_type)
        self.search_type_label.setStyleSheet(f"color: {type_color};")

    def _get_score_color(self, score: float) -> str:
        """スコアに基づいて色を取得"""
        if score >= 0.8:
            return "#4caf50"  # 緑（高スコア）
        elif score >= 0.6:
            return "#ff9800"  # オレンジ（中スコア）
        else:
            return "#f44336"  # 赤（低スコア）

    def _get_search_type_color(self, search_type: SearchType) -> str:
        """検索タイプに基づいて色を取得"""
        type_colors = {
            SearchType.FULL_TEXT: "#2196f3",  # 青
            SearchType.SEMANTIC: "#9c27b0",  # 紫
            SearchType.HYBRID: "#ff5722",  # 深いオレンジ
        }
        return type_colors.get(search_type, "#666666")

    def _setup_interactions(self) -> None:
        """インタラクションを設定します"""
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def mousePressEvent(self, event) -> None:
        """マウスクリックイベントをハンドル"""
        if event.button() == Qt.LeftButton:
            self.item_clicked.emit(self.search_result)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """マウスダブルクリックイベントをハンドル"""
        if event.button() == Qt.LeftButton:
            self.preview_requested.emit(self.search_result)
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event) -> None:
        """マウスエンターイベントをハンドル"""
        self.is_hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """マウスリーブイベントをハンドル"""
        self.is_hovered = False
        self._update_style()
        super().leaveEvent(event)

    def set_selected(self, selected: bool) -> None:
        """選択状態を設定"""
        self.is_selected = selected
        self._update_style()

    def get_search_result(self) -> SearchResult:
        """検索結果を取得"""
        return self.search_result


class SearchResultsWidget(QWidget):
    """
    検索結果表示ウィジェット

    QListWidgetを拡張した検索結果表示機能を提供します。
    ソート、フィルタリング、ページネーション機能を含みます。
    """

    # シグナル定義
    result_selected = Signal(SearchResult)  # 結果が選択された時
    preview_requested = Signal(SearchResult)  # プレビューが要求された時
    page_changed = Signal(int)  # ページが変更された時
    sort_changed = Signal(SortOrder)  # ソート順が変更された時
    filter_changed = Signal(dict)  # フィルターが変更された時

    def __init__(self, parent: QWidget | None = None):
        """
        検索結果ウィジェットの初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

        # データ管理
        self.all_results: list[SearchResult] = []
        self.filtered_results: list[SearchResult] = []
        self.current_results: list[SearchResult] = []
        self.selected_result: SearchResult | None = None

        # ページネーション設定
        self.results_per_page = 20
        self.current_page = 1
        self.total_pages = 1

        # ソート・フィルター設定
        self.current_sort_order = SortOrder.RELEVANCE_DESC
        self.current_filters: dict[str, Any] = {}

        # UI コンポーネント
        self.result_items: list[SearchResultItemWidget] = []

        self._setup_ui()
        self._setup_interactions()

        self.logger.info("検索結果ウィジェットが初期化されました")

    def _setup_ui(self) -> None:
        """UIレイアウトを設定します"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ツールバー（ソート・フィルター・ページネーション）
        self.toolbar = self._create_toolbar()
        main_layout.addWidget(self.toolbar)

        # 結果表示エリア
        self.results_area = self._create_results_area()
        main_layout.addWidget(self.results_area, 1)

        # ページネーションコントロール
        self.pagination_bar = self._create_pagination_bar()
        main_layout.addWidget(self.pagination_bar)

        # 初期状態では空の状態を表示
        self._show_empty_state()

    def _create_toolbar(self) -> QFrame:
        """ツールバーを作成"""
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.StyledPanel)
        toolbar.setMaximumHeight(50)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # 結果数表示
        self.result_count_label = QLabel("結果: 0件")
        self.result_count_label.setFont(QFont("", 9))
        layout.addWidget(self.result_count_label)

        layout.addStretch()

        # ソート選択
        sort_label = QLabel("ソート:")
        sort_label.setFont(QFont("", 9))
        layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(
            [
                "関連度（高→低）",
                "関連度（低→高）",
                "タイトル（A→Z）",
                "タイトル（Z→A）",
                "日付（新→古）",
                "日付（古→新）",
                "サイズ（大→小）",
                "サイズ（小→大）",
            ]
        )
        self.sort_combo.setMinimumWidth(120)
        layout.addWidget(self.sort_combo)

        # フィルターボタン
        self.filter_button = QPushButton("フィルター")
        self.filter_button.setCheckable(True)
        self.filter_button.setMaximumWidth(80)
        layout.addWidget(self.filter_button)

        return toolbar

    def _create_results_area(self) -> QWidget:
        """結果表示エリアを作成"""
        # スクロールエリアを作成
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 結果コンテナ
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(4, 4, 4, 4)
        self.results_layout.setSpacing(2)

        scroll_area.setWidget(self.results_container)

        return scroll_area

    def _create_pagination_bar(self) -> QFrame:
        """ページネーションバーを作成"""
        pagination_bar = QFrame()
        pagination_bar.setFrameStyle(QFrame.StyledPanel)
        pagination_bar.setMaximumHeight(40)

        layout = QHBoxLayout(pagination_bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # ページ情報
        self.page_info_label = QLabel("ページ 1 / 1")
        self.page_info_label.setFont(QFont("", 9))
        layout.addWidget(self.page_info_label)

        layout.addStretch()

        # ページネーションコントロール
        self.first_page_button = QPushButton("<<")
        self.first_page_button.setMaximumWidth(30)
        self.first_page_button.setEnabled(False)
        layout.addWidget(self.first_page_button)

        self.prev_page_button = QPushButton("<")
        self.prev_page_button.setMaximumWidth(30)
        self.prev_page_button.setEnabled(False)
        layout.addWidget(self.prev_page_button)

        # ページ番号入力
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setValue(1)
        self.page_spin.setMaximumWidth(60)
        layout.addWidget(self.page_spin)

        self.next_page_button = QPushButton(">")
        self.next_page_button.setMaximumWidth(30)
        self.next_page_button.setEnabled(False)
        layout.addWidget(self.next_page_button)

        self.last_page_button = QPushButton(">>")
        self.last_page_button.setMaximumWidth(30)
        self.last_page_button.setEnabled(False)
        layout.addWidget(self.last_page_button)

        layout.addStretch()

        # 1ページあたりの結果数設定
        per_page_label = QLabel("表示件数:")
        per_page_label.setFont(QFont("", 9))
        layout.addWidget(per_page_label)

        self.per_page_combo = QComboBox()
        self.per_page_combo.addItems(["10", "20", "50", "100"])
        self.per_page_combo.setCurrentText("20")
        self.per_page_combo.setMaximumWidth(60)
        layout.addWidget(self.per_page_combo)

        return pagination_bar

    def _setup_interactions(self) -> None:
        """インタラクションを設定します"""
        # ソート変更
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)

        # フィルターボタン
        self.filter_button.toggled.connect(self._on_filter_toggled)

        # ページネーション
        self.first_page_button.clicked.connect(lambda: self.go_to_page(1))
        self.prev_page_button.clicked.connect(
            lambda: self.go_to_page(self.current_page - 1)
        )
        self.next_page_button.clicked.connect(
            lambda: self.go_to_page(self.current_page + 1)
        )
        self.last_page_button.clicked.connect(lambda: self.go_to_page(self.total_pages))
        self.page_spin.valueChanged.connect(self.go_to_page)

        # 1ページあたりの結果数変更
        self.per_page_combo.currentTextChanged.connect(self._on_per_page_changed)

    def display_results(self, results: list[SearchResult]) -> None:
        """
        検索結果を表示します

        Args:
            results: 表示する検索結果のリスト
        """
        self.logger.info(f"検索結果を表示: {len(results)}件")

        self.all_results = results.copy()
        self.selected_result = None

        # フィルターを適用
        self._apply_filters()

        # ソートを適用
        self._apply_sort()

        # ページネーションを更新
        self._update_pagination()

        # 最初のページを表示
        self.go_to_page(1)

        # 結果数を更新
        self._update_result_count()

    def _apply_filters(self) -> None:
        """現在のフィルター設定を適用"""
        self.filtered_results = self.all_results.copy()

        # TODO: フィルター機能の実装
        # 現在はすべての結果を通す

        self.logger.debug(f"フィルター適用後: {len(self.filtered_results)}件")

    def _apply_sort(self) -> None:
        """現在のソート設定を適用"""
        if not self.filtered_results:
            return

        sort_functions = {
            SortOrder.RELEVANCE_DESC: lambda x: -x.score,
            SortOrder.RELEVANCE_ASC: lambda x: x.score,
            SortOrder.TITLE_ASC: lambda x: x.document.title.lower(),
            SortOrder.TITLE_DESC: lambda x: x.document.title.lower(),
            SortOrder.DATE_DESC: lambda x: -x.document.modified_date.timestamp(),
            SortOrder.DATE_ASC: lambda x: x.document.modified_date.timestamp(),
            SortOrder.SIZE_DESC: lambda x: -x.document.size,
            SortOrder.SIZE_ASC: lambda x: x.document.size,
        }

        sort_func = sort_functions.get(self.current_sort_order)
        if sort_func:
            reverse = self.current_sort_order in [SortOrder.TITLE_DESC]
            self.filtered_results.sort(key=sort_func, reverse=reverse)

        self.logger.debug(f"ソート適用: {self.current_sort_order}")

    def _update_pagination(self) -> None:
        """ページネーション情報を更新"""
        total_results = len(self.filtered_results)
        self.total_pages = max(1, math.ceil(total_results / self.results_per_page))

        # ページスピンボックスの範囲を更新
        self.page_spin.setMaximum(self.total_pages)

        # 現在のページが範囲外の場合は調整
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages

        self._update_pagination_controls()

    def _update_pagination_controls(self) -> None:
        """ページネーションコントロールの状態を更新"""
        # ボタンの有効/無効状態
        self.first_page_button.setEnabled(self.current_page > 1)
        self.prev_page_button.setEnabled(self.current_page > 1)
        self.next_page_button.setEnabled(self.current_page < self.total_pages)
        self.last_page_button.setEnabled(self.current_page < self.total_pages)

        # ページ情報の更新
        self.page_info_label.setText(f"ページ {self.current_page} / {self.total_pages}")
        self.page_spin.setValue(self.current_page)

    def _update_result_count(self) -> None:
        """結果数表示を更新"""
        total_count = len(self.all_results)
        filtered_count = len(self.filtered_results)

        if total_count == filtered_count:
            self.result_count_label.setText(f"結果: {total_count}件")
        else:
            self.result_count_label.setText(
                f"結果: {filtered_count}件 (全{total_count}件中)"
            )

    def go_to_page(self, page: int) -> None:
        """
        指定されたページに移動

        Args:
            page: 移動先のページ番号
        """
        if page < 1 or page > self.total_pages:
            return

        self.current_page = page

        # 現在のページの結果を取得
        start_index = (page - 1) * self.results_per_page
        end_index = start_index + self.results_per_page
        self.current_results = self.filtered_results[start_index:end_index]

        # 結果を表示
        self._display_current_page()

        # ページネーションコントロールを更新
        self._update_pagination_controls()

        # シグナルを発行
        self.page_changed.emit(page)

        self.logger.debug(f"ページ {page} に移動: {len(self.current_results)}件表示")

    def _display_current_page(self) -> None:
        """現在のページの結果を表示"""
        # 既存のアイテムをクリア
        self._clear_result_items()

        if not self.current_results:
            self._show_empty_state()
            return

        # 新しいアイテムを作成
        for result in self.current_results:
            item_widget = SearchResultItemWidget(result)
            item_widget.item_clicked.connect(self._on_result_selected)
            item_widget.preview_requested.connect(self._on_preview_requested)

            self.results_layout.addWidget(item_widget)
            self.result_items.append(item_widget)

        # ストレッチを追加して上詰めにする
        self.results_layout.addStretch()

    def _clear_result_items(self) -> None:
        """結果アイテムをクリア"""
        for item in self.result_items:
            item.deleteLater()
        self.result_items.clear()

        # レイアウトからすべてのアイテムを削除
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _show_empty_state(self) -> None:
        """空の状態を表示"""
        empty_label = QLabel("検索結果がありません")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("color: gray; font-style: italic; font-size: 14px;")
        self.results_layout.addWidget(empty_label)

    # イベントハンドラー

    def _on_sort_changed(self, index: int) -> None:
        """ソート順が変更された時の処理"""
        sort_orders = [
            SortOrder.RELEVANCE_DESC,
            SortOrder.RELEVANCE_ASC,
            SortOrder.TITLE_ASC,
            SortOrder.TITLE_DESC,
            SortOrder.DATE_DESC,
            SortOrder.DATE_ASC,
            SortOrder.SIZE_DESC,
            SortOrder.SIZE_ASC,
        ]

        if 0 <= index < len(sort_orders):
            self.current_sort_order = sort_orders[index]
            self._apply_sort()
            self._update_pagination()
            self.go_to_page(1)  # 最初のページに戻る

            self.sort_changed.emit(self.current_sort_order)
            self.logger.debug(f"ソート順変更: {self.current_sort_order}")

    def _on_filter_toggled(self, checked: bool) -> None:
        """フィルターボタンが切り替えられた時の処理"""
        # TODO: フィルターパネルの表示/非表示を実装
        self.logger.debug(f"フィルター切り替え: {checked}")

    def _on_per_page_changed(self, text: str) -> None:
        """1ページあたりの結果数が変更された時の処理"""
        try:
            new_per_page = int(text)
            if new_per_page != self.results_per_page:
                self.results_per_page = new_per_page
                self._update_pagination()
                self.go_to_page(1)  # 最初のページに戻る
                self.logger.debug(f"1ページあたりの結果数変更: {new_per_page}")
        except ValueError:
            pass

    def _on_result_selected(self, result: SearchResult) -> None:
        """結果が選択された時の処理"""
        # 前の選択を解除
        if self.selected_result:
            for item in self.result_items:
                if item.get_search_result() == self.selected_result:
                    item.set_selected(False)
                    break

        # 新しい選択を設定
        self.selected_result = result
        for item in self.result_items:
            if item.get_search_result() == result:
                item.set_selected(True)
                break

        self.result_selected.emit(result)
        self.logger.debug(f"結果選択: {result.document.title}")

    def _on_preview_requested(self, result: SearchResult) -> None:
        """プレビューが要求された時の処理"""
        self.preview_requested.emit(result)
        self.logger.debug(f"プレビュー要求: {result.document.title}")

    # パブリックメソッド

    def clear_results(self) -> None:
        """すべての結果をクリア"""
        self.all_results.clear()
        self.filtered_results.clear()
        self.current_results.clear()
        self.selected_result = None

        self._clear_result_items()
        self._show_empty_state()

        self.current_page = 1
        self.total_pages = 1
        self._update_pagination_controls()
        self._update_result_count()

        self.logger.debug("検索結果をクリアしました")

    def get_selected_result(self) -> SearchResult | None:
        """選択された結果を取得"""
        return self.selected_result

    def get_all_results(self) -> list[SearchResult]:
        """すべての結果を取得"""
        return self.all_results.copy()

    def get_filtered_results(self) -> list[SearchResult]:
        """フィルター済みの結果を取得"""
        return self.filtered_results.copy()

    def set_results_per_page(self, count: int) -> None:
        """1ページあたりの結果数を設定"""
        if count > 0:
            self.results_per_page = count
            self.per_page_combo.setCurrentText(str(count))
            self._update_pagination()
            self.go_to_page(1)

    def refresh_display(self) -> None:
        """表示を更新"""
        if self.all_results:
            self._apply_filters()
            self._apply_sort()
            self._update_pagination()
            self.go_to_page(self.current_page)
            self._update_result_count()
