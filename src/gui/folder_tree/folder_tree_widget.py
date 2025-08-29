#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind フォルダツリーナビゲーションウィジェット

QTreeWidgetを拡張したフォルダツリーナビゲーション機能を提供します。
フォルダ構造の表示、選択、展開、コンテキストメニュー、フィルタリング機能を実装します。
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Set
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QMenu, QMessageBox, QFileDialog,
    QLabel
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut

# 新しいコンポーネントをインポート
from ..folder_tree_components import AsyncOperationManager
from .state_management import FolderItemType, FolderTreeItem
from .ui_management import UISetupManager, FilterManager, ContextMenuManager


class FolderTreeWidget(QTreeWidget):
    """
    フォルダツリーナビゲーションウィジェット
    
    QTreeWidgetを拡張して、フォルダ構造の表示、選択、展開、
    コンテキストメニュー、フィルタリング機能を提供します。
    """
    
    # シグナル定義
    folder_selected = Signal(str)           # フォルダが選択された時
    folder_indexed = Signal(str)            # フォルダのインデックス要求
    folder_excluded = Signal(str)           # フォルダの除外要求
    refresh_requested = Signal()            # リフレッシュ要求
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        フォルダツリーウィジェットの初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        
        # 内部状態
        self.root_paths: List[str] = []                    # ルートパスのリスト
        self.expanded_paths: Set[str] = set()              # 展開済みパスのセット
        self.indexing_paths: Set[str] = set()              # インデックス処理中パスのセット
        self.indexed_paths: Set[str] = set()               # インデックス済みパスのセット
        self.excluded_paths: Set[str] = set()              # 除外パスのセット
        self.error_paths: Set[str] = set()                 # エラー状態パスのセット
        self.item_map: Dict[str, FolderTreeItem] = {}      # パス→アイテムのマッピング
        
        # 非同期処理管理
        self.async_manager = AsyncOperationManager(self)
        
        # UI管理コンポーネント
        self.ui_setup_manager = UISetupManager(self)
        self.filter_manager = FilterManager(self)
        self.context_menu_manager = ContextMenuManager(self)
        
        # UI設定
        self.ui_setup_manager.setup_tree_widget()
        self.context_menu_manager.setup_context_menu()
        self.ui_setup_manager.setup_shortcuts()
        self.ui_setup_manager.setup_tree_signals()
        self.ui_setup_manager.setup_async_signals()
        
        self.logger.info("フォルダツリーウィジェットが初期化されました")
    

    

    

    

    
    def load_folder_structure(self, root_path: str) -> None:
        """
        フォルダ構造を読み込みます
        
        Args:
            root_path: ルートフォルダのパス
        """
        try:
            if not os.path.exists(root_path) or not os.path.isdir(root_path):
                self.logger.error(f"無効なフォルダパス: {root_path}")
                QMessageBox.warning(
                    self,
                    "エラー",
                    f"指定されたフォルダが見つかりません:\n{root_path}"
                )
                return
            
            # 既存の非同期処理を停止
            self.async_manager.cleanup_workers()
            
            # 既存のフォルダを保持するかチェック
            if root_path in self.root_paths:
                self.logger.info(f"フォルダは既に追加されています: {root_path}")
                return
            
            # ルートアイテムを作成
            root_item = FolderTreeItem()
            root_item.set_folder_data(root_path, FolderItemType.ROOT)
            self.addTopLevelItem(root_item)
            self.item_map[root_path] = root_item
            
            # ルートパスを記録
            self.root_paths.append(root_path)
            
            # 非同期でサブフォルダを読み込み
            self._load_subfolders_async(root_path)
            
            # ルートアイテムを展開
            root_item.setExpanded(True)
            
            self.logger.info(f"フォルダ構造の読み込み完了: {root_path}")
            
        except Exception as e:
            self.logger.error(f"フォルダ構造の読み込み中にエラーが発生しました: {e}")
            QMessageBox.critical(
                self,
                "エラー",
                f"フォルダ構造の読み込みに失敗しました:\n{str(e)}"
            )
            # エラーが発生した場合は、追加されたパスを削除
            if root_path in self.root_paths:
                self.root_paths.remove(root_path)
            if root_path in self.item_map:
                self.item_map.pop(root_path, None)
    
    def _load_subfolders_async(self, path: str):
        """
        サブフォルダを非同期で読み込みます
        
        Args:
            path: 読み込み対象パス
        """
        try:
            # 非同期処理マネージャーを使用
            self.async_manager.start_folder_loading(path, max_depth=2)
            
        except Exception as e:
            self.logger.error(f"サブフォルダの非同期読み込み開始エラー: {e}")
    
    def _on_folder_loaded(self, path: str, subdirectories: List[str]):
        """
        フォルダ読み込み完了時の処理
        
        Args:
            path: 読み込まれたパス
            subdirectories: サブディレクトリのリスト
        """
        parent_item = self.item_map.get(path)
        if not parent_item:
            return
        
        # サブディレクトリをアイテムとして追加
        for subdir in sorted(subdirectories):
            if subdir not in self.item_map:
                child_item = FolderTreeItem(parent_item)
                child_item.set_folder_data(subdir)
                self.item_map[subdir] = child_item
                
                # インデックス状態を反映
                if subdir in self.indexing_paths:
                    child_item.item_type = FolderItemType.INDEXING
                    child_item._update_icon()
                elif subdir in self.indexed_paths:
                    child_item.item_type = FolderItemType.INDEXED
                    child_item._update_icon()
                elif subdir in self.excluded_paths:
                    child_item.item_type = FolderItemType.EXCLUDED
                    child_item._update_icon()
                elif subdir in self.error_paths:
                    child_item.item_type = FolderItemType.ERROR
                    child_item._update_icon()
    
    def _on_load_error(self, path: str, error_message: str):
        """
        フォルダ読み込みエラー時の処理
        
        Args:
            path: エラーが発生したパス
            error_message: エラーメッセージ
        """
        self.logger.warning(f"フォルダ読み込みエラー [{path}]: {error_message}")
        
        # エラーアイテムにマークを付ける
        item = self.item_map.get(path)
        if item:
            item.is_accessible = False
            item.setDisabled(True)
            item.setToolTip(0, f"{path}\n{error_message}")
    
    def _cleanup_workers(self):
        """非同期処理をクリーンアップします"""
        self.async_manager.cleanup_workers()
    
    def _on_load_finished(self):
        """フォルダ読み込み完了時の処理"""
        self.logger.info("フォルダ構造の読み込みが完了しました")
        
        # 統計情報を更新
        self._update_statistics()
    
    def _update_statistics(self):
        """各フォルダの統計情報を更新します"""
        # TODO: 実際のファイル数とインデックス数を取得して更新
        # 現在はプレースホルダー実装
        for path, item in self.item_map.items():
            if os.path.exists(path):
                try:
                    file_count = len([f for f in os.listdir(path) 
                                    if os.path.isfile(os.path.join(path, f))])
                    indexed_count = file_count if path in self.indexed_paths else 0
                    item.update_statistics(file_count, indexed_count)
                except (PermissionError, OSError):
                    item.update_statistics(0, 0)    

    # イベントハンドラー
    
    def _on_selection_changed(self):
        """選択変更時の処理"""
        current_item = self.currentItem()
        if isinstance(current_item, FolderTreeItem) and current_item.folder_path:
            self.logger.debug(f"フォルダが選択されました: {current_item.folder_path}")
            self.folder_selected.emit(current_item.folder_path)
    
    def _on_item_expanded(self, item: QTreeWidgetItem):
        """アイテム展開時の処理"""
        if isinstance(item, FolderTreeItem):
            self.expanded_paths.add(item.folder_path)
            
            # 遅延読み込み: 初回展開時にサブフォルダを読み込み
            if not item.is_expanded_once and item.childCount() == 0:
                item.is_expanded_once = True
                self._load_subfolders_async(item.folder_path)
    
    def _on_item_collapsed(self, item: QTreeWidgetItem):
        """アイテム折りたたみ時の処理"""
        if isinstance(item, FolderTreeItem):
            self.expanded_paths.discard(item.folder_path)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """アイテムダブルクリック時の処理"""
        if isinstance(item, FolderTreeItem) and item.folder_path:
            self.logger.debug(f"フォルダがダブルクリックされました: {item.folder_path}")
            self.folder_selected.emit(item.folder_path)
    
    # コンテキストメニュー関連
    
    def _show_context_menu(self, position):
        """コンテキストメニューを表示します"""
        self.context_menu_manager.show_context_menu(position)
    
    # コンテキストメニューアクション
    

    

    
    def _remove_from_maps(self, root_path: str):
        """指定されたルートパス以下のアイテムを内部マップから削除します"""
        paths_to_remove = [path for path in self.item_map.keys() 
                          if path.startswith(root_path)]
        
        for path in paths_to_remove:
            self.item_map.pop(path, None)
            self.expanded_paths.discard(path)
            self.indexing_paths.discard(path)
            self.indexed_paths.discard(path)
            self.excluded_paths.discard(path)
            self.error_paths.discard(path)
    

    

    
    def _refresh_folder(self):
        """選択されたフォルダまたは全体を更新します"""
        self.context_menu_manager._refresh_folder()
    
    def _refresh_specific_folder(self, folder_path: str):
        """特定のフォルダを更新します"""
        item = self.item_map.get(folder_path)
        if not item:
            return
        
        # 子アイテムを削除
        item.takeChildren()
        
        # 内部状態をクリア
        paths_to_remove = [path for path in self.item_map.keys() 
                          if path.startswith(folder_path) and path != folder_path]
        for path in paths_to_remove:
            self.item_map.pop(path, None)
        
        # 再読み込み
        item.is_expanded_once = False
        if item.isExpanded():
            self._load_subfolders_async(folder_path)
        
        self.logger.info(f"フォルダが更新されました: {folder_path}")
    
    def _refresh_all_folders(self):
        """すべてのルートフォルダを更新します"""
        root_paths = self.root_paths.copy()  # コピーを作成
        
        # ツリーをクリア
        self.clear()
        self.item_map.clear()
        self.expanded_paths.clear()
        self.indexing_paths.clear()
        self.indexed_paths.clear()
        self.excluded_paths.clear()
        self.error_paths.clear()
        self.root_paths.clear()
        
        # 各ルートフォルダを再読み込み
        for root_path in root_paths:
            self.load_folder_structure(root_path)
        
        self.logger.info("すべてのフォルダが更新されました")
    
    def _select_current_folder(self):
        """現在選択されているフォルダを選択シグナルで通知します"""
        current_item = self.currentItem()
        if isinstance(current_item, FolderTreeItem) and current_item.folder_path:
            self.folder_selected.emit(current_item.folder_path)
    

    
    # フィルタリング機能
    
    def filter_folders(self, filter_text: str):
        """
        フォルダをフィルタリングします
        
        Args:
            filter_text: フィルター文字列
        """
        self.filter_manager.filter_folders(filter_text)
    

    
    # パブリックメソッド
    
    def get_selected_folder(self) -> Optional[str]:
        """
        現在選択されているフォルダのパスを取得します
        
        Returns:
            選択されているフォルダのパス、または None
        """
        current_item = self.currentItem()
        if isinstance(current_item, FolderTreeItem):
            return current_item.folder_path
        return None
    
    def get_indexed_folders(self) -> List[str]:
        """
        インデックス済みフォルダのリストを取得します
        
        Returns:
            インデックス済みフォルダパスのリスト
        """
        return list(self.indexed_paths)
    
    def get_excluded_folders(self) -> List[str]:
        """
        除外フォルダのリストを取得します
        
        Returns:
            除外フォルダパスのリスト
        """
        return list(self.excluded_paths)
    
    def set_indexed_folders(self, paths: List[str]):
        """
        インデックス済みフォルダを設定します
        
        Args:
            paths: インデックス済みフォルダパスのリスト
        """
        self.indexed_paths = set(paths)
        self._update_item_types()
    
    def set_excluded_folders(self, paths: List[str]):
        """
        除外フォルダを設定します
        
        Args:
            paths: 除外フォルダパスのリスト
        """
        self.excluded_paths = set(paths)
        self._update_item_types()
    
    def _update_item_types(self):
        """アイテムの種類表示を更新します"""
        for path, item in self.item_map.items():
            if path in self.indexing_paths:
                item.item_type = FolderItemType.INDEXING
            elif path in self.indexed_paths:
                item.item_type = FolderItemType.INDEXED
            elif path in self.excluded_paths:
                item.item_type = FolderItemType.EXCLUDED
            elif path in self.error_paths:
                item.item_type = FolderItemType.ERROR
            else:
                item.item_type = FolderItemType.FOLDER
            
            item._update_icon()
    
    def set_folder_indexing(self, folder_path: str):
        """
        フォルダをインデックス処理中状態に設定します
        
        Args:
            folder_path: フォルダパス
        """
        self.indexing_paths.add(folder_path)
        self.indexed_paths.discard(folder_path)
        self.excluded_paths.discard(folder_path)
        self.error_paths.discard(folder_path)
        
        item = self.item_map.get(folder_path)
        if item:
            item.item_type = FolderItemType.INDEXING
            item._update_icon()
            
            # 処理中の表示テキストを更新
            folder_name = os.path.basename(folder_path) if folder_path else "ルート"
            if not folder_name:
                folder_name = folder_path
            item.setText(0, f"{folder_name} (処理中...)")
        
        self.logger.info(f"フォルダをインデックス処理中状態に設定: {folder_path}")
    
    def set_folder_indexed(self, folder_path: str, file_count: int = 0, indexed_count: int = 0):
        """
        フォルダをインデックス済み状態に設定します
        
        Args:
            folder_path: フォルダパス
            file_count: 総ファイル数
            indexed_count: インデックス済みファイル数
        """
        self.indexing_paths.discard(folder_path)
        self.indexed_paths.add(folder_path)
        self.excluded_paths.discard(folder_path)
        self.error_paths.discard(folder_path)
        
        item = self.item_map.get(folder_path)
        if item:
            item.item_type = FolderItemType.INDEXED
            item._update_icon()
            
            # 統計情報を更新
            item.update_statistics(file_count, indexed_count)
        
        self.logger.info(f"フォルダをインデックス済み状態に設定: {folder_path} ({indexed_count}/{file_count})")
    
    def set_folder_error(self, folder_path: str, error_message: str = ""):
        """
        フォルダをエラー状態に設定します
        
        Args:
            folder_path: フォルダパス
            error_message: エラーメッセージ
        """
        self.indexing_paths.discard(folder_path)
        self.indexed_paths.discard(folder_path)
        self.excluded_paths.discard(folder_path)
        self.error_paths.add(folder_path)
        
        item = self.item_map.get(folder_path)
        if item:
            item.item_type = FolderItemType.ERROR
            item._update_icon()
            
            # エラー表示テキストを更新
            folder_name = os.path.basename(folder_path) if folder_path else "ルート"
            if not folder_name:
                folder_name = folder_path
            item.setText(0, f"{folder_name} (エラー)")
            
            # ツールチップにエラーメッセージを設定
            if error_message:
                item.setToolTip(0, f"{folder_path}\nエラー: {error_message}")
        
        self.logger.error(f"フォルダをエラー状態に設定: {folder_path} - {error_message}")
    
    def clear_folder_state(self, folder_path: str):
        """
        フォルダの状態をクリアして通常状態に戻します
        
        Args:
            folder_path: フォルダパス
        """
        self.indexing_paths.discard(folder_path)
        self.indexed_paths.discard(folder_path)
        self.excluded_paths.discard(folder_path)
        self.error_paths.discard(folder_path)
        
        item = self.item_map.get(folder_path)
        if item:
            item.item_type = FolderItemType.FOLDER
            item._update_icon()
            
            # 表示テキストを通常に戻す
            folder_name = os.path.basename(folder_path) if folder_path else "ルート"
            if not folder_name:
                folder_name = folder_path
            item.setText(0, folder_name)
            item.setToolTip(0, folder_path)
        
        self.logger.info(f"フォルダ状態をクリア: {folder_path}")
    
    def get_indexing_folders(self) -> List[str]:
        """
        インデックス処理中フォルダのリストを取得します
        
        Returns:
            インデックス処理中フォルダパスのリスト
        """
        return list(self.indexing_paths)
    
    def get_error_folders(self) -> List[str]:
        """
        エラー状態フォルダのリストを取得します
        
        Returns:
            エラー状態フォルダパスのリスト
        """
        return list(self.error_paths)
    
    def expand_to_path(self, path: str):
        """
        指定されたパスまでツリーを展開します
        
        Args:
            path: 展開対象のパス
        """
        item = self.item_map.get(path)
        if item:
            # 親アイテムを順次展開
            parent = item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()
            
            # アイテムを選択
            self.setCurrentItem(item)
            self.scrollToItem(item)
    
    def closeEvent(self, event):
        """ウィジェット終了時の処理"""
        self._cleanup_workers()
        # UI管理コンポーネントのクリーンアップ
        if hasattr(self, 'ui_setup_manager'):
            self.ui_setup_manager.cleanup()
        if hasattr(self, 'filter_manager'):
            self.filter_manager.cleanup()
        if hasattr(self, 'context_menu_manager'):
            self.context_menu_manager.cleanup()
        super().closeEvent(event)
    
    def __del__(self):
        """デストラクタ"""
        self._cleanup_workers()


