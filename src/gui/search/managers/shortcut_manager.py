#!/usr/bin/env python3
"""
ショートカット管理

検索インターフェースのキーボードショートカットを担当します。
"""

import logging

from PySide6.QtCore import QObject
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget


class ShortcutManager(QObject):
    """
    ショートカット管理クラス

    検索インターフェースのキーボードショートカットを担当します。
    """

    def __init__(self, parent: QWidget | None = None):
        """
        ショートカット管理を初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.parent_widget = parent
        self.shortcuts = []

    def setup_search_shortcuts(
        self, execute_search_callback, toggle_options_callback
    ) -> None:
        """
        検索関連のショートカットを設定

        Args:
            execute_search_callback: 検索実行コールバック
            toggle_options_callback: オプション切り替えコールバック
        """
        # Ctrl+Enterで検索実行
        search_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.parent_widget)
        search_shortcut.activated.connect(execute_search_callback)
        self.shortcuts.append(search_shortcut)

        # F3で高度なオプション切り替え
        options_shortcut = QShortcut(QKeySequence("F3"), self.parent_widget)
        options_shortcut.activated.connect(toggle_options_callback)
        self.shortcuts.append(options_shortcut)

        self.logger.debug("検索ショートカットを設定しました")

    def cleanup_shortcuts(self) -> None:
        """ショートカットをクリーンアップ"""
        for shortcut in self.shortcuts:
            shortcut.deleteLater()
        self.shortcuts.clear()
        self.logger.debug("ショートカットをクリーンアップしました")
