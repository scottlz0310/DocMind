#!/usr/bin/env python3
"""
DocMind フォルダツリーアイテム

QTreeWidgetItemを拡張したフォルダツリー専用アイテムクラスを提供します。
"""

import os

from PySide6.QtWidgets import QApplication, QTreeWidgetItem

from .folder_item_type import FolderItemType


class FolderTreeItem(QTreeWidgetItem):
    """
    フォルダツリーアイテムの拡張クラス

    フォルダパス、種類、統計情報などの追加データを保持し、
    フォルダツリー表示に特化した機能を提供します。
    """

    def __init__(self, parent: QTreeWidgetItem | None = None):
        """
        フォルダツリーアイテムを初期化します

        Args:
            parent: 親アイテム
        """
        super().__init__(parent)

        # フォルダ情報
        self.folder_path: str = ""
        self.item_type: FolderItemType = FolderItemType.FOLDER

        # 統計情報
        self.file_count: int = 0
        self.indexed_count: int = 0

        # 状態フラグ
        self.is_expanded_once: bool = False  # 遅延読み込み用フラグ
        self.is_accessible: bool = True  # アクセス可能かどうか

    def set_folder_data(
        self, path: str, item_type: FolderItemType = FolderItemType.FOLDER
    ):
        """
        フォルダデータを設定します

        Args:
            path: フォルダパス
            item_type: アイテムの種類
        """
        self.folder_path = path
        self.item_type = item_type

        # 表示名を設定
        folder_name = self._get_display_name(path)
        self.setText(0, folder_name)

        # ツールチップを設定
        self.setToolTip(0, path)

        # アイコンを更新
        self._update_icon()

    def _get_display_name(self, path: str) -> str:
        """
        パスから表示名を生成します

        Args:
            path: フォルダパス

        Returns:
            表示名
        """
        if not path:
            return "ルート"

        folder_name = os.path.basename(path)
        if not folder_name:
            # ドライブルートの場合
            return path

        return folder_name

    def _update_icon(self):
        """アイテムのアイコンを更新します"""
        app = QApplication.instance()
        if not app:
            return

        style = app.style()

        # アイテムタイプに応じてアイコンを設定
        icon_map = {
            FolderItemType.ROOT: style.StandardPixmap.SP_DriveHDIcon,
            FolderItemType.INDEXING: style.StandardPixmap.SP_BrowserReload,
            FolderItemType.INDEXED: style.StandardPixmap.SP_DirOpenIcon,
            FolderItemType.EXCLUDED: style.StandardPixmap.SP_DialogCancelButton,
            FolderItemType.ERROR: style.StandardPixmap.SP_MessageBoxCritical,
            FolderItemType.FOLDER: style.StandardPixmap.SP_DirClosedIcon,
        }

        pixmap = icon_map.get(self.item_type, style.StandardPixmap.SP_DirClosedIcon)
        icon = style.standardIcon(pixmap)
        self.setIcon(0, icon)

    def update_statistics(self, file_count: int, indexed_count: int):
        """
        統計情報を更新します

        Args:
            file_count: ファイル数
            indexed_count: インデックス済みファイル数
        """
        self.file_count = file_count
        self.indexed_count = indexed_count

        # 表示テキストを更新（ファイル数を含む）
        base_name = self._get_display_name(self.folder_path)

        if file_count > 0:
            if indexed_count > 0 and indexed_count != file_count:
                display_text = f"{base_name} ({indexed_count}/{file_count})"
            else:
                display_text = f"{base_name} ({file_count})"
        else:
            display_text = base_name

        self.setText(0, display_text)

    def set_processing_state(self, is_processing: bool = True):
        """
        処理中状態を設定します

        Args:
            is_processing: 処理中かどうか
        """
        if is_processing:
            self.item_type = FolderItemType.INDEXING
            base_name = self._get_display_name(self.folder_path)
            self.setText(0, f"{base_name} (処理中...)")
        else:
            self.item_type = FolderItemType.FOLDER
            self.setText(0, self._get_display_name(self.folder_path))

        self._update_icon()

    def set_indexed_state(self, file_count: int = 0, indexed_count: int = 0):
        """
        インデックス済み状態を設定します

        Args:
            file_count: 総ファイル数
            indexed_count: インデックス済みファイル数
        """
        self.item_type = FolderItemType.INDEXED
        self.update_statistics(file_count, indexed_count)
        self._update_icon()

    def set_excluded_state(self):
        """除外状態を設定します"""
        self.item_type = FolderItemType.EXCLUDED
        self._update_icon()

    def set_error_state(self, error_message: str = ""):
        """
        エラー状態を設定します

        Args:
            error_message: エラーメッセージ
        """
        self.item_type = FolderItemType.ERROR
        self.is_accessible = False

        # エラー表示テキストを更新
        base_name = self._get_display_name(self.folder_path)
        self.setText(0, f"{base_name} (エラー)")

        # ツールチップにエラーメッセージを設定
        if error_message:
            self.setToolTip(0, f"{self.folder_path}\nエラー: {error_message}")

        self._update_icon()

    def clear_state(self):
        """状態をクリアして通常状態に戻します"""
        self.item_type = FolderItemType.FOLDER
        self.is_accessible = True
        self.file_count = 0
        self.indexed_count = 0

        # 表示テキストを通常に戻す
        self.setText(0, self._get_display_name(self.folder_path))
        self.setToolTip(0, self.folder_path)

        self._update_icon()

    def get_state_info(self) -> dict:
        """
        現在の状態情報を取得します

        Returns:
            状態情報の辞書
        """
        return {
            "path": self.folder_path,
            "type": self.item_type,
            "file_count": self.file_count,
            "indexed_count": self.indexed_count,
            "is_accessible": self.is_accessible,
            "is_expanded_once": self.is_expanded_once,
            "display_name": self.text(0),
        }

    def is_processing(self) -> bool:
        """処理中状態かどうかを判定します"""
        return self.item_type.is_processing()

    def is_available(self) -> bool:
        """利用可能状態かどうかを判定します"""
        return self.item_type.is_available() and self.is_accessible

    def is_error_state(self) -> bool:
        """エラー状態かどうかを判定します"""
        return self.item_type.is_error_state()

    def is_excluded(self) -> bool:
        """除外状態かどうかを判定します"""
        return self.item_type.is_excluded()
