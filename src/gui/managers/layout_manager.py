#!/usr/bin/env python3
"""
レイアウト管理マネージャー

main_window.pyから分離されたUI構築・レイアウト管理機能を提供します。
ウィンドウ設定、UIコンポーネント作成、メニューバー、ステータスバー、
ショートカット、アクセシビリティ、スタイリングを管理します。
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.gui.folder_tree import FolderTreeContainer
from src.gui.preview_widget import PreviewWidget
from src.gui.resources import get_app_icon, get_search_icon, get_settings_icon
from src.gui.search_interface import SearchInterface
from src.gui.search_results import SearchResultsWidget
from src.utils.logging_config import LoggerMixin

if TYPE_CHECKING:
    from src.gui.main_window import MainWindow


class LayoutManager(QObject, LoggerMixin):
    """
    レイアウト管理マネージャー

    UI構築、レイアウト設定、メニューバー、ステータスバー、
    ショートカット、アクセシビリティ、スタイリングを管理します。
    """

    def __init__(self, main_window: "MainWindow"):
        """
        レイアウトマネージャーの初期化

        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        self.main_window = main_window

    def setup_window(self) -> None:
        """ウィンドウの基本設定を行います"""
        self.main_window.setWindowTitle("DocMind - ローカルドキュメント検索")
        self.main_window.setMinimumSize(1000, 700)
        self.main_window.resize(1400, 900)

        # ウィンドウアイコンの設定
        self.main_window.setWindowIcon(get_app_icon())

        # ウィンドウを画面中央に配置
        self.center_window()

    def setup_ui(self) -> None:
        """メインUIレイアウトを設定します"""
        # 中央ウィジェットの作成
        central_widget = QWidget()
        self.main_window.setCentralWidget(central_widget)

        # メインレイアウトの作成
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 3ペインスプリッターの作成
        self.main_window.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_window.main_splitter)

        # 左ペイン: フォルダツリー
        self.main_window.folder_pane = self.create_folder_pane()
        self.main_window.main_splitter.addWidget(self.main_window.folder_pane)

        # 中央ペイン: 検索結果
        self.main_window.search_pane = self.create_search_pane()
        self.main_window.main_splitter.addWidget(self.main_window.search_pane)

        # 右ペイン: ドキュメントプレビュー
        self.main_window.preview_pane = self.create_preview_pane()
        self.main_window.main_splitter.addWidget(self.main_window.preview_pane)

        # スプリッターのサイズ比率を設定 (25%, 40%, 35%)
        self.main_window.main_splitter.setSizes([250, 400, 350])
        self.main_window.main_splitter.setCollapsible(
            0, False
        )  # 左ペインは折りたたみ不可
        self.main_window.main_splitter.setCollapsible(
            1, False
        )  # 中央ペインは折りたたみ不可
        self.main_window.main_splitter.setCollapsible(
            2, True
        )  # 右ペインは折りたたみ可能

    def create_folder_pane(self) -> QWidget:
        """左ペイン（フォルダツリー）を作成"""
        # フォルダツリーコンテナを作成
        self.main_window.folder_tree_container = FolderTreeContainer()
        self.main_window.folder_tree_container.setMinimumWidth(200)

        # シグナル接続
        self.main_window.folder_tree_container.folder_selected.connect(
            self.main_window._on_folder_selected
        )
        self.main_window.folder_tree_container.folder_indexed.connect(
            self.main_window._on_folder_indexed
        )
        self.main_window.folder_tree_container.folder_excluded.connect(
            self.main_window._on_folder_excluded
        )
        self.main_window.folder_tree_container.refresh_requested.connect(
            self.main_window._on_folder_refresh
        )

        return self.main_window.folder_tree_container

    def create_search_pane(self) -> QWidget:
        """中央ペイン（検索結果）を作成"""
        # 中央ペインのコンテナを作成
        search_container = QWidget()
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(5, 5, 5, 5)
        search_layout.setSpacing(5)

        # 検索インターフェースを作成
        self.main_window.search_interface = SearchInterface()
        search_layout.addWidget(self.main_window.search_interface)

        # 検索結果ウィジェットを作成
        self.main_window.search_results_widget = SearchResultsWidget()
        self.main_window.search_results_widget.setMinimumWidth(300)
        search_layout.addWidget(self.main_window.search_results_widget)

        # 検索インターフェースのシグナル接続
        self.main_window.search_interface.search_requested.connect(
            self.main_window._on_search_requested
        )
        self.main_window.search_interface.search_cancelled.connect(
            self.main_window._on_search_cancelled
        )

        # 検索提案機能の接続
        self.main_window.search_interface.search_input.textChanged.connect(
            self.main_window._on_search_text_changed
        )

        # 検索結果ウィジェットのシグナル接続
        self.main_window.search_results_widget.result_selected.connect(
            self.main_window._on_search_result_selected
        )
        self.main_window.search_results_widget.preview_requested.connect(
            self.main_window._on_preview_requested
        )
        self.main_window.search_results_widget.page_changed.connect(
            self.main_window._on_page_changed
        )
        self.main_window.search_results_widget.sort_changed.connect(
            self.main_window._on_sort_changed
        )
        self.main_window.search_results_widget.filter_changed.connect(
            self.main_window._on_filter_changed
        )

        search_container.setMinimumWidth(400)
        return search_container

    def create_preview_pane(self) -> QWidget:
        """右ペイン（ドキュメントプレビュー）を作成"""
        # プレビューウィジェットを作成
        self.main_window.preview_widget = PreviewWidget()
        self.main_window.preview_widget.setMinimumWidth(250)

        # シグナル接続
        self.main_window.preview_widget.zoom_changed.connect(
            self.main_window._on_preview_zoom_changed
        )
        self.main_window.preview_widget.format_changed.connect(
            self.main_window._on_preview_format_changed
        )

        return self.main_window.preview_widget

    def setup_menu_bar(self) -> None:
        """メニューバーを設定します"""
        menubar = self.main_window.menuBar()

        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル(&F)")

        # フォルダを開くアクション
        self.main_window.open_folder_action = QAction(
            "フォルダを開く(&O)...", self.main_window
        )
        self.main_window.open_folder_action.setShortcut(QKeySequence.Open)
        self.main_window.open_folder_action.setStatusTip(
            "検索対象のフォルダを選択します"
        )
        self.main_window.open_folder_action.triggered.connect(
            self.main_window._open_folder_dialog
        )
        file_menu.addAction(self.main_window.open_folder_action)

        file_menu.addSeparator()

        # 終了アクション
        self.main_window.exit_action = QAction("終了(&X)", self.main_window)
        self.main_window.exit_action.setShortcut(QKeySequence.Quit)
        self.main_window.exit_action.setStatusTip("アプリケーションを終了します")
        self.main_window.exit_action.triggered.connect(self.main_window.close)
        file_menu.addAction(self.main_window.exit_action)

        # 検索メニュー
        search_menu = menubar.addMenu("検索(&S)")

        # 検索実行アクション
        self.main_window.search_action = QAction(
            get_search_icon(), "検索(&S)...", self.main_window
        )
        self.main_window.search_action.setShortcut(QKeySequence.Find)
        self.main_window.search_action.setStatusTip("ドキュメント検索を実行します")
        self.main_window.search_action.triggered.connect(
            self.main_window._show_search_dialog
        )
        search_menu.addAction(self.main_window.search_action)

        # インデックス再構築アクション
        self.main_window.rebuild_index_action = QAction(
            "インデックス再構築(&R)", self.main_window
        )
        self.main_window.rebuild_index_action.setShortcut(QKeySequence("Ctrl+R"))
        self.main_window.rebuild_index_action.setStatusTip(
            "検索インデックスを再構築します"
        )
        self.main_window.rebuild_index_action.triggered.connect(
            self.main_window.index_controller.rebuild_index
        )
        search_menu.addAction(self.main_window.rebuild_index_action)

        # インデックスクリアアクション
        self.main_window.clear_index_action = QAction(
            "インデックスクリア(&C)", self.main_window
        )
        self.main_window.clear_index_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.main_window.clear_index_action.setStatusTip(
            "検索インデックスをクリアします"
        )
        self.main_window.clear_index_action.triggered.connect(
            self.main_window.index_controller.clear_index
        )
        search_menu.addAction(self.main_window.clear_index_action)

        # 表示メニュー
        view_menu = menubar.addMenu("表示(&V)")

        # プレビューペイン表示切り替え
        self.main_window.toggle_preview_action = QAction(
            "プレビューペイン(&P)", self.main_window
        )
        self.main_window.toggle_preview_action.setCheckable(True)
        self.main_window.toggle_preview_action.setChecked(True)
        self.main_window.toggle_preview_action.setShortcut(QKeySequence("F3"))
        self.main_window.toggle_preview_action.setStatusTip(
            "プレビューペインの表示を切り替えます"
        )
        self.main_window.toggle_preview_action.triggered.connect(
            self.main_window._toggle_preview_pane
        )
        view_menu.addAction(self.main_window.toggle_preview_action)

        # ツールメニュー
        tools_menu = menubar.addMenu("ツール(&T)")

        # 設定アクション
        self.main_window.settings_action = QAction(
            get_settings_icon(), "設定(&S)...", self.main_window
        )
        self.main_window.settings_action.setShortcut(QKeySequence.Preferences)
        self.main_window.settings_action.setStatusTip("アプリケーション設定を開きます")
        self.main_window.settings_action.triggered.connect(
            self.main_window._show_settings_dialog
        )
        tools_menu.addAction(self.main_window.settings_action)

        # ヘルプメニュー
        help_menu = menubar.addMenu("ヘルプ(&H)")

        # バージョン情報アクション
        self.main_window.about_action = QAction(
            "DocMindについて(&A)...", self.main_window
        )
        self.main_window.about_action.setStatusTip("アプリケーションの情報を表示します")
        self.main_window.about_action.triggered.connect(
            self.main_window._show_about_dialog
        )
        help_menu.addAction(self.main_window.about_action)

    def setup_status_bar(self) -> None:
        """ステータスバーを設定します"""
        self.main_window.status_bar = self.main_window.statusBar()

        # メインステータスラベル
        self.main_window.status_label = QLabel("準備完了")
        self.main_window.status_bar.addWidget(self.main_window.status_label)

        # 進捗バー（通常は非表示）
        self.main_window.progress_bar = QProgressBar()
        self.main_window.progress_bar.setVisible(False)
        self.main_window.progress_bar.setMaximumWidth(200)
        self.main_window.status_bar.addPermanentWidget(self.main_window.progress_bar)

        # 進捗ラベル（progress_manager用）
        self.main_window.progress_label = self.main_window.status_label

        # システム情報ラベル
        self.main_window.system_info_label = QLabel("インデックス: 未作成")
        self.main_window.status_bar.addPermanentWidget(
            self.main_window.system_info_label
        )

        # 初期メッセージを表示
        self.main_window.show_status_message("DocMindが起動しました", 3000)

    def setup_shortcuts(self) -> None:
        """キーボードショートカットを設定します"""
        # 既にメニューアクションで設定済みのショートカット以外を追加

        # Escキーでプレビューペインをクリア
        self.main_window.clear_preview_shortcut = QShortcut(
            QKeySequence("Escape"), self.main_window
        )
        self.main_window.clear_preview_shortcut.activated.connect(
            self.main_window._clear_preview
        )

        # F5キーでリフレッシュ
        self.main_window.refresh_shortcut = QShortcut(
            QKeySequence("F5"), self.main_window
        )
        self.main_window.refresh_shortcut.activated.connect(
            self.main_window._refresh_view
        )

    def setup_accessibility(self) -> None:
        """アクセシビリティ機能を設定します"""
        # ウィンドウのアクセシブル名と説明を設定
        self.main_window.setAccessibleName("DocMind メインウィンドウ")
        self.main_window.setAccessibleDescription(
            "ローカルドキュメント検索アプリケーションのメインウィンドウ"
        )

        # 各ペインにアクセシブル名を設定
        self.main_window.folder_tree_container.setAccessibleName("フォルダツリーペイン")
        self.main_window.folder_tree_container.setAccessibleDescription(
            "検索対象フォルダの階層構造を表示します"
        )

        self.main_window.search_results_widget.setAccessibleName("検索結果ペイン")
        self.main_window.search_results_widget.setAccessibleDescription(
            "検索結果の一覧を表示します"
        )

        self.main_window.preview_widget.setAccessibleName("プレビューペイン")
        self.main_window.preview_widget.setAccessibleDescription(
            "選択されたドキュメントの内容をプレビュー表示します"
        )

        # ステータスバーコンポーネントにアクセシブル名を設定
        self.main_window.status_label.setAccessibleName("ステータス情報")
        self.main_window.progress_bar.setAccessibleName("進捗インジケーター")
        self.main_window.system_info_label.setAccessibleName("システム情報")

        # タブオーダーの設定（キーボードナビゲーション用）
        self.main_window.setTabOrder(
            self.main_window.folder_tree_container,
            self.main_window.search_results_widget,
        )
        self.main_window.setTabOrder(
            self.main_window.search_results_widget, self.main_window.preview_widget
        )

    def apply_styling(self) -> None:
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

        self.main_window.setStyleSheet(style_sheet)

    def center_window(self) -> None:
        """ウィンドウを画面中央に配置します"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.main_window.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.main_window.move(window_geometry.topLeft())
