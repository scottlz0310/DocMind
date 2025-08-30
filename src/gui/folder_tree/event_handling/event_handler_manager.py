#!/usr/bin/env python3
"""
DocMind フォルダツリー イベントハンドラーマネージャー

フォルダツリーウィジェットのイベントハンドラー処理を管理します。
"""

import logging
import os

from PySide6.QtWidgets import QTreeWidgetItem


class EventHandlerManager:
    """
    フォルダツリーのイベントハンドラー管理クラス

    選択変更、アイテム展開/折りたたみ、ダブルクリック、
    フォルダ読み込み完了などのイベント処理を管理します。
    """

    def __init__(self, tree_widget):
        """
        イベントハンドラーマネージャーの初期化

        Args:
            tree_widget: フォルダツリーウィジェット
        """
        self.tree_widget = tree_widget
        self.logger = logging.getLogger(__name__)

        self.logger.debug("EventHandlerManagerが初期化されました")

    def on_selection_changed(self):
        """選択変更時の処理"""
        from ..state_management import FolderTreeItem

        current_item = self.tree_widget.currentItem()
        if isinstance(current_item, FolderTreeItem) and current_item.folder_path:
            self.logger.debug(f"フォルダが選択されました: {current_item.folder_path}")
            self.tree_widget.folder_selected.emit(current_item.folder_path)

    def on_item_expanded(self, item: QTreeWidgetItem):
        """アイテム展開時の処理"""
        from ..state_management import FolderTreeItem

        if isinstance(item, FolderTreeItem):
            self.tree_widget.expanded_paths.add(item.folder_path)

            # 遅延読み込み: 初回展開時にサブフォルダを読み込み
            if not item.is_expanded_once and item.childCount() == 0:
                item.is_expanded_once = True
                self.tree_widget._load_subfolders_async(item.folder_path)

    def on_item_collapsed(self, item: QTreeWidgetItem):
        """アイテム折りたたみ時の処理"""
        from ..state_management import FolderTreeItem

        if isinstance(item, FolderTreeItem):
            self.tree_widget.expanded_paths.discard(item.folder_path)

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """アイテムダブルクリック時の処理"""
        from ..state_management import FolderTreeItem

        if isinstance(item, FolderTreeItem) and item.folder_path:
            self.logger.debug(f"フォルダがダブルクリックされました: {item.folder_path}")
            self.tree_widget.folder_selected.emit(item.folder_path)

    def on_folder_loaded(self, path: str, subdirectories: list[str]):
        """
        フォルダ読み込み完了時の処理

        Args:
            path: 読み込まれたパス
            subdirectories: サブディレクトリのリスト
        """
        from ..state_management import FolderItemType, FolderTreeItem

        parent_item = self.tree_widget.item_map.get(path)
        if not parent_item:
            return

        # サブディレクトリをアイテムとして追加
        for subdir in sorted(subdirectories):
            if subdir not in self.tree_widget.item_map:
                child_item = FolderTreeItem(parent_item)
                child_item.set_folder_data(subdir)
                self.tree_widget.item_map[subdir] = child_item

                # インデックス状態を反映
                if subdir in self.tree_widget.indexing_paths:
                    child_item.item_type = FolderItemType.INDEXING
                    child_item._update_icon()
                elif subdir in self.tree_widget.indexed_paths:
                    child_item.item_type = FolderItemType.INDEXED
                    child_item._update_icon()
                elif subdir in self.tree_widget.excluded_paths:
                    child_item.item_type = FolderItemType.EXCLUDED
                    child_item._update_icon()
                elif subdir in self.tree_widget.error_paths:
                    child_item.item_type = FolderItemType.ERROR
                    child_item._update_icon()

    def on_load_error(self, path: str, error_message: str):
        """
        フォルダ読み込みエラー時の処理

        Args:
            path: エラーが発生したパス
            error_message: エラーメッセージ
        """
        self.logger.warning(f"フォルダ読み込みエラー [{path}]: {error_message}")

        # エラーアイテムにマークを付ける
        item = self.tree_widget.item_map.get(path)
        if item:
            item.is_accessible = False
            item.setDisabled(True)
            item.setToolTip(0, f"{path}\n{error_message}")

    def on_load_finished(self):
        """フォルダ読み込み完了時の処理"""
        self.logger.info("フォルダ構造の読み込みが完了しました")

        # 統計情報を更新
        self._update_statistics()

    def _update_statistics(self):
        """各フォルダの統計情報を更新します"""
        # TODO: 実際のファイル数とインデックス数を取得して更新
        # 現在はプレースホルダー実装
        for path, item in self.tree_widget.item_map.items():
            if os.path.exists(path):
                try:
                    file_count = len(
                        [
                            f
                            for f in os.listdir(path)
                            if os.path.isfile(os.path.join(path, f))
                        ]
                    )
                    indexed_count = (
                        file_count if path in self.tree_widget.indexed_paths else 0
                    )
                    item.update_statistics(file_count, indexed_count)
                except (PermissionError, OSError):
                    item.update_statistics(0, 0)

    def cleanup(self):
        """クリーンアップ処理"""
        self.logger.debug("EventHandlerManagerをクリーンアップしました")
