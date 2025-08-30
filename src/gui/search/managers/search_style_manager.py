#!/usr/bin/env python3
"""
検索スタイル管理

検索インターフェースのスタイル設定を担当します。
"""

import logging

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget


class SearchStyleManager(QObject):
    """
    検索スタイル管理クラス

    検索インターフェースのスタイル設定を担当します。
    """

    def __init__(self, parent: QWidget | None = None):
        """
        検索スタイル管理を初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

    def get_search_button_style(self) -> str:
        """検索ボタンのスタイルを取得"""
        return """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """

    def get_clear_button_style(self) -> str:
        """クリアボタンのスタイルを取得"""
        return """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """

    def get_frame_style(self) -> str:
        """フレームのスタイルを取得"""
        return """
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """

    def apply_button_styles(self, search_button, clear_button) -> None:
        """ボタンにスタイルを適用"""
        search_button.setStyleSheet(self.get_search_button_style())
        clear_button.setStyleSheet(self.get_clear_button_style())

    def apply_interface_style(self, interface_widget) -> None:
        """インターフェース全体にスタイルを適用"""
        interface_widget.setStyleSheet(self.get_frame_style())