class FolderTreeContainer(QWidget):
    """
    フォルダツリーウィジェットのコンテナ
    
    検索機能とフィルタリング機能を含む完全なフォルダナビゲーションUIを提供します。
    """
    
    # シグナル定義（FolderTreeWidgetのシグナルを転送）
    folder_selected = Signal(str)
    folder_indexed = Signal(str)
    folder_excluded = Signal(str)
    refresh_requested = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        フォルダツリーコンテナの初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        
        # UI設定
        self._setup_ui()
        
        # シグナル接続
        self._connect_signals()
        
        self.logger.info("フォルダツリーコンテナが初期化されました")
    
    def _setup_ui(self):
        """UIレイアウトを設定します"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # ヘッダー部分
        header_layout = QHBoxLayout()
        
        # タイトルラベル
        title_label = QLabel("フォルダツリー")
        title_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # フォルダ追加ボタン
        self.add_button = QPushButton("追加")
        self.add_button.setToolTip("フォルダを追加します")
        self.add_button.setMaximumWidth(60)
        header_layout.addWidget(self.add_button)
        
        layout.addLayout(header_layout)
        
        # 検索/フィルター部分
        filter_layout = QHBoxLayout()
        
        # フィルター入力
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("フォルダを検索...")
        self.filter_input.setToolTip("フォルダ名でフィルタリングします")
        filter_layout.addWidget(self.filter_input)
        
        # フィルタークリアボタン
        self.clear_filter_button = QPushButton("×")
        self.clear_filter_button.setMaximumWidth(30)
        self.clear_filter_button.setToolTip("フィルターをクリアします")
        filter_layout.addWidget(self.clear_filter_button)
        
        layout.addLayout(filter_layout)
        
        # フォルダツリーウィジェット
        self.tree_widget = FolderTreeWidget()
        layout.addWidget(self.tree_widget)
        
        # フッター部分（統計情報）
        self.stats_label = QLabel("フォルダ: 0, インデックス: 0")
        self.stats_label.setStyleSheet("color: gray; font-size: 8pt;")
        layout.addWidget(self.stats_label)
    
    def _connect_signals(self):
        """シグナルを接続します"""
        # ボタンのシグナル
        self.add_button.clicked.connect(self.tree_widget.context_menu_manager._add_folder)
        self.clear_filter_button.clicked.connect(self._clear_filter)
        
        # フィルター入力のシグナル
        self.filter_input.textChanged.connect(self._on_filter_changed)
        
        # ツリーウィジェットのシグナルを転送
        self.tree_widget.folder_selected.connect(self.folder_selected.emit)
        self.tree_widget.folder_indexed.connect(self.folder_indexed.emit)
        self.tree_widget.folder_excluded.connect(self.folder_excluded.emit)
        self.tree_widget.refresh_requested.connect(self.refresh_requested.emit)
        
        # 統計情報更新用のシグナル
        self.tree_widget.folder_indexed.connect(self._update_stats)
        self.tree_widget.folder_excluded.connect(self._update_stats)
        self.tree_widget.refresh_requested.connect(self._update_stats)
    
    def _on_filter_changed(self, text: str):
        """フィルター入力変更時の処理"""
        # 少し遅延させてパフォーマンスを向上
        if hasattr(self, '_filter_timer'):
            self._filter_timer.stop()
        
        self._filter_timer = QTimer()
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(lambda: self.tree_widget.filter_folders(text))
        self._filter_timer.start(300)  # 300ms遅延
    
    def _clear_filter(self):
        """フィルターをクリアします"""
        self.filter_input.clear()
        self.tree_widget.filter_manager.clear_filter()
    
    def _update_stats(self):
        """統計情報を更新します"""
        total_folders = len(self.tree_widget.item_map)
        indexing_folders = len(self.tree_widget.indexing_paths)
        indexed_folders = len(self.tree_widget.indexed_paths)
        excluded_folders = len(self.tree_widget.excluded_paths)
        error_folders = len(self.tree_widget.error_paths)
        
        stats_text = f"フォルダ: {total_folders}, インデックス: {indexed_folders}"
        if indexing_folders > 0:
            stats_text += f", 処理中: {indexing_folders}"
        if excluded_folders > 0:
            stats_text += f", 除外: {excluded_folders}"
        if error_folders > 0:
            stats_text += f", エラー: {error_folders}"
        
        self.stats_label.setText(stats_text)
    
    # パブリックメソッド（FolderTreeWidgetのメソッドを転送）
    
    def load_folder_structure(self, root_path: str):
        """フォルダ構造を読み込みます"""
        self.tree_widget.load_folder_structure(root_path)
        self._update_stats()
    
    def get_selected_folder(self) -> Optional[str]:
        """現在選択されているフォルダのパスを取得します"""
        return self.tree_widget.get_selected_folder()
    
    def get_indexed_folders(self) -> List[str]:
        """インデックス済みフォルダのリストを取得します"""
        return self.tree_widget.get_indexed_folders()
    
    def get_excluded_folders(self) -> List[str]:
        """除外フォルダのリストを取得します"""
        return self.tree_widget.get_excluded_folders()
    
    def set_indexed_folders(self, paths: List[str]):
        """インデックス済みフォルダを設定します"""
        self.tree_widget.set_indexed_folders(paths)
        self._update_stats()
    
    def set_excluded_folders(self, paths: List[str]):
        """除外フォルダを設定します"""
        self.tree_widget.set_excluded_folders(paths)
        self._update_stats()
    
    def set_folder_indexing(self, folder_path: str):
        """フォルダをインデックス処理中状態に設定します"""
        self.tree_widget.set_folder_indexing(folder_path)
        self._update_stats()
    
    def set_folder_indexed(self, folder_path: str, file_count: int = 0, indexed_count: int = 0):
        """フォルダをインデックス済み状態に設定します"""
        self.tree_widget.set_folder_indexed(folder_path, file_count, indexed_count)
        self._update_stats()
    
    def set_folder_error(self, folder_path: str, error_message: str = ""):
        """フォルダをエラー状態に設定します"""
        self.tree_widget.set_folder_error(folder_path, error_message)
        self._update_stats()
    
    def clear_folder_state(self, folder_path: str):
        """フォルダの状態をクリアします"""
        self.tree_widget.clear_folder_state(folder_path)
        self._update_stats()
    
    def get_indexing_folders(self) -> List[str]:
        """インデックス処理中フォルダのリストを取得します"""
        return self.tree_widget.get_indexing_folders()
    
    def get_error_folders(self) -> List[str]:
        """エラー状態フォルダのリストを取得します"""
        return self.tree_widget.get_error_folders()
    
    def expand_to_path(self, path: str):
        """指定されたパスまでツリーを展開します"""
        self.tree_widget.expand_to_path(path)
    
    def closeEvent(self, event):
        """ウィジェット終了時の処理"""
        if hasattr(self, 'tree_widget') and self.tree_widget:
            self.tree_widget._cleanup_workers()
        super().closeEvent(event)