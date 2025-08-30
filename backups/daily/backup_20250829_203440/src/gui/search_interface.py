#!/usr/bin/env python3
"""
検索インターフェースウィジェット

分離されたコンポーネントを統合した検索インターフェースを提供します。
各マネージャーが特定の責務を担当し、保守性と拡張性を確保しています。
"""

import logging
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from ..data.models import SearchQuery
from .search.controllers.search_controller import SearchController
from .search.managers.search_api_manager import SearchAPIManager
from .search.managers.search_connection_manager import SearchConnectionManager
from .search.managers.search_event_manager import SearchEventManager
from .search.managers.search_layout_manager import SearchLayoutManager
from .search.managers.search_options_manager import SearchOptionsManager
from .search.managers.search_style_manager import SearchStyleManager
from .search.managers.search_ui_manager import SearchUIManager
from .search.managers.shortcut_manager import ShortcutManager


class SearchInterface(QWidget):
    """
    統合検索インターフェースウィジェット

    各種マネージャーを使用して責務を分離し、
    保守性と拡張性を確保した検索インターフェースです。
    """

    # シグナル定義
    search_requested = Signal(SearchQuery)  # 検索が要求された時
    search_cancelled = Signal()             # 検索がキャンセルされた時

    def __init__(self, parent: QWidget | None = None):
        """
        統合検索インターフェースを初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)

        # 各種マネージャーを初期化（責務分離のため）
        self.search_controller = SearchController(self)      # 検索ロジック制御
        self.ui_manager = SearchUIManager(self)              # UI状態管理
        self.event_manager = SearchEventManager(self)        # イベント処理
        self.style_manager = SearchStyleManager(self)        # スタイル管理
        self.shortcut_manager = ShortcutManager(self)        # ショートカット管理
        self.options_manager = SearchOptionsManager(self)    # オプション管理
        self.layout_manager = SearchLayoutManager(self)      # レイアウト管理
        self.connection_manager = SearchConnectionManager(self)  # シグナル接続管理
        self.api_manager = SearchAPIManager(self)            # 外部API管理

        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        """ユーザーインターフェースの設定"""
        # メインレイアウトを設定
        layout = self.layout_manager.setup_main_layout(self)
        main_search_frame = self.layout_manager.create_search_frame()

        # 検索入力エリアを設定
        self.search_input, self.search_button, self.clear_button = \
            self.layout_manager.setup_search_input_layout(main_search_frame)

        # ボタンスタイルを適用
        self.style_manager.apply_button_styles(self.search_button, self.clear_button)

        # 検索コンポーネントを作成
        self.search_type_selector, self.progress_widget, self.advanced_options, self.history_widget = \
            self.layout_manager.create_search_components(layout, main_search_frame)

        # 全体のスタイルを適用
        self.style_manager.apply_interface_style(self)

    def _setup_connections(self) -> None:
        """シグナル接続の設定"""
        # 基本的なボタン接続
        self.connection_manager.setup_basic_connections(
            self.search_input, self.search_button, self.clear_button,
            self._execute_search, self._clear_all
        )

        # ウィジェット間の接続
        self.connection_manager.setup_widget_connections(
            self.search_input, self.search_type_selector, self.advanced_options,
            self.progress_widget, self.history_widget, self.event_manager,
            self.ui_manager, self._execute_search, self._cancel_search,
            self._apply_search_options
        )

        # コントローラーとの接続
        self.connection_manager.setup_controller_connections(
            self.search_controller, self.search_requested, self.search_cancelled,
            self._on_search_state_changed
        )

    def _setup_shortcuts(self) -> None:
        """キーボードショートカットの設定"""
        self.shortcut_manager.setup_search_shortcuts(
            self._execute_search, self._toggle_advanced_options
        )

    def _execute_search(self) -> None:
        query_text = self.search_input.text().strip()
        search_type = self.search_type_selector.get_search_type()
        search_options = self.advanced_options.get_search_options()

        if query_text:
            self.progress_widget.start_search(f"'{query_text}' を検索中...")

        self.search_controller.execute_search(query_text, search_type, search_options)

    def _cancel_search(self) -> None:
        self.progress_widget.finish_search("検索がキャンセルされました")
        self.search_controller.cancel_search()

    def _on_search_state_changed(self, is_searching: bool) -> None:
        self.ui_manager.update_search_button_state(self.search_button, is_searching)

    def _clear_all(self) -> None:
        self.ui_manager.clear_search_interface(
            self.search_input, self.advanced_options, self.progress_widget
        )

    def _apply_search_options(self, options: dict[str, Any]) -> None:
        self.options_manager.apply_search_options(options, self.advanced_options)

    def _toggle_advanced_options(self) -> None:
        current_state = self.advanced_options.isChecked()
        self.advanced_options.setChecked(not current_state)

    def on_search_completed(self, results: list[Any], execution_time: float) -> None:
        """
        検索完了時の処理

        Args:
            results: 検索結果
            execution_time: 実行時間（秒）
        """
        self.api_manager.handle_search_completed(
            results, execution_time, self.progress_widget, self.search_controller
        )

    def on_search_error(self, error_message: str) -> None:
        """
        検索エラー時の処理

        Args:
            error_message: エラーメッセージ
        """
        self.api_manager.handle_search_error(
            error_message, self.progress_widget, self.search_controller
        )

    def update_search_suggestions(self, suggestions: list[str]) -> None:
        """
        検索提案を更新

        Args:
            suggestions: 提案リスト
        """
        self.api_manager.update_search_suggestions(
            suggestions, self.search_input, self.ui_manager
        )

    def update_search_history(self, recent_searches: list[dict[str, Any]],
                            popular_searches: list[dict[str, Any]],
                            saved_searches: list[dict[str, Any]] = None) -> None:
        """
        検索履歴を更新

        Args:
            recent_searches: 最近の検索リスト
            popular_searches: 人気の検索リスト
            saved_searches: 保存された検索リスト
        """
        self.api_manager.update_search_history(
            recent_searches, popular_searches, saved_searches,
            self.history_widget, self.ui_manager
        )

    def set_search_text(self, text: str) -> None:
        """
        検索テキストを設定

        Args:
            text: 設定するテキスト
        """
        self.api_manager.set_search_text(text, self.search_input)

    def get_search_text(self) -> str:
        """現在の検索テキストを取得"""
        return self.api_manager.get_search_text(self.search_input)

    def clear_search(self) -> None:
        """検索フィールドをクリア"""
        self.api_manager.clear_search(self.search_input)

    def set_enabled(self, enabled: bool) -> None:
        """インターフェースの有効/無効を設定"""
        self.api_manager.set_interface_enabled(
            enabled, self.search_input, self.search_button, self.search_type_selector,
            self.advanced_options, self.search_controller, self.ui_manager
        )

