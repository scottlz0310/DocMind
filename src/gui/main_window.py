#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind メインウィンドウ

PySide6を使用した3ペインレイアウトのメインアプリケーションウィンドウを実装します。
左ペイン: フォルダツリーナビゲーション
中央ペイン: 検索結果表示
右ペイン: ドキュメントプレビュー

包括的エラーハンドリングと優雅な劣化機能を統合しています。
"""

import logging
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout,
                               QLabel, QMainWindow, QMenuBar, QMessageBox,
                               QProgressBar, QSplitter, QStatusBar,
                               QVBoxLayout, QWidget)

from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager
from src.core.search_manager import SearchManager
from src.core.document_processor import DocumentProcessor
from src.core.indexing_worker import IndexingWorker
from src.core.thread_manager import IndexingThreadManager
from src.core.rebuild_timeout_manager import RebuildTimeoutManager
from src.data.database import DatabaseManager
from src.gui.folder_tree import FolderTreeContainer
from src.gui.preview_widget import PreviewWidget
from src.gui.resources import get_app_icon, get_search_icon, get_settings_icon
from src.gui.search_interface import SearchInterface, SearchWorkerThread
from src.gui.search_results import SearchResultsWidget
from src.utils.config import Config
from src.utils.error_handler import get_global_error_handler, handle_exceptions
from src.utils.exceptions import DocMindException
from src.utils.graceful_degradation import get_global_degradation_manager
from src.utils.logging_config import LoggerMixin


class MainWindow(QMainWindow, LoggerMixin):
    """
    DocMindのメインアプリケーションウィンドウ

    3ペインレイアウト（フォルダツリー、検索結果、プレビュー）を提供し、
    メニューバー、ステータスバー、キーボードショートカットを含む
    完全なデスクトップアプリケーションインターフェースを実装します。

    包括的エラーハンドリングと優雅な劣化機能を統合し、
    コンポーネント障害時の適切なフォールバック処理を提供します。
    """

    # シグナル定義
    folder_selected = Signal(str)  # フォルダが選択された時
    search_requested = Signal(str, str)  # 検索が要求された時 (query, search_type)
    document_selected = Signal(str)  # ドキュメントが選択された時
    error_occurred = Signal(str, str)  # エラーが発生した時 (title, message)

    @handle_exceptions(
        context="メインウィンドウ初期化",
        user_message="メインウィンドウの初期化中にエラーが発生しました。",
        attempt_recovery=True,
        reraise=True
    )
    def __init__(self, parent: Optional[QWidget] = None):
        """
        メインウィンドウの初期化

        Args:
            parent: 親ウィジェット（通常はNone）
        """
        super().__init__(parent)

        # LoggerMixinのloggerプロパティを使用
        self.config = Config()

        # 検索関連コンポーネントの初期化
        self._initialize_search_components()

        # ウィンドウの基本設定
        self._setup_window()

        # UI コンポーネントの初期化
        self._setup_ui()

        # メニューバーの設定
        self._setup_menu_bar()

        # ステータスバーの設定
        self._setup_status_bar()

        # キーボードショートカットの設定
        self._setup_shortcuts()

        # アクセシビリティ機能の設定
        self._setup_accessibility()

        # スタイリングの適用
        self._apply_styling()

        # フォルダツリーのシグナル接続
        self._connect_folder_tree_signals()

        # 検索結果ウィジェットのシグナル接続
        self._connect_search_results_signals()

        self.logger.info("メインウィンドウが初期化されました")

    def _initialize_search_components(self) -> None:
        """検索関連コンポーネントを初期化"""
        try:
            # データベースパスを設定
            db_path = self.config.data_dir / "documents.db"

            # データベースマネージャーの初期化
            self.database_manager = DatabaseManager(str(db_path))

            # インデックスパスを設定
            index_path = self.config.data_dir / "whoosh_index"

            # インデックスマネージャーの初期化
            self.index_manager = IndexManager(str(index_path))

            # 埋め込みマネージャーの初期化
            self.embedding_manager = EmbeddingManager()

            # ドキュメントプロセッサーの初期化
            self.document_processor = DocumentProcessor()

            # 検索マネージャーの初期化
            self.search_manager = SearchManager(
                self.index_manager,
                self.embedding_manager
            )

            # スレッドマネージャーの初期化
            self.thread_manager = IndexingThreadManager(max_concurrent_threads=2)
            self._connect_thread_manager_signals()

            # タイムアウトマネージャーの初期化
            self.timeout_manager = RebuildTimeoutManager(timeout_minutes=30, parent=self)
            self._connect_timeout_manager_signals()

            # 劣化管理マネージャーで検索機能を有効化
            degradation_manager = get_global_degradation_manager()
            degradation_manager.mark_component_healthy("search_manager")

            self.logger.info("検索コンポーネントが初期化されました")

        except Exception as e:
            self.logger.error(f"検索コンポーネントの初期化に失敗: {e}")
            # 劣化管理で検索機能を無効化
            degradation_manager = get_global_degradation_manager()
            degradation_manager.mark_component_degraded(
                "search_manager",
                ["full_text_search", "semantic_search", "hybrid_search"],
                f"検索コンポーネントの初期化に失敗: {e}"
            )

    def _setup_window(self) -> None:
        """ウィンドウの基本設定を行います"""
        self.setWindowTitle("DocMind - ローカルドキュメント検索")
        self.setMinimumSize(1000, 700)
        self.resize(1400, 900)

        # ウィンドウアイコンの設定
        self.setWindowIcon(get_app_icon())

        # ウィンドウを画面中央に配置
        self._center_window()

    def _setup_ui(self) -> None:
        """メインUIレイアウトを設定します"""
        # 中央ウィジェットの作成
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # メインレイアウトの作成
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 3ペインスプリッターの作成
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)

        # 左ペイン: フォルダツリー（プレースホルダー）
        self.folder_pane = self._create_folder_pane()
        self.main_splitter.addWidget(self.folder_pane)

        # 中央ペイン: 検索結果（プレースホルダー）
        self.search_pane = self._create_search_pane()
        self.main_splitter.addWidget(self.search_pane)

        # 右ペイン: ドキュメントプレビュー（プレースホルダー）
        self.preview_pane = self._create_preview_pane()
        self.main_splitter.addWidget(self.preview_pane)

        # スプリッターのサイズ比率を設定 (25%, 40%, 35%)
        self.main_splitter.setSizes([250, 400, 350])
        self.main_splitter.setCollapsible(0, False)  # 左ペインは折りたたみ不可
        self.main_splitter.setCollapsible(1, False)  # 中央ペインは折りたたみ不可
        self.main_splitter.setCollapsible(2, True)   # 右ペインは折りたたみ可能

    def _create_folder_pane(self) -> QWidget:
        """左ペイン（フォルダツリー）を作成"""
        # フォルダツリーコンテナを作成
        self.folder_tree_container = FolderTreeContainer()
        self.folder_tree_container.setMinimumWidth(200)

        # シグナル接続
        self.folder_tree_container.folder_selected.connect(self._on_folder_selected)
        self.folder_tree_container.folder_indexed.connect(self._on_folder_indexed)
        self.folder_tree_container.folder_excluded.connect(self._on_folder_excluded)
        self.folder_tree_container.refresh_requested.connect(self._on_folder_refresh)

        return self.folder_tree_container

    def _create_search_pane(self) -> QWidget:
        """中央ペイン（検索結果）を作成"""
        # 中央ペインのコンテナを作成
        search_container = QWidget()
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(5, 5, 5, 5)
        search_layout.setSpacing(5)

        # 検索インターフェースを作成
        self.search_interface = SearchInterface()
        search_layout.addWidget(self.search_interface)

        # 検索結果ウィジェットを作成
        self.search_results_widget = SearchResultsWidget()
        self.search_results_widget.setMinimumWidth(300)
        search_layout.addWidget(self.search_results_widget)

        # 検索インターフェースのシグナル接続
        self.search_interface.search_requested.connect(self._on_search_requested)
        self.search_interface.search_cancelled.connect(self._on_search_cancelled)

        # 検索提案機能の接続
        self.search_interface.search_input.textChanged.connect(self._on_search_text_changed)

        # 検索結果ウィジェットのシグナル接続
        self.search_results_widget.result_selected.connect(self._on_search_result_selected)
        self.search_results_widget.preview_requested.connect(self._on_preview_requested)
        self.search_results_widget.page_changed.connect(self._on_page_changed)
        self.search_results_widget.sort_changed.connect(self._on_sort_changed)
        self.search_results_widget.filter_changed.connect(self._on_filter_changed)

        search_container.setMinimumWidth(400)
        return search_container

    def _create_preview_pane(self) -> QWidget:
        """右ペイン（ドキュメントプレビュー）を作成"""
        # プレビューウィジェットを作成
        self.preview_widget = PreviewWidget()
        self.preview_widget.setMinimumWidth(250)

        # シグナル接続
        self.preview_widget.zoom_changed.connect(self._on_preview_zoom_changed)
        self.preview_widget.format_changed.connect(self._on_preview_format_changed)

        return self.preview_widget

    def _setup_menu_bar(self) -> None:
        """メニューバーを設定します"""
        menubar = self.menuBar()

        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル(&F)")

        # フォルダを開くアクション
        self.open_folder_action = QAction("フォルダを開く(&O)...", self)
        self.open_folder_action.setShortcut(QKeySequence.Open)
        self.open_folder_action.setStatusTip("検索対象のフォルダを選択します")
        self.open_folder_action.triggered.connect(self._open_folder_dialog)
        file_menu.addAction(self.open_folder_action)

        file_menu.addSeparator()

        # 終了アクション
        self.exit_action = QAction("終了(&X)", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.setStatusTip("アプリケーションを終了します")
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

        # 検索メニュー
        search_menu = menubar.addMenu("検索(&S)")

        # 検索実行アクション
        self.search_action = QAction(get_search_icon(), "検索(&S)...", self)
        self.search_action.setShortcut(QKeySequence.Find)
        self.search_action.setStatusTip("ドキュメント検索を実行します")
        self.search_action.triggered.connect(self._show_search_dialog)
        search_menu.addAction(self.search_action)

        # インデックス再構築アクション
        self.rebuild_index_action = QAction("インデックス再構築(&R)", self)
        self.rebuild_index_action.setShortcut(QKeySequence("Ctrl+R"))
        self.rebuild_index_action.setStatusTip("検索インデックスを再構築します")
        self.rebuild_index_action.triggered.connect(self._rebuild_index)
        search_menu.addAction(self.rebuild_index_action)

        # インデックスクリアアクション
        self.clear_index_action = QAction("インデックスクリア(&C)", self)
        self.clear_index_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.clear_index_action.setStatusTip("検索インデックスをクリアします")
        self.clear_index_action.triggered.connect(self._clear_index)
        search_menu.addAction(self.clear_index_action)

        # 表示メニュー
        view_menu = menubar.addMenu("表示(&V)")

        # プレビューペイン表示切り替え
        self.toggle_preview_action = QAction("プレビューペイン(&P)", self)
        self.toggle_preview_action.setCheckable(True)
        self.toggle_preview_action.setChecked(True)
        self.toggle_preview_action.setShortcut(QKeySequence("F3"))
        self.toggle_preview_action.setStatusTip("プレビューペインの表示を切り替えます")
        self.toggle_preview_action.triggered.connect(self._toggle_preview_pane)
        view_menu.addAction(self.toggle_preview_action)

        # ツールメニュー
        tools_menu = menubar.addMenu("ツール(&T)")

        # 設定アクション
        self.settings_action = QAction(get_settings_icon(), "設定(&S)...", self)
        self.settings_action.setShortcut(QKeySequence.Preferences)
        self.settings_action.setStatusTip("アプリケーション設定を開きます")
        self.settings_action.triggered.connect(self._show_settings_dialog)
        tools_menu.addAction(self.settings_action)

        # ヘルプメニュー
        help_menu = menubar.addMenu("ヘルプ(&H)")

        # バージョン情報アクション
        self.about_action = QAction("DocMindについて(&A)...", self)
        self.about_action.setStatusTip("アプリケーションの情報を表示します")
        self.about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(self.about_action)

    def _setup_status_bar(self) -> None:
        """ステータスバーを設定します"""
        self.status_bar = self.statusBar()

        # メインステータスラベル
        self.status_label = QLabel("準備完了")
        self.status_bar.addWidget(self.status_label)

        # 進捗バー（通常は非表示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # システム情報ラベル
        self.system_info_label = QLabel("インデックス: 未作成")
        self.status_bar.addPermanentWidget(self.system_info_label)

        # 初期メッセージを表示
        self.show_status_message("DocMindが起動しました", 3000)

    def _setup_shortcuts(self) -> None:
        """キーボードショートカットを設定します"""
        # 既にメニューアクションで設定済みのショートカット以外を追加

        # Escキーでプレビューペインをクリア
        self.clear_preview_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.clear_preview_shortcut.activated.connect(self._clear_preview)

        # F5キーでリフレッシュ
        self.refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        self.refresh_shortcut.activated.connect(self._refresh_view)

    def _setup_accessibility(self) -> None:
        """アクセシビリティ機能を設定します"""
        # ウィンドウのアクセシブル名と説明を設定
        self.setAccessibleName("DocMind メインウィンドウ")
        self.setAccessibleDescription("ローカルドキュメント検索アプリケーションのメインウィンドウ")

        # 各ペインにアクセシブル名を設定
        self.folder_tree_container.setAccessibleName("フォルダツリーペイン")
        self.folder_tree_container.setAccessibleDescription("検索対象フォルダの階層構造を表示します")

        self.search_results_widget.setAccessibleName("検索結果ペイン")
        self.search_results_widget.setAccessibleDescription("検索結果の一覧を表示します")

        self.preview_widget.setAccessibleName("プレビューペイン")
        self.preview_widget.setAccessibleDescription("選択されたドキュメントの内容をプレビュー表示します")

        # ステータスバーコンポーネントにアクセシブル名を設定
        self.status_label.setAccessibleName("ステータス情報")
        self.progress_bar.setAccessibleName("進捗インジケーター")
        self.system_info_label.setAccessibleName("システム情報")

        # タブオーダーの設定（キーボードナビゲーション用）
        self.setTabOrder(self.folder_tree_container, self.search_results_widget)
        self.setTabOrder(self.search_results_widget, self.preview_widget)

    def _apply_styling(self) -> None:
        """基本的なスタイリングを適用します"""
        # アプリケーション全体のスタイルシート
        style_sheet = """
        QMainWindow {
            background-color: #f5f5f5;
        }

        QFrame {
            background-color: white;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
        }

        QLabel {
            color: #333333;
        }

        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #d0d0d0;
        }

        QMenuBar::item {
            padding: 4px 8px;
            background-color: transparent;
        }

        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }

        QStatusBar {
            background-color: #f0f0f0;
            border-top: 1px solid #d0d0d0;
        }

        QProgressBar {
            border: 1px solid #d0d0d0;
            border-radius: 3px;
            text-align: center;
        }

        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 2px;
        }
        """

        self.setStyleSheet(style_sheet)

    def _center_window(self) -> None:
        """ウィンドウを画面中央に配置します"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

    # メニューアクションのスロット関数

    def _open_folder_dialog(self) -> None:
        """フォルダ選択ダイアログを表示します"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "検索対象フォルダを選択",
            str(Path.home()),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if folder_path:
            self.logger.info(f"フォルダが選択されました: {folder_path}")
            self.folder_selected.emit(folder_path)
            self.show_status_message(f"フォルダを選択: {folder_path}", 5000)

            # フォルダツリーに追加
            self.folder_tree_container.load_folder_structure(folder_path)

    def _show_search_dialog(self) -> None:
        """検索インターフェースにフォーカスを設定"""
        self.search_interface.search_input.setFocus()
        self.search_interface.search_input.selectAll()

    def _rebuild_index(self) -> None:
        """インデックス再構築を実行します"""
        try:
            # 確認ダイアログの表示
            reply = QMessageBox.question(
                self,
                "インデックス再構築",
                "インデックスを再構築しますか？\n\n"
                "この操作により、既存のインデックスが削除され、\n"
                "すべてのドキュメントが再度処理されます。\n"
                "処理には時間がかかる場合があります。\n\n"
                "続行しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 現在選択されているフォルダパスを取得
            current_folder = self.folder_tree_container.get_selected_folder()
            if not current_folder:
                QMessageBox.warning(
                    self,
                    "フォルダが選択されていません",
                    "インデックスを再構築するフォルダを選択してください。"
                )
                return

            # 既存のインデックスをクリア
            self.logger.info(f"インデックス再構築開始: {current_folder}")
            self.index_manager.clear_index()

            # 進捗表示を開始
            self.show_progress("インデックスを再構築中...", 0)

            # IndexingThreadManagerを使用してインデックス再構築を開始
            try:
                thread_id = self.thread_manager.start_indexing_thread(
                    folder_path=current_folder,
                    document_processor=self.document_processor,
                    index_manager=self.index_manager
                )

                if thread_id:
                    # タイムアウト監視を開始
                    self.timeout_manager.start_timeout(thread_id)
                    self.logger.info(f"インデックス再構築スレッド開始: {thread_id}")
                    self.show_status_message(f"インデックス再構築を開始しました (ID: {thread_id})", 3000)
                else:
                    # スレッド開始に失敗した場合の処理
                    self.hide_progress("インデックス再構築の開始に失敗しました")
                    
                    # 詳細なエラー情報を提供
                    active_count = self.thread_manager.get_active_thread_count()
                    max_threads = self.thread_manager.max_concurrent_threads
                    
                    if active_count >= max_threads:
                        error_msg = (
                            f"最大同時実行数に達しています ({active_count}/{max_threads})。\n"
                            "他の処理が完了してから再試行してください。"
                        )
                    elif self.thread_manager._is_folder_being_processed(current_folder):
                        error_msg = (
                            "このフォルダは既に処理中です。\n"
                            "処理が完了してから再試行してください。"
                        )
                    else:
                        error_msg = (
                            "インデックス再構築の開始に失敗しました。\n"
                            "しばらく待ってから再試行してください。"
                        )
                    
                    QMessageBox.critical(self, "エラー", error_msg)
                    
            except Exception as thread_error:
                # スレッド開始時の例外処理
                self.hide_progress("インデックス再構築の開始でエラーが発生しました")
                self.logger.error(f"スレッド開始エラー: {thread_error}")
                
                QMessageBox.critical(
                    self,
                    "スレッド開始エラー",
                    f"インデックス再構築スレッドの開始でエラーが発生しました:\n{str(thread_error)}\n\n"
                    "システムリソースが不足している可能性があります。"
                )
                return

        except Exception as e:
            self.logger.error(f"インデックス再構築エラー: {e}")
            self.hide_progress("インデックス再構築でエラーが発生しました")
            QMessageBox.critical(
                self,
                "エラー",
                f"インデックス再構築でエラーが発生しました:\n{str(e)}"
            )

    def _clear_index(self) -> None:
        """インデックスをクリアします"""
        reply = QMessageBox.question(
            self,
            "インデックスクリア",
            "インデックスをクリアしますか？\n\n"
            "この操作により、すべての検索インデックスが削除されます。\n"
            "この操作は取り消しできません。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.show_progress("インデックスをクリア中...", 0)

                # インデックスマネージャーからクリアを実行
                if hasattr(self, 'index_manager') and self.index_manager:
                    self.index_manager.clear_index()

                    # 検索結果をクリア
                    if hasattr(self, 'search_results_widget'):
                        self.search_results_widget.clear_results()

                    # プレビューをクリア
                    if hasattr(self, 'preview_widget'):
                        self.preview_widget.clear_preview()

                    # 検索提案キャッシュをクリア
                    if hasattr(self, 'search_manager'):
                        self.search_manager.clear_suggestion_cache()

                    self.hide_progress("インデックスクリアが完了しました")
                    self.show_status_message("インデックスをクリアしました", 3000)

                    # システム情報を更新
                    if hasattr(self, 'system_info_label'):
                        self.system_info_label.setText("インデックス: クリア済み")

                else:
                    self.hide_progress("")
                    QMessageBox.warning(
                        self, "警告",
                        "インデックスマネージャーが利用できません。"
                    )

            except Exception as e:
                self.hide_progress("")
                self.logger.error(f"インデックスクリアに失敗しました: {e}")
                QMessageBox.critical(
                    self, "エラー",
                    f"インデックスクリアに失敗しました:\n{e}"
                )

    def _toggle_preview_pane(self) -> None:
        """プレビューペインの表示を切り替えます"""
        is_visible = self.preview_widget.isVisible()
        self.preview_widget.setVisible(not is_visible)

        status_msg = "プレビューペインを非表示にしました" if is_visible else "プレビューペインを表示しました"
        self.show_status_message(status_msg, 2000)

    def _show_settings_dialog(self) -> None:
        """設定ダイアログを表示します"""
        from src.gui.settings_dialog import SettingsDialog

        try:
            dialog = SettingsDialog(self.config, self)
            dialog.settings_changed.connect(self._on_settings_changed)

            if dialog.exec() == SettingsDialog.Accepted:
                self.logger.info("設定が更新されました")
                self.show_status_message("設定が保存されました", 3000)

        except Exception as e:
            self.logger.error(f"設定ダイアログの表示に失敗しました: {e}")
            QMessageBox.critical(
                self, "エラー",
                f"設定ダイアログの表示に失敗しました:\n{e}"
            )

    def _on_settings_changed(self, settings: dict) -> None:
        """設定変更時の処理"""
        try:
            # ログ設定の更新
            from src.utils.logging_config import reconfigure_logging
            reconfigure_logging(
                level=settings.get("log_level"),
                enable_console=settings.get("console_logging"),
                enable_file=settings.get("file_logging")
            )

            # ウィンドウサイズの更新
            if "window_width" in settings and "window_height" in settings:
                self.resize(settings["window_width"], settings["window_height"])

            # UIテーマの更新
            if "ui_theme" in settings:
                self._apply_theme(settings["ui_theme"])

            # フォント設定の更新
            if "font_family" in settings or "font_size" in settings:
                self._apply_font_settings(settings)

            self.logger.info("設定変更が適用されました")

        except Exception as e:
            self.logger.error(f"設定変更の適用に失敗しました: {e}")
            QMessageBox.warning(
                self, "警告",
                f"一部の設定変更の適用に失敗しました:\n{e}"
            )

    def _apply_theme(self, theme: str) -> None:
        """UIテーマを適用"""
        # 基本的なテーマ適用（将来の拡張用）
        if theme == "dark":
            # ダークテーマの適用（実装は将来の拡張）
            pass
        elif theme == "light":
            # ライトテーマの適用
            pass
        # デフォルトテーマは現在のスタイルを維持

    def _apply_font_settings(self, settings: dict) -> None:
        """フォント設定を適用"""
        from PySide6.QtGui import QFont

        font_family = settings.get("font_family", "システムデフォルト")
        font_size = settings.get("font_size", 10)

        if font_family != "システムデフォルト":
            font = QFont(font_family, font_size)
            self.setFont(font)
            QApplication.instance().setFont(font)



    def _show_about_dialog(self) -> None:
        """バージョン情報ダイアログを表示します"""
        QMessageBox.about(
            self,
            "DocMindについて",
            "<h3>DocMind v1.0.0</h3>"
            "<p>ローカルAI搭載ドキュメント検索アプリケーション</p>"
            "<p>完全オフラインで動作する高性能ドキュメント検索ツール</p>"
            "<p><b>技術スタック:</b></p>"
            "<ul>"
            "<li>Python 3.11+</li>"
            "<li>PySide6 (Qt6)</li>"
            "<li>Whoosh (全文検索)</li>"
            "<li>sentence-transformers (セマンティック検索)</li>"
            "</ul>"
            "<p>© 2024 DocMind Project</p>"
        )

    # ショートカットのスロット関数

    def _clear_preview(self) -> None:
        """プレビューペインをクリアします"""
        self.preview_widget.clear_preview()
        self.show_status_message("プレビューをクリアしました", 2000)

    def _refresh_view(self) -> None:
        """ビューをリフレッシュします"""
        # TODO: 実際のリフレッシュ処理を実装
        self.show_status_message("ビューをリフレッシュしました", 2000)

    # ユーティリティメソッド

    def show_status_message(self, message: str, timeout: int = 0) -> None:
        """
        ステータスバーにメッセージを表示します

        Args:
            message: 表示するメッセージ
            timeout: 表示時間（ミリ秒、0で永続表示）
        """
        self.status_bar.showMessage(message, timeout)
        self.logger.debug(f"ステータスメッセージ: {message}")

    def show_progress(self, message: str, value: int, current: int = 0, total: int = 0) -> None:
        """
        進捗バーを表示します

        Args:
            message: 進捗メッセージ
            value: 進捗値（0-100、0で不定進捗）
            current: 現在の処理数（オプション）
            total: 総処理数（オプション）
        """
        # ステータスラベルに詳細メッセージを表示
        self.status_label.setText(message)
        self.progress_bar.setVisible(True)

        if value == 0:
            # 不定進捗（スキャン中など）
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("処理中...")
            # 不定進捗の場合はアニメーション効果を有効化
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #d0d0d0;
                    border-radius: 3px;
                    text-align: center;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    border-radius: 2px;
                }
            """)
        else:
            # 定進捗
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(value)
            
            # 進捗表示フォーマットを改善
            if current > 0 and total > 0:
                self.progress_bar.setFormat(f"{value}% ({current}/{total})")
            else:
                self.progress_bar.setFormat(f"{value}%")

            # 進捗率に応じて色を変更
            if value < 30:
                color = "#FF9800"  # オレンジ（開始段階）
            elif value < 70:
                color = "#2196F3"  # 青（進行中）
            else:
                color = "#4CAF50"  # 緑（完了間近）

            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #d0d0d0;
                    border-radius: 3px;
                    text-align: center;
                    font-weight: bold;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 2px;
                }}
            """)

        # 進捗バーのツールチップに詳細情報を設定
        if current > 0 and total > 0:
            tooltip = f"{message}\n進捗: {current}/{total} ({value}%)"
        else:
            tooltip = f"{message}\n進捗: {value}%"
        self.progress_bar.setToolTip(tooltip)

        # アクセシビリティ用の説明を更新
        self.progress_bar.setAccessibleDescription(f"進捗: {message}")

        # ログに進捗情報を記録
        if current > 0 and total > 0:
            self.logger.debug(f"進捗表示更新: {message} ({current}/{total}, {value}%)")
        else:
            self.logger.debug(f"進捗表示更新: {message} ({value}%)")

    def hide_progress(self, completion_message: str = "") -> None:
        """
        進捗バーを非表示にします

        Args:
            completion_message: 完了メッセージ
        """
        # 進捗バーを非表示にしてリセット
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        self.progress_bar.setToolTip("")
        
        # スタイルシートをリセット
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)

        if completion_message:
            self.show_status_message(completion_message, 5000)  # 完了メッセージは少し長く表示
        else:
            self.status_label.setText("準備完了")
            
        # ログに非表示化を記録
        self.logger.debug("進捗バーを非表示にしました")

    def update_system_info(self, info: str) -> None:
        """
        システム情報を更新します

        Args:
            info: システム情報文字列
        """
        self.system_info_label.setText(info)

    def update_progress(self, current: int, total: int, message: str = "") -> None:
        """
        進捗率を正確に計算して表示します

        Args:
            current: 現在の処理数
            total: 総処理数
            message: 進捗メッセージ（オプション）
        """
        if total <= 0:
            # 総数が0以下の場合は不定進捗として表示
            self.show_progress(message or "処理中...", 0)
            return

        # 進捗率を計算（0-100の範囲）
        percentage = min(100, max(0, int((current / total) * 100)))
        
        # デフォルトメッセージを生成
        if not message:
            message = f"処理中: {current}/{total}"
        
        # 進捗バーを更新
        self.show_progress(message, percentage, current, total)

    def set_progress_indeterminate(self, message: str = "処理中...") -> None:
        """
        不定進捗モードに設定します

        Args:
            message: 表示するメッセージ
        """
        self.show_progress(message, 0)

    def is_progress_visible(self) -> bool:
        """
        進捗バーが表示されているかどうかを確認します

        Returns:
            bool: 進捗バーが表示されている場合True
        """
        return self.progress_bar.isVisible()

    def get_progress_value(self) -> int:
        """
        現在の進捗値を取得します

        Returns:
            int: 現在の進捗値（0-100）
        """
        return self.progress_bar.value()

    def set_progress_style(self, style: str) -> None:
        """
        進捗バーのスタイルを設定します

        Args:
            style: 'success', 'warning', 'error', 'info' のいずれか
        """
        color_map = {
            'success': '#4CAF50',  # 緑
            'warning': '#FF9800',  # オレンジ
            'error': '#F44336',    # 赤
            'info': '#2196F3'      # 青
        }
        
        color = color_map.get(style, '#4CAF50')
        
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                text-align: center;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)

    def _connect_folder_tree_signals(self) -> None:
        """フォルダツリーのシグナルを接続します"""
        # フォルダツリーのシグナルはすでに_create_folder_paneで接続済み
        pass

    def _connect_search_results_signals(self) -> None:
        """検索結果ウィジェットのシグナルを接続します"""
        # 検索結果ウィジェットのシグナルはすでに_create_search_paneで接続済み
        pass

    def _connect_thread_manager_signals(self) -> None:
        """スレッドマネージャーのシグナルを接続"""
        if hasattr(self, 'thread_manager'):
            # スレッド開始シグナル
            self.thread_manager.thread_started.connect(self._on_thread_started)

            # スレッド完了シグナル
            self.thread_manager.thread_finished.connect(self._on_thread_finished)

            # スレッドエラーシグナル
            self.thread_manager.thread_error.connect(self._on_thread_error)

            # スレッド進捗シグナル
            self.thread_manager.thread_progress.connect(self._on_thread_progress)

            # マネージャー状態変更シグナル
            self.thread_manager.manager_status_changed.connect(self._on_manager_status_changed)

    def _connect_timeout_manager_signals(self) -> None:
        """タイムアウトマネージャーのシグナルを接続"""
        if hasattr(self, 'timeout_manager'):
            # タイムアウト発生シグナル
            self.timeout_manager.timeout_occurred.connect(self._handle_rebuild_timeout)

    # フォルダツリーのシグナルハンドラー

    def _on_folder_selected(self, folder_path: str) -> None:
        """
        フォルダが選択された時の処理

        Args:
            folder_path: 選択されたフォルダのパス
        """
        self.logger.info(f"フォルダツリーでフォルダが選択されました: {folder_path}")
        self.folder_selected.emit(folder_path)
        self.show_status_message(f"選択: {folder_path}", 3000)

        # TODO: 選択されたフォルダの内容を検索結果ペインに表示
        # これは後のタスクで実装されます

    def _on_folder_indexed(self, folder_path: str) -> None:
        """
        フォルダがインデックスに追加された時の処理

        Args:
            folder_path: インデックスに追加されたフォルダのパス
        """
        self.logger.info(f"フォルダがインデックスに追加されました: {folder_path}")
        self.show_status_message(f"インデックスに追加: {os.path.basename(folder_path)}", 3000)

        # 実際のインデックス処理を開始
        self._start_indexing_process(folder_path)

    def _start_indexing_process(self, folder_path: str) -> None:
        """
        実際のインデックス処理を開始

        IndexingThreadManagerを使用してバックグラウンドスレッドで実行し、
        複数の同時インデックス処理を制御します。

        Args:
            folder_path: インデックス化するフォルダのパス
        """
        try:
            # 必要なコンポーネントが初期化されているかチェック
            if not hasattr(self, 'document_processor') or not self.document_processor:
                self.logger.error("DocumentProcessorが初期化されていません")
                self.show_status_message("エラー: ドキュメントプロセッサーが利用できません", 5000)
                return

            if not hasattr(self, 'index_manager') or not self.index_manager:
                self.logger.error("IndexManagerが初期化されていません")
                self.show_status_message("エラー: インデックスマネージャーが利用できません", 5000)
                return

            if not hasattr(self, 'thread_manager') or not self.thread_manager:
                self.logger.error("IndexingThreadManagerが初期化されていません")
                self.show_status_message("エラー: スレッドマネージャーが利用できません", 5000)
                return

            # スレッドマネージャーを使用してインデックス処理を開始
            thread_id = self.thread_manager.start_indexing_thread(
                folder_path=folder_path,
                document_processor=self.document_processor,
                index_manager=self.index_manager
            )

            if thread_id:
                self.logger.info(f"インデックス処理スレッドを開始しました: {thread_id} ({folder_path})")
                self.show_status_message(f"インデックス処理を開始: {os.path.basename(folder_path)}", 3000)
            else:
                # 同時実行数制限などで開始できない場合
                active_count = self.thread_manager.get_active_thread_count()
                max_count = self.thread_manager.max_concurrent_threads
                self.logger.warning(f"インデックス処理を開始できませんでした: {folder_path} (アクティブ: {active_count}/{max_count})")
                self.show_status_message(
                    f"インデックス処理を開始できません (同時実行数制限: {active_count}/{max_count})",
                    5000
                )

        except Exception as e:
            self.logger.error(f"インデックス処理の開始に失敗しました: {e}")
            self.show_status_message(f"エラー: インデックス処理を開始できませんでした", 5000)



    def _format_completion_message(self, statistics: dict) -> str:
        """
        完了メッセージをフォーマット

        Args:
            statistics: 統計情報

        Returns:
            str: フォーマットされた完了メッセージ
        """
        try:
            files_processed = statistics.get('files_processed', 0)
            files_failed = statistics.get('files_failed', 0)
            documents_added = statistics.get('documents_added', 0)
            processing_time = statistics.get('processing_time', 0.0)

            if files_processed == 0 and files_failed == 0:
                return "インデックス処理完了（処理対象ファイルなし）"

            success_rate = (files_processed / (files_processed + files_failed)) * 100 if (files_processed + files_failed) > 0 else 0

            return (
                f"インデックス作成完了: {files_processed}ファイル処理済み "
                f"(成功率: {success_rate:.1f}%, 処理時間: {processing_time:.1f}秒)"
            )

        except Exception as e:
            self.logger.warning(f"完了メッセージのフォーマットに失敗: {e}")
            return "インデックス処理完了"

    def _cleanup_indexing_thread(self) -> None:
        """
        インデックス処理スレッドのクリーンアップ
        """
        try:
            # ワーカーを先にクリーンアップ
            if hasattr(self, 'indexing_worker') and self.indexing_worker:
                try:
                    self.indexing_worker.deleteLater()
                except RuntimeError:
                    # C++オブジェクトが既に削除されている場合は無視
                    pass
                self.indexing_worker = None

            # スレッドをクリーンアップ
            if hasattr(self, 'indexing_thread') and self.indexing_thread:
                try:
                    self.indexing_thread.deleteLater()
                except RuntimeError:
                    # C++オブジェクトが既に削除されている場合は無視
                    pass
                self.indexing_thread = None

            self.logger.debug("インデックス処理スレッドをクリーンアップしました")

        except Exception as e:
            self.logger.warning(f"インデックス処理スレッドのクリーンアップに失敗: {e}")

    def _on_thread_started(self, thread_id: str) -> None:
        """スレッド開始時の処理

        Args:
            thread_id (str): 開始されたスレッドのID
        """
        thread_info = self.thread_manager.get_thread_info(thread_id)
        if thread_info:
            folder_name = os.path.basename(thread_info.folder_path)
            self.logger.info(f"インデックス処理スレッド開始: {thread_id} ({folder_name})")

            # フォルダツリーの状態をINDEXINGに更新
            self.folder_tree_container.set_folder_indexing(thread_info.folder_path)

            # 初期進捗表示（新しい不定進捗機能を使用）
            start_message = f"📁 インデックス処理開始: {folder_name}"
            self.set_progress_indeterminate(start_message)
            self.set_progress_style('info')  # 開始時は情報スタイル

            # システム情報を更新
            active_count = self.thread_manager.get_active_thread_count()
            indexed_count = len(self.folder_tree_container.get_indexed_folders())
            self.update_system_info(f"インデックス: {indexed_count}フォルダ, 処理中: {active_count}スレッド")
            
            # ステータスメッセージも更新
            self.show_status_message(start_message, 3000)

    def _on_thread_finished(self, thread_id: str, statistics: dict) -> None:
        """スレッド完了時の処理

        Args:
            thread_id (str): 完了したスレッドのID
            statistics (dict): 処理統計情報
        """
        thread_info = self.thread_manager.get_thread_info(thread_id)
        if thread_info:
            folder_name = os.path.basename(thread_info.folder_path)

            # フォルダツリーの状態をINDEXEDに更新
            files_processed = statistics.get('files_processed', 0)
            documents_added = statistics.get('documents_added', 0)
            self.folder_tree_container.set_folder_indexed(
                thread_info.folder_path, 
                files_processed, 
                documents_added
            )

            # 詳細な完了メッセージを生成
            completion_message = self._format_detailed_completion_message(folder_name, statistics)
            
            # 進捗バーの表示制御を改善
            active_count = self.thread_manager.get_active_thread_count() - 1  # 完了したスレッドを除く
            
            if active_count > 0:
                # 他のスレッドがまだ実行中の場合は進捗バーを維持
                # 完了メッセージをステータスに表示するが進捗バーは非表示にしない
                self.show_status_message(completion_message, 5000)
                self.logger.info(f"スレッド完了（他のスレッド実行中）: {folder_name}")
            else:
                # すべてのスレッドが完了した場合のみ進捗バーを非表示
                self.hide_progress(completion_message)
                self.logger.info(f"全スレッド完了: 進捗バーを非表示")

                # インデックス再構築完了時の追加処理
                self._on_rebuild_completed(thread_id, statistics)

            # システム情報を更新
            indexed_count = len(self.folder_tree_container.get_indexed_folders())

            if active_count > 0:
                self.update_system_info(f"インデックス: {indexed_count}フォルダ, 処理中: {active_count}スレッド")
            else:
                self.update_system_info(f"インデックス: {indexed_count}フォルダ, 待機中")

            # 完了ログ
            duration = thread_info.get_duration()
            self.logger.info(f"インデックス処理完了: {thread_id} ({folder_name}, {duration:.2f}秒)")
            self.logger.info(f"統計情報: {statistics}")

    def _format_detailed_completion_message(self, folder_name: str, statistics: dict) -> str:
        """
        詳細な完了メッセージをフォーマット

        Args:
            folder_name (str): フォルダ名
            statistics (dict): 統計情報

        Returns:
            str: フォーマットされた完了メッセージ
        """
        try:
            files_processed = statistics.get('files_processed', 0)
            files_failed = statistics.get('files_failed', 0)
            documents_added = statistics.get('documents_added', 0)
            processing_time = statistics.get('processing_time', 0.0)

            if files_processed == 0 and files_failed == 0:
                return f"✅ {folder_name}: 処理対象ファイルなし"

            total_files = files_processed + files_failed
            success_rate = (files_processed / total_files) * 100 if total_files > 0 else 0

            if files_failed == 0:
                return f"✅ {folder_name}: {files_processed}ファイル処理完了 ({processing_time:.1f}秒)"
            else:
                return f"⚠️ {folder_name}: {files_processed}/{total_files}ファイル処理完了 (成功率: {success_rate:.1f}%)"

        except Exception as e:
            self.logger.warning(f"完了メッセージのフォーマットに失敗: {e}")
            return f"✅ {folder_name}: インデックス処理完了"

    def _on_thread_error(self, thread_id: str, error_message: str) -> None:
        """スレッドエラー時の処理

        Args:
            thread_id (str): エラーが発生したスレッドのID
            error_message (str): エラーメッセージ
        """
        thread_info = self.thread_manager.get_thread_info(thread_id)
        folder_name = "不明"
        if thread_info:
            folder_name = os.path.basename(thread_info.folder_path)
            
            # フォルダツリーの状態をERRORに更新
            self.folder_tree_container.set_folder_error(thread_info.folder_path, error_message)

        # 進捗バーの表示制御を改善
        active_count = self.thread_manager.get_active_thread_count() - 1  # エラーしたスレッドを除く
        
        if active_count > 0:
            # 他のスレッドがまだ実行中の場合は進捗バーを維持し、エラースタイルに変更
            self.set_progress_style('error')
            error_msg = f"エラー発生 ({folder_name}): {error_message}"
            self.show_status_message(error_msg, 8000)
            self.logger.warning(f"スレッドエラー（他のスレッド実行中）: {folder_name}")
        else:
            # すべてのスレッドが完了/エラーした場合のみ進捗バーを非表示
            self.hide_progress("")
            error_msg = f"インデックス処理エラー ({folder_name}): {error_message}"
            self.show_status_message(error_msg, 10000)
            self.logger.error(f"全スレッド完了/エラー: 進捗バーを非表示")

            # インデックス再構築エラー時の追加処理
            self._on_rebuild_error(thread_id, error_message)

        # エラーログ
        self.logger.error(f"スレッドエラー: {thread_id} - {error_message}")

        # システム情報を更新
        indexed_count = len(self.folder_tree_container.get_indexed_folders())
        if active_count > 0:
            self.update_system_info(f"インデックス: {indexed_count}フォルダ, 処理中: {active_count}スレッド (エラー発生)")
        else:
            self.update_system_info(f"インデックス: {indexed_count}フォルダ, エラーで停止")

        # 必要に応じてエラーダイアログを表示
        if "予期しない" in error_message or "重大" in error_message:
            QMessageBox.critical(
                self,
                "インデックス処理エラー",
                f"インデックス処理中に重大なエラーが発生しました:\n\n{error_message}\n\n"
                f"詳細はログファイルを確認してください。"
            )

    def _on_thread_progress(self, thread_id: str, message: str, current: int, total: int) -> None:
        """スレッド進捗更新時の処理

        Args:
            thread_id (str): 進捗を報告したスレッドのID
            message (str): 進捗メッセージ
            current (int): 現在の処理数
            total (int): 総処理数
        """
        try:
            # スレッド情報を取得してフォルダ名を正確に取得
            thread_info = None
            folder_name = "不明"

            if hasattr(self, 'thread_manager') and self.thread_manager:
                thread_info = self.thread_manager.get_thread_info(thread_id)
                if thread_info:
                    folder_name = os.path.basename(thread_info.folder_path)

            # 詳細な進捗メッセージを生成
            detailed_message = self._format_progress_message(message, current, total)

            # フォルダ名を含む完全なメッセージを作成
            full_message = f"[{folder_name}] {detailed_message}"

            # 新しい進捗表示機能を使用
            if total > 0:
                # 正確な進捗率計算を使用
                self.update_progress(current, total, full_message)
                
                # システム情報を更新（詳細な進捗情報を含む）
                self._update_system_info_with_progress(folder_name, current, total, self.get_progress_value())
            else:
                # 不定進捗の場合（スキャン中など）
                self.set_progress_indeterminate(full_message)
                self._update_system_info_with_progress(folder_name, current, total, 0)

            # ステータスメッセージを更新
            self.show_status_message(full_message, 0)

            self.logger.debug(f"スレッド進捗更新: {thread_id} - {full_message} ({current}/{total})")

        except Exception as e:
            self.logger.error(f"進捗更新処理中にエラーが発生: {e}")
            # エラーが発生しても進捗表示は継続
            fallback_message = f"処理中: {message}"
            if total > 0:
                self.update_progress(current, total, fallback_message)
            else:
                self.set_progress_indeterminate(fallback_message)

    def _update_system_info_with_progress(self, folder_name: str, current: int, total: int, percentage: int) -> None:
        """
        システム情報を進捗情報で更新

        Args:
            folder_name (str): 処理中のフォルダ名
            current (int): 現在の処理数
            total (int): 総処理数
            percentage (int): 進捗率
        """
        try:
            # アクティブなスレッド数を取得
            active_threads = 0
            if hasattr(self, 'thread_manager') and self.thread_manager:
                active_threads = self.thread_manager.get_active_thread_count()

            # インデックス済みフォルダ数を取得
            indexed_count = 0
            if hasattr(self, 'folder_tree_container'):
                indexed_count = len(self.folder_tree_container.get_indexed_folders())

            if total > 0:
                # 定進捗の場合
                system_info = (
                    f"インデックス: {indexed_count}フォルダ | "
                    f"処理中: {folder_name} ({current}/{total} - {percentage}%) | "
                    f"アクティブ: {active_threads}スレッド"
                )
            else:
                # 不定進捗の場合
                system_info = (
                    f"インデックス: {indexed_count}フォルダ | "
                    f"処理中: {folder_name} (スキャン中) | "
                    f"アクティブ: {active_threads}スレッド"
                )

            self.update_system_info(system_info)

        except Exception as e:
            self.logger.warning(f"システム情報の更新に失敗: {e}")
            # フォールバック
            self.update_system_info(f"処理中: {folder_name}")

    def _format_progress_message(self, message: str, current: int, total: int) -> str:
        """
        進捗メッセージをフォーマットして詳細情報を追加

        Args:
            message (str): 基本メッセージ
            current (int): 現在の処理数
            total (int): 総処理数

        Returns:
            str: フォーマットされた進捗メッセージ
        """
        try:
            # 進捗率を計算
            percentage = 0
            if total > 0:
                percentage = min(100, max(0, int((current / total) * 100)))

            # 処理段階を判定してアイコンと詳細情報を追加
            if "スキャン" in message:
                if total > 0:
                    return f"📁 {message} ({current}/{total}ファイル)"
                else:
                    return f"📁 {message}"
            elif "処理中:" in message:
                # ファイル名を抽出して短縮表示
                if total > 0:
                    # ファイル名を抽出（"処理中: filename.pdf" の形式から）
                    if ":" in message:
                        file_part = message.split(":", 1)[1].strip()
                        # ファイル名が長い場合は短縮
                        if len(file_part) > 30:
                            file_part = file_part[:27] + "..."
                        return f"📄 処理中: {file_part} ({current}/{total} - {percentage}%)"
                    else:
                        return f"📄 {message} ({current}/{total} - {percentage}%)"
                else:
                    return f"📄 {message}"
            elif "インデックス" in message:
                if total > 0:
                    return f"🔍 {message} ({current}/{total} - {percentage}%)"
                else:
                    return f"🔍 {message}"
            elif "監視" in message or "FileWatcher" in message:
                return f"👁️ {message}"
            elif "完了" in message:
                return f"✅ {message}"
            elif "エラー" in message:
                return f"❌ {message}"
            else:
                # その他のメッセージ
                if total > 0:
                    return f"⚙️ {message} ({current}/{total} - {percentage}%)"
                else:
                    return f"⚙️ {message}"

        except Exception as e:
            self.logger.warning(f"進捗メッセージのフォーマットに失敗: {e}")
            return message

    def _on_manager_status_changed(self, status_message: str) -> None:
        """マネージャー状態変更時の処理

        Args:
            status_message (str): 状態メッセージ
        """
        # システム情報にスレッド状態を追加
        try:
            indexed_count = len(self.folder_tree_container.get_indexed_folders())
            active_threads = self.thread_manager.get_active_thread_count() if hasattr(self, 'thread_manager') else 0

            if active_threads > 0:
                info_text = f"インデックス: {indexed_count}フォルダ, 処理中: {active_threads}スレッド"
            else:
                info_text = f"インデックス: {indexed_count}フォルダ, {status_message}"

            self.update_system_info(info_text)
        except Exception as e:
            self.logger.warning(f"システム情報の更新に失敗: {e}")
            self.update_system_info("システム情報取得中...")

    def _on_folder_excluded(self, folder_path: str) -> None:
        """
        フォルダが除外された時の処理

        Args:
            folder_path: 除外されたフォルダのパス
        """
        self.logger.info(f"フォルダが除外されました: {folder_path}")
        self.show_status_message(f"除外: {os.path.basename(folder_path)}", 3000)

        # システム情報を更新
        indexed_count = len(self.folder_tree_container.get_indexed_folders())
        excluded_count = len(self.folder_tree_container.get_excluded_folders())
        info_text = f"インデックス: {indexed_count}フォルダ"
        if excluded_count > 0:
            info_text += f", 除外: {excluded_count}フォルダ"
        self.update_system_info(info_text)

    def _on_folder_refresh(self) -> None:
        """
        フォルダツリーがリフレッシュされた時の処理
        """
        self.logger.info("フォルダツリーがリフレッシュされました")
        self.show_status_message("フォルダツリーを更新しました", 2000)

        # システム情報を更新
        indexed_count = len(self.folder_tree_container.get_indexed_folders())
        excluded_count = len(self.folder_tree_container.get_excluded_folders())
        info_text = f"インデックス: {indexed_count}フォルダ"
        if excluded_count > 0:
            info_text += f", 除外: {excluded_count}フォルダ"
        self.update_system_info(info_text)

    def closeEvent(self, event) -> None:
        """
        ウィンドウクローズイベントをハンドルします

        Args:
            event: クローズイベント
        """
        reply = QMessageBox.question(
            self,
            "終了確認",
            "DocMindを終了しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.logger.info("アプリケーションを終了します")

            # すべてのコンポーネントを適切にクリーンアップ
            self._cleanup_all_components()

            event.accept()
        else:
            event.ignore()

    def _cleanup_all_components(self):
        """
        すべてのコンポーネントをクリーンアップします
        """
        try:
            # フォルダツリーのクリーンアップ
            if hasattr(self, 'folder_tree_container') and self.folder_tree_container:
                self.folder_tree_container.tree_widget._cleanup_worker()
                self.logger.info("フォルダツリーをクリーンアップしました")

            # 検索インターフェースのクリーンアップ（ワーカースレッドがあれば）
            if hasattr(self, 'search_interface') and self.search_interface:
                # 実行中のタスクがあればキャンセル
                try:
                    if hasattr(self, 'search_worker') and self.search_worker.isRunning():
                        self.search_worker.cancel()
                        self.search_worker.wait()
                except:
                    pass
                self.logger.info("検索インターフェースをクリーンアップしました")

            # スレッドマネージャーのクリーンアップ
            if hasattr(self, 'thread_manager') and self.thread_manager:
                self.thread_manager.shutdown()
                self.logger.info("スレッドマネージャーをクリーンアップしました")

            # タイムアウトマネージャーのクリーンアップ
            if hasattr(self, 'timeout_manager') and self.timeout_manager:
                self.timeout_manager.cancel_all_timeouts()
                self.logger.info("タイムアウトマネージャーをクリーンアップしました")

            # 検索コンポーネントのクリーンアップ
            if hasattr(self, 'search_manager'):
                try:
                    self.search_manager.clear_suggestion_cache()
                except:
                    pass
                self.logger.info("検索マネージャーをクリーンアップしました")

            # プレビューウィジェットのクリーンアップ
            if hasattr(self, 'preview_widget') and self.preview_widget:
                self.preview_widget.clear_preview()
                self.logger.info("プレビューウィジェットをクリーンアップしました")

            # インデックス処理スレッドのクリーンアップ
            if hasattr(self, 'indexing_worker') and self.indexing_worker:
                try:
                    self.indexing_worker.stop()
                    if hasattr(self, 'indexing_thread') and self.indexing_thread:
                        if self.indexing_thread.isRunning():
                            self.indexing_thread.quit()
                            self.indexing_thread.wait(3000)  # 3秒待機
                        try:
                            self.indexing_thread.deleteLater()
                        except RuntimeError:
                            pass
                    try:
                        self.indexing_worker.deleteLater()
                    except RuntimeError:
                        pass
                    self.logger.info("インデックス処理スレッドをクリーンアップしました")
                except Exception as cleanup_error:
                    self.logger.debug(f"インデックス処理スレッドクリーンアップエラー: {cleanup_error}")
                    pass

        except Exception as e:
            self.logger.error(f"コンポーネントクリーンアップ中にエラーが発生しました: {e}")

    # 検索結果ウィジェットのシグナルハンドラー

    def _on_search_result_selected(self, result) -> None:
        """
        検索結果が選択された時の処理

        Args:
            result: 選択された検索結果
        """
        self.logger.info(f"検索結果が選択されました: {result.document.title}")
        self.document_selected.emit(result.document.file_path)
        self.show_status_message(f"選択: {result.document.title}", 3000)

        # プレビューペインに内容を表示
        self.preview_widget.display_document(result.document)

        # 検索語をハイライト
        if hasattr(result, 'highlighted_terms') and result.highlighted_terms:
            self.preview_widget.highlight_search_terms(result.highlighted_terms)

    def _on_preview_requested(self, result) -> None:
        """
        プレビューが要求された時の処理

        Args:
            result: プレビューが要求された検索結果
        """
        self.logger.info(f"プレビューが要求されました: {result.document.title}")
        self.document_selected.emit(result.document.file_path)
        self.show_status_message(f"プレビュー: {result.document.title}", 3000)

        # プレビューペインに内容を表示
        self.preview_widget.display_document(result.document)

        # 検索語をハイライト
        if hasattr(result, 'highlighted_terms') and result.highlighted_terms:
            self.preview_widget.highlight_search_terms(result.highlighted_terms)

    def _on_page_changed(self, page: int) -> None:
        """
        ページが変更された時の処理

        Args:
            page: 新しいページ番号
        """
        self.logger.debug(f"検索結果のページが変更されました: {page}")
        self.show_status_message(f"ページ {page} を表示中", 2000)

    def _on_sort_changed(self, sort_order) -> None:
        """
        ソート順が変更された時の処理

        Args:
            sort_order: 新しいソート順
        """
        self.logger.debug(f"検索結果のソート順が変更されました: {sort_order}")
        self.show_status_message("検索結果を並び替えました", 2000)

    def _on_filter_changed(self, filters: dict) -> None:
        """
        フィルターが変更された時の処理

        Args:
            filters: 新しいフィルター設定
        """
        self.logger.debug(f"検索結果のフィルターが変更されました: {filters}")
        self.show_status_message("検索結果をフィルタリングしました", 2000)

    # プレビューウィジェットのシグナルハンドラー

    def _on_preview_zoom_changed(self, zoom_level: int) -> None:
        """
        プレビューのズームレベルが変更された時の処理

        Args:
            zoom_level: 新しいズームレベル
        """
        self.logger.debug(f"プレビューのズームレベルが変更されました: {zoom_level}%")
        self.show_status_message(f"ズーム: {zoom_level}%", 2000)

    def _on_preview_format_changed(self, format_name: str) -> None:
        """
        プレビューの表示フォーマットが変更された時の処理

        Args:
            format_name: 新しい表示フォーマット名
        """
        self.logger.debug(f"プレビューの表示フォーマットが変更されました: {format_name}")
        self.show_status_message(f"表示形式: {format_name}", 2000)

    # 検索インターフェースのシグナルハンドラー

    def _on_search_requested(self, search_query) -> None:
        """
        検索要求時の処理

        Args:
            search_query: 検索クエリオブジェクト
        """
        self.logger.info(f"検索要求: '{search_query.query_text}' ({search_query.search_type.value})")

        if not hasattr(self, 'search_manager') or self.search_manager is None:
            error_msg = "検索機能が初期化されていません"
            self.logger.error(error_msg)
            self.search_interface.on_search_error(error_msg)
            return

        self.show_status_message(f"検索実行: '{search_query.query_text}'", 3000)

        # 検索ワーカースレッドを作成して実行
        self.search_worker = SearchWorkerThread(self.search_manager, search_query)
        self.search_worker.progress_updated.connect(self.search_interface.progress_widget.update_progress)
        self.search_worker.search_completed.connect(self._on_search_completed)
        self.search_worker.search_error.connect(self._on_search_error)
        self.search_worker.start()

    def _on_search_cancelled(self) -> None:
        """検索キャンセル時の処理"""
        self.logger.info("検索がキャンセルされました")
        self.show_status_message("検索がキャンセルされました", 3000)

        # 実際の検索キャンセル処理
        if hasattr(self, 'search_worker') and self.search_worker.isRunning():
            self.search_worker.cancel()
            self.search_worker.wait()

    def _on_search_completed(self, results, execution_time: float) -> None:
        """
        検索完了時の処理

        Args:
            results: 検索結果
            execution_time: 実行時間（秒）
        """
        self.logger.info(f"検索完了: {len(results)}件, {execution_time:.1f}秒")

        # 検索結果を表示
        self.search_results_widget.display_results(results)

        # 検索インターフェースに完了を通知
        self.search_interface.on_search_completed(results, execution_time)

        # ステータス更新
        result_count = len(results)
        self.show_status_message(f"検索完了: {result_count}件の結果 ({execution_time:.1f}秒)", 5000)

    def _on_search_error(self, error_message: str) -> None:
        """
        検索エラー時の処理

        Args:
            error_message: エラーメッセージ
        """
        self.logger.error(f"検索エラー: {error_message}")

        # 検索インターフェースにエラーを通知
        self.search_interface.on_search_error(error_message)

        # ステータス更新
        self.show_status_message("検索エラーが発生しました", 5000)

    def _on_search_text_changed(self, text: str) -> None:
        """
        検索テキスト変更時の処理（検索提案を更新）

        Args:
            text: 入力されたテキスト
        """
        if hasattr(self, 'search_manager') and self.search_manager and len(text.strip()) >= 2:
            try:
                suggestions = self.search_manager.get_search_suggestions(text.strip(), limit=10)
                self.search_interface.update_search_suggestions(suggestions)
            except Exception as e:
                self.logger.debug(f"検索提案の取得に失敗: {e}")
                # エラーが発生しても検索提案は必須機能ではないため、ログのみ出力
    # インデックス再構築関連のシグナルハンドラー

    def _on_rebuild_completed(self, thread_id: str, statistics: dict) -> None:
        """インデックス再構築完了時の処理
        
        Args:
            thread_id: 完了したスレッドID
            statistics: 処理統計情報
        """
        try:
            # タイムアウト監視をキャンセル
            self.timeout_manager.cancel_timeout(thread_id)
            
            # SearchManagerのキャッシュをクリア
            if hasattr(self, 'search_manager') and self.search_manager:
                self.search_manager.clear_suggestion_cache()
            
            # システム情報ラベルを更新
            self._update_system_info_after_rebuild(statistics)
            
            # フォルダツリーの状態を更新（既に_on_thread_finishedで実行済み）
            
            self.logger.info(f"インデックス再構築完了: {thread_id}")
            
        except Exception as e:
            self.logger.error(f"インデックス再構築完了処理でエラー: {e}")

    def _handle_rebuild_timeout(self, thread_id: str) -> None:
        """インデックス再構築タイムアウト時の処理
        
        Args:
            thread_id: タイムアウトが発生したスレッドID
        """
        try:
            self.logger.warning(f"インデックス再構築タイムアウト: {thread_id}")
            
            # タイムアウトダイアログを表示
            reply = QMessageBox.warning(
                self,
                "処理タイムアウト",
                "インデックス再構築が長時間応答していません。\n\n"
                "処理を中断しますか？\n\n"
                "注意: 中断すると部分的に処理されたインデックスが\n"
                "不整合な状態になる可能性があります。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # 強制停止処理
                self._force_stop_rebuild(thread_id)
            else:
                # ユーザーが継続を選択した場合、タイムアウト監視を再開
                self.timeout_manager.start_timeout(thread_id)
                
        except Exception as e:
            self.logger.error(f"タイムアウト処理でエラー: {e}")

    def _force_stop_rebuild(self, thread_id: str) -> None:
        """インデックス再構築を強制停止
        
        Args:
            thread_id: 停止対象のスレッドID
        """
        try:
            # スレッドを強制停止
            self.thread_manager.stop_thread(thread_id)
            
            # 部分的なインデックスをクリア
            self.index_manager.clear_index()
            
            # 進捗表示を非表示
            self.hide_progress("インデックス再構築が中断されました")
            
            # ユーザーに通知
            QMessageBox.information(
                self,
                "処理中断",
                "インデックス再構築が中断されました。\n\n"
                "部分的に処理されたインデックスはクリアされました。\n"
                "必要に応じて再度インデックス再構築を実行してください。"
            )
            
            self.logger.info(f"インデックス再構築強制停止完了: {thread_id}")
            
        except Exception as e:
            self.logger.error(f"強制停止処理でエラー: {e}")
            QMessageBox.critical(
                self,
                "エラー",
                f"インデックス再構築の停止処理でエラーが発生しました:\n{str(e)}"
            )

    def _update_system_info_after_rebuild(self, statistics: dict) -> None:
        """インデックス再構築後のシステム情報更新
        
        Args:
            statistics: 処理統計情報
        """
        try:
            # インデックス統計を取得
            if hasattr(self, 'index_manager') and self.index_manager:
                index_stats = self.index_manager.get_index_stats()
                document_count = index_stats.get('document_count', 0)
                
                # システム情報ラベルを更新
                if hasattr(self, 'system_info_label'):
                    files_processed = statistics.get('files_processed', 0)
                    self.system_info_label.setText(
                        f"インデックス済み: {document_count}ドキュメント | "
                        f"処理済み: {files_processed}ファイル"
                    )
                    
        except Exception as e:
            self.logger.error(f"システム情報更新でエラー: {e}")

    def _on_rebuild_error(self, thread_id: str, error_message: str) -> None:
        """インデックス再構築エラー時の処理
        
        Args:
            thread_id: エラーが発生したスレッドID
            error_message: エラーメッセージ
        """
        try:
            # タイムアウト監視をキャンセル
            self.timeout_manager.cancel_timeout(thread_id)
            
            # エラータイプに応じた処理分岐
            if "タイムアウト" in error_message:
                # タイムアウトエラーの場合は既に_handle_rebuild_timeoutで処理済み
                return
            elif "ファイルアクセス" in error_message or "権限" in error_message:
                # ファイルアクセスエラーの場合
                self._handle_file_access_error(thread_id, error_message)
            elif "メモリ" in error_message or "リソース" in error_message:
                # リソースエラーの場合
                self._handle_resource_error(thread_id, error_message)
            else:
                # その他のシステムエラー
                self._handle_system_error(thread_id, error_message)
                
        except Exception as e:
            self.logger.error(f"インデックス再構築エラー処理でエラー: {e}")

    def _handle_file_access_error(self, thread_id: str, error_message: str) -> None:
        """ファイルアクセスエラーの処理"""
        QMessageBox.warning(
            self,
            "ファイルアクセスエラー",
            f"一部のファイルにアクセスできませんでした:\n\n{error_message}\n\n"
            "ファイルの権限を確認するか、管理者権限で実行してください。"
        )

    def _handle_resource_error(self, thread_id: str, error_message: str) -> None:
        """リソースエラーの処理"""
        # 部分的なインデックスをクリア
        self.index_manager.clear_index()
        
        QMessageBox.critical(
            self,
            "リソースエラー",
            f"システムリソースが不足しています:\n\n{error_message}\n\n"
            "部分的に処理されたインデックスはクリアされました。\n"
            "他のアプリケーションを終了してから再試行してください。"
        )

    def _handle_system_error(self, thread_id: str, error_message: str) -> None:
        """システムエラーの処理"""
        # 部分的なインデックスをクリア
        self.index_manager.clear_index()
        
        QMessageBox.critical(
            self,
            "システムエラー",
            f"インデックス再構築中にシステムエラーが発生しました:\n\n{error_message}\n\n"
            "部分的に処理されたインデックスはクリアされました。\n"
            "しばらく待ってから再試行してください。"
        )
