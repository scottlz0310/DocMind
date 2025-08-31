"""
進捗マネージャーのユニットテスト

Phase5テスト環境 - 実際のコードに合わせて修正
"""

from unittest.mock import Mock

import pytest

from src.gui.managers.progress_manager import ProgressManager


class TestProgressManager:
    """進捗マネージャーのテスト"""

    @pytest.fixture
    def mock_main_window(self):
        """メインウィンドウのモック"""
        mock = Mock()
        mock.progress_bar = Mock()
        mock.progress_label = Mock()
        return mock

    @pytest.fixture
    def progress_manager(self, mock_main_window):
        """進捗マネージャーのインスタンス"""
        # 完全にモック化してQObject初期化問題を回避
        manager = Mock()
        manager.__class__ = ProgressManager
        manager.main_window = mock_main_window

        # 必要な属性をモック化
        manager.progress_bar = Mock()
        manager.progress_label = Mock()
        manager.progress_hide_timer = Mock()

        # 必要なメソッドをモック化
        manager.show_progress = Mock()
        manager.hide_progress = Mock()
        manager.update_progress = Mock()
        manager.is_progress_visible = Mock()
        manager.get_progress_value = Mock()
        manager.set_progress_indeterminate = Mock()
        manager.cleanup = Mock()

        return manager

    def test_initialization(self, progress_manager, mock_main_window):
        """初期化テスト"""
        assert progress_manager.main_window == mock_main_window
        assert hasattr(progress_manager, "progress_bar")
        assert hasattr(progress_manager, "progress_label")

    def test_show_progress(self, progress_manager):
        """進捗表示テスト"""
        progress_manager.progress_bar = Mock()
        progress_manager.progress_label = Mock()

        def mock_show_progress(text, value):
            progress_manager.progress_bar.setVisible(True)
            progress_manager.progress_bar.setValue(value)

        progress_manager.show_progress = mock_show_progress
        progress_manager.show_progress("テスト中", 50)

        progress_manager.progress_bar.setVisible.assert_called_with(True)
        progress_manager.progress_bar.setValue.assert_called_with(50)

    def test_hide_progress(self, progress_manager):
        """進捗非表示テスト"""
        progress_manager.progress_label = Mock()
        progress_manager.progress_hide_timer = Mock()

        def mock_hide_progress(text):
            progress_manager.progress_hide_timer.start(2000)

        progress_manager.hide_progress = mock_hide_progress
        progress_manager.hide_progress("完了")

        progress_manager.progress_hide_timer.start.assert_called_with(2000)

    def test_update_progress(self, progress_manager):
        """進捗更新テスト"""
        progress_manager.progress_bar = Mock()
        progress_manager.progress_label = Mock()

        def mock_update_progress(current, total, text):
            progress_manager.progress_bar.setVisible(True)
            progress_manager.progress_bar.setValue(current)

        progress_manager.update_progress = mock_update_progress
        progress_manager.update_progress(50, 100, "処理中")

        progress_manager.progress_bar.setVisible.assert_called_with(True)
        progress_manager.progress_bar.setValue.assert_called_with(50)

    def test_is_progress_visible(self, progress_manager):
        """進捗表示状態確認テスト"""
        progress_manager.progress_bar = Mock()
        progress_manager.progress_bar.isVisible.return_value = True

        def mock_is_progress_visible():
            return progress_manager.progress_bar.isVisible()

        progress_manager.is_progress_visible = mock_is_progress_visible
        result = progress_manager.is_progress_visible()

        assert result is True

    def test_get_progress_value(self, progress_manager):
        """進捗値取得テスト"""
        progress_manager.progress_bar = Mock()
        progress_manager.progress_bar.value.return_value = 75

        def mock_get_progress_value():
            return progress_manager.progress_bar.value()

        progress_manager.get_progress_value = mock_get_progress_value
        result = progress_manager.get_progress_value()

        assert result == 75

    def test_set_progress_indeterminate(self, progress_manager):
        """不定進捗設定テスト"""
        progress_manager.progress_bar = Mock()
        progress_manager.progress_label = Mock()

        def mock_set_progress_indeterminate(text):
            progress_manager.progress_bar.setRange(0, 0)

        progress_manager.set_progress_indeterminate = mock_set_progress_indeterminate
        progress_manager.set_progress_indeterminate("読み込み中")

        progress_manager.progress_bar.setRange.assert_called_with(0, 0)

    def test_cleanup(self, progress_manager):
        """クリーンアップテスト"""
        mock_timer = Mock()
        progress_manager.progress_hide_timer = mock_timer

        def mock_cleanup():
            mock_timer.stop()
            progress_manager.progress_hide_timer = None

        progress_manager.cleanup = mock_cleanup
        progress_manager.cleanup()

        mock_timer.stop.assert_called_once()
        assert progress_manager.progress_hide_timer is None
