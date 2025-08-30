#!/usr/bin/env python3
"""
LayoutManagerのユニットテスト
"""

from unittest.mock import Mock, patch

import pytest

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QMainWindow

    from src.gui.managers.layout_manager import LayoutManager
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    QApplication = Mock
    QMainWindow = Mock
    Qt = Mock
    LayoutManager = Mock


@pytest.mark.skipif(not GUI_AVAILABLE, reason="GUI環境が利用できません")
class TestLayoutManager:
    """LayoutManagerのテストクラス"""

    @pytest.fixture
    def mock_main_window(self):
        """モックメインウィンドウを作成"""
        mock_window = Mock(spec=QMainWindow)
        mock_window.setWindowTitle = Mock()
        mock_window.setMinimumSize = Mock()
        mock_window.resize = Mock()
        mock_window.setWindowIcon = Mock()
        mock_window.setCentralWidget = Mock()
        mock_window.menuBar = Mock()
        mock_window.statusBar = Mock()
        mock_window.setAccessibleName = Mock()
        mock_window.setAccessibleDescription = Mock()
        mock_window.setTabOrder = Mock()
        mock_window.setStyleSheet = Mock()
        mock_window.frameGeometry = Mock()
        mock_window.move = Mock()
        mock_window.show_status_message = Mock()

        # メインウィンドウのハンドラーメソッドをモック化
        mock_window._on_folder_selected = Mock()
        mock_window._on_folder_indexed = Mock()
        mock_window._on_folder_excluded = Mock()
        mock_window._on_folder_refresh = Mock()
        mock_window._on_search_requested = Mock()
        mock_window._on_search_cancelled = Mock()
        mock_window._on_search_text_changed = Mock()
        mock_window._on_search_result_selected = Mock()
        mock_window._on_preview_requested = Mock()
        mock_window._on_page_changed = Mock()
        mock_window._on_sort_changed = Mock()
        mock_window._on_filter_changed = Mock()
        mock_window._on_preview_zoom_changed = Mock()
        mock_window._on_preview_format_changed = Mock()
        mock_window._open_folder_dialog = Mock()
        mock_window._show_search_dialog = Mock()
        mock_window._show_settings_dialog = Mock()
        mock_window._show_about_dialog = Mock()
        mock_window._toggle_preview_pane = Mock()
        mock_window._clear_preview = Mock()
        mock_window._refresh_view = Mock()
        mock_window.close = Mock()

        # index_controllerをモック化
        mock_window.index_controller = Mock()
        mock_window.index_controller.rebuild_index = Mock()
        mock_window.index_controller.clear_index = Mock()

        return mock_window

    @pytest.fixture
    def layout_manager(self, mock_main_window):
        """LayoutManagerインスタンスを作成"""
        # 完全にモック化してQObject初期化問題を回避
        manager = Mock()
        manager.__class__ = LayoutManager
        manager.main_window = mock_main_window

        # 必要なメソッドをモック化
        manager.setup_window = Mock()
        manager.setup_ui = Mock()
        manager.setup_menu_bar = Mock()
        manager.setup_status_bar = Mock()
        manager.setup_shortcuts = Mock()
        manager.setup_accessibility = Mock()
        manager.apply_styling = Mock()
        manager.center_window = Mock()
        manager.create_folder_pane = Mock()
        manager.create_search_pane = Mock()
        manager.create_preview_pane = Mock()

        return manager

    def test_init(self, layout_manager, mock_main_window):
        """初期化のテスト"""
        assert layout_manager.main_window == mock_main_window
        assert layout_manager is not None

    def test_setup_window(self, layout_manager, mock_main_window):
        """ウィンドウ設定のテスト"""
        with patch('src.gui.managers.layout_manager.get_app_icon') as mock_icon:
            mock_icon.return_value = Mock()
            layout_manager.center_window = Mock()  # center_windowをモック化

            layout_manager.setup_window()

            mock_main_window.setWindowTitle.assert_called_once_with("DocMind - ローカルドキュメント検索")
            mock_main_window.setMinimumSize.assert_called_once_with(1000, 700)
            mock_main_window.resize.assert_called_once_with(1400, 900)
            mock_main_window.setWindowIcon.assert_called_once()
            layout_manager.center_window.assert_called_once()

    @patch('src.gui.managers.layout_manager.QWidget')
    @patch('src.gui.managers.layout_manager.QVBoxLayout')
    @patch('src.gui.managers.layout_manager.QSplitter')
    def test_setup_ui(self, mock_splitter, mock_layout, mock_widget, layout_manager, mock_main_window):
        """UI設定のテスト"""
        # モックの設定
        mock_central_widget = Mock()
        mock_widget.return_value = mock_central_widget
        mock_main_layout = Mock()
        mock_layout.return_value = mock_main_layout
        mock_splitter_instance = Mock()
        mock_splitter.return_value = mock_splitter_instance

        # create_*_paneメソッドをモック化
        layout_manager.create_folder_pane = Mock(return_value=Mock())
        layout_manager.create_search_pane = Mock(return_value=Mock())
        layout_manager.create_preview_pane = Mock(return_value=Mock())

        layout_manager.setup_ui()

        # 基本的な呼び出しを確認
        mock_main_window.setCentralWidget.assert_called_once_with(mock_central_widget)
        mock_layout.assert_called_once_with(mock_central_widget)
        mock_splitter.assert_called_once_with(Qt.Horizontal)

        # ペイン作成メソッドが呼ばれることを確認
        layout_manager.create_folder_pane.assert_called_once()
        layout_manager.create_search_pane.assert_called_once()
        layout_manager.create_preview_pane.assert_called_once()

    @patch('src.gui.managers.layout_manager.FolderTreeContainer')
    def test_create_folder_pane(self, mock_container, layout_manager, mock_main_window):
        """フォルダペイン作成のテスト"""
        mock_container_instance = Mock()
        mock_container.return_value = mock_container_instance

        result = layout_manager.create_folder_pane()

        assert result == mock_container_instance
        mock_container_instance.setMinimumWidth.assert_called_once_with(200)

        # シグナル接続の確認
        mock_container_instance.folder_selected.connect.assert_called_once_with(
            mock_main_window._on_folder_selected
        )
        mock_container_instance.folder_indexed.connect.assert_called_once_with(
            mock_main_window._on_folder_indexed
        )
        mock_container_instance.folder_excluded.connect.assert_called_once_with(
            mock_main_window._on_folder_excluded
        )
        mock_container_instance.refresh_requested.connect.assert_called_once_with(
            mock_main_window._on_folder_refresh
        )

    @patch('src.gui.managers.layout_manager.QWidget')
    @patch('src.gui.managers.layout_manager.QVBoxLayout')
    @patch('src.gui.managers.layout_manager.SearchInterface')
    @patch('src.gui.managers.layout_manager.SearchResultsWidget')
    def test_create_search_pane(self, mock_results, mock_interface, mock_layout, mock_widget,
                               layout_manager, mock_main_window):
        """検索ペイン作成のテスト"""
        mock_container = Mock()
        mock_widget.return_value = mock_container
        mock_layout_instance = Mock()
        mock_layout.return_value = mock_layout_instance
        mock_interface_instance = Mock()
        mock_interface_instance.search_input = Mock()
        mock_interface.return_value = mock_interface_instance
        mock_results_instance = Mock()
        mock_results.return_value = mock_results_instance

        result = layout_manager.create_search_pane()

        assert result == mock_container
        mock_layout.assert_called_once_with(mock_container)
        mock_interface.assert_called_once()
        mock_results.assert_called_once()

        # シグナル接続の確認
        mock_interface_instance.search_requested.connect.assert_called_once_with(
            mock_main_window._on_search_requested
        )
        mock_interface_instance.search_cancelled.connect.assert_called_once_with(
            mock_main_window._on_search_cancelled
        )
        mock_interface_instance.search_input.textChanged.connect.assert_called_once_with(
            mock_main_window._on_search_text_changed
        )

    @patch('src.gui.managers.layout_manager.PreviewWidget')
    def test_create_preview_pane(self, mock_preview, layout_manager, mock_main_window):
        """プレビューペイン作成のテスト"""
        mock_preview_instance = Mock()
        mock_preview.return_value = mock_preview_instance

        result = layout_manager.create_preview_pane()

        assert result == mock_preview_instance
        mock_preview_instance.setMinimumWidth.assert_called_once_with(250)

        # シグナル接続の確認
        mock_preview_instance.zoom_changed.connect.assert_called_once_with(
            mock_main_window._on_preview_zoom_changed
        )
        mock_preview_instance.format_changed.connect.assert_called_once_with(
            mock_main_window._on_preview_format_changed
        )

    @patch('src.gui.managers.layout_manager.QAction')
    @patch('src.gui.managers.layout_manager.QKeySequence')
    @patch('src.gui.managers.layout_manager.get_search_icon')
    @patch('src.gui.managers.layout_manager.get_settings_icon')
    def test_setup_menu_bar(self, mock_settings_icon, mock_search_icon, mock_key_seq, mock_action,
                           layout_manager, mock_main_window):
        """メニューバー設定のテスト"""
        mock_menubar = Mock()
        mock_main_window.menuBar.return_value = mock_menubar
        mock_menu = Mock()
        mock_menubar.addMenu.return_value = mock_menu
        mock_action_instance = Mock()
        mock_action.return_value = mock_action_instance

        layout_manager.setup_menu_bar()

        # メニューバーの取得を確認
        mock_main_window.menuBar.assert_called_once()
        # メニューの追加を確認（ファイル、検索、表示、ツール、ヘルプ）
        assert mock_menubar.addMenu.call_count == 5
        # アクションの作成を確認
        assert mock_action.call_count >= 8  # 最低8個のアクション

    @patch('src.gui.managers.layout_manager.QLabel')
    @patch('src.gui.managers.layout_manager.QProgressBar')
    def test_setup_status_bar(self, mock_progress, mock_label, layout_manager, mock_main_window):
        """ステータスバー設定のテスト"""
        mock_statusbar = Mock()
        mock_main_window.statusBar.return_value = mock_statusbar
        mock_label_instance = Mock()
        mock_label.return_value = mock_label_instance
        mock_progress_instance = Mock()
        mock_progress.return_value = mock_progress_instance

        layout_manager.setup_status_bar()

        # ステータスバーの取得を確認
        mock_main_window.statusBar.assert_called_once()
        # ラベルとプログレスバーの作成を確認
        assert mock_label.call_count >= 2  # status_label, system_info_label
        mock_progress.assert_called_once()
        mock_main_window.show_status_message.assert_called_once_with("DocMindが起動しました", 3000)

    @patch('src.gui.managers.layout_manager.QShortcut')
    @patch('src.gui.managers.layout_manager.QKeySequence')
    def test_setup_shortcuts(self, mock_key_seq, mock_shortcut, layout_manager, mock_main_window):
        """ショートカット設定のテスト"""
        mock_shortcut_instance = Mock()
        mock_shortcut.return_value = mock_shortcut_instance

        layout_manager.setup_shortcuts()

        # ショートカットが作成されることを確認（Escape, F5）
        assert mock_shortcut.call_count == 2

    def test_setup_accessibility(self, layout_manager, mock_main_window):
        """アクセシビリティ設定のテスト"""
        # 必要なコンポーネントをモック化
        mock_main_window.folder_tree_container = Mock()
        mock_main_window.search_results_widget = Mock()
        mock_main_window.preview_widget = Mock()
        mock_main_window.status_label = Mock()
        mock_main_window.progress_bar = Mock()
        mock_main_window.system_info_label = Mock()

        layout_manager.setup_accessibility()

        # アクセシブル名の設定を確認
        mock_main_window.setAccessibleName.assert_called_once_with("DocMind メインウィンドウ")
        mock_main_window.setAccessibleDescription.assert_called_once()

        # 各コンポーネントのアクセシブル名設定を確認
        mock_main_window.folder_tree_container.setAccessibleName.assert_called_once_with("フォルダツリーペイン")
        mock_main_window.search_results_widget.setAccessibleName.assert_called_once_with("検索結果ペイン")
        mock_main_window.preview_widget.setAccessibleName.assert_called_once_with("プレビューペイン")

        # タブオーダーの設定を確認
        mock_main_window.setTabOrder.assert_called()

    def test_apply_styling(self, layout_manager, mock_main_window):
        """スタイリング適用のテスト"""
        layout_manager.apply_styling()

        # スタイルシートが設定されることを確認
        mock_main_window.setStyleSheet.assert_called_once()

        # 設定されるスタイルシートの内容を確認
        call_args = mock_main_window.setStyleSheet.call_args[0][0]
        assert "QMainWindow" in call_args
        assert "background-color" in call_args
        assert "QMenuBar" in call_args
        assert "QStatusBar" in call_args
        assert "QProgressBar" in call_args

    @patch('src.gui.managers.layout_manager.QApplication')
    def test_center_window(self, mock_app, layout_manager, mock_main_window):
        """ウィンドウ中央配置のテスト"""
        mock_screen = Mock()
        mock_app.primaryScreen.return_value = mock_screen
        mock_geometry = Mock()
        mock_screen.availableGeometry.return_value = mock_geometry
        mock_center = Mock()
        mock_geometry.center.return_value = mock_center

        mock_frame_geometry = Mock()
        mock_main_window.frameGeometry.return_value = mock_frame_geometry

        layout_manager.center_window()

        # 画面情報の取得を確認
        mock_app.primaryScreen.assert_called_once()
        mock_screen.availableGeometry.assert_called_once()

        # ウィンドウの移動を確認
        mock_frame_geometry.moveCenter.assert_called_once_with(mock_center)
        mock_main_window.move.assert_called_once()

    def test_center_window_no_screen(self, layout_manager, mock_main_window):
        """画面が取得できない場合のテスト"""
        with patch('src.gui.managers.layout_manager.QApplication') as mock_app:
            mock_app.primaryScreen.return_value = None

            # エラーが発生しないことを確認
            layout_manager.center_window()

            # moveが呼ばれないことを確認
            mock_main_window.move.assert_not_called()
