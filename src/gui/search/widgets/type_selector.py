#!/usr/bin/env python3
"""
検索タイプ選択ウィジェット

全文検索、セマンティック検索、ハイブリッド検索の選択機能を提供します。
"""

import logging

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QRadioButton, QWidget

from ....data.models import SearchType


class SearchTypeSelector(QWidget):
    """
    検索タイプ選択ウィジェット

    全文検索、セマンティック検索、ハイブリッド検索の選択機能を提供します。
    """

    # シグナル定義
    search_type_changed = Signal(SearchType)  # 検索タイプが変更された時

    def __init__(self, parent: QWidget | None = None):
        """
        検索タイプ選択ウィジェットを初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.current_search_type = SearchType.HYBRID

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """UIの設定"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ラベル
        label = QLabel("検索タイプ:")
        label.setFont(QFont("", 9))
        layout.addWidget(label)

        # ラジオボタングループ
        self.button_group = QButtonGroup(self)

        # 全文検索ラジオボタン
        self.full_text_radio = QRadioButton("全文検索")
        self.full_text_radio.setToolTip("キーワードの完全一致による検索")
        self.button_group.addButton(self.full_text_radio, 0)
        layout.addWidget(self.full_text_radio)

        # セマンティック検索ラジオボタン
        self.semantic_radio = QRadioButton("セマンティック検索")
        self.semantic_radio.setToolTip("意味的類似性による検索")
        self.button_group.addButton(self.semantic_radio, 1)
        layout.addWidget(self.semantic_radio)

        # ハイブリッド検索ラジオボタン（デフォルト選択）
        self.hybrid_radio = QRadioButton("ハイブリッド検索")
        self.hybrid_radio.setToolTip("全文検索とセマンティック検索の組み合わせ")
        self.hybrid_radio.setChecked(True)
        self.button_group.addButton(self.hybrid_radio, 2)
        layout.addWidget(self.hybrid_radio)

        # スペーサー
        layout.addStretch()

        # スタイル設定
        self.setStyleSheet(
            """
            QRadioButton {
                font-size: 12px;
                spacing: 5px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                background-color: white;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #4CAF50;
                border-radius: 8px;
                background-color: #4CAF50;
            }
        """
        )

    def _setup_connections(self) -> None:
        """シグナル接続の設定"""
        self.button_group.buttonClicked.connect(self._on_search_type_changed)

    def _on_search_type_changed(self, button) -> None:
        """検索タイプ変更時の処理"""
        if button == self.full_text_radio:
            self.current_search_type = SearchType.FULL_TEXT
        elif button == self.semantic_radio:
            self.current_search_type = SearchType.SEMANTIC
        elif button == self.hybrid_radio:
            self.current_search_type = SearchType.HYBRID

        self.search_type_changed.emit(self.current_search_type)
        self.logger.debug(f"検索タイプ変更: {self.current_search_type.value}")

    def get_search_type(self) -> SearchType:
        """現在の検索タイプを取得"""
        return self.current_search_type

    def set_search_type(self, search_type: SearchType) -> None:
        """検索タイプを設定"""
        self.current_search_type = search_type

        if search_type == SearchType.FULL_TEXT:
            self.full_text_radio.setChecked(True)
        elif search_type == SearchType.SEMANTIC:
            self.semantic_radio.setChecked(True)
        elif search_type == SearchType.HYBRID:
            self.hybrid_radio.setChecked(True)
