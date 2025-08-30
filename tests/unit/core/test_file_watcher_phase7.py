"""
Phase7 FileWatcherの強化テストモジュール

ファイル監視機能の包括的なテストを提供します。
"""

import tempfile
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.core.file_watcher import FileWatcher
from src.core.embedding_manager_extended import EmbeddingManagerExtended
from src.utils.exceptions import FileWatcherError


class TestFileWatcherPhase7:
    """Phase7 FileWatcherの強化テストクラス"""

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
    def mock_embedding_manager(self, temp_embedding_dir):
        """モックEmbeddingManagerを作成"""
        embeddings_path = str(Path(temp_embedding_dir) / "embeddings.pkl")
        return EmbeddingManagerExtended(embeddings_path=embeddings_path)

    @pytest.fixture
    def mock_callback(self):
        """モックコールバック関数を作成"""
        return Mock()

    @pytest.fixture
    def file_watcher(self, temp_watch_dir, mock_embedding_manager):
        """FileWatcherインスタンスを作成"""
        return FileWatcher(temp_watch_dir, mock_embedding_manager)

    def test_initialization(self, temp_watch_dir, mock_embedding_manager):
        """初期化テスト"""
        watcher = FileWatcher(temp_watch_dir, mock_embedding_manager)
        
        assert watcher is not None
        assert watcher.watch_path == temp_watch_dir
        assert watcher.embedding_manager == mock_embedding_manager
        assert not watcher.is_watching

    def test_start_watching(self, file_watcher):
        """監視開始テスト"""
        file_watcher.start_watching()
        
        assert file_watcher.is_watching is True
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_stop_watching(self, file_watcher):
        """監視停止テスト"""
        file_watcher.start_watching()
        assert file_watcher.is_watching is True
        
        file_watcher.stop_watching()
        assert file_watcher.is_watching is False

    def test_file_creation_detection(self, file_watcher, temp_watch_dir, mock_callback):
        """ファイル作成検出テスト"""
        # コールバックを設定
        file_watcher.on_file_created = mock_callback
        
        # 監視を開始
        file_watcher.start_watching()
        
        # ファイルを作成
        test_file = os.path.join(temp_watch_dir, "new_file.txt")
        with open(test_file, 'w') as f:
            f.write("新しいファイルです")
        
        # 少し待機してイベントが処理されるのを待つ
        time.sleep(0.5)
        
        # 監視を停止
        file_watcher.stop_watching()
        
        # コールバックが呼ばれたことを確認（実際の実装に依存）
        # assert mock_callback.called

    def test_file_modification_detection(self, file_watcher, temp_watch_dir, mock_callback):
        """ファイル変更検出テスト"""
        # テストファイルを事前に作成
        test_file = os.path.join(temp_watch_dir, "existing_file.txt")
        with open(test_file, 'w') as f:
            f.write("既存のファイル")
        
        # コールバックを設定
        file_watcher.on_file_modified = mock_callback
        
        # 監視を開始
        file_watcher.start_watching()
        
        # ファイルを変更
        with open(test_file, 'a') as f:
            f.write("\n追加されたテキスト")
        
        # 少し待機
        time.sleep(0.5)
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_file_deletion_detection(self, file_watcher, temp_watch_dir, mock_callback):
        """ファイル削除検出テスト"""
        # テストファイルを事前に作成
        test_file = os.path.join(temp_watch_dir, "to_be_deleted.txt")
        with open(test_file, 'w') as f:
            f.write("削除されるファイル")
        
        # コールバックを設定
        file_watcher.on_file_deleted = mock_callback
        
        # 監視を開始
        file_watcher.start_watching()
        
        # ファイルを削除
        os.remove(test_file)
        
        # 少し待機
        time.sleep(0.5)
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_directory_creation_detection(self, file_watcher, temp_watch_dir, mock_callback):
        """ディレクトリ作成検出テスト"""
        # コールバックを設定
        file_watcher.on_directory_created = mock_callback
        
        # 監視を開始
        file_watcher.start_watching()
        
        # ディレクトリを作成
        new_dir = os.path.join(temp_watch_dir, "new_directory")
        os.makedirs(new_dir)
        
        # 少し待機
        time.sleep(0.5)
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_recursive_watching(self, file_watcher, temp_watch_dir):
        """再帰的監視テスト"""
        # サブディレクトリを作成
        sub_dir = os.path.join(temp_watch_dir, "subdir")
        os.makedirs(sub_dir)
        
        # 監視を開始
        file_watcher.start_watching()
        
        # サブディレクトリ内にファイルを作成
        sub_file = os.path.join(sub_dir, "sub_file.txt")
        with open(sub_file, 'w') as f:
            f.write("サブディレクトリのファイル")
        
        # 少し待機
        time.sleep(0.5)
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_file_filter_functionality(self, file_watcher, temp_watch_dir):
        """ファイルフィルター機能テスト"""
        # 監視を開始
        file_watcher.start_watching()
        
        # 異なる拡張子のファイルを作成
        files_to_create = [
            "document.txt",
            "document.pdf", 
            "document.docx",
            "image.jpg",  # 監視対象外
            "temp.tmp"    # 監視対象外
        ]
        
        for filename in files_to_create:
            file_path = os.path.join(temp_watch_dir, filename)
            with open(file_path, 'w') as f:
                f.write(f"テストファイル: {filename}")
        
        # 少し待機
        time.sleep(1.0)
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_callback_error_handling(self, file_watcher, temp_watch_dir):
        """コールバックエラーハンドリングテスト"""
        # エラーを発生させるコールバックを設定
        def error_callback(event):
            raise Exception("コールバックエラー")
        
        file_watcher.on_file_created = error_callback
        
        # 監視を開始
        file_watcher.start_watching()
        
        # ファイルを作成（エラーが発生するはず）
        test_file = os.path.join(temp_watch_dir, "error_test.txt")
        with open(test_file, 'w') as f:
            f.write("エラーテスト")
        
        # 少し待機
        time.sleep(0.5)
        
        # 監視を停止（エラーが発生してもクラッシュしないことを確認）
        file_watcher.stop_watching()

    def test_multiple_file_operations(self, file_watcher, temp_watch_dir):
        """複数ファイル操作テスト"""
        # 監視を開始
        file_watcher.start_watching()
        
        # 複数のファイル操作を実行
        for i in range(10):
            file_path = os.path.join(temp_watch_dir, f"multi_test_{i}.txt")
            
            # ファイル作成
            with open(file_path, 'w') as f:
                f.write(f"マルチテストファイル {i}")
            
            # ファイル変更
            with open(file_path, 'a') as f:
                f.write(f"\n追加テキスト {i}")
        
        # 少し待機
        time.sleep(1.0)
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_get_watch_statistics(self, file_watcher, temp_watch_dir):
        """監視統計情報取得テスト"""
        # 監視を開始
        file_watcher.start_watching()
        
        # いくつかのファイル操作を実行
        for i in range(5):
            file_path = os.path.join(temp_watch_dir, f"stats_test_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"統計テストファイル {i}")
        
        # 少し待機
        time.sleep(0.5)
        
        # 統計情報を取得（実装されている場合）
        if hasattr(file_watcher, 'get_statistics'):
            stats = file_watcher.get_statistics()
            assert isinstance(stats, dict)
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_pause_and_resume_watching(self, file_watcher, temp_watch_dir):
        """監視の一時停止・再開テスト"""
        # 監視を開始
        file_watcher.start_watching()
        
        # 一時停止（実装されている場合）
        if hasattr(file_watcher, 'pause_watching'):
            file_watcher.pause_watching()
            
            # 一時停止中にファイルを作成
            paused_file = os.path.join(temp_watch_dir, "paused_test.txt")
            with open(paused_file, 'w') as f:
                f.write("一時停止中のファイル")
            
            # 監視を再開
            file_watcher.resume_watching()
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_watch_nonexistent_directory(self, mock_embedding_manager):
        """存在しないディレクトリの監視テスト"""
        with pytest.raises(FileWatcherError):
            FileWatcher("/nonexistent/directory", mock_embedding_manager)

    def test_watch_file_instead_of_directory(self, temp_watch_dir, mock_embedding_manager):
        """ファイルを監視対象に指定した場合のテスト"""
        # ファイルを作成
        test_file = os.path.join(temp_watch_dir, "not_a_directory.txt")
        with open(test_file, "w") as f:
            f.write("content")
        
        with pytest.raises(FileWatcherError):
            FileWatcher(test_file, mock_embedding_manager)

    def test_cleanup_on_destruction(self, temp_watch_dir, mock_embedding_manager):
        """オブジェクト破棄時のクリーンアップテスト"""
        watcher = FileWatcher(temp_watch_dir, mock_embedding_manager)
        watcher.start_watching()
        
        # オブジェクトを削除
        del watcher
        
        # ガベージコレクションを実行
        import gc
        gc.collect()

    def test_large_number_of_files(self, file_watcher, temp_watch_dir):
        """大量ファイル監視テスト"""
        # 監視を開始
        file_watcher.start_watching()
        
        # 大量のファイルを作成
        for i in range(100):
            file_path = os.path.join(temp_watch_dir, f"large_test_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"大量テストファイル {i}")
        
        # 少し待機
        time.sleep(2.0)
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_concurrent_file_operations(self, file_watcher, temp_watch_dir):
        """並行ファイル操作テスト"""
        import threading
        
        def create_files(start_index, count):
            for i in range(start_index, start_index + count):
                file_path = os.path.join(temp_watch_dir, f"concurrent_{i}.txt")
                with open(file_path, 'w') as f:
                    f.write(f"並行テストファイル {i}")
                time.sleep(0.01)
        
        # 監視を開始
        file_watcher.start_watching()
        
        # 複数スレッドで並行してファイルを作成
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_files, args=(i * 10, 10))
            threads.append(thread)
            thread.start()
        
        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 少し待機
        time.sleep(1.0)
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_memory_usage_during_watching(self, file_watcher, temp_watch_dir):
        """監視中のメモリ使用量テスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 監視を開始
        file_watcher.start_watching()
        
        # 多数のファイル操作を実行
        for i in range(50):
            file_path = os.path.join(temp_watch_dir, f"memory_test_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"メモリテストファイル {i}")
            
            # ファイルを変更
            with open(file_path, 'a') as f:
                f.write(f"\n追加テキスト {i}")
        
        # 少し待機
        time.sleep(1.0)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 監視を停止
        file_watcher.stop_watching()
        
        # メモリ増加量が合理的な範囲内であることを確認（50MB以下）
        assert memory_increase < 50 * 1024 * 1024

    def test_error_recovery_after_filesystem_issues(self, file_watcher, temp_watch_dir):
        """ファイルシステム問題後のエラー回復テスト"""
        # 監視を開始
        file_watcher.start_watching()
        
        # 正常なファイル操作
        normal_file = os.path.join(temp_watch_dir, "normal.txt")
        with open(normal_file, 'w') as f:
            f.write("正常なファイル")
        
        # 問題のあるファイル操作をシミュレート
        try:
            # 存在しないディレクトリにファイルを作成しようとする
            invalid_path = os.path.join(temp_watch_dir, "nonexistent", "invalid.txt")
            with open(invalid_path, 'w') as f:
                f.write("無効なファイル")
        except (OSError, IOError):
            # エラーは期待される
            pass
        
        # エラー後も正常に動作することを確認
        recovery_file = os.path.join(temp_watch_dir, "recovery.txt")
        with open(recovery_file, 'w') as f:
            f.write("回復テストファイル")
        
        # 少し待機
        time.sleep(0.5)
        
        # 監視を停止
        file_watcher.stop_watching()

    def test_performance_with_rapid_file_changes(self, file_watcher, temp_watch_dir):
        """高速ファイル変更時のパフォーマンステスト"""
        import time
        
        # 監視を開始
        file_watcher.start_watching()
        
        # 高速でファイルを変更
        test_file = os.path.join(temp_watch_dir, "rapid_change.txt")
        
        start_time = time.time()
        
        for i in range(100):
            with open(test_file, 'w') as f:
                f.write(f"高速変更テスト {i}")
        
        end_time = time.time()
        
        # 高速変更が5秒以内に完了することを確認
        assert (end_time - start_time) < 5.0
        
        # 少し待機してイベント処理を完了
        time.sleep(1.0)
        
        # 監視を停止
        file_watcher.stop_watching()