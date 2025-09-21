#!/usr/bin/env python3
"""
DocMind フォルダツリーコンテキストメニューマネージャー

フォルダツリーのコンテキストメニュー機能を管理します。
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMenu, QMessageBox

if TYPE_CHECKING:
    from ..folder_tree_widget import FolderTreeWidget
    from ..state_management import FolderTreeItem


class ContextMenuManager:
    """
    フォルダツリーのコンテキストメニューを管理するクラス

    右クリックメニューの表示、アクション処理、プロパティ表示を担当します。
    """

    def __init__(self, tree_widget: "FolderTreeWidget"):
        """
        コンテキストメニューマネージャーの初期化

        Args:
            tree_widget: 管理対象のフォルダツリーウィジェット
        """
        self.tree_widget = tree_widget
        self.logger = logging.getLogger(__name__)

        # アクション参照を保持
        self.actions = {}

        self._create_actions()
        self.logger.debug("コンテキストメニューマネージャーが初期化されました")

    def _create_actions(self):
        """コンテキストメニューアクションを作成します"""
        # フォルダ操作アクション
        self.actions["add_folder"] = QAction("フォルダを追加...", self.tree_widget)
        self.actions["add_folder"].triggered.connect(self._add_folder)

        self.actions["remove_folder"] = QAction("フォルダを削除", self.tree_widget)
        self.actions["remove_folder"].triggered.connect(self._remove_folder)

        # インデックス操作アクション
        self.actions["index_folder"] = QAction("インデックスに追加", self.tree_widget)
        self.actions["index_folder"].triggered.connect(self._index_folder)

        self.actions["exclude_folder"] = QAction("フォルダを除外", self.tree_widget)
        self.actions["exclude_folder"].triggered.connect(self._exclude_folder)

        # 表示操作アクション
        self.actions["refresh"] = QAction("更新", self.tree_widget)
        self.actions["refresh"].triggered.connect(self._refresh_folder)

        self.actions["expand_all"] = QAction("すべて展開", self.tree_widget)
        self.actions["expand_all"].triggered.connect(self.tree_widget.expandAll)

        self.actions["collapse_all"] = QAction("すべて折りたたみ", self.tree_widget)
        self.actions["collapse_all"].triggered.connect(self.tree_widget.collapseAll)

        # 情報表示アクション
        self.actions["properties"] = QAction("プロパティ...", self.tree_widget)
        self.actions["properties"].triggered.connect(self._show_properties)

    def setup_context_menu(self):
        """コンテキストメニューを設定します"""
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.logger.debug("コンテキストメニューが設定されました")

    def show_context_menu(self, position):
        """コンテキストメニューを表示します"""
        from ..state_management import FolderTreeItem

        item = self.tree_widget.itemAt(position)
        menu = QMenu(self.tree_widget)

        if isinstance(item, FolderTreeItem):
            # フォルダアイテムが選択されている場合
            self._build_folder_menu(menu, item)
        else:
            # 空白部分が選択されている場合
            self._build_empty_menu(menu)

        # メニューを表示
        menu.exec(self.tree_widget.mapToGlobal(position))

    def _build_folder_menu(self, menu: QMenu, item: "FolderTreeItem"):
        """フォルダアイテム用のメニューを構築します"""
        # インデックス操作
        menu.addAction(self.actions["index_folder"])
        menu.addAction(self.actions["exclude_folder"])
        menu.addSeparator()

        # フォルダ操作
        menu.addAction(self.actions["remove_folder"])
        menu.addSeparator()

        # 表示操作
        menu.addAction(self.actions["refresh"])
        menu.addSeparator()
        menu.addAction(self.actions["expand_all"])
        menu.addAction(self.actions["collapse_all"])
        menu.addSeparator()

        # 情報表示
        menu.addAction(self.actions["properties"])

        # アクションの有効/無効を設定
        self._update_action_states(item)

    def _build_empty_menu(self, menu: QMenu):
        """空白部分用のメニューを構築します"""
        menu.addAction(self.actions["add_folder"])
        menu.addSeparator()
        menu.addAction(self.actions["refresh"])
        menu.addSeparator()
        menu.addAction(self.actions["expand_all"])
        menu.addAction(self.actions["collapse_all"])

    def _update_action_states(self, item: "FolderTreeItem"):
        """アクションの有効/無効状態を更新します"""
        folder_path = item.folder_path

        # 状態チェック
        is_indexing = folder_path in self.tree_widget.indexing_paths
        is_indexed = folder_path in self.tree_widget.indexed_paths
        is_excluded = folder_path in self.tree_widget.excluded_paths
        is_root = folder_path in self.tree_widget.root_paths

        # アクション状態を設定
        self.actions["index_folder"].setEnabled(
            not is_indexing and not is_indexed and not is_excluded
        )
        self.actions["exclude_folder"].setEnabled(not is_indexing and not is_excluded)
        self.actions["remove_folder"].setEnabled(is_root)

    # アクション実装メソッド

    def _add_folder(self):
        """フォルダを追加します"""
        try:
            folder_path = QFileDialog.getExistingDirectory(
                self.tree_widget,
                "追加するフォルダを選択",
                str(Path.home()),
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
            )

            if folder_path:
                self.tree_widget.load_folder_structure(folder_path)
                self.logger.info(f"フォルダが追加されました: {folder_path}")
        except Exception as e:
            self.logger.error(f"フォルダ追加中にエラーが発生しました: {e}")
            QMessageBox.critical(
                self.tree_widget, "エラー", f"フォルダの追加に失敗しました:\n{str(e)}"
            )

    def _remove_folder(self):
        """選択されたフォルダを削除します"""
        from ..state_management import FolderTreeItem

        current_item = self.tree_widget.currentItem()
        if not isinstance(current_item, FolderTreeItem):
            return

        folder_path = current_item.folder_path
        if folder_path not in self.tree_widget.root_paths:
            QMessageBox.information(
                self.tree_widget, "情報", "ルートフォルダのみ削除できます。"
            )
            return

        reply = QMessageBox.question(
            self.tree_widget,
            "フォルダ削除",
            f"以下のフォルダをツリーから削除しますか?\n\n{folder_path}\n\n"
            "※ファイルシステムからは削除されません。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # ツリーから削除
            index = self.tree_widget.indexOfTopLevelItem(current_item)
            if index >= 0:
                self.tree_widget.takeTopLevelItem(index)

            # 内部状態から削除
            self.tree_widget.root_paths.remove(folder_path)
            self.tree_widget._remove_from_maps(folder_path)

            self.logger.info(f"フォルダが削除されました: {folder_path}")

    def _index_folder(self):
        """選択されたフォルダをインデックスに追加します"""
        from ..state_management import FolderTreeItem

        current_item = self.tree_widget.currentItem()
        if not isinstance(current_item, FolderTreeItem):
            return

        folder_path = current_item.folder_path

        reply = QMessageBox.question(
            self.tree_widget,
            "インデックス追加",
            f"以下のフォルダをインデックスに追加しますか?\n\n{folder_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        if reply == QMessageBox.Yes:
            # インデックス処理開始時はINDEXING状態に設定
            self.tree_widget.set_folder_indexing(folder_path)

            # シグナルを発行
            self.tree_widget.folder_indexed.emit(folder_path)

            self.logger.info(f"フォルダのインデックス処理を開始: {folder_path}")

    def _exclude_folder(self):
        """選択されたフォルダを除外します"""
        from ..state_management import FolderItemType, FolderTreeItem

        current_item = self.tree_widget.currentItem()
        if not isinstance(current_item, FolderTreeItem):
            return

        folder_path = current_item.folder_path

        reply = QMessageBox.question(
            self.tree_widget,
            "フォルダ除外",
            f"以下のフォルダを検索対象から除外しますか?\n\n{folder_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.tree_widget.excluded_paths.add(folder_path)
            self.tree_widget.indexed_paths.discard(
                folder_path
            )  # インデックスリストから削除

            # アイテムの表示を更新
            current_item.item_type = FolderItemType.EXCLUDED
            current_item._update_icon()

            # シグナルを発行
            self.tree_widget.folder_excluded.emit(folder_path)

            self.logger.info(f"フォルダが除外されました: {folder_path}")

    def _refresh_folder(self):
        """選択されたフォルダまたは全体を更新します"""
        # ActionManagerに委譲
        self.tree_widget.action_manager.refresh_folder()
        self.tree_widget.refresh_requested.emit()

    def _show_properties(self):
        """選択されたフォルダのプロパティを表示します"""
        from ..state_management import FolderTreeItem

        current_item = self.tree_widget.currentItem()
        if not isinstance(current_item, FolderTreeItem):
            return

        folder_path = current_item.folder_path

        try:
            # フォルダ情報を取得
            stat_info = os.stat(folder_path)

            # ファイル数を計算
            file_count = 0
            dir_count = 0
            total_size = 0

            for root, dirs, files in os.walk(folder_path):
                file_count += len(files)
                dir_count += len(dirs)
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except (OSError, PermissionError):
                        pass

            # サイズを人間が読みやすい形式に変換
            def format_size(size_bytes):
                if size_bytes == 0:
                    return "0 B"
                size_names = ["B", "KB", "MB", "GB", "TB"]
                import math

                i = int(math.floor(math.log(size_bytes, 1024)))
                p = math.pow(1024, i)
                s = round(size_bytes / p, 2)
                return f"{s} {size_names[i]}"

            # プロパティダイアログを表示
            modified_time = datetime.fromtimestamp(stat_info.st_mtime)

            properties_text = f"""
フォルダ: {os.path.basename(folder_path)}
パス: {folder_path}

統計情報:
  ファイル数: {file_count:,}
  フォルダ数: {dir_count:,}
  合計サイズ: {format_size(total_size)}

最終更新: {modified_time.strftime("%Y/%m/%d %H:%M:%S")}

インデックス状態: {"インデックス済み" if folder_path in self.tree_widget.indexed_paths else "未インデックス"}
除外状態: {"除外中" if folder_path in self.tree_widget.excluded_paths else "対象"}
            """.strip()

            QMessageBox.information(
                self.tree_widget, "フォルダプロパティ", properties_text
            )

        except Exception as e:
            QMessageBox.warning(
                self.tree_widget,
                "エラー",
                f"フォルダ情報の取得に失敗しました:\n{str(e)}",
            )

    def cleanup(self):
        """リソースをクリーンアップします"""
        # アクションを削除
        for action in self.actions.values():
            if action:
                action.deleteLater()
        self.actions.clear()

        self.logger.debug("コンテキストメニューマネージャーがクリーンアップされました")
