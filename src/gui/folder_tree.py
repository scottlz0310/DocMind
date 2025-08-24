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
from enum import Enum

from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QMenu, QMessageBox, QFileDialog,
    QLabel, QFrame, QSplitter, QCheckBox, QComboBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QObject
from PySide6.QtGui import QIcon, QAction, QKeySequence, QShortcut

from src.utils.exceptions import DocMindException


class FolderLoadWorker(QObject):
    """
    フォルダ構造を非同期で読み込むワーカー
    """
    
    # シグナル定義
    folder_loaded = Signal(str, list)  # path, subdirectories
    load_error = Signal(str, str)      # path, error_message
    finished = Signal()
    
    def __init__(self, root_path: str, max_depth: int = 3):
        super().__init__()
        self.root_path = root_path
        self.max_depth = max_depth
        self.should_stop = False
        
    def do_work(self):
        """フォルダ構造を読み込みます"""
        try:
            self._load_folder_recursive(self.root_path, 0)
        except Exception as e:
            if not self.should_stop:
                self.load_error.emit(self.root_path, str(e))
        finally:
            self.finished.emit()
    
    def stop(self):
        """読み込みを停止します"""
        self.should_stop = True
    
    def _load_folder_recursive(self, path: str, depth: int):
        """
        再帰的にフォルダ構造を読み込みます
        
        Args:
            path: 読み込み対象パス
            depth: 現在の深度
        """
        if self.should_stop or depth > self.max_depth:
            return
            
        try:
            # パスの妥当性チェック
            if not os.path.exists(path) or not os.path.isdir(path):
                return
                
            # アクセス権限チェック
            if not os.access(path, os.R_OK):
                self.load_error.emit(path, "アクセス権限がありません")
                return
                
            # ファイル数制限（メモリ保護）
            try:
                items = os.listdir(path)
                if len(items) > 10000:  # 大量ファイル制限
                    self.load_error.emit(
                        path, "ファイル数が多すぎます（10,000件以上）"
                    )
                    return
                    
                # 深さ制限によるメモリ保護
                if depth > 5:  # 最大深さ5レベルまで
                    self.load_error.emit(
                        path, "フォルダの深さが深すぎます（5レベル以上）"
                    )
                    return
                    
            except OSError as e:
                self.load_error.emit(path, f"ディレクトリ読み込みエラー: {e}")
                return
                
            subdirs = []
            
            for item in items:
                if self.should_stop:
                    break
                    
                try:
                    item_path = os.path.join(path, item)
                    
                    # シンボリックリンクの安全な処理
                    if os.path.islink(item_path):
                        try:
                            real_path = os.path.realpath(item_path)
                            if os.path.isdir(real_path) and not item.startswith('.'):
                                subdirs.append(item_path)
                        except (OSError, RuntimeError):
                            # シンボリックリンクの解決に失敗した場合はスキップ
                            continue
                    elif os.path.isdir(item_path) and not item.startswith('.'):
                        subdirs.append(item_path)
                        
                except (OSError, PermissionError):
                    # 個別アイテムのエラーはログに記録してスキップ
                    continue
            
            if not self.should_stop:
                self.folder_loaded.emit(path, subdirs)
            
            if depth < self.max_depth:
                for subdir in subdirs:
                    if not self.should_stop:
                        self._load_folder_recursive(subdir, depth + 1)
                        
        except PermissionError:
            if not self.should_stop:
                self.load_error.emit(path, "アクセス権限がありません")
        except OSError as e:
            if not self.should_stop:
                self.load_error.emit(path, f"OSエラー: {e}")
        except Exception as e:
            if not self.should_stop:
                self.load_error.emit(path, f"予期しないエラー: {type(e).__name__}: {str(e)}")


class FolderItemType(Enum):
    """フォルダアイテムの種類"""
    ROOT = "root"           # ルートフォルダ
    FOLDER = "folder"       # 通常のフォルダ
    INDEXED = "indexed"     # インデックス済みフォルダ
    EXCLUDED = "excluded"   # 除外されたフォルダ


