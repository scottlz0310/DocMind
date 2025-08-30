#!/usr/bin/env python3
"""
検索API管理

検索インターフェースの外部APIメソッドを担当します。
"""

import logging
from typing import Any

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget


class SearchAPIManager(QObject):
    """
    検索API管理クラス

    検索インターフェースの外部APIメソッドを担当します。
    """

    def __init__(self, parent: QWidget | None = None):
        """
        検索API管理を初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

    def handle_search_completed(self, results: list[Any], execution_time: float,
                              progress_widget, search_controller) -> None:
        """検索完了時の処理"""
        result_count = len(results)
        message = f"検索完了: {result_count}件の結果 ({execution_time:.1f}秒)"
        progress_widget.finish_search(message)
        search_controller.on_search_completed(results, execution_time)

    def handle_search_error(self, error_message: str, progress_widget, search_controller) -> None:
        """検索エラー時の処理"""
        progress_widget.finish_search("検索エラーが発生しました")
        search_controller.on_search_error(error_message)

    def update_search_suggestions(self, suggestions: list[str], search_input, ui_manager) -> None:
        """検索提案を更新"""
        ui_manager.update_search_suggestions(search_input, suggestions)

    def update_search_history(self, recent_searches: list[dict[str, Any]],
                            popular_searches: list[dict[str, Any]],
                            saved_searches: list[dict[str, Any]],
                            history_widget, ui_manager) -> None:
        """検索履歴を更新"""
        ui_manager.update_search_history(
            history_widget, recent_searches, popular_searches, saved_searches
        )

    def set_search_text(self, text: str, search_input) -> None:
        """検索テキストを設定"""
        search_input.setText(text)
        search_input.setFocus()

    def get_search_text(self, search_input) -> str:
        """現在の検索テキストを取得"""
        return search_input.text().strip()

    def clear_search(self, search_input) -> None:
        """検索フィールドをクリア"""
        search_input.clear()
        search_input.setFocus()

    def set_interface_enabled(self, enabled: bool, search_input, search_button,
                            search_type_selector, advanced_options,
                            search_controller, ui_manager) -> None:
        """インターフェースの有効/無効を設定"""
        is_searching = search_controller.get_searching_state()
        ui_manager.set_interface_enabled(
            search_input, search_button, search_type_selector,
            advanced_options, enabled, is_searching
        )
