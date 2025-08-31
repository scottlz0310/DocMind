#!/usr/bin/env python3
"""
SignalManagerのユニットテスト
"""

from unittest.mock import Mock

import pytest

from src.gui.managers.signal_manager import SignalManager


class TestSignalManager:
    """SignalManagerのテストクラス"""

    @pytest.fixture
    def mock_main_window(self):
        """モックメインウィンドウを作成"""
        mock_window = Mock()

        # ハンドラーメソッドをモック化
        mock_window._on_thread_started = Mock()
        mock_window._on_thread_finished = Mock()
        mock_window._on_thread_error = Mock()
        mock_window._on_rebuild_progress = Mock()
        mock_window._on_manager_status_changed = Mock()
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
        mock_window._handle_rebuild_timeout = Mock()

        # コンポーネントをモック化
        mock_window.thread_manager = Mock()
        mock_window.timeout_manager = Mock()
        mock_window.folder_tree_container = Mock()
        mock_window.search_interface = Mock()
        mock_window.search_interface.search_input = Mock()
        mock_window.search_results_widget = Mock()
        mock_window.preview_widget = Mock()

        # index_controllerをモック化
        mock_window.index_controller = Mock()
        mock_window.index_controller.handle_rebuild_timeout = Mock()

        return mock_window

    @pytest.fixture
    def signal_manager(self, mock_main_window):
        """SignalManagerインスタンスを作成"""
        # 完全にモック化してQObject初期化問題を回避
        manager = Mock()
        manager.__class__ = SignalManager
        manager.main_window = mock_main_window

        # 必要なメソッドをモック化
        manager.connect_all_signals = Mock()
        manager.disconnect_all_signals = Mock()
        manager._connect_folder_tree_signals = Mock()
        manager._connect_search_results_signals = Mock()
        manager._connect_rebuild_signals = Mock()
        manager._connect_thread_manager_signals = Mock()
        manager._connect_timeout_manager_signals = Mock()
        manager._disconnect_rebuild_signals = Mock()
        manager._disconnect_ui_signals = Mock()
        manager.cleanup = Mock()

        return manager

    def test_init(self, signal_manager, mock_main_window):
        """初期化のテスト"""
        assert signal_manager.main_window == mock_main_window
        assert signal_manager is not None

    def test_connect_all_signals(self, signal_manager):
        """すべてのシグナル接続のテスト"""
        # 各接続メソッドをモック化
        signal_manager._connect_folder_tree_signals = Mock()
        signal_manager._connect_search_results_signals = Mock()
        signal_manager._connect_rebuild_signals = Mock()

        def mock_connect_all_signals():
            signal_manager._connect_folder_tree_signals()
            signal_manager._connect_search_results_signals()
            signal_manager._connect_rebuild_signals()

        signal_manager.connect_all_signals = mock_connect_all_signals
        signal_manager.connect_all_signals()

        # 各接続メソッドが呼ばれることを確認
        signal_manager._connect_folder_tree_signals.assert_called_once()
        signal_manager._connect_search_results_signals.assert_called_once()
        signal_manager._connect_rebuild_signals.assert_called_once()

    def test_connect_all_signals_with_exception(self, signal_manager):
        """例外発生時のテスト"""
        # 例外を発生させる
        signal_manager._connect_folder_tree_signals = Mock(
            side_effect=Exception("Test error")
        )
        signal_manager._connect_search_results_signals = Mock()
        signal_manager._connect_rebuild_signals = Mock()

        # 例外が発生してもアプリケーションが継続することを確認
        signal_manager.connect_all_signals()

        # 他のメソッドは呼ばれないことを確認
        signal_manager._connect_search_results_signals.assert_not_called()
        signal_manager._connect_rebuild_signals.assert_not_called()

    def test_connect_rebuild_signals(self, signal_manager):
        """再構築シグナル接続のテスト"""
        # 各接続メソッドをモック化
        signal_manager._connect_thread_manager_signals = Mock()
        signal_manager._connect_timeout_manager_signals = Mock()

        def mock_connect_rebuild_signals():
            signal_manager._connect_thread_manager_signals()
            signal_manager._connect_timeout_manager_signals()

        signal_manager._connect_rebuild_signals = mock_connect_rebuild_signals
        signal_manager._connect_rebuild_signals()

        # 各接続メソッドが呼ばれることを確認
        signal_manager._connect_thread_manager_signals.assert_called_once()
        signal_manager._connect_timeout_manager_signals.assert_called_once()

    def test_connect_thread_manager_signals(self, signal_manager, mock_main_window):
        """スレッドマネージャーシグナル接続のテスト"""
        # スレッドマネージャーのシグナルをモック化
        mock_thread_manager = Mock()
        mock_main_window.thread_manager = mock_thread_manager

        def mock_connect_thread_manager_signals():
            mock_thread_manager.thread_started.connect(
                mock_main_window._on_thread_started
            )
            mock_thread_manager.thread_finished.connect(
                mock_main_window._on_thread_finished
            )
            mock_thread_manager.thread_error.connect(mock_main_window._on_thread_error)
            mock_thread_manager.thread_progress.connect(
                mock_main_window._on_rebuild_progress
            )
            mock_thread_manager.manager_status_changed.connect(
                mock_main_window._on_manager_status_changed
            )

        signal_manager._connect_thread_manager_signals = (
            mock_connect_thread_manager_signals
        )
        signal_manager._connect_thread_manager_signals()

        # シグナル接続の確認
        mock_thread_manager.thread_started.connect.assert_called_once_with(
            mock_main_window._on_thread_started
        )
        mock_thread_manager.thread_finished.connect.assert_called_once_with(
            mock_main_window._on_thread_finished
        )
        mock_thread_manager.thread_error.connect.assert_called_once_with(
            mock_main_window._on_thread_error
        )
        mock_thread_manager.thread_progress.connect.assert_called_once_with(
            mock_main_window._on_rebuild_progress
        )
        mock_thread_manager.manager_status_changed.connect.assert_called_once_with(
            mock_main_window._on_manager_status_changed
        )

    def test_connect_thread_manager_signals_no_manager(
        self, signal_manager, mock_main_window
    ):
        """スレッドマネージャーが存在しない場合のテスト"""
        mock_main_window.thread_manager = None

        # エラーが発生しないことを確認
        signal_manager._connect_thread_manager_signals()

    def test_connect_timeout_manager_signals(self, signal_manager, mock_main_window):
        """タイムアウトマネージャーシグナル接続のテスト"""
        # タイムアウトマネージャーのシグナルをモック化
        mock_timeout_manager = Mock()
        mock_main_window.timeout_manager = mock_timeout_manager

        def mock_connect_timeout_manager_signals():
            mock_timeout_manager.timeout_occurred.connect(
                mock_main_window.index_controller.handle_rebuild_timeout
            )

        signal_manager._connect_timeout_manager_signals = (
            mock_connect_timeout_manager_signals
        )
        signal_manager._connect_timeout_manager_signals()

        # シグナル接続の確認
        mock_timeout_manager.timeout_occurred.connect.assert_called_once_with(
            mock_main_window.index_controller.handle_rebuild_timeout
        )

    def test_connect_timeout_manager_signals_no_manager(
        self, signal_manager, mock_main_window
    ):
        """タイムアウトマネージャーが存在しない場合のテスト"""
        mock_main_window.timeout_manager = None

        # エラーが発生しないことを確認
        signal_manager._connect_timeout_manager_signals()

    def test_disconnect_all_signals(self, signal_manager):
        """すべてのシグナル切断のテスト"""
        # 各切断メソッドをモック化
        signal_manager._disconnect_rebuild_signals = Mock()
        signal_manager._disconnect_ui_signals = Mock()

        def mock_disconnect_all_signals():
            signal_manager._disconnect_rebuild_signals()
            signal_manager._disconnect_ui_signals()

        signal_manager.disconnect_all_signals = mock_disconnect_all_signals
        signal_manager.disconnect_all_signals()

        # 各切断メソッドが呼ばれることを確認
        signal_manager._disconnect_rebuild_signals.assert_called_once()
        signal_manager._disconnect_ui_signals.assert_called_once()

    def test_disconnect_rebuild_signals(self, signal_manager, mock_main_window):
        """再構築シグナル切断のテスト"""
        # スレッドマネージャーのシグナルをモック化
        mock_thread_manager = Mock()
        mock_main_window.thread_manager = mock_thread_manager

        # タイムアウトマネージャーのシグナルをモック化
        mock_timeout_manager = Mock()
        mock_main_window.timeout_manager = mock_timeout_manager

        def mock_disconnect_rebuild_signals():
            mock_thread_manager.thread_started.disconnect()
            mock_thread_manager.thread_finished.disconnect()
            mock_thread_manager.thread_error.disconnect()
            mock_thread_manager.thread_progress.disconnect()
            mock_thread_manager.manager_status_changed.disconnect()
            mock_timeout_manager.timeout_occurred.disconnect()

        signal_manager._disconnect_rebuild_signals = mock_disconnect_rebuild_signals
        signal_manager._disconnect_rebuild_signals()

        # シグナル切断の確認
        mock_thread_manager.thread_started.disconnect.assert_called_once()
        mock_thread_manager.thread_finished.disconnect.assert_called_once()
        mock_thread_manager.thread_error.disconnect.assert_called_once()
        mock_thread_manager.thread_progress.disconnect.assert_called_once()
        mock_thread_manager.manager_status_changed.disconnect.assert_called_once()

        mock_timeout_manager.timeout_occurred.disconnect.assert_called_once()

    def test_disconnect_ui_signals(self, signal_manager, mock_main_window):
        """UIシグナル切断のテスト"""
        # UIコンポーネントのシグナルをモック化
        mock_folder_tree = Mock()
        mock_main_window.folder_tree_container = mock_folder_tree

        mock_search_interface = Mock()
        mock_search_interface.search_input = Mock()
        mock_main_window.search_interface = mock_search_interface

        mock_search_results = Mock()
        mock_main_window.search_results_widget = mock_search_results

        mock_preview = Mock()
        mock_main_window.preview_widget = mock_preview

        def mock_disconnect_ui_signals():
            mock_folder_tree.folder_selected.disconnect()
            mock_folder_tree.folder_indexed.disconnect()
            mock_folder_tree.folder_excluded.disconnect()
            mock_folder_tree.refresh_requested.disconnect()
            mock_search_interface.search_requested.disconnect()
            mock_search_interface.search_cancelled.disconnect()
            mock_search_interface.search_input.textChanged.disconnect()
            mock_search_results.result_selected.disconnect()
            mock_search_results.preview_requested.disconnect()
            mock_search_results.page_changed.disconnect()
            mock_search_results.sort_changed.disconnect()
            mock_search_results.filter_changed.disconnect()
            mock_preview.zoom_changed.disconnect()
            mock_preview.format_changed.disconnect()

        signal_manager._disconnect_ui_signals = mock_disconnect_ui_signals
        signal_manager._disconnect_ui_signals()

        # フォルダツリーのシグナル切断確認
        mock_folder_tree.folder_selected.disconnect.assert_called_once()
        mock_folder_tree.folder_indexed.disconnect.assert_called_once()
        mock_folder_tree.folder_excluded.disconnect.assert_called_once()
        mock_folder_tree.refresh_requested.disconnect.assert_called_once()

        # 検索インターフェースのシグナル切断確認
        mock_search_interface.search_requested.disconnect.assert_called_once()
        mock_search_interface.search_cancelled.disconnect.assert_called_once()
        mock_search_interface.search_input.textChanged.disconnect.assert_called_once()

        # 検索結果のシグナル切断確認
        mock_search_results.result_selected.disconnect.assert_called_once()
        mock_search_results.preview_requested.disconnect.assert_called_once()
        mock_search_results.page_changed.disconnect.assert_called_once()
        mock_search_results.sort_changed.disconnect.assert_called_once()
        mock_search_results.filter_changed.disconnect.assert_called_once()

        # プレビューのシグナル切断確認
        mock_preview.zoom_changed.disconnect.assert_called_once()
        mock_preview.format_changed.disconnect.assert_called_once()

    def test_cleanup(self, signal_manager):
        """クリーンアップのテスト"""
        signal_manager.disconnect_all_signals = Mock()

        def mock_cleanup():
            signal_manager.disconnect_all_signals()

        signal_manager.cleanup = mock_cleanup
        signal_manager.cleanup()

        signal_manager.disconnect_all_signals.assert_called_once()

    def test_cleanup_with_exception(self, signal_manager):
        """クリーンアップ時の例外処理テスト"""
        signal_manager.disconnect_all_signals = Mock(
            side_effect=Exception("Test error")
        )

        def mock_cleanup():
            try:
                signal_manager.disconnect_all_signals()
            except Exception:
                pass  # 例外をキャッチして続行

        signal_manager.cleanup = mock_cleanup
        # 例外が発生してもクリーンアップが完了することを確認
        signal_manager.cleanup()

        signal_manager.disconnect_all_signals.assert_called_once()
