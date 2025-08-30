"""
RebuildTimeoutManagerのテストケース

タイムアウト管理システムの動作を検証します。
"""

import sys
from unittest.mock import Mock, patch

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.core.rebuild_timeout_manager import RebuildTimeoutManager


@pytest.fixture(scope="session")
def qapp():
    """QApplicationのフィクスチャ"""
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    yield app


class TestRebuildTimeoutManager:
    """RebuildTimeoutManagerのテストクラス"""

    @pytest.fixture(autouse=True)
    def setup_method(self, qapp):
        """各テストメソッドの前に実行される初期化処理"""
        self.app = qapp
        self.timeout_manager = RebuildTimeoutManager(
            timeout_minutes=1
        )  # テスト用に1分に設定
        self.mock_timeout_handler = Mock()
        self.timeout_manager.timeout_occurred.connect(self.mock_timeout_handler)
        yield
        # teardown
        self.timeout_manager.cancel_all_timeouts()
        self.timeout_manager.deleteLater()

    def test_initialization(self):
        """初期化処理のテスト"""
        manager = RebuildTimeoutManager(timeout_minutes=30)

        assert manager.timeout_minutes == 30
        assert manager.timeout_milliseconds == 30 * 60 * 1000
        assert len(manager.active_timers) == 0

        manager.deleteLater()

    def test_start_timeout(self):
        """タイムアウト監視開始のテスト"""
        thread_id = "test_thread_001"

        # タイムアウト監視を開始
        self.timeout_manager.start_timeout(thread_id)

        # タイマーが作成されていることを確認
        assert thread_id in self.timeout_manager.active_timers
        assert self.timeout_manager.is_timeout_active(thread_id)

        # アクティブなタイムアウトリストに含まれていることを確認
        active_timeouts = self.timeout_manager.get_active_timeouts()
        assert thread_id in active_timeouts

    def test_cancel_timeout(self):
        """タイムアウト監視キャンセルのテスト"""
        thread_id = "test_thread_002"

        # タイムアウト監視を開始
        self.timeout_manager.start_timeout(thread_id)
        assert self.timeout_manager.is_timeout_active(thread_id)

        # タイムアウト監視をキャンセル
        self.timeout_manager.cancel_timeout(thread_id)

        # タイマーが削除されていることを確認
        assert thread_id not in self.timeout_manager.active_timers
        assert not self.timeout_manager.is_timeout_active(thread_id)

    def test_multiple_timeouts(self):
        """複数のタイムアウト監視のテスト"""
        thread_ids = ["thread_001", "thread_002", "thread_003"]

        # 複数のタイムアウト監視を開始
        for thread_id in thread_ids:
            self.timeout_manager.start_timeout(thread_id)

        # すべてのタイマーがアクティブであることを確認
        for thread_id in thread_ids:
            assert self.timeout_manager.is_timeout_active(thread_id)

        # アクティブなタイムアウトリストを確認
        active_timeouts = self.timeout_manager.get_active_timeouts()
        assert len(active_timeouts) == 3
        for thread_id in thread_ids:
            assert thread_id in active_timeouts

    def test_duplicate_timeout_start(self):
        """同じスレッドIDで複数回タイムアウト監視を開始するテスト"""
        thread_id = "test_thread_duplicate"

        # 最初のタイムアウト監視を開始
        self.timeout_manager.start_timeout(thread_id)
        first_timer = self.timeout_manager.active_timers[thread_id]

        # 同じスレッドIDで再度タイムアウト監視を開始
        self.timeout_manager.start_timeout(thread_id)
        second_timer = self.timeout_manager.active_timers[thread_id]

        # 新しいタイマーに置き換わっていることを確認
        assert first_timer != second_timer
        assert self.timeout_manager.is_timeout_active(thread_id)
        assert len(self.timeout_manager.active_timers) == 1

    def test_empty_thread_id(self):
        """空のスレッドIDでタイムアウト監視を開始するテスト"""
        # 空文字列でタイムアウト監視を開始
        self.timeout_manager.start_timeout("")

        # タイマーが作成されていないことを確認
        assert "" not in self.timeout_manager.active_timers
        assert len(self.timeout_manager.active_timers) == 0

    def test_cancel_nonexistent_timeout(self):
        """存在しないタイムアウト監視をキャンセルするテスト"""
        # 存在しないスレッドIDでキャンセルを実行
        # エラーが発生しないことを確認
        self.timeout_manager.cancel_timeout("nonexistent_thread")

        # 状態に変化がないことを確認
        assert len(self.timeout_manager.active_timers) == 0

    def test_cancel_all_timeouts(self):
        """すべてのタイムアウト監視をキャンセルするテスト"""
        thread_ids = ["thread_001", "thread_002", "thread_003"]

        # 複数のタイムアウト監視を開始
        for thread_id in thread_ids:
            self.timeout_manager.start_timeout(thread_id)

        assert len(self.timeout_manager.active_timers) == 3

        # すべてのタイムアウト監視をキャンセル
        self.timeout_manager.cancel_all_timeouts()

        # すべてのタイマーが削除されていることを確認
        assert len(self.timeout_manager.active_timers) == 0
        assert len(self.timeout_manager.get_active_timeouts()) == 0

    @patch("src.core.rebuild_timeout_manager.logger")
    def test_logging(self, mock_logger):
        """ログ出力のテスト"""
        thread_id = "test_thread_logging"

        # タイムアウト監視を開始
        self.timeout_manager.start_timeout(thread_id)

        # ログが出力されていることを確認
        mock_logger.info.assert_called()

        # タイムアウト監視をキャンセル
        self.timeout_manager.cancel_timeout(thread_id)

        # キャンセルのログが出力されていることを確認
        assert mock_logger.info.call_count >= 2


class TestRebuildTimeoutManagerIntegration:
    """RebuildTimeoutManagerの統合テストクラス"""

    def test_timeout_signal_emission(self, qapp):
        """タイムアウトシグナル送信の統合テスト"""
        # 短いタイムアウト時間でテスト（100ミリ秒）
        timeout_manager = RebuildTimeoutManager(timeout_minutes=0.001667)  # 約0.1秒

        # シグナルハンドラーを設定
        timeout_occurred = False
        received_thread_id = None

        def on_timeout(thread_id):
            nonlocal timeout_occurred, received_thread_id
            timeout_occurred = True
            received_thread_id = thread_id

        timeout_manager.timeout_occurred.connect(on_timeout)

        # タイムアウト監視を開始
        test_thread_id = "integration_test_thread"
        timeout_manager.start_timeout(test_thread_id)

        # タイムアウトが発生するまで待機
        QTest.qWait(200)  # 200ミリ秒待機

        # タイムアウトシグナルが送信されたことを確認
        assert timeout_occurred
        assert received_thread_id == test_thread_id

        # タイマーがクリーンアップされていることを確認
        assert test_thread_id not in timeout_manager.active_timers

        timeout_manager.deleteLater()


if __name__ == "__main__":
    pytest.main([__file__])
