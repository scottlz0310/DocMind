#!/usr/bin/env python3
"""
検索レイアウト管理

検索インターフェースのレイアウト構築を担当します。
"""

import logging

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ..widgets.advanced_options import AdvancedSearchOptions
from ..widgets.history_widget import SearchHistoryWidget
from ..widgets.input_widget import SearchInputWidget
from ..widgets.progress_widget import SearchProgressWidget
from ..widgets.type_selector import SearchTypeSelector


class SearchLayoutManager(QObject):
    """
    検索レイアウト管理クラス

    検索インターフェースのレイアウト構築を担当します。
    """

    def __init__(self, parent: QWidget | None = None):
        """
        検索レイアウト管理を初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

    def setup_main_layout(self, parent_widget) -> QVBoxLayout:
        """メインレイアウトを設定"""
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        return layout

    def create_search_frame(self) -> QFrame:
        """検索フレームを作成"""
        main_search_frame = QFrame()
        main_search_frame.setFrameStyle(QFrame.StyledPanel)
        return main_search_frame

    def setup_search_input_layout(self, frame: QFrame) -> tuple:
        """検索入力レイアウトを設定"""
        main_search_layout = QVBoxLayout(frame)
        search_input_layout = QHBoxLayout()

        # 検索入力ウィジェット
        search_input = SearchInputWidget()
        search_input.setMinimumWidth(400)
        search_input_layout.addWidget(search_input)

        # 検索ボタン
        search_button = QPushButton("検索")
        search_button.setMinimumWidth(80)
        search_button.setMinimumHeight(35)
        search_input_layout.addWidget(search_button)

        # クリアボタン
        clear_button = QPushButton("クリア")
        clear_button.setMinimumWidth(80)
        clear_button.setMinimumHeight(35)
        search_input_layout.addWidget(clear_button)

        main_search_layout.addLayout(search_input_layout)

        return search_input, search_button, clear_button

    def create_search_components(self, layout: QVBoxLayout, main_frame: QFrame) -> tuple:
        """検索コンポーネントを作成"""
        # 検索タイプ選択
        search_type_selector = SearchTypeSelector()
        main_frame.layout().addWidget(search_type_selector)

        layout.addWidget(main_frame)

        # 進捗表示ウィジェット
        progress_widget = SearchProgressWidget()
        layout.addWidget(progress_widget)

        # 高度な検索オプション
        advanced_options = AdvancedSearchOptions()
        layout.addWidget(advanced_options)

        # 検索履歴ウィジェット
        history_widget = SearchHistoryWidget()
        layout.addWidget(history_widget)

        # スペーサー
        layout.addStretch()

        return search_type_selector, progress_widget, advanced_options, history_widget
