#!/usr/bin/env python3
"""
DocMind フォルダツリー アクションマネージャー

フォルダツリーウィジェットのアクション処理を管理します。
"""

import logging

from ..state_management import FolderTreeItem


class ActionManager:
    """
    フォルダツリーのアクション管理クラス

    フォルダの更新、選択、リフレッシュなどの
    ユーザーアクション処理を管理します。
    """

    def __init__(self, tree_widget):
        """
        アクションマネージャーの初期化

        Args:
            tree_widget: フォルダツリーウィジェット
        """
        self.tree_widget = tree_widget
        self.logger = logging.getLogger(__name__)

        self.logger.debug("ActionManagerが初期化されました")

    def refresh_folder(self):
        """選択されたフォルダまたは全体を更新します"""
        current_item = self.tree_widget.currentItem()

        if isinstance(current_item, FolderTreeItem) and current_item.folder_path:
            # 選択されたフォルダを更新
            self.refresh_specific_folder(current_item.folder_path)
        else:
            # 全体を更新
            self.refresh_all_folders()

    def refresh_specific_folder(self, folder_path: str):
        """
        特定のフォルダを更新します

        Args:
            folder_path: 更新対象のフォルダパス
        """
        item = self.tree_widget.item_map.get(folder_path)
        if not item:
            return

        # 子アイテムを削除
        item.takeChildren()

        # 内部状態をクリア
        paths_to_remove = [
            path
            for path in self.tree_widget.item_map.keys()
            if path.startswith(folder_path) and path != folder_path
        ]
        for path in paths_to_remove:
            self.tree_widget.item_map.pop(path, None)

        # 再読み込み
        item.is_expanded_once = False
        if item.isExpanded():
            self.tree_widget._load_subfolders_async(folder_path)

        self.logger.info(f"フォルダが更新されました: {folder_path}")

    def refresh_all_folders(self):
        """すべてのルートフォルダを更新します"""
        root_paths = self.tree_widget.root_paths.copy()  # コピーを作成

        # ツリーをクリア
        self.tree_widget.clear()
        self.tree_widget.item_map.clear()
        self.tree_widget.expanded_paths.clear()
        self.tree_widget.indexing_paths.clear()
        self.tree_widget.indexed_paths.clear()
        self.tree_widget.excluded_paths.clear()
        self.tree_widget.error_paths.clear()
        self.tree_widget.root_paths.clear()

        # 各ルートフォルダを再読み込み
        for root_path in root_paths:
            self.tree_widget.load_folder_structure(root_path)

        self.logger.info("すべてのフォルダが更新されました")

    def select_current_folder(self):
        """現在選択されているフォルダを選択シグナルで通知します"""
        current_item = self.tree_widget.currentItem()
        if isinstance(current_item, FolderTreeItem) and current_item.folder_path:
            self.tree_widget.folder_selected.emit(current_item.folder_path)

    def expand_to_path(self, path: str):
        """
        指定されたパスまでツリーを展開します

        Args:
            path: 展開対象のパス
        """
        item = self.tree_widget.item_map.get(path)
        if item:
            # 親アイテムを順次展開
            parent = item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()

            # アイテムを選択
            self.tree_widget.setCurrentItem(item)
            self.tree_widget.scrollToItem(item)

            self.logger.debug(f"パスまで展開しました: {path}")

    def select_folder_by_path(self, path: str) -> bool:
        """
        指定されたパスのフォルダを選択します

        Args:
            path: 選択対象のフォルダパス

        Returns:
            選択に成功した場合True
        """
        item = self.tree_widget.item_map.get(path)
        if item:
            self.tree_widget.setCurrentItem(item)
            self.tree_widget.scrollToItem(item)
            self.tree_widget.folder_selected.emit(path)
            self.logger.debug(f"フォルダを選択しました: {path}")
            return True

        self.logger.warning(f"フォルダが見つかりません: {path}")
        return False

    def get_selected_folder_path(self) -> str | None:
        """
        現在選択されているフォルダのパスを取得します

        Returns:
            選択されているフォルダのパス、または None
        """
        current_item = self.tree_widget.currentItem()
        if isinstance(current_item, FolderTreeItem):
            return current_item.folder_path
        return None

    def cleanup(self):
        """クリーンアップ処理"""
        self.logger.debug("ActionManagerをクリーンアップしました")
