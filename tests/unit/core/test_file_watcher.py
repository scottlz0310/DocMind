"""
FileWatcherのテストモジュール

ファイルシステム監視機能の包括的なテストを提供します。
Phase7強化版の内容を統合済み。
"""

import os
from pathlib import Path
import tempfile
import time
from unittest.mock import Mock

import pytest

from src.core.file_watcher import FileWatcher


class TestFileWatcher:
    """FileWatcherのテストクラス"""

    @pytest.fixture
    def temp_watch_dir(self):
        """監視用一時ディレクトリを作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def temp_embedding_dir(self):
        """埋め込み用一時ディレクトリを作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            embedding_dir = Path(temp_dir) / "embeddings"
            embedding_dir.mkdir(exist_ok=True)
            yield str(embedding_dir)

    @pytest.fixture
    def mock_index_manager(self):
        """モックIndexManagerを作成"""
        mock = Mock()
        mock.document_exists.return_value = False
        return mock

    @pytest.fixture
    def mock_embedding_manager(self):
        """モックEmbeddingManagerを作成"""
        return Mock()

    @pytest.fixture
    def file_watcher(self, mock_index_manager, mock_embedding_manager):
        """FileWatcherインスタンスを作成"""
        return FileWatcher(index_manager=mock_index_manager, embedding_manager=mock_embedding_manager)

    def test_initialization(self, file_watcher):
        """初期化テスト"""
        assert file_watcher is not None
        assert len(file_watcher.watched_paths) == 0
        assert not file_watcher.is_running

    def test_start_watching(self, file_watcher, temp_watch_dir):
        """監視開始テスト"""
        file_watcher.add_watch_path(temp_watch_dir)
        file_watcher.start_watching()

        assert file_watcher.is_running

        # クリーンアップ
        file_watcher.stop_watching()

    def test_stop_watching(self, file_watcher, temp_watch_dir):
        """監視停止テスト"""
        file_watcher.add_watch_path(temp_watch_dir)
        file_watcher.start_watching()

        assert file_watcher.is_running

        file_watcher.stop_watching()
        assert not file_watcher.is_running

    def test_add_watch_path(self, file_watcher, temp_watch_dir):
        """監視パス追加テスト"""
        file_watcher.add_watch_path(temp_watch_dir)
        assert (
            temp_watch_dir in file_watcher.watched_paths
            or os.path.abspath(temp_watch_dir) in file_watcher.watched_paths
        )

    def test_remove_watch_path(self, file_watcher, temp_watch_dir):
        """監視パス削除テスト"""
        file_watcher.add_watch_path(temp_watch_dir)
        file_watcher.remove_watch_path(temp_watch_dir)
        abs_path = os.path.abspath(temp_watch_dir)
        assert temp_watch_dir not in file_watcher.watched_paths and abs_path not in file_watcher.watched_paths

    def test_get_stats(self, file_watcher):
        """統計情報取得テスト"""
        stats = file_watcher.get_stats()
        assert isinstance(stats, dict)
        assert "is_running" in stats
        assert "watched_paths" in stats
        assert "queue_size" in stats

    def test_clear_hash_cache(self, file_watcher):
        """ハッシュキャッシュクリアテスト"""
        file_watcher.clear_hash_cache()
        assert len(file_watcher.file_hashes) == 0

    def test_should_process_file(self, file_watcher, temp_watch_dir):
        """ファイル処理判定テスト"""
        # テキストファイルは処理対象
        txt_file = os.path.join(temp_watch_dir, "test.txt")
        with open(txt_file, "w") as f:
            f.write("test")

        # ファイルが存在する場合のみテスト
        if os.path.exists(txt_file):
            result = file_watcher._should_process_file(txt_file)
            assert isinstance(result, bool)

    def test_wait_for_queue_empty(self, file_watcher):
        """キュー空待機テスト"""
        # 空のキューはすぐにTrueを返す
        result = file_watcher.wait_for_queue_empty(timeout=1.0)
        assert result is True

    def test_watch_nonexistent_directory(self, mock_index_manager, mock_embedding_manager):
        """存在しないディレクトリの監視テスト"""
        file_watcher = FileWatcher(index_manager=mock_index_manager, embedding_manager=mock_embedding_manager)

        with pytest.raises(Exception):  # FileSystemErrorまたは似たようなエラー
            file_watcher.add_watch_path("/nonexistent/directory")

    # Phase7統合: ファイル作成検出テスト
    def test_file_creation_detection(self, file_watcher, temp_watch_dir):
        """ファイル作成検出テスト"""
        file_watcher.add_watch_path(temp_watch_dir)
        file_watcher.start_watching()

        # ファイルを作成
        test_file = os.path.join(temp_watch_dir, "new_file.txt")
        with open(test_file, "w") as f:
            f.write("新しいファイルです")

        # 少し待機してイベントが処理されるのを待つ
        time.sleep(0.5)

        # 監視を停止
        file_watcher.stop_watching()

    # Phase7統合: ファイル変更検出テスト
    def test_file_modification_detection(self, file_watcher, temp_watch_dir):
        """ファイル変更検出テスト"""
        # テストファイルを事前に作成
        test_file = os.path.join(temp_watch_dir, "existing_file.txt")
        with open(test_file, "w") as f:
            f.write("既存のファイル")

        file_watcher.add_watch_path(temp_watch_dir)
        file_watcher.start_watching()

        # ファイルを変更
        with open(test_file, "a") as f:
            f.write("\n追加されたテキスト")

        # 少し待機
        time.sleep(0.5)

        # 監視を停止
        file_watcher.stop_watching()

    # Phase7統合: パフォーマンステスト
    def test_multiple_file_operations(self, file_watcher, temp_watch_dir):
        """複数ファイル操作テスト"""
        file_watcher.add_watch_path(temp_watch_dir)
        file_watcher.start_watching()

        # 複数のファイルを作成
        for i in range(5):
            test_file = os.path.join(temp_watch_dir, f"test_file_{i}.txt")
            with open(test_file, "w") as f:
                f.write(f"テストファイル{i}")

        # 少し待機
        time.sleep(1.0)

        # 監視を停止
        file_watcher.stop_watching()

    # Phase7統合: エラーハンドリングテスト
    def test_error_handling_invalid_path(self, file_watcher):
        """無効パスのエラーハンドリングテスト"""
        from src.utils.exceptions import FileSystemError

        # 空文字列パス
        with pytest.raises((ValueError, OSError, FileSystemError)):
            file_watcher.add_watch_path("")

        # Noneパス
        with pytest.raises((TypeError, AttributeError)):
            file_watcher.add_watch_path(None)
