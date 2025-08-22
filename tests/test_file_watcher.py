"""
FileWatcherクラスのユニットテスト

ファイルシステム監視と増分更新機能のテストを行います。
"""

import os
import time
import tempfile
import shutil
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.core.file_watcher import FileWatcher, FileChangeEvent, FileHashInfo
from src.core.index_manager import IndexManager
from src.core.embedding_manager import EmbeddingManager
from src.core.document_processor import DocumentProcessor
from src.data.models import Document, FileType
from src.utils.config import Config
from src.utils.exceptions import FileSystemError


class TestFileWatcher:
    """FileWatcherクラスのテストクラス"""
    
    @pytest.fixture
    def temp_dir(self):
        """テスト用の一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_index_manager(self):
        """モックIndexManagerを作成"""
        mock = Mock(spec=IndexManager)
        mock.document_exists.return_value = False
        return mock
    
    @pytest.fixture
    def mock_embedding_manager(self):
        """モックEmbeddingManagerを作成"""
        mock = Mock(spec=EmbeddingManager)
        return mock
    
    @pytest.fixture
    def mock_document_processor(self, temp_dir):
        """モックDocumentProcessorを作成"""
        mock = Mock(spec=DocumentProcessor)
        mock.is_supported_file.return_value = True
        
        # テスト用の実際のファイルを作成
        test_file_path = os.path.join(temp_dir, "test.txt")
        with open(test_file_path, 'w') as f:
            f.write("Test content")
        
        # テスト用のDocumentオブジェクトを返すように設定
        test_doc = Document(
            id="test_id",
            file_path=test_file_path,
            title="Test Document",
            content="Test content",
            file_type=FileType.TEXT,
            size=100,
            created_date=time.time(),
            modified_date=time.time(),
            indexed_date=time.time()
        )
        mock.process_file.return_value = test_doc
        return mock
    
    @pytest.fixture
    def mock_config(self, temp_dir):
        """モックConfigを作成"""
        mock = Mock(spec=Config)
        mock.data_dir = temp_dir
        return mock
    
    @pytest.fixture
    def file_watcher(self, mock_index_manager, mock_embedding_manager, 
                    mock_document_processor, mock_config):
        """FileWatcherインスタンスを作成"""
        return FileWatcher(
            index_manager=mock_index_manager,
            embedding_manager=mock_embedding_manager,
            document_processor=mock_document_processor,
            config=mock_config
        )
    
    def test_init(self, file_watcher):
        """初期化のテスト"""
        assert file_watcher.watched_paths == set()
        assert file_watcher.is_running is False
        assert file_watcher.observer is None
        assert file_watcher.worker_thread is None
        assert isinstance(file_watcher.file_hashes, dict)
        assert isinstance(file_watcher.stats, dict)
    
    def test_add_watch_path_valid(self, file_watcher, temp_dir):
        """有効なパスの監視追加テスト"""
        file_watcher.add_watch_path(temp_dir)
        assert os.path.abspath(temp_dir) in file_watcher.watched_paths
    
    def test_add_watch_path_invalid(self, file_watcher):
        """無効なパスの監視追加テスト"""
        with pytest.raises(FileSystemError):
            file_watcher.add_watch_path("/nonexistent/path")
    
    def test_add_watch_path_file(self, file_watcher, temp_dir):
        """ファイルパスの監視追加テスト（エラーになるべき）"""
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        
        with pytest.raises(FileSystemError):
            file_watcher.add_watch_path(test_file)
    
    def test_remove_watch_path(self, file_watcher, temp_dir):
        """監視パス削除のテスト"""
        file_watcher.add_watch_path(temp_dir)
        file_watcher.remove_watch_path(temp_dir)
        assert os.path.abspath(temp_dir) not in file_watcher.watched_paths
    
    def test_should_process_file_supported(self, file_watcher):
        """サポートされているファイルの処理判定テスト"""
        # DocumentProcessorのis_supported_fileがTrueを返すように設定済み
        assert file_watcher._should_process_file("test.txt") is True
    
    def test_should_process_file_unsupported(self, file_watcher):
        """サポートされていないファイルの処理判定テスト"""
        file_watcher.document_processor.is_supported_file.return_value = False
        assert file_watcher._should_process_file("test.exe") is False
    
    def test_should_process_file_excluded_pattern(self, file_watcher):
        """除外パターンのファイルの処理判定テスト"""
        assert file_watcher._should_process_file(".hidden.txt") is False
        assert file_watcher._should_process_file("temp.tmp") is False
        assert file_watcher._should_process_file("Thumbs.db") is False
    
    def test_match_pattern(self, file_watcher):
        """パターンマッチングのテスト"""
        assert file_watcher._match_pattern("test.txt", "*.txt") is True
        assert file_watcher._match_pattern("test.pdf", "*.txt") is False
        assert file_watcher._match_pattern(".hidden", ".*") is True
        assert file_watcher._match_pattern("temp.tmp", "*.tmp") is True
    
    def test_calculate_file_hash(self, file_watcher, temp_dir):
        """ファイルハッシュ計算のテスト"""
        test_file = os.path.join(temp_dir, "test.txt")
        test_content = "This is test content"
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        hash1 = file_watcher._calculate_file_hash(test_file)
        hash2 = file_watcher._calculate_file_hash(test_file)
        
        # 同じファイルは同じハッシュを返すべき
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256は64文字
    
    def test_is_file_actually_changed_new_file(self, file_watcher, temp_dir):
        """新しいファイルの変更検出テスト"""
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # 新しいファイルは変更ありと判定されるべき
        assert file_watcher._is_file_actually_changed(test_file) is True
    
    def test_is_file_actually_changed_unchanged_file(self, file_watcher, temp_dir):
        """変更されていないファイルの検出テスト"""
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # 最初の呼び出し（キャッシュに追加）
        file_watcher._is_file_actually_changed(test_file)
        
        # 2回目の呼び出し（変更なしと判定されるべき）
        assert file_watcher._is_file_actually_changed(test_file) is False
    
    def test_is_file_actually_changed_modified_file(self, file_watcher, temp_dir):
        """変更されたファイルの検出テスト"""
        test_file = os.path.join(temp_dir, "test.txt")
        
        # 最初のコンテンツ
        with open(test_file, 'w') as f:
            f.write("original content")
        
        # 最初の呼び出し
        file_watcher._is_file_actually_changed(test_file)
        
        # ファイルを変更
        time.sleep(0.1)  # ファイルシステムの時刻精度を考慮
        with open(test_file, 'w') as f:
            f.write("modified content")
        
        # 変更ありと判定されるべき
        assert file_watcher._is_file_actually_changed(test_file) is True
    
    def test_file_change_event_creation(self):
        """FileChangeEventの作成テスト"""
        event = FileChangeEvent(
            event_type='created',
            file_path='/test/path.txt'
        )
        
        assert event.event_type == 'created'
        assert event.file_path == '/test/path.txt'
        assert event.old_path is None
        assert event.timestamp is not None
    
    def test_file_hash_info_creation(self):
        """FileHashInfoの作成テスト"""
        hash_info = FileHashInfo(
            file_path='/test/path.txt',
            content_hash='abc123',
            file_size=100,
            modified_time=time.time(),
            last_processed=time.time()
        )
        
        assert hash_info.file_path == '/test/path.txt'
        assert hash_info.content_hash == 'abc123'
        assert hash_info.file_size == 100
    
    def test_handle_file_deleted(self, file_watcher, mock_index_manager, mock_embedding_manager, temp_dir):
        """ファイル削除処理のテスト"""
        test_path = os.path.join(temp_dir, "test.txt")
        
        # document_existsがTrueを返すように設定
        mock_index_manager.document_exists.return_value = True
        
        file_watcher._handle_file_deleted(test_path)
        
        # インデックスから削除が呼ばれることを確認
        mock_index_manager.remove_document.assert_called_once()
        
        # 埋め込みキャッシュから削除が呼ばれることを確認
        mock_embedding_manager.remove_document_embedding.assert_called_once()
        
        # 統計が更新されることを確認
        assert file_watcher.stats['files_deleted'] == 1
    
    def test_handle_file_created_or_modified(self, file_watcher, mock_index_manager, 
                                           mock_embedding_manager, mock_document_processor, temp_dir):
        """ファイル作成・変更処理のテスト"""
        test_path = os.path.join(temp_dir, "test.txt")
        
        file_watcher._handle_file_created_or_modified(test_path, 'created')
        
        # ドキュメント処理が呼ばれることを確認
        mock_document_processor.process_file.assert_called_once_with(test_path)
        
        # インデックスに追加が呼ばれることを確認
        mock_index_manager.add_document.assert_called_once()
        
        # 埋め込み追加が呼ばれることを確認
        mock_embedding_manager.add_document_embedding.assert_called_once()
        
        # 統計が更新されることを確認
        assert file_watcher.stats['files_added'] == 1
    
    def test_handle_file_moved(self, file_watcher, temp_dir):
        """ファイル移動処理のテスト"""
        old_path = os.path.join(temp_dir, "old_path.txt")
        new_path = os.path.join(temp_dir, "new_path.txt")
        
        # _handle_file_deletedと_handle_file_created_or_modifiedをモック
        with patch.object(file_watcher, '_handle_file_deleted') as mock_delete, \
             patch.object(file_watcher, '_handle_file_created_or_modified') as mock_create:
            
            file_watcher._handle_file_moved(old_path, new_path)
            
            # 削除処理が呼ばれることを確認
            mock_delete.assert_called_once_with(old_path)
            
            # 作成処理が呼ばれることを確認
            mock_create.assert_called_once_with(new_path, 'created')
    
    def test_process_file_event_created(self, file_watcher, temp_dir):
        """ファイル作成イベント処理のテスト"""
        test_path = os.path.join(temp_dir, "test.txt")
        event = FileChangeEvent(
            event_type='created',
            file_path=test_path
        )
        
        with patch.object(file_watcher, '_handle_file_created_or_modified') as mock_handle:
            file_watcher._process_file_event(event)
            mock_handle.assert_called_once_with(test_path, 'created')
    
    def test_process_file_event_deleted(self, file_watcher, temp_dir):
        """ファイル削除イベント処理のテスト"""
        test_path = os.path.join(temp_dir, "test.txt")
        event = FileChangeEvent(
            event_type='deleted',
            file_path=test_path
        )
        
        with patch.object(file_watcher, '_handle_file_deleted') as mock_handle:
            file_watcher._process_file_event(event)
            mock_handle.assert_called_once_with(test_path)
    
    def test_process_file_event_moved(self, file_watcher, temp_dir):
        """ファイル移動イベント処理のテスト"""
        old_path = os.path.join(temp_dir, "old_path.txt")
        new_path = os.path.join(temp_dir, "new_path.txt")
        event = FileChangeEvent(
            event_type='moved',
            file_path=new_path,
            old_path=old_path
        )
        
        with patch.object(file_watcher, '_handle_file_moved') as mock_handle:
            file_watcher._process_file_event(event)
            mock_handle.assert_called_once_with(old_path, new_path)
    
    def test_get_stats(self, file_watcher, temp_dir):
        """統計情報取得のテスト"""
        file_watcher.add_watch_path(temp_dir)
        
        stats = file_watcher.get_stats()
        
        assert 'is_running' in stats
        assert 'watched_paths' in stats
        assert 'queue_size' in stats
        assert 'cached_hashes' in stats
        assert 'stats' in stats
        
        assert stats['is_running'] is False
        assert len(stats['watched_paths']) == 1
        assert stats['queue_size'] == 0
        assert stats['cached_hashes'] == 0
    
    def test_clear_hash_cache(self, file_watcher, temp_dir):
        """ハッシュキャッシュクリアのテスト"""
        # テストファイルを作成してハッシュキャッシュに追加
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        file_watcher._is_file_actually_changed(test_file)
        assert len(file_watcher.file_hashes) > 0
        
        # キャッシュをクリア
        file_watcher.clear_hash_cache()
        assert len(file_watcher.file_hashes) == 0
    
    @patch('src.core.file_watcher.Observer')
    def test_start_watching_success(self, mock_observer_class, file_watcher, temp_dir):
        """監視開始成功のテスト"""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        file_watcher.add_watch_path(temp_dir)
        
        # ワーカーループをモック
        with patch.object(file_watcher, '_worker_loop'):
            file_watcher.start_watching()
        
        assert file_watcher.is_running is True
        assert file_watcher.observer is not None
        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()
    
    def test_start_watching_no_paths(self, file_watcher):
        """監視パスなしでの監視開始テスト（エラーになるべき）"""
        with pytest.raises(FileSystemError):
            file_watcher.start_watching()
    
    def test_start_watching_already_running(self, file_watcher, temp_dir):
        """既に実行中の状態での監視開始テスト"""
        file_watcher.is_running = True
        file_watcher.add_watch_path(temp_dir)
        
        # 警告が出るが例外は発生しないはず
        file_watcher.start_watching()
    
    @patch('src.core.file_watcher.Observer')
    def test_stop_watching(self, mock_observer_class, file_watcher, temp_dir):
        """監視停止のテスト"""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        file_watcher.add_watch_path(temp_dir)
        
        # 監視を開始
        with patch.object(file_watcher, '_worker_loop'):
            file_watcher.start_watching()
        
        # 監視を停止
        with patch.object(file_watcher, '_save_hash_cache'):
            file_watcher.stop_watching()
        
        assert file_watcher.is_running is False
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
    
    def test_force_rescan(self, file_watcher, temp_dir):
        """強制再スキャンのテスト"""
        # テストファイルを作成
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        file_watcher.add_watch_path(temp_dir)
        
        # 強制再スキャンを実行
        file_watcher.force_rescan(temp_dir)
        
        # キューにイベントが追加されることを確認
        assert not file_watcher.processing_queue.empty()
    
    def test_wait_for_queue_empty_success(self, file_watcher):
        """キュー空待機成功のテスト"""
        # キューが空の状態でテスト
        result = file_watcher.wait_for_queue_empty(timeout=1.0)
        assert result is True
    
    def test_wait_for_queue_empty_timeout(self, file_watcher, temp_dir):
        """キュー空待機タイムアウトのテスト"""
        # キューにアイテムを追加
        test_path = os.path.join(temp_dir, "test.txt")
        event = FileChangeEvent('created', test_path)
        file_watcher.processing_queue.put(event)
        
        # タイムアウトするはず
        result = file_watcher.wait_for_queue_empty(timeout=0.1)
        assert result is False


class TestFileWatcherIntegration:
    """FileWatcherの統合テスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """テスト用の一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_real_file_operations(self, temp_dir):
        """実際のファイル操作を使った統合テスト"""
        # 実際のコンポーネントを使用（ただし一時ディレクトリで）
        config = Config()
        config.set("data_directory", temp_dir)
        
        # モックを使用してテスト
        mock_index_manager = Mock(spec=IndexManager)
        mock_embedding_manager = Mock(spec=EmbeddingManager)
        mock_document_processor = Mock(spec=DocumentProcessor)
        
        # テスト用の実際のファイルを作成
        test_file_path = os.path.join(temp_dir, "test.txt")
        with open(test_file_path, 'w') as f:
            f.write("Test content")
        
        # テスト用のDocumentオブジェクトを返すように設定
        test_doc = Document(
            id="test_id",
            file_path=test_file_path,
            title="Test Document",
            content="Test content",
            file_type=FileType.TEXT,
            size=100,
            created_date=time.time(),
            modified_date=time.time(),
            indexed_date=time.time()
        )
        mock_document_processor.process_file.return_value = test_doc
        mock_document_processor.is_supported_file.return_value = True
        
        file_watcher = FileWatcher(
            index_manager=mock_index_manager,
            embedding_manager=mock_embedding_manager,
            document_processor=mock_document_processor,
            config=config
        )
        
        # 監視対象パスを追加
        file_watcher.add_watch_path(temp_dir)
        
        # テストファイルを作成
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # ファイル変更イベントを手動で処理
        event = FileChangeEvent('created', test_file)
        file_watcher._process_file_event(event)
        
        # 処理が呼ばれたことを確認
        mock_document_processor.process_file.assert_called_once_with(test_file)
        mock_index_manager.add_document.assert_called_once()
        mock_embedding_manager.add_document_embedding.assert_called_once()