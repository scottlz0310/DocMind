"""
FileWatcher - ファイルシステム監視と増分更新システム

このモジュールは、watchdogライブラリを使用してファイルシステムの変更を監視し、
ドキュメントのインデックスと埋め込みの増分更新を行います。
"""

from dataclasses import dataclass
from datetime import datetime
import hashlib
import logging
import os
from queue import Empty, Queue
import threading
import time
from typing import Any

from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from ..data.models import Document
from ..utils.config import Config
from ..utils.exceptions import DocumentProcessingError, FileSystemError
from .document_processor import DocumentProcessor
from .embedding_manager import EmbeddingManager
from .index_manager import IndexManager


@dataclass
class FileChangeEvent:
    """ファイル変更イベントを表すデータクラス"""

    event_type: str  # 'created', 'modified', 'deleted', 'moved'
    file_path: str
    old_path: str | None = None  # 移動イベントの場合の元のパス
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class FileHashInfo:
    """ファイルハッシュ情報を管理するデータクラス"""

    file_path: str
    content_hash: str
    file_size: int
    modified_time: float
    last_processed: float


class FileWatcher(FileSystemEventHandler):
    """
    ファイルシステム監視と増分更新を管理するクラス

    watchdogライブラリを使用してファイルシステムの変更を監視し、
    変更されたファイルのインデックスと埋め込みを増分的に更新します。
    """

    def __init__(
        self,
        index_manager: IndexManager,
        embedding_manager: EmbeddingManager,
        document_processor: DocumentProcessor | None = None,
        config: Config | None = None,
    ):
        """
        FileWatcherを初期化

        Args:
            index_manager: インデックス管理クラス
            embedding_manager: 埋め込み管理クラス
            document_processor: ドキュメント処理クラス(Noneの場合は新規作成)
            config: 設定クラス(Noneの場合はデフォルト設定を使用)
        """
        super().__init__()

        self.index_manager = index_manager
        self.embedding_manager = embedding_manager
        self.document_processor = document_processor or DocumentProcessor()
        self.config = config or Config()

        # ログ設定
        self.logger = logging.getLogger(__name__)

        # 監視対象パスのセット
        self.watched_paths: set[str] = set()

        # ファイルハッシュキャッシュ(重複処理を避けるため)
        self.file_hashes: dict[str, FileHashInfo] = {}

        # バックグラウンド処理キュー
        self.processing_queue: Queue[FileChangeEvent] = Queue()

        # ワーカースレッド
        self.worker_thread: threading.Thread | None = None
        self.is_running = False

        # watchdog Observer
        self.observer: Observer | None = None

        # 処理統計
        self.stats = {
            "files_processed": 0,
            "files_added": 0,
            "files_updated": 0,
            "files_deleted": 0,
            "processing_errors": 0,
            "last_activity": None,
        }

        # 除外パターン(処理しないファイル/ディレクトリ)
        self.exclude_patterns = {
            # 隠しファイル・ディレクトリ
            ".*",
            # 一時ファイル
            "~*",
            "*.tmp",
            "*.temp",
            "*.bak",
            # システムファイル
            "Thumbs.db",
            "Desktop.ini",
            ".DS_Store",
            # ログファイル
            "*.log",
            # バイナリファイル(画像、動画など)
            "*.jpg",
            "*.jpeg",
            "*.png",
            "*.gif",
            "*.bmp",
            "*.mp4",
            "*.avi",
            "*.mov",
            "*.wmv",
            "*.mp3",
            "*.wav",
            "*.flac",
            # 実行ファイル
            "*.exe",
            "*.dll",
            "*.so",
            "*.dylib",
        }

        # ハッシュキャッシュファイルのパス
        self.hash_cache_path = os.path.join(self.config.data_dir, "file_hashes.pkl")

        # ハッシュキャッシュを読み込み
        self._load_hash_cache()

    def add_watch_path(self, path: str) -> None:
        """
        監視対象パスを追加

        Args:
            path: 監視するディレクトリパス

        Raises:
            FileSystemError: パスが存在しない場合
        """
        if not os.path.exists(path):
            raise FileSystemError(f"監視対象パスが存在しません: {path}", path=path)

        if not os.path.isdir(path):
            raise FileSystemError(f"監視対象パスはディレクトリである必要があります: {path}", path=path)

        abs_path = os.path.abspath(path)
        self.watched_paths.add(abs_path)
        self.logger.info(f"監視対象パスを追加しました: {abs_path}")

    def remove_watch_path(self, path: str) -> None:
        """
        監視対象パスを削除

        Args:
            path: 削除するディレクトリパス
        """
        abs_path = os.path.abspath(path)
        if abs_path in self.watched_paths:
            self.watched_paths.remove(abs_path)
            self.logger.info(f"監視対象パスを削除しました: {abs_path}")

    def start_watching(self) -> None:
        """
        ファイルシステム監視を開始

        Raises:
            FileSystemError: 監視開始に失敗した場合
        """
        if self.is_running:
            self.logger.warning("ファイル監視は既に実行中です")
            return

        if not self.watched_paths:
            raise FileSystemError("監視対象パスが設定されていません")

        try:
            # ワーカースレッドを開始
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()

            # watchdog Observerを開始
            self.observer = Observer()

            for path in self.watched_paths:
                self.observer.schedule(self, path, recursive=True)
                self.logger.info(f"ファイル監視を開始: {path}")

            self.observer.start()
            self.logger.info("ファイルシステム監視が開始されました")

        except Exception as e:
            self.is_running = False
            error_msg = f"ファイル監視の開始に失敗しました: {e}"
            self.logger.error(error_msg)
            raise FileSystemError(error_msg) from e

    def stop_watching(self) -> None:
        """
        ファイルシステム監視を停止
        """
        if not self.is_running:
            return

        self.logger.info("ファイルシステム監視を停止中...")

        # フラグを設定してワーカースレッドを停止
        self.is_running = False

        # watchdog Observerを停止
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5.0)
            self.observer = None

        # ワーカースレッドの終了を待機
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
            self.worker_thread = None

        # ハッシュキャッシュを保存
        self._save_hash_cache()

        self.logger.info("ファイルシステム監視が停止されました")

    def on_created(self, event: FileCreatedEvent) -> None:
        """ファイル作成イベントのハンドラ"""
        if not event.is_directory and self._should_process_file(event.src_path):
            change_event = FileChangeEvent(event_type="created", file_path=event.src_path)
            self.processing_queue.put(change_event)
            self.logger.debug(f"ファイル作成イベント: {event.src_path}")

    def on_modified(self, event: FileModifiedEvent) -> None:
        """ファイル変更イベントのハンドラ"""
        if not event.is_directory and self._should_process_file(event.src_path):
            # ファイルハッシュをチェックして実際に変更されているかを確認
            if self._is_file_actually_changed(event.src_path):
                change_event = FileChangeEvent(event_type="modified", file_path=event.src_path)
                self.processing_queue.put(change_event)
                self.logger.debug(f"ファイル変更イベント: {event.src_path}")

    def on_deleted(self, event: FileDeletedEvent) -> None:
        """ファイル削除イベントのハンドラ"""
        if not event.is_directory:
            change_event = FileChangeEvent(event_type="deleted", file_path=event.src_path)
            self.processing_queue.put(change_event)
            self.logger.debug(f"ファイル削除イベント: {event.src_path}")

    def on_moved(self, event: FileMovedEvent) -> None:
        """ファイル移動イベントのハンドラ"""
        if not event.is_directory:
            change_event = FileChangeEvent(event_type="moved", file_path=event.dest_path, old_path=event.src_path)
            self.processing_queue.put(change_event)
            self.logger.debug(f"ファイル移動イベント: {event.src_path} -> {event.dest_path}")

    def _should_process_file(self, file_path: str) -> bool:
        """
        ファイルを処理すべきかどうかを判定

        Args:
            file_path: ファイルパス

        Returns:
            処理すべき場合True
        """
        # サポートされているファイル形式かチェック
        if not self.document_processor.is_supported_file(file_path):
            return False

        # 除外パターンをチェック
        file_name = os.path.basename(file_path)
        for pattern in self.exclude_patterns:
            if self._match_pattern(file_name, pattern):
                return False

        return True

    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """
        ファイル名がパターンにマッチするかチェック

        Args:
            filename: ファイル名
            pattern: パターン(*をワイルドカードとして使用)

        Returns:
            マッチする場合True
        """
        import fnmatch

        return fnmatch.fnmatch(filename.lower(), pattern.lower())

    def _is_file_actually_changed(self, file_path: str) -> bool:
        """
        ファイルが実際に変更されているかハッシュベースでチェック

        Args:
            file_path: ファイルパス

        Returns:
            変更されている場合True
        """
        try:
            if not os.path.exists(file_path):
                return True

            # ファイル情報を取得
            file_stat = os.stat(file_path)
            current_size = file_stat.st_size
            current_mtime = file_stat.st_mtime

            # キャッシュされた情報と比較
            if file_path in self.file_hashes:
                cached_info = self.file_hashes[file_path]

                # サイズと更新時刻が同じ場合は変更なしと判定
                if cached_info.file_size == current_size and cached_info.modified_time == current_mtime:
                    return False

            # ファイルハッシュを計算
            current_hash = self._calculate_file_hash(file_path)

            # キャッシュされたハッシュと比較
            if file_path in self.file_hashes:
                cached_info = self.file_hashes[file_path]
                if cached_info.content_hash == current_hash:
                    # ハッシュが同じ場合は変更なし、キャッシュ情報を更新
                    self.file_hashes[file_path] = FileHashInfo(
                        file_path=file_path,
                        content_hash=current_hash,
                        file_size=current_size,
                        modified_time=current_mtime,
                        last_processed=time.time(),
                    )
                    return False

            # ハッシュが異なる場合は変更あり、キャッシュを更新
            self.file_hashes[file_path] = FileHashInfo(
                file_path=file_path,
                content_hash=current_hash,
                file_size=current_size,
                modified_time=current_mtime,
                last_processed=time.time(),
            )

            return True

        except Exception as e:
            self.logger.warning(f"ファイル変更チェックに失敗: {file_path} - {e}")
            return True  # エラーの場合は変更ありとして処理

    def _calculate_file_hash(self, file_path: str) -> str:
        """
        ファイルのハッシュ値を計算

        Args:
            file_path: ファイルパス

        Returns:
            ハッシュ値(SHA-256)
        """
        hash_sha256 = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                # ファイルを小さなチャンクに分けて読み込み
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)

            return hash_sha256.hexdigest()

        except Exception as e:
            self.logger.warning(f"ファイルハッシュ計算に失敗: {file_path} - {e}")
            # フォールバック: ファイルサイズと更新時刻を使用
            file_stat = os.stat(file_path)
            fallback_data = f"{file_path}:{file_stat.st_size}:{file_stat.st_mtime}"
            return hashlib.sha256(fallback_data.encode()).hexdigest()

    def _worker_loop(self) -> None:
        """
        バックグラウンド処理ワーカーのメインループ
        """
        self.logger.info("ファイル処理ワーカーを開始しました")

        while self.is_running:
            try:
                # キューからイベントを取得(タイムアウト付き)
                event = self.processing_queue.get(timeout=1.0)

                # イベントを処理
                self._process_file_event(event)

                # キューのタスク完了を通知
                self.processing_queue.task_done()

            except Empty:
                # タイムアウト(正常)
                continue
            except Exception as e:
                self.logger.error(f"ワーカーループでエラーが発生: {e}")
                self.stats["processing_errors"] += 1

        self.logger.info("ファイル処理ワーカーを停止しました")

    def _process_file_event(self, event: FileChangeEvent) -> None:
        """
        ファイル変更イベントを処理

        Args:
            event: 処理するファイル変更イベント
        """
        try:
            self.logger.info(f"ファイルイベント処理開始: {event.event_type} - {event.file_path}")

            if event.event_type == "deleted":
                self._handle_file_deleted(event.file_path)
            elif event.event_type == "moved":
                self._handle_file_moved(event.old_path, event.file_path)
            elif event.event_type in ["created", "modified"]:
                self._handle_file_created_or_modified(event.file_path, event.event_type)

            # 統計を更新
            self.stats["files_processed"] += 1
            self.stats["last_activity"] = datetime.now()

            self.logger.debug(f"ファイルイベント処理完了: {event.event_type} - {event.file_path}")

        except Exception as e:
            self.logger.error(f"ファイルイベント処理中にエラー: {event.file_path} - {e}")
            self.stats["processing_errors"] += 1

    def _handle_file_deleted(self, file_path: str) -> None:
        """
        ファイル削除イベントを処理

        Args:
            file_path: 削除されたファイルのパス
        """
        # ドキュメントIDを生成
        doc_id = Document._generate_id(file_path)

        # インデックスから削除
        try:
            if self.index_manager.document_exists(doc_id):
                self.index_manager.remove_document(doc_id)
                self.logger.info(f"インデックスからドキュメントを削除: {file_path}")
        except Exception as e:
            self.logger.error(f"インデックスからの削除に失敗: {file_path} - {e}")

        # 埋め込みキャッシュから削除
        try:
            self.embedding_manager.remove_document_embedding(doc_id)
            self.logger.info(f"埋め込みキャッシュからドキュメントを削除: {file_path}")
        except Exception as e:
            self.logger.error(f"埋め込みキャッシュからの削除に失敗: {file_path} - {e}")

        # ハッシュキャッシュから削除
        if file_path in self.file_hashes:
            del self.file_hashes[file_path]

        self.stats["files_deleted"] += 1

    def _handle_file_moved(self, old_path: str, new_path: str) -> None:
        """
        ファイル移動イベントを処理

        Args:
            old_path: 元のファイルパス
            new_path: 新しいファイルパス
        """
        # 古いファイルを削除
        self._handle_file_deleted(old_path)

        # 新しいファイルを追加(サポートされている場合のみ)
        if self._should_process_file(new_path):
            self._handle_file_created_or_modified(new_path, "created")

    def _handle_file_created_or_modified(self, file_path: str, event_type: str) -> None:
        """
        ファイル作成・変更イベントを処理

        Args:
            file_path: ファイルパス
            event_type: イベントタイプ('created' または 'modified')
        """
        try:
            # ドキュメントを処理
            document = self.document_processor.process_file(file_path)

            # インデックスを更新
            if event_type == "created" or not self.index_manager.document_exists(document.id):
                self.index_manager.add_document(document)
                self.stats["files_added"] += 1
                self.logger.info(f"インデックスにドキュメントを追加: {file_path}")
            else:
                self.index_manager.update_document(document)
                self.stats["files_updated"] += 1
                self.logger.info(f"インデックスのドキュメントを更新: {file_path}")

            # 埋め込みを更新
            self.embedding_manager.add_document_embedding(document.id, document.content)
            self.logger.info(f"埋め込みを更新: {file_path}")

        except DocumentProcessingError as e:
            self.logger.warning(f"ドキュメント処理をスキップ: {file_path} - {e.message}")
        except Exception as e:
            self.logger.error(f"ファイル処理中にエラー: {file_path} - {e}")
            raise

    def _load_hash_cache(self) -> None:
        """ハッシュキャッシュをファイルから読み込み"""
        try:
            if os.path.exists(self.hash_cache_path):
                import pickle

                with open(self.hash_cache_path, "rb") as f:
                    self.file_hashes = pickle.load(f)
                self.logger.info(f"ハッシュキャッシュを読み込み: {len(self.file_hashes)}件")
            else:
                self.file_hashes = {}
                self.logger.info("ハッシュキャッシュファイルが存在しません。空のキャッシュで開始します。")
        except Exception as e:
            self.logger.warning(f"ハッシュキャッシュの読み込みに失敗: {e}")
            self.file_hashes = {}

    def _save_hash_cache(self) -> None:
        """ハッシュキャッシュをファイルに保存"""
        try:
            import pickle

            os.makedirs(os.path.dirname(self.hash_cache_path), exist_ok=True)

            # 一時ファイルに保存してから移動(原子的操作)
            temp_path = self.hash_cache_path + ".tmp"
            with open(temp_path, "wb") as f:
                pickle.dump(self.file_hashes, f, protocol=pickle.HIGHEST_PROTOCOL)

            os.replace(temp_path, self.hash_cache_path)
            self.logger.info(f"ハッシュキャッシュを保存: {len(self.file_hashes)}件")
        except Exception as e:
            self.logger.error(f"ハッシュキャッシュの保存に失敗: {e}")

    def force_rescan(self, path: str | None = None) -> None:
        """
        指定されたパス(またはすべての監視パス)を強制的に再スキャン

        Args:
            path: 再スキャンするパス(Noneの場合はすべての監視パス)
        """
        scan_paths = [path] if path else list(self.watched_paths)

        for scan_path in scan_paths:
            if not os.path.exists(scan_path):
                self.logger.warning(f"再スキャン対象パスが存在しません: {scan_path}")
                continue

            self.logger.info(f"強制再スキャン開始: {scan_path}")

            # ディレクトリを再帰的にスキャン
            for root, _dirs, files in os.walk(scan_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)

                    if self._should_process_file(file_path):
                        # ハッシュキャッシュをクリアして強制処理
                        if file_path in self.file_hashes:
                            del self.file_hashes[file_path]

                        # 処理キューに追加
                        event = FileChangeEvent(event_type="modified", file_path=file_path)
                        self.processing_queue.put(event)

            self.logger.info(f"強制再スキャン完了: {scan_path}")

    def get_stats(self) -> dict[str, Any]:
        """
        監視統計情報を取得

        Returns:
            統計情報の辞書
        """
        return {
            "is_running": self.is_running,
            "watched_paths": list(self.watched_paths),
            "queue_size": self.processing_queue.qsize(),
            "cached_hashes": len(self.file_hashes),
            "stats": self.stats.copy(),
        }

    def clear_hash_cache(self) -> None:
        """ハッシュキャッシュをクリア"""
        self.file_hashes.clear()
        if os.path.exists(self.hash_cache_path):
            os.remove(self.hash_cache_path)
        self.logger.info("ハッシュキャッシュをクリアしました")

    def wait_for_queue_empty(self, timeout: float = 30.0) -> bool:
        """
        処理キューが空になるまで待機

        Args:
            timeout: タイムアウト時間(秒)

        Returns:
            キューが空になった場合True、タイムアウトした場合False
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.processing_queue.empty():
                return True
            time.sleep(0.1)

        return False
