#!/usr/bin/env python3
"""
DocMind フォルダツリー シグナルマネージャー

フォルダツリーウィジェットのシグナル接続を管理します。
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut


class SignalManager:
    """
    フォルダツリーのシグナル接続管理クラス

    ツリーウィジェットのシグナル接続、ショートカット設定、
    非同期処理のシグナル接続を一元管理します。
    """

    def __init__(self, tree_widget):
        """
        シグナルマネージャーの初期化

        Args:
            tree_widget: フォルダツリーウィジェット
        """
        self.tree_widget = tree_widget
        self.logger = logging.getLogger(__name__)

        # ショートカット保持用
        self.shortcuts = []

        self.logger.debug("SignalManagerが初期化されました")

    def setup_tree_signals(self):
        """ツリーウィジェットのシグナルを接続します"""
        # 選択変更シグナル
        self.tree_widget.itemSelectionChanged.connect(self.tree_widget.event_handler_manager.on_selection_changed)

        # アイテム展開/折りたたみシグナル
        self.tree_widget.itemExpanded.connect(self.tree_widget.event_handler_manager.on_item_expanded)
        self.tree_widget.itemCollapsed.connect(self.tree_widget.event_handler_manager.on_item_collapsed)

        # ダブルクリックシグナル
        self.tree_widget.itemDoubleClicked.connect(self.tree_widget.event_handler_manager.on_item_double_clicked)

        # コンテキストメニューシグナル
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.tree_widget._show_context_menu)

        self.logger.debug("ツリーウィジェットのシグナルを接続しました")

    def setup_async_signals(self):
        """非同期処理のシグナルを接続します"""
        # 非同期処理マネージャーのシグナル接続
        self.tree_widget.async_manager.folder_loaded.connect(self.tree_widget.event_handler_manager.on_folder_loaded)
        self.tree_widget.async_manager.load_error.connect(self.tree_widget.event_handler_manager.on_load_error)
        self.tree_widget.async_manager.load_finished.connect(self.tree_widget.event_handler_manager.on_load_finished)

        self.logger.debug("非同期処理のシグナルを接続しました")

    def setup_shortcuts(self):
        """キーボードショートカットを設定します"""
        # F5: リフレッシュ
        refresh_shortcut = QShortcut(QKeySequence.Refresh, self.tree_widget)
        refresh_shortcut.activated.connect(self.tree_widget.action_manager.refresh_folder)
        self.shortcuts.append(refresh_shortcut)

        # Ctrl+A: フォルダ追加
        add_shortcut = QShortcut(QKeySequence("Ctrl+A"), self.tree_widget)
        add_shortcut.activated.connect(self.tree_widget.context_menu_manager._add_folder)
        self.shortcuts.append(add_shortcut)

        # Delete: フォルダ削除
        delete_shortcut = QShortcut(QKeySequence.Delete, self.tree_widget)
        delete_shortcut.activated.connect(self.tree_widget.context_menu_manager._remove_folder)
        self.shortcuts.append(delete_shortcut)

        # Enter: フォルダ選択
        select_shortcut = QShortcut(QKeySequence("Return"), self.tree_widget)
        select_shortcut.activated.connect(self.tree_widget.action_manager.select_current_folder)
        self.shortcuts.append(select_shortcut)

        self.logger.debug("キーボードショートカットを設定しました")

    def disconnect_all_signals(self):
        """すべてのシグナル接続を切断します"""
        try:
            # ツリーウィジェットのシグナル切断
            self.tree_widget.itemSelectionChanged.disconnect()
            self.tree_widget.itemExpanded.disconnect()
            self.tree_widget.itemCollapsed.disconnect()
            self.tree_widget.itemDoubleClicked.disconnect()
            self.tree_widget.customContextMenuRequested.disconnect()

            # 非同期処理のシグナル切断
            if hasattr(self.tree_widget, "async_manager"):
                self.tree_widget.async_manager.folder_loaded.disconnect()
                self.tree_widget.async_manager.load_error.disconnect()
                self.tree_widget.async_manager.load_finished.disconnect()

            self.logger.debug("すべてのシグナル接続を切断しました")

        except Exception as e:
            self.logger.warning(f"シグナル切断中にエラーが発生しました: {e}")

    def cleanup(self):
        """クリーンアップ処理"""
        # ショートカットを削除
        for shortcut in self.shortcuts:
            shortcut.deleteLater()
        self.shortcuts.clear()

        # シグナル切断
        self.disconnect_all_signals()

        self.logger.debug("SignalManagerをクリーンアップしました")