class FolderTreeItem(QTreeWidgetItem):
    """
    フォルダツリーアイテムの拡張クラス
    
    フォルダパス、種類、統計情報などの追加データを保持します。
    """
    
    def __init__(self, parent: Optional[QTreeWidgetItem] = None):
        super().__init__(parent)
        
        self.folder_path: str = ""
        self.item_type: FolderItemType = FolderItemType.FOLDER
        self.file_count: int = 0
        self.indexed_count: int = 0
        self.is_expanded_once: bool = False  # 遅延読み込み用フラグ
        self.is_accessible: bool = True      # アクセス可能かどうか
        
    def set_folder_data(self, path: str, item_type: FolderItemType = FolderItemType.FOLDER):
        """
        フォルダデータを設定します
        
        Args:
            path: フォルダパス
            item_type: アイテムの種類
        """
        self.folder_path = path
        self.item_type = item_type
        
        # 表示名を設定
        folder_name = os.path.basename(path) if path else "ルート"
        if not folder_name:
            folder_name = path  # ドライブルートの場合
            
        self.setText(0, folder_name)
        
        # ツールチップを設定
        self.setToolTip(0, path)
        
        # アイコンを設定
        self._update_icon()
    
    def _update_icon(self):
        """アイテムのアイコンを更新します"""
        from PySide6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if not app:
            return
            
        style = app.style()
        
        if self.item_type == FolderItemType.ROOT:
            icon = style.standardIcon(style.StandardPixmap.SP_DriveHDIcon)
        elif self.item_type == FolderItemType.INDEXED:
            icon = style.standardIcon(style.StandardPixmap.SP_DirOpenIcon)
        elif self.item_type == FolderItemType.EXCLUDED:
            icon = style.standardIcon(style.StandardPixmap.SP_DialogCancelButton)
        else:
            icon = style.standardIcon(style.StandardPixmap.SP_DirClosedIcon)
            
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
        folder_name = os.path.basename(self.folder_path) if self.folder_path else "ルート"
        if not folder_name:
            folder_name = self.folder_path
            
        if file_count > 0:
            display_text = f"{folder_name} ({file_count})"
            if indexed_count > 0 and indexed_count != file_count:
                display_text = f"{folder_name} ({indexed_count}/{file_count})"
        else:
            display_text = folder_name
            
        self.setText(0, display_text)





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
        self.indexed_paths: Set[str] = set()               # インデックス済みパスのセット
        self.excluded_paths: Set[str] = set()              # 除外パスのセット
        self.item_map: Dict[str, FolderTreeItem] = {}      # パス→アイテムのマッピング
        
        # ワーカースレッド
        self.load_worker: Optional[QThread] = None
        self.folder_worker: Optional['FolderLoadWorker'] = None
        
        # UI設定
        self._setup_tree_widget()
        self._setup_context_menu()
        self._setup_shortcuts()
        
        self.logger.info("フォルダツリーウィジェットが初期化されました")
    
    def _setup_tree_widget(self):
        """ツリーウィジェットの基本設定を行います"""
        # ヘッダー設定
        self.setHeaderLabel("フォルダ構造")
        self.setHeaderHidden(False)
        
        # 基本設定
        self.setRootIsDecorated(True)           # ルートアイテムに展開アイコンを表示
        self.setAlternatingRowColors(True)      # 行の色を交互に変更
        self.setSelectionMode(QTreeWidget.SingleSelection)  # 単一選択
        self.setExpandsOnDoubleClick(True)      # ダブルクリックで展開
        self.setSortingEnabled(True)            # ソート機能を有効化
        self.sortByColumn(0, Qt.AscendingOrder) # 名前順でソート
        
        # ドラッグ&ドロップを無効化（今回は不要）
        self.setDragDropMode(QTreeWidget.NoDragDrop)
        
        # シグナル接続
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemCollapsed.connect(self._on_item_collapsed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # アクセシビリティ設定
        self.setAccessibleName("フォルダツリー")
        self.setAccessibleDescription("検索対象フォルダの階層構造を表示します")
        
        # スタイル設定
        self.setStyleSheet("""
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
        """)
    
    def _setup_context_menu(self):
        """コンテキストメニューを設定します"""
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # コンテキストメニューアクションを作成
        self.add_folder_action = QAction("フォルダを追加...", self)
        self.add_folder_action.triggered.connect(self._add_folder)
        
        self.remove_folder_action = QAction("フォルダを削除", self)
        self.remove_folder_action.triggered.connect(self._remove_folder)
        
        self.index_folder_action = QAction("インデックスに追加", self)
        self.index_folder_action.triggered.connect(self._index_folder)
        
        self.exclude_folder_action = QAction("フォルダを除外", self)
        self.exclude_folder_action.triggered.connect(self._exclude_folder)
        
        self.refresh_action = QAction("更新", self)
        self.refresh_action.triggered.connect(self._refresh_folder)
        
        self.expand_all_action = QAction("すべて展開", self)
        self.expand_all_action.triggered.connect(self.expandAll)
        
        self.collapse_all_action = QAction("すべて折りたたみ", self)
        self.collapse_all_action.triggered.connect(self.collapseAll)
        
        self.properties_action = QAction("プロパティ...", self)
        self.properties_action.triggered.connect(self._show_properties)
    
    def _setup_shortcuts(self):
        """キーボードショートカットを設定します"""
        # F5キーでリフレッシュ
        self.refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        self.refresh_shortcut.activated.connect(self._refresh_folder)
        
        # Deleteキーでフォルダ削除
        self.delete_shortcut = QShortcut(QKeySequence.Delete, self)
        self.delete_shortcut.activated.connect(self._remove_folder)
        
        # Enterキーでフォルダ選択
        self.enter_shortcut = QShortcut(QKeySequence.InsertParagraphSeparator, self)
        self.enter_shortcut.activated.connect(self._select_current_folder)
    
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
            
            # 既存のワーカーを停止
            self._cleanup_worker()
            
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
            # 既存のワーカーを確実にクリーンアップ
            self._cleanup_worker()
            
            # 新しいワーカー作成
            self.load_worker = QThread()
            self.folder_worker = FolderLoadWorker(path, max_depth=2)
            
            # ワーカーをスレッドに移動
            self.folder_worker.moveToThread(self.load_worker)
            
            # シグナル接続（安全な接続方法 - Qt.QueuedConnection使用）
            self.load_worker.started.connect(self.folder_worker.do_work, Qt.QueuedConnection)
            self.folder_worker.finished.connect(self.load_worker.quit, Qt.QueuedConnection)
            self.folder_worker.finished.connect(self.folder_worker.deleteLater, Qt.QueuedConnection)
            self.load_worker.finished.connect(self.load_worker.deleteLater, Qt.QueuedConnection)
            
            # アプリケーションシグナル接続（安全な接続方法）
            self.folder_worker.folder_loaded.connect(self._on_folder_loaded, Qt.QueuedConnection)
            self.folder_worker.load_error.connect(self._on_load_error, Qt.QueuedConnection)
            self.folder_worker.finished.connect(self._on_load_finished, Qt.QueuedConnection)
            
            self.load_worker.start()
            
        except Exception as e:
            self.logger.error(f"サブフォルダの非同期読み込み開始エラー: {e}")
            # エラー時のフォールバック処理
            self._cleanup_worker()
    
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
                if subdir in self.indexed_paths:
                    child_item.item_type = FolderItemType.INDEXED
                    child_item._update_icon()
                elif subdir in self.excluded_paths:
                    child_item.item_type = FolderItemType.EXCLUDED
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
    
    def _cleanup_worker(self):
        """ワーカーをクリーンアップします"""
        try:
            # フォルダワーカーの停止
            if self.folder_worker:
                self.folder_worker.stop()
                # シグナル接続を切断（安全な方法）
                try:
                    self.folder_worker.folder_loaded.disconnect()
                    self.folder_worker.load_error.disconnect()
                    self.folder_worker.finished.disconnect()
                except (TypeError, RuntimeError):
                    # シグナルが接続されていない場合のエラーは無視
                    pass
                self.folder_worker = None
            
            # ロードワーカーの停止
            if self.load_worker:
                if self.load_worker.isRunning():
                    # シグナル接続を切断（安全な方法）
                    try:
                        self.load_worker.started.disconnect()
                        self.load_worker.finished.disconnect()
                    except (TypeError, RuntimeError):
                        # シグナルが接続されていない場合のエラーは無視
                        pass
                    
                    # スレッドの安全な終了
                    self.load_worker.quit()
                    
                    # スレッドが終了するまで待機（最大3秒）
                    if not self.load_worker.wait(3000):
                        self.logger.warning(
                            "ワーカースレッドの終了を強制終了します"
                        )
                        self.load_worker.terminate()
                        self.load_worker.wait(1000)
                        
                    # スレッドの状態確認
                    if self.load_worker.isRunning():
                        self.logger.error("スレッドの終了に失敗しました")
                        
                self.load_worker = None
                
        except Exception as e:
            self.logger.error(f"ワーカークリーンアップ中にエラーが発生しました: {e}")
        finally:
            # 確実にNoneに設定
            self.folder_worker = None
            self.load_worker = None
    
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
        item = self.itemAt(position)
        
        menu = QMenu(self)
        
        if isinstance(item, FolderTreeItem):
            # フォルダアイテムが選択されている場合
            menu.addAction(self.index_folder_action)
            menu.addAction(self.exclude_folder_action)
            menu.addSeparator()
            menu.addAction(self.remove_folder_action)
            menu.addSeparator()
            menu.addAction(self.refresh_action)
            menu.addSeparator()
            menu.addAction(self.expand_all_action)
            menu.addAction(self.collapse_all_action)
            menu.addSeparator()
            menu.addAction(self.properties_action)
            
            # アクションの有効/無効を設定
            is_indexed = item.folder_path in self.indexed_paths
            is_excluded = item.folder_path in self.excluded_paths
            
            self.index_folder_action.setEnabled(not is_indexed and not is_excluded)
            self.exclude_folder_action.setEnabled(not is_excluded)
            self.remove_folder_action.setEnabled(item.folder_path in self.root_paths)
            
        else:
            # 空白部分が選択されている場合
            menu.addAction(self.add_folder_action)
            menu.addSeparator()
            menu.addAction(self.refresh_action)
            menu.addSeparator()
            menu.addAction(self.expand_all_action)
            menu.addAction(self.collapse_all_action)
        
        # メニューを表示
        menu.exec(self.mapToGlobal(position))
    
    # コンテキストメニューアクション
    
    def _add_folder(self):
        """フォルダを追加します"""
        try:
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "追加するフォルダを選択",
                str(Path.home()),
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if folder_path:
                self.load_folder_structure(folder_path)
                self.logger.info(f"フォルダが追加されました: {folder_path}")
        except Exception as e:
            self.logger.error(f"フォルダ追加中にエラーが発生しました: {e}")
            QMessageBox.critical(
                self,
                "エラー",
                f"フォルダの追加に失敗しました:\n{str(e)}"
            )
    
    def _remove_folder(self):
        """選択されたフォルダを削除します"""
        current_item = self.currentItem()
        if not isinstance(current_item, FolderTreeItem):
            return
        
        folder_path = current_item.folder_path
        if folder_path not in self.root_paths:
            QMessageBox.information(
                self,
                "情報",
                "ルートフォルダのみ削除できます。"
            )
            return
        
        reply = QMessageBox.question(
            self,
            "フォルダ削除",
            f"以下のフォルダをツリーから削除しますか？\n\n{folder_path}\n\n"
            "※ファイルシステムからは削除されません。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # ツリーから削除
            index = self.indexOfTopLevelItem(current_item)
            if index >= 0:
                self.takeTopLevelItem(index)
                
            # 内部状態から削除
            self.root_paths.remove(folder_path)
            self._remove_from_maps(folder_path)
            
            self.logger.info(f"フォルダが削除されました: {folder_path}")
    
    def _remove_from_maps(self, root_path: str):
        """指定されたルートパス以下のアイテムを内部マップから削除します"""
        paths_to_remove = [path for path in self.item_map.keys() 
                          if path.startswith(root_path)]
        
        for path in paths_to_remove:
            self.item_map.pop(path, None)
            self.expanded_paths.discard(path)
            self.indexed_paths.discard(path)
            self.excluded_paths.discard(path)
    
    def _index_folder(self):
        """選択されたフォルダをインデックスに追加します"""
        current_item = self.currentItem()
        if not isinstance(current_item, FolderTreeItem):
            return
        
        folder_path = current_item.folder_path
        
        reply = QMessageBox.question(
            self,
            "インデックス追加",
            f"以下のフォルダをインデックスに追加しますか？\n\n{folder_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.indexed_paths.add(folder_path)
            self.excluded_paths.discard(folder_path)  # 除外リストから削除
            
            # アイテムの表示を更新
            current_item.item_type = FolderItemType.INDEXED
            current_item._update_icon()
            
            # シグナルを発行
            self.folder_indexed.emit(folder_path)
            
            self.logger.info(f"フォルダがインデックスに追加されました: {folder_path}")
    
    def _exclude_folder(self):
        """選択されたフォルダを除外します"""
        current_item = self.currentItem()
        if not isinstance(current_item, FolderTreeItem):
            return
        
        folder_path = current_item.folder_path
        
        reply = QMessageBox.question(
            self,
            "フォルダ除外",
            f"以下のフォルダを検索対象から除外しますか？\n\n{folder_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.excluded_paths.add(folder_path)
            self.indexed_paths.discard(folder_path)  # インデックスリストから削除
            
            # アイテムの表示を更新
            current_item.item_type = FolderItemType.EXCLUDED
            current_item._update_icon()
            
            # シグナルを発行
            self.folder_excluded.emit(folder_path)
            
            self.logger.info(f"フォルダが除外されました: {folder_path}")
    
    def _refresh_folder(self):
        """選択されたフォルダまたは全体を更新します"""
        current_item = self.currentItem()
        
        if isinstance(current_item, FolderTreeItem):
            # 特定のフォルダを更新
            folder_path = current_item.folder_path
            self._refresh_specific_folder(folder_path)
        else:
            # 全体を更新
            self._refresh_all_folders()
        
        self.refresh_requested.emit()
    
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
    
    def _show_properties(self):
        """選択されたフォルダのプロパティを表示します"""
        current_item = self.currentItem()
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
            from datetime import datetime
            modified_time = datetime.fromtimestamp(stat_info.st_mtime)
            
            properties_text = f"""
フォルダ: {os.path.basename(folder_path)}
パス: {folder_path}

統計情報:
  ファイル数: {file_count:,}
  フォルダ数: {dir_count:,}
  合計サイズ: {format_size(total_size)}

最終更新: {modified_time.strftime('%Y/%m/%d %H:%M:%S')}

インデックス状態: {'インデックス済み' if folder_path in self.indexed_paths else '未インデックス'}
除外状態: {'除外中' if folder_path in self.excluded_paths else '対象'}
            """.strip()
            
            QMessageBox.information(
                self,
                "フォルダプロパティ",
                properties_text
            )
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "エラー",
                f"フォルダ情報の取得に失敗しました:\n{str(e)}"
            )
    
    # フィルタリング機能
    
    def filter_folders(self, filter_text: str):
        """
        フォルダをフィルタリングします
        
        Args:
            filter_text: フィルター文字列
        """
        if not filter_text.strip():
            # フィルターをクリア
            self._show_all_items()
            return
        
        filter_text = filter_text.lower()
        
        # すべてのアイテムを非表示にしてから、マッチするものだけ表示
        self._hide_all_items()
        
        for path, item in self.item_map.items():
            folder_name = os.path.basename(path).lower()
            if filter_text in folder_name or filter_text in path.lower():
                self._show_item_and_parents(item)
    
    def _hide_all_items(self):
        """すべてのアイテムを非表示にします"""
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
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
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
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
            if path in self.indexed_paths:
                item.item_type = FolderItemType.INDEXED
            elif path in self.excluded_paths:
                item.item_type = FolderItemType.EXCLUDED
            else:
                item.item_type = FolderItemType.FOLDER
            
            item._update_icon()
    
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
        self._cleanup_worker()
        super().closeEvent(event)
    

    
    def __del__(self):
        """デストラクタ"""
        self._cleanup_worker()


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
        self.add_button.clicked.connect(self.tree_widget._add_folder)
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
        self.tree_widget.filter_folders("")
    
    def _update_stats(self):
        """統計情報を更新します"""
        total_folders = len(self.tree_widget.item_map)
        indexed_folders = len(self.tree_widget.indexed_paths)
        excluded_folders = len(self.tree_widget.excluded_paths)
        
        stats_text = f"フォルダ: {total_folders}, インデックス: {indexed_folders}"
        if excluded_folders > 0:
            stats_text += f", 除外: {excluded_folders}"
        
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
    
    def expand_to_path(self, path: str):
        """指定されたパスまでツリーを展開します"""
        self.tree_widget.expand_to_path(path)
    
    def closeEvent(self, event):
        """ウィジェット終了時の処理"""
        if hasattr(self, 'tree_widget') and self.tree_widget:
            self.tree_widget._cleanup_worker()
        super().closeEvent(event)