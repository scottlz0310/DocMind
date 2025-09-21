#!/usr/bin/env python3
"""
DocMind フォルダツリーUIセットアップマネージャー

フォルダツリーウィジェットのUI設定、ショートカット、シグナル接続を管理します。
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget

if TYPE_CHECKING:
    from ..folder_tree_widget import FolderTreeWidget


class UISetupManager:
    """
    フォルダツリーウィジェットのUI設定を管理するクラス

    UIの基本設定、ショートカット設定、シグナル接続を担当します。
    """

    def __init__(self, tree_widget: "FolderTreeWidget"):
        """
        UIセットアップマネージャーの初期化

        Args:
            tree_widget: 管理対象のフォルダツリーウィジェット
        """
        self.tree_widget = tree_widget
        self.logger = logging.getLogger(__name__)

        # ショートカット参照を保持
        self.shortcuts = {}

        self.logger.debug("UIセットアップマネージャーが初期化されました")

    def setup_tree_widget(self):
        """ツリーウィジェットの基本設定を行います"""
        # ヘッダー設定
        self.tree_widget.setHeaderLabel("フォルダ構造")
        self.tree_widget.setHeaderHidden(False)

        # 基本設定
        self.tree_widget.setRootIsDecorated(True)  # ルートアイテムに展開アイコンを表示
        self.tree_widget.setAlternatingRowColors(True)  # 行の色を交互に変更
        self.tree_widget.setSelectionMode(QTreeWidget.SingleSelection)  # 単一選択
        self.tree_widget.setExpandsOnDoubleClick(True)  # ダブルクリックで展開
        self.tree_widget.setSortingEnabled(True)  # ソート機能を有効化
        self.tree_widget.sortByColumn(0, Qt.AscendingOrder)  # 名前順でソート

        # ドラッグ&ドロップを無効化(今回は不要)
        self.tree_widget.setDragDropMode(QTreeWidget.NoDragDrop)

        # アクセシビリティ設定
        self.tree_widget.setAccessibleName("フォルダツリー")
        self.tree_widget.setAccessibleDescription("検索対象フォルダの階層構造を表示します")

        # スタイル設定
        self._apply_tree_styles()

        self.logger.debug("ツリーウィジェットの基本設定が完了しました")

    def _apply_tree_styles(self):
        """ツリーウィジェットのスタイルを適用します"""
        self.tree_widget.setStyleSheet(
            """
            QTreeWidget {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-size: 9pt;
            }

            QTreeWidget::item {
                height: 24px;
                padding: 2px;
            }

            QTreeWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }

            QTreeWidget::item:hover {
                background-color: #f0f0f0;
            }
        """
        )

    # シグナル関連メソッドはSignalManagerに移動済み

    def cleanup(self):
        """リソースをクリーンアップします"""
        # ショートカット関連はSignalManagerに移動済み
        self.logger.debug("UIセットアップマネージャーがクリーンアップされました")
