#!/usr/bin/env python3
"""
検索接続管理

検索インターフェースのシグナル接続を担当します。
"""

import logging

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget


class SearchConnectionManager(QObject):
    """
    検索接続管理クラス

    検索インターフェースのシグナル接続を担当します。
    """

    def __init__(self, parent: QWidget | None = None):
        """
        検索接続管理を初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

    def setup_basic_connections(
        self,
        search_input,
        search_button,
        clear_button,
        execute_callback,
        clear_callback,
    ) -> None:
        """基本的な接続を設定"""
        search_input.search_requested.connect(execute_callback)
        search_button.clicked.connect(execute_callback)
        clear_button.clicked.connect(clear_callback)

    def setup_widget_connections(
        self,
        search_input,
        search_type_selector,
        advanced_options,
        progress_widget,
        history_widget,
        event_manager,
        ui_manager,
        execute_callback,
        cancel_callback,
        apply_options_callback,
    ) -> None:
        """ウィジェット間の接続を設定"""
        # 検索提案選択
        search_input.suggestion_selected.connect(
            lambda suggestion: event_manager.handle_suggestion_selected(suggestion, search_input, execute_callback)
        )

        # 検索タイプ変更
        search_type_selector.search_type_changed.connect(
            lambda search_type: event_manager.handle_search_type_changed(search_type, ui_manager, advanced_options)
        )

        # 高度なオプション変更
        advanced_options.options_changed.connect(event_manager.handle_options_changed)

        # 進捗キャンセル
        progress_widget.cancel_requested.connect(cancel_callback)

        # 履歴選択
        history_widget.history_selected.connect(
            lambda query: event_manager.handle_history_selected(query, search_input)
        )
        history_widget.history_deleted.connect(event_manager.handle_history_deleted)

        # 保存された検索
        history_widget.search_save_requested.connect(event_manager.handle_search_save_requested)
        history_widget.saved_search_selected.connect(
            lambda search_data: event_manager.handle_saved_search_selected(
                search_data, search_input, search_type_selector, apply_options_callback
            )
        )
        history_widget.saved_search_deleted.connect(event_manager.handle_saved_search_deleted)

    def setup_controller_connections(
        self,
        search_controller,
        search_requested_signal,
        search_cancelled_signal,
        state_changed_callback,
    ) -> None:
        """コントローラーとの接続を設定"""
        search_controller.search_requested.connect(search_requested_signal)
        search_controller.search_cancelled.connect(search_cancelled_signal)
        search_controller.search_state_changed.connect(state_changed_callback)
