#!/usr/bin/env python3
"""
DocMind フォルダツリーフィルターマネージャー

フォルダツリーのフィルタリング機能を管理します。
"""

import logging
import os
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QTreeWidgetItem

if TYPE_CHECKING:
    from ..folder_tree_widget import FolderTreeWidget


class FilterManager:
    """
    フォルダツリーのフィルタリング機能を管理するクラス

    フォルダ名による検索・フィルタリング、表示・非表示制御を担当します。
    """

    def __init__(self, tree_widget: "FolderTreeWidget"):
        """
        フィルターマネージャーの初期化

        Args:
            tree_widget: 管理対象のフォルダツリーウィジェット
        """
        self.tree_widget = tree_widget
        self.logger = logging.getLogger(__name__)

        # フィルター状態
        self.current_filter = ""
        self.is_filtering = False

        self.logger.debug("フィルターマネージャーが初期化されました")

    def filter_folders(self, filter_text: str):
        """
        フォルダをフィルタリングします

        Args:
            filter_text: フィルター文字列
        """
        self.current_filter = filter_text.strip()

        if not self.current_filter:
            # フィルターをクリア
            self.clear_filter()
            return

        self.is_filtering = True
        filter_text_lower = self.current_filter.lower()

        # すべてのアイテムを非表示にしてから、マッチするものだけ表示
        self._hide_all_items()

        # マッチするアイテムを検索して表示
        matched_count = 0
        for path, item in self.tree_widget.item_map.items():
            folder_name = os.path.basename(path).lower()
            if filter_text_lower in folder_name or filter_text_lower in path.lower():
                self._show_item_and_parents(item)
                matched_count += 1

        self.logger.debug(f"フィルタリング完了: '{self.current_filter}' - {matched_count}件マッチ")

    def clear_filter(self):
        """フィルターをクリアして全アイテムを表示します"""
        self.current_filter = ""
        self.is_filtering = False
        self._show_all_items()
        self.logger.debug("フィルターがクリアされました")

    def _hide_all_items(self):
        """すべてのアイテムを非表示にします"""
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item:
                self._hide_item_recursive(item)

    def _hide_item_recursive(self, item: QTreeWidgetItem):
        """アイテムとその子を再帰的に非表示にします"""
        item.setHidden(True)
        for i in range(item.childCount()):
            child = item.child(i)
            if child:
                self._hide_item_recursive(child)

    def _show_all_items(self):
        """すべてのアイテムを表示します"""
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item:
                self._show_item_recursive(item)

    def _show_item_recursive(self, item: QTreeWidgetItem):
        """アイテムとその子を再帰的に表示します"""
        item.setHidden(False)
        for i in range(item.childCount()):
            child = item.child(i)
            if child:
                self._show_item_recursive(child)

    def _show_item_and_parents(self, item: QTreeWidgetItem):
        """アイテムとその親を表示します"""
        current = item
        while current:
            current.setHidden(False)
            current = current.parent()

    def get_filter_status(self) -> dict:
        """
        現在のフィルター状態を取得します

        Returns:
            フィルター状態の辞書
        """
        return {
            "current_filter": self.current_filter,
            "is_filtering": self.is_filtering,
            "visible_items": self._count_visible_items(),
        }

    def _count_visible_items(self) -> int:
        """表示中のアイテム数をカウントします"""
        count = 0
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item:
                count += self._count_visible_recursive(item)
        return count

    def _count_visible_recursive(self, item: QTreeWidgetItem) -> int:
        """再帰的に表示中のアイテム数をカウントします"""
        count = 0 if item.isHidden() else 1
        for i in range(item.childCount()):
            child = item.child(i)
            if child:
                count += self._count_visible_recursive(child)
        return count

    def cleanup(self):
        """リソースをクリーンアップします"""
        self.clear_filter()
        self.logger.debug("フィルターマネージャーがクリーンアップされました")
