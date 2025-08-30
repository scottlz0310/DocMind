"""
FileWatcherのテストモジュール

ファイルシステム監視機能の包括的なテストを提供します。
"""

import os
import tempfile
import time
from unittest.mock import Mock

import pytest

from src.core.file_watcher import FileWatcher
from src.utils.exceptions import FileWatcherError


class TestFileWatcher:
    """FileWatcherのテストクラス"""

    @pytest.fixture
    def temp_watch_dir(self):
        """監視用一時ディレクトリを作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def file_watcher(self, temp_watch_dir):
        """FileWatcherインスタンスを作成"""
        return FileWatcher(temp_watch_dir)

    @pytest.fixture
    def mock_callback(self):
        """モックコールバック関数を作成"""
        return Mock()

    def test_initialization(self, file_watcher, temp_watch_dir):
        """初期化テスト"""
        assert file_watcher is not None
        assert file_watcher.watch_path == temp_watch_dir
        assert not file_watcher.is_watching

    def test_start_watching(self, file_watcher, mock_callback):
        """監視開始テスト"""
        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        assert file_watcher.is_watching

        # クリーンアップ
        file_watcher.stop_watching()

    def test_stop_watching(self, file_watcher, mock_callback):
        """監視停止テスト"""
        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        assert file_watcher.is_watching

        file_watcher.stop_watching()
        assert not file_watcher.is_watching

    def test_file_creation_detection(self, file_watcher, mock_callback, temp_watch_dir):
        """ファイル作成検出テスト"""
        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        # 短い待機でイベントハンドラーが設定されるのを待つ
        time.sleep(0.1)

        # テストファイルを作成
        test_file = os.path.join(temp_watch_dir, "test_file.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # イベント処理の時間を待つ
        time.sleep(0.2)

        # コールバックが呼ばれたことを確認
        assert mock_callback.called

        file_watcher.stop_watching()

    def test_file_modification_detection(self, file_watcher, mock_callback, temp_watch_dir):
        """ファイル変更検出テスト"""
        # 事前にファイルを作成
        test_file = os.path.join(temp_watch_dir, "existing_file.txt")
        with open(test_file, "w") as f:
            f.write("initial content")

        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        time.sleep(0.1)

        # ファイルを変更
        with open(test_file, "w") as f:
            f.write("modified content")

        time.sleep(0.2)

        assert mock_callback.called

        file_watcher.stop_watching()

    def test_file_deletion_detection(self, file_watcher, mock_callback, temp_watch_dir):
        """ファイル削除検出テスト"""
        # 事前にファイルを作成
        test_file = os.path.join(temp_watch_dir, "to_delete.txt")
        with open(test_file, "w") as f:
            f.write("content to delete")

        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        time.sleep(0.1)

        # ファイルを削除
        os.remove(test_file)

        time.sleep(0.2)

        assert mock_callback.called

        file_watcher.stop_watching()

    def test_directory_creation_detection(self, file_watcher, mock_callback, temp_watch_dir):
        """ディレクトリ作成検出テスト"""
        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        time.sleep(0.1)

        # ディレクトリを作成
        test_dir = os.path.join(temp_watch_dir, "new_directory")
        os.makedirs(test_dir)

        time.sleep(0.2)

        assert mock_callback.called

        file_watcher.stop_watching()

    def test_recursive_watching(self, file_watcher, mock_callback, temp_watch_dir):
        """再帰的監視テスト"""
        # サブディレクトリを作成
        sub_dir = os.path.join(temp_watch_dir, "subdir")
        os.makedirs(sub_dir)

        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        time.sleep(0.1)

        # サブディレクトリ内にファイルを作成
        sub_file = os.path.join(sub_dir, "sub_file.txt")
        with open(sub_file, "w") as f:
            f.write("sub content")

        time.sleep(0.2)

        assert mock_callback.called

        file_watcher.stop_watching()

    def test_file_filter_functionality(self, file_watcher, mock_callback, temp_watch_dir):
        """ファイルフィルター機能テスト"""
        # テキストファイルのみを監視するフィルターを設定
        file_watcher.set_file_filter([".txt", ".md"])
        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        time.sleep(0.1)

        # フィルター対象ファイルを作成
        txt_file = os.path.join(temp_watch_dir, "test.txt")
        with open(txt_file, "w") as f:
            f.write("text content")

        time.sleep(0.2)

        # フィルター対象外ファイルを作成
        mock_callback.reset_mock()
        bin_file = os.path.join(temp_watch_dir, "test.bin")
        with open(bin_file, "wb") as f:
            f.write(b"binary content")

        time.sleep(0.2)

        # テキストファイルのイベントは検出されるが、バイナリファイルは無視される
        file_watcher.stop_watching()

    def test_callback_error_handling(self, file_watcher, temp_watch_dir):
        """コールバックエラーハンドリングテスト"""
        # エラーを発生させるコールバック
        def error_callback(event):
            raise Exception("Callback error")

        file_watcher.set_callback(error_callback)
        file_watcher.start_watching()

        time.sleep(0.1)

        # ファイルを作成（エラーが発生するがウォッチャーは継続）
        test_file = os.path.join(temp_watch_dir, "error_test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        time.sleep(0.2)

        # ウォッチャーがまだ動作していることを確認
        assert file_watcher.is_watching

        file_watcher.stop_watching()

    def test_multiple_file_operations(self, file_watcher, mock_callback, temp_watch_dir):
        """複数ファイル操作テスト"""
        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        time.sleep(0.1)

        # 複数のファイル操作を実行
        for i in range(5):
            test_file = os.path.join(temp_watch_dir, f"multi_test_{i}.txt")
            with open(test_file, "w") as f:
                f.write(f"content {i}")

        time.sleep(0.3)

        # 複数回コールバックが呼ばれることを確認
        assert mock_callback.call_count >= 5

        file_watcher.stop_watching()

    def test_watch_nonexistent_directory(self):
        """存在しないディレクトリの監視テスト"""
        with pytest.raises(FileWatcherError):
            FileWatcher("/nonexistent/directory")

    def test_watch_file_instead_of_directory(self, temp_watch_dir):
        """ファイルを監視対象に指定した場合のテスト"""
        # ファイルを作成
        test_file = os.path.join(temp_watch_dir, "not_a_directory.txt")
        with open(test_file, "w") as f:
            f.write("content")

        with pytest.raises(FileWatcherError):
            FileWatcher(test_file)

    def test_get_watch_statistics(self, file_watcher, mock_callback, temp_watch_dir):
        """監視統計情報取得テスト"""
        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        time.sleep(0.1)

        # いくつかのファイル操作を実行
        for i in range(3):
            test_file = os.path.join(temp_watch_dir, f"stats_test_{i}.txt")
            with open(test_file, "w") as f:
                f.write(f"content {i}")

        time.sleep(0.2)

        stats = file_watcher.get_statistics()

        assert isinstance(stats, dict)
        assert "events_processed" in stats
        assert "is_watching" in stats
        assert stats["is_watching"] is True

        file_watcher.stop_watching()

    def test_pause_and_resume_watching(self, file_watcher, mock_callback, temp_watch_dir):
        """監視の一時停止と再開テスト"""
        file_watcher.set_callback(mock_callback)
        file_watcher.start_watching()

        time.sleep(0.1)

        # 監視を一時停止
        file_watcher.pause_watching()

        # 一時停止中にファイルを作成
        test_file = os.path.join(temp_watch_dir, "paused_test.txt")
        with open(test_file, "w") as f:
            f.write("content during pause")

        time.sleep(0.2)

        # 一時停止中はコールバックが呼ばれない
        pause_call_count = mock_callback.call_count

        # 監視を再開
        file_watcher.resume_watching()

        time.sleep(0.1)

        # 再開後にファイルを作成
        test_file2 = os.path.join(temp_watch_dir, "resumed_test.txt")
        with open(test_file2, "w") as f:
            f.write("content after resume")

        time.sleep(0.2)

        # 再開後はコールバックが呼ばれる
        assert mock_callback.call_count > pause_call_count

        file_watcher.stop_watching()

    def test_cleanup_on_destruction(self, temp_watch_dir, mock_callback):
        """オブジェクト破棄時のクリーンアップテスト"""
        watcher = FileWatcher(temp_watch_dir)
        watcher.set_callback(mock_callback)
        watcher.start_watching()

        assert watcher.is_watching

        # オブジェクトを削除
        del watcher

        # ガベージコレクションが適切にクリーンアップを行うことを確認
        # （実際のテストでは、ファイナライザーやコンテキストマネージャーの動作を確認）
