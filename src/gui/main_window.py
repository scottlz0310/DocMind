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

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QMenuBar, QStatusBar, QProgressBar, QLabel, QMessageBox,
    QFileDialog, QApplication, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QAction, QShortcut

from src.utils.config import Config
from src.utils.exceptions import DocMindException
from src.utils.error_handler import handle_exceptions, get_global_error_handler
from src.utils.graceful_degradation import get_global_degradation_manager
from src.utils.logging_config import LoggerMixin
from src.gui.resources import get_app_icon, get_search_icon, get_settings_icon
from src.gui.folder_tree import FolderTreeContainer
from src.gui.search_results import SearchResultsWidget
from src.gui.preview_widget import PreviewWidget
from src.gui.search_interface import SearchInterface, SearchWorkerThread
from src.core.search_manager import SearchManager
from src.core.index_manager import IndexManager
from src.core.embedding_manager import EmbeddingManager
from src.data.database import DatabaseManager


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
            
            # 検索マネージャーの初期化
            self.search_manager = SearchManager(
                self.index_manager,
                self.embedding_manager
            )
            
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
        """インデックス再構築を実行します（プレースホルダー）"""
        reply = QMessageBox.question(
            self,
            "インデックス再構築",
            "インデックスを再構築しますか？\n\n"
            "この操作には時間がかかる場合があります。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.show_progress("インデックスを再構築中...", 0)
            # TODO: 実際のインデックス再構築処理を実装
            QTimer.singleShot(2000, lambda: self.hide_progress("インデックス再構築が完了しました"))
    
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
    
    def _show_settings_dialog(self) -> None:
        """設定ダイアログを表示します"""
        # TODO: 設定ダイアログの実装
        QMessageBox.information(
            self,
            "設定",
            "設定機能はタスク14で実装されます。"
        )
    
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
    
    def show_progress(self, message: str, value: int) -> None:
        """
        進捗バーを表示します
        
        Args:
            message: 進捗メッセージ
            value: 進捗値（0-100、0で不定進捗）
        """
        self.status_label.setText(message)
        self.progress_bar.setVisible(True)
        
        if value == 0:
            # 不定進捗
            self.progress_bar.setRange(0, 0)
        else:
            # 定進捗
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(value)
    
    def hide_progress(self, completion_message: str = "") -> None:
        """
        進捗バーを非表示にします
        
        Args:
            completion_message: 完了メッセージ
        """
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        if completion_message:
            self.show_status_message(completion_message, 3000)
        else:
            self.status_label.setText("準備完了")
    
    def update_system_info(self, info: str) -> None:
        """
        システム情報を更新します
        
        Args:
            info: システム情報文字列
        """
        self.system_info_label.setText(info)
    
    def _connect_folder_tree_signals(self) -> None:
        """フォルダツリーのシグナルを接続します"""
        # フォルダツリーのシグナルはすでに_create_folder_paneで接続済み
        pass
    
    def _connect_search_results_signals(self) -> None:
        """検索結果ウィジェットのシグナルを接続します"""
        # 検索結果ウィジェットのシグナルはすでに_create_search_paneで接続済み
        pass
    
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
        
        # 進捗表示
        self.show_progress(f"インデックス作成中: {os.path.basename(folder_path)}", 0)
        
        # TODO: 実際のインデックス処理を実行
        # 現在はプレースホルダー
        QTimer.singleShot(2000, lambda: self.hide_progress("インデックス作成完了"))
        
        # システム情報を更新
        indexed_count = len(self.folder_tree_container.get_indexed_folders())
        self.update_system_info(f"インデックス: {indexed_count}フォルダ")
    
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