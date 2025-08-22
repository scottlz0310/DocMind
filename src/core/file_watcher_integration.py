"""
FileWatcher統合モジュール

FileWatcherを他のコンポーネントと統合して使用するためのヘルパークラスと関数を提供します。
"""

import os
import logging
import threading
from typing import List, Optional, Callable, Dict, Any
from pathlib import Path

from .file_watcher import FileWatcher
from .index_manager import IndexManager
from .embedding_manager import EmbeddingManager
from .document_processor import DocumentProcessor
from .search_manager import SearchManager
from ..utils.config import Config
from ..utils.exceptions import FileSystemError


class DocumentIndexingService:
    """
    ドキュメントインデックス化サービス
    
    FileWatcherと他のコンポーネントを統合して、
    自動的なドキュメントインデックス化サービスを提供します。
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        サービスを初期化
        
        Args:
            config: 設定オブジェクト（Noneの場合はデフォルト設定を使用）
        """
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        
        # コンポーネントの初期化
        self._initialize_components()
        
        # FileWatcherの初期化
        self.file_watcher = FileWatcher(
            index_manager=self.index_manager,
            embedding_manager=self.embedding_manager,
            document_processor=self.document_processor,
            config=self.config
        )
        
        # 状態管理
        self.is_running = False
        self._shutdown_event = threading.Event()
        
        # コールバック関数
        self.on_document_added: Optional[Callable[[str], None]] = None
        self.on_document_updated: Optional[Callable[[str], None]] = None
        self.on_document_deleted: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
    
    def _initialize_components(self) -> None:
        """必要なコンポーネントを初期化"""
        try:
            # IndexManagerの初期化
            index_path = self.config.get_index_path()
            self.index_manager = IndexManager(index_path)
            
            # EmbeddingManagerの初期化
            model_name = self.config.get_embedding_model()
            embeddings_path = self.config.get_embeddings_path()
            self.embedding_manager = EmbeddingManager(model_name, embeddings_path)
            
            # DocumentProcessorの初期化
            self.document_processor = DocumentProcessor()
            
            # SearchManagerの初期化
            self.search_manager = SearchManager(
                self.index_manager,
                self.embedding_manager
            )
            
            self.logger.info("すべてのコンポーネントが初期化されました")
            
        except Exception as e:
            error_msg = f"コンポーネントの初期化に失敗しました: {e}"
            self.logger.error(error_msg)
            raise FileSystemError(error_msg) from e
    
    def add_watch_directory(self, directory_path: str) -> None:
        """
        監視対象ディレクトリを追加
        
        Args:
            directory_path: 監視するディレクトリのパス
            
        Raises:
            FileSystemError: ディレクトリが存在しない場合
        """
        if not os.path.exists(directory_path):
            raise FileSystemError(f"ディレクトリが存在しません: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise FileSystemError(f"指定されたパスはディレクトリではありません: {directory_path}")
        
        self.file_watcher.add_watch_path(directory_path)
        self.logger.info(f"監視対象ディレクトリを追加しました: {directory_path}")
    
    def remove_watch_directory(self, directory_path: str) -> None:
        """
        監視対象ディレクトリを削除
        
        Args:
            directory_path: 削除するディレクトリのパス
        """
        self.file_watcher.remove_watch_path(directory_path)
        self.logger.info(f"監視対象ディレクトリを削除しました: {directory_path}")
    
    def start_service(self) -> None:
        """
        インデックス化サービスを開始
        
        Raises:
            FileSystemError: サービス開始に失敗した場合
        """
        if self.is_running:
            self.logger.warning("サービスは既に実行中です")
            return
        
        try:
            # ファイル監視を開始
            if self.config.is_file_watching_enabled():
                self.file_watcher.start_watching()
                self.logger.info("ファイル監視を開始しました")
            else:
                self.logger.info("ファイル監視は無効化されています")
            
            self.is_running = True
            self.logger.info("ドキュメントインデックス化サービスを開始しました")
            
        except Exception as e:
            error_msg = f"サービスの開始に失敗しました: {e}"
            self.logger.error(error_msg)
            raise FileSystemError(error_msg) from e
    
    def stop_service(self) -> None:
        """インデックス化サービスを停止"""
        if not self.is_running:
            return
        
        self.logger.info("ドキュメントインデックス化サービスを停止中...")
        
        # ファイル監視を停止
        self.file_watcher.stop_watching()
        
        # 埋め込みキャッシュを保存
        try:
            self.embedding_manager.save_embeddings()
        except Exception as e:
            self.logger.error(f"埋め込みキャッシュの保存に失敗: {e}")
        
        # インデックスを最適化
        try:
            self.index_manager.optimize_index()
        except Exception as e:
            self.logger.error(f"インデックス最適化に失敗: {e}")
        
        self.is_running = False
        self._shutdown_event.set()
        self.logger.info("ドキュメントインデックス化サービスを停止しました")
    
    def initial_scan(self, directory_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        初期スキャンを実行
        
        Args:
            directory_paths: スキャンするディレクトリのリスト（Noneの場合は監視対象すべて）
            
        Returns:
            スキャン結果の統計情報
        """
        if directory_paths is None:
            directory_paths = list(self.file_watcher.watched_paths)
        
        if not directory_paths:
            self.logger.warning("スキャン対象のディレクトリが指定されていません")
            return {"processed_files": 0, "errors": 0}
        
        self.logger.info(f"初期スキャンを開始します: {len(directory_paths)}個のディレクトリ")
        
        stats = {
            "processed_files": 0,
            "added_files": 0,
            "updated_files": 0,
            "errors": 0,
            "skipped_files": 0
        }
        
        for directory_path in directory_paths:
            if not os.path.exists(directory_path):
                self.logger.warning(f"ディレクトリが存在しません: {directory_path}")
                continue
            
            self.logger.info(f"ディレクトリをスキャン中: {directory_path}")
            
            # ディレクトリを再帰的にスキャン
            for root, dirs, files in os.walk(directory_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    
                    try:
                        # ファイルを処理すべきかチェック
                        if not self.file_watcher._should_process_file(file_path):
                            stats["skipped_files"] += 1
                            continue
                        
                        # ドキュメントを処理
                        document = self.document_processor.process_file(file_path)
                        
                        # インデックスに追加または更新
                        if self.index_manager.document_exists(document.id):
                            self.index_manager.update_document(document)
                            stats["updated_files"] += 1
                        else:
                            self.index_manager.add_document(document)
                            stats["added_files"] += 1
                        
                        # 埋め込みを生成
                        self.embedding_manager.add_document_embedding(
                            document.id, document.content
                        )
                        
                        stats["processed_files"] += 1
                        
                        # 進捗をログ出力
                        if stats["processed_files"] % 100 == 0:
                            self.logger.info(f"進捗: {stats['processed_files']}ファイル処理完了")
                        
                    except Exception as e:
                        self.logger.error(f"ファイル処理中にエラー: {file_path} - {e}")
                        stats["errors"] += 1
                        
                        if self.on_error:
                            self.on_error(e)
        
        # 埋め込みキャッシュを保存
        try:
            self.embedding_manager.save_embeddings()
        except Exception as e:
            self.logger.error(f"埋め込みキャッシュの保存に失敗: {e}")
        
        # インデックスを最適化
        try:
            self.index_manager.optimize_index()
        except Exception as e:
            self.logger.error(f"インデックス最適化に失敗: {e}")
        
        self.logger.info(f"初期スキャン完了: {stats}")
        return stats
    
    def force_rescan(self, directory_path: Optional[str] = None) -> None:
        """
        強制再スキャンを実行
        
        Args:
            directory_path: 再スキャンするディレクトリ（Noneの場合はすべて）
        """
        self.logger.info("強制再スキャンを開始します")
        self.file_watcher.force_rescan(directory_path)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        サービスの統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        file_watcher_stats = self.file_watcher.get_stats()
        index_stats = self.index_manager.get_index_stats()
        embedding_stats = self.embedding_manager.get_cache_info()
        search_stats = self.search_manager.get_search_stats()
        
        return {
            "service_running": self.is_running,
            "file_watcher": file_watcher_stats,
            "index": index_stats,
            "embeddings": embedding_stats,
            "search": search_stats
        }
    
    def wait_for_processing_complete(self, timeout: float = 30.0) -> bool:
        """
        処理完了まで待機
        
        Args:
            timeout: タイムアウト時間（秒）
            
        Returns:
            処理が完了した場合True、タイムアウトした場合False
        """
        return self.file_watcher.wait_for_queue_empty(timeout)
    
    def set_callbacks(self, 
                     on_document_added: Optional[Callable[[str], None]] = None,
                     on_document_updated: Optional[Callable[[str], None]] = None,
                     on_document_deleted: Optional[Callable[[str], None]] = None,
                     on_error: Optional[Callable[[Exception], None]] = None) -> None:
        """
        コールバック関数を設定
        
        Args:
            on_document_added: ドキュメント追加時のコールバック
            on_document_updated: ドキュメント更新時のコールバック
            on_document_deleted: ドキュメント削除時のコールバック
            on_error: エラー発生時のコールバック
        """
        self.on_document_added = on_document_added
        self.on_document_updated = on_document_updated
        self.on_document_deleted = on_document_deleted
        self.on_error = on_error
    
    def __enter__(self):
        """コンテキストマネージャーのエントリー"""
        self.start_service()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了"""
        self.stop_service()


def create_document_indexing_service(config: Optional[Config] = None) -> DocumentIndexingService:
    """
    DocumentIndexingServiceのファクトリー関数
    
    Args:
        config: 設定オブジェクト
        
    Returns:
        初期化されたDocumentIndexingService
    """
    return DocumentIndexingService(config)


def setup_file_watching_for_directories(directories: List[str], 
                                       config: Optional[Config] = None) -> DocumentIndexingService:
    """
    指定されたディレクトリのファイル監視を設定
    
    Args:
        directories: 監視対象ディレクトリのリスト
        config: 設定オブジェクト
        
    Returns:
        設定されたDocumentIndexingService
    """
    service = create_document_indexing_service(config)
    
    for directory in directories:
        service.add_watch_directory(directory)
    
    return service


# 使用例
if __name__ == "__main__":
    import sys
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 設定を作成
    config = Config()
    
    # サービスを作成
    service = create_document_indexing_service(config)
    
    # 監視対象ディレクトリを追加（コマンドライン引数から）
    if len(sys.argv) > 1:
        for directory in sys.argv[1:]:
            if os.path.exists(directory):
                service.add_watch_directory(directory)
                print(f"監視対象に追加: {directory}")
            else:
                print(f"ディレクトリが存在しません: {directory}")
    else:
        print("使用方法: python file_watcher_integration.py <監視対象ディレクトリ1> [<監視対象ディレクトリ2> ...]")
        sys.exit(1)
    
    try:
        # サービスを開始
        service.start_service()
        
        # 初期スキャンを実行
        print("初期スキャンを実行中...")
        scan_results = service.initial_scan()
        print(f"初期スキャン完了: {scan_results}")
        
        # サービス統計を表示
        stats = service.get_service_stats()
        print(f"サービス統計: {stats}")
        
        print("ファイル監視を開始しました。Ctrl+Cで終了してください。")
        
        # メインループ（Ctrl+Cで終了）
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n終了シグナルを受信しました。")
    
    finally:
        # サービスを停止
        service.stop_service()
        print("サービスを停止しました。")