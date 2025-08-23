"""
DocMindアプリケーション用のデータベース管理モジュール

このモジュールは、SQLiteデータベースの接続、スキーマ管理、マイグレーション機能を提供します。
ドキュメントメタデータと検索履歴の永続化を担当します。
パフォーマンス最適化とコネクションプーリング機能を含みます。
"""

import sqlite3
import logging
import json
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from queue import Queue, Empty

from .models import Document, FileType, SearchType, IndexStats
from ..utils.exceptions import DatabaseError, DocumentNotFoundError
from ..utils.logging_config import LoggerMixin


class ConnectionPool:
    """
    SQLiteコネクションプール
    
    複数のデータベース接続を管理し、パフォーマンスを向上させます。
    """
    
    def __init__(self, db_path: str, pool_size: int = 10, timeout: float = 30.0):
        """
        コネクションプールを初期化
        
        Args:
            db_path: データベースファイルのパス
            pool_size: プールサイズ
            timeout: 接続タイムアウト
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created_connections = 0
        
        # 初期接続を作成
        self._initialize_pool()
    
    def _initialize_pool(self):
        """プールを初期化"""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            self._pool.put(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """新しい接続を作成"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            check_same_thread=False
        )
        
        # 最適化設定
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -64000")  # 64MB キャッシュ
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA mmap_size = 268435456")  # 256MB mmap
        
        conn.row_factory = sqlite3.Row
        self._created_connections += 1
        return conn
    
    @contextmanager
    def get_connection(self):
        """接続を取得するコンテキストマネージャー"""
        conn = None
        try:
            # プールから接続を取得
            try:
                conn = self._pool.get(timeout=5.0)
            except Empty:
                # プールが空の場合、新しい接続を作成
                conn = self._create_connection()
            
            yield conn
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"データベース操作に失敗しました: {e}")
        finally:
            if conn:
                try:
                    # 接続をプールに戻す
                    if self._pool.qsize() < self.pool_size:
                        self._pool.put_nowait(conn)
                    else:
                        conn.close()
                except:
                    conn.close()
    
    def close_all(self):
        """すべての接続を閉じる"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break


class DatabaseManager(LoggerMixin):
    """SQLiteデータベースの管理を行うクラス
    
    データベース接続、スキーマ作成、マイグレーション、基本的なCRUD操作を提供します。
    スレッドセーフな操作とトランザクション管理をサポートします。
    パフォーマンス最適化とコネクションプーリング機能を含みます。
    """
    
    # データベーススキーマのバージョン
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: str, pool_size: int = 10):
        """DatabaseManagerを初期化
        
        Args:
            db_path (str): データベースファイルのパス
            pool_size (int): コネクションプールサイズ
        """
        self.db_path = Path(db_path)
        
        # データベースディレクトリを作成
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # コネクションプールを初期化
        self._connection_pool = ConnectionPool(str(self.db_path), pool_size)
        
        # クエリキャッシュ
        self._query_cache: Dict[str, Any] = {}
        self._cache_lock = threading.RLock()
        self._cache_ttl = 300  # 5分のTTL
        
        # パフォーマンス統計
        self._query_stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_query_time": 0.0
        }
        self._stats_lock = threading.Lock()
        
        # 初期化フラグ
        self._initialized = False
        
        # 自動初期化（既存動作を維持）
        self.initialize()
    
    def initialize(self) -> None:
        """
        データベースの初期化
        
        冪等性を保証し、複数回呼び出しても安全。
        テストでの明示的な初期化呼び出しをサポート。
        """
        if self._initialized:
            self.logger.debug("データベースは既に初期化済みです")
            return
        
        self._initialize_database()
        self._initialized = True
        self.logger.info("データベースが初期化されました")
    
    def _initialize_database(self):
        """データベースの初期化とスキーマ作成"""
        try:
            with self.get_connection() as conn:
                # スキーマバージョンテーブルを作成
                self._create_schema_version_table(conn)
                
                # 現在のスキーマバージョンを確認
                current_version = self._get_schema_version(conn)
                
                if current_version == 0:
                    # 新しいデータベースの場合、スキーマを作成
                    self._create_schema(conn)
                    self._set_schema_version(conn, self.SCHEMA_VERSION)
                    self.logger.info(f"新しいデータベースを作成しました: {self.db_path}")
                elif current_version < self.SCHEMA_VERSION:
                    # マイグレーションが必要
                    self._migrate_schema(conn, current_version, self.SCHEMA_VERSION)
                    self.logger.info(f"データベースをバージョン{current_version}から{self.SCHEMA_VERSION}にマイグレーションしました")
                
        except Exception as e:
            self.logger.error(f"データベース初期化エラー: {e}")
            raise DatabaseError(f"データベースの初期化に失敗しました: {e}")
    
    def _execute_cached_query(self, query: str, params: tuple = (), 
                            cache_key: Optional[str] = None,
                            cache_ttl: Optional[float] = None) -> List[sqlite3.Row]:
        """
        キャッシュ機能付きクエリ実行
        
        Args:
            query: SQLクエリ
            params: クエリパラメータ
            cache_key: キャッシュキー
            cache_ttl: キャッシュTTL
            
        Returns:
            クエリ結果
        """
        start_time = time.time()
        
        # キャッシュキーを生成
        if cache_key is None:
            cache_key = f"{query}:{str(params)}"
        
        # キャッシュから結果を取得
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            with self._stats_lock:
                self._query_stats["cache_hits"] += 1
                self._query_stats["total_queries"] += 1
            return cached_result
        
        # キャッシュにない場合はクエリを実行
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                results = cursor.fetchall()
                
                # 結果をキャッシュに保存
                self._put_to_cache(cache_key, results, cache_ttl or self._cache_ttl)
                
                # 統計を更新
                execution_time = time.time() - start_time
                with self._stats_lock:
                    self._query_stats["cache_misses"] += 1
                    self._query_stats["total_queries"] += 1
                    
                    # 平均クエリ時間を更新
                    total = self._query_stats["total_queries"]
                    current_avg = self._query_stats["avg_query_time"]
                    self._query_stats["avg_query_time"] = (
                        (current_avg * (total - 1) + execution_time) / total
                    )
                
                return results
                
        except Exception as e:
            self.logger.error(f"クエリ実行エラー: {e}")
            raise DatabaseError(f"クエリの実行に失敗しました: {e}")
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[sqlite3.Row]]:
        """キャッシュから結果を取得"""
        with self._cache_lock:
            if cache_key in self._query_cache:
                entry = self._query_cache[cache_key]
                if time.time() - entry["timestamp"] < entry["ttl"]:
                    return entry["data"]
                else:
                    # 期限切れエントリを削除
                    del self._query_cache[cache_key]
        return None
    
    def _put_to_cache(self, cache_key: str, data: List[sqlite3.Row], ttl: float):
        """結果をキャッシュに保存"""
        with self._cache_lock:
            self._query_cache[cache_key] = {
                "data": data,
                "timestamp": time.time(),
                "ttl": ttl
            }
            
            # キャッシュサイズ制限（1000エントリ）
            if len(self._query_cache) > 1000:
                # 最も古いエントリを削除
                oldest_key = min(self._query_cache.keys(), 
                               key=lambda k: self._query_cache[k]["timestamp"])
                del self._query_cache[oldest_key]
    
    def clear_query_cache(self):
        """クエリキャッシュをクリア"""
        with self._cache_lock:
            self._query_cache.clear()
        self.logger.info("クエリキャッシュをクリアしました")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計を取得"""
        with self._stats_lock:
            stats = self._query_stats.copy()
        
        with self._cache_lock:
            stats["cache_size"] = len(self._query_cache)
        
        stats["connection_pool_size"] = self._connection_pool._created_connections
        
        return stats
    
    def get_connection(self):
        """データベース接続のコンテキストマネージャー
        
        Yields:
            sqlite3.Connection: データベース接続オブジェクト
        """
        return self._connection_pool.get_connection()
    
    def _create_schema_version_table(self, conn: sqlite3.Connection):
        """スキーマバージョン管理テーブルを作成"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)
    
    def _get_schema_version(self, conn: sqlite3.Connection) -> int:
        """現在のスキーマバージョンを取得
        
        Returns:
            int: スキーマバージョン（存在しない場合は0）
        """
        cursor = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else 0
    
    def _set_schema_version(self, conn: sqlite3.Connection, version: int):
        """スキーマバージョンを設定"""
        conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (version,))
        conn.commit()
    
    def _create_schema(self, conn: sqlite3.Connection):
        """データベーススキーマを作成"""
        
        # ドキュメントテーブル
        conn.execute("""
            CREATE TABLE documents (
                id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                file_type TEXT NOT NULL,
                size INTEGER NOT NULL,
                created_date TIMESTAMP NOT NULL,
                modified_date TIMESTAMP NOT NULL,
                indexed_date TIMESTAMP NOT NULL,
                content_hash TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                CONSTRAINT chk_file_type CHECK (file_type IN ('pdf', 'word', 'excel', 'markdown', 'text', 'unknown')),
                CONSTRAINT chk_size CHECK (size >= 0)
            )
        """)
        
        # 検索履歴テーブル
        conn.execute("""
            CREATE TABLE search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                search_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                result_count INTEGER DEFAULT 0,
                execution_time_ms INTEGER DEFAULT 0,
                CONSTRAINT chk_search_type CHECK (search_type IN ('full_text', 'semantic', 'hybrid')),
                CONSTRAINT chk_result_count CHECK (result_count >= 0),
                CONSTRAINT chk_execution_time CHECK (execution_time_ms >= 0)
            )
        """)
        
        # 保存された検索テーブル
        conn.execute("""
            CREATE TABLE saved_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                query TEXT NOT NULL,
                search_type TEXT NOT NULL,
                search_options TEXT DEFAULT '{}',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                use_count INTEGER DEFAULT 0,
                CONSTRAINT chk_search_type CHECK (search_type IN ('full_text', 'semantic', 'hybrid')),
                CONSTRAINT chk_use_count CHECK (use_count >= 0)
            )
        """)
        
        # インデックス作成
        self._create_indexes(conn)
        
        conn.commit()
        self.logger.info("データベーススキーマを作成しました")
    
    def _create_indexes(self, conn: sqlite3.Connection):
        """パフォーマンス最適化のためのインデックスを作成"""
        
        # ドキュメントテーブルのインデックス
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_path ON documents(file_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(file_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_modified ON documents(modified_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_indexed ON documents(indexed_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash)")
        
        # 検索履歴テーブルのインデックス
        conn.execute("CREATE INDEX IF NOT EXISTS idx_search_history_timestamp ON search_history(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_search_history_type ON search_history(search_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_search_history_query ON search_history(query)")
        
        # 保存された検索テーブルのインデックス
        conn.execute("CREATE INDEX IF NOT EXISTS idx_saved_searches_name ON saved_searches(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_saved_searches_last_used ON saved_searches(last_used)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_saved_searches_use_count ON saved_searches(use_count)")
        
        self.logger.info("データベースインデックスを作成しました")
    
    def _migrate_schema(self, conn: sqlite3.Connection, from_version: int, to_version: int):
        """スキーママイグレーションを実行
        
        Args:
            conn: データベース接続
            from_version: 現在のバージョン
            to_version: 目標バージョン
        """
        self.logger.info(f"スキーママイグレーションを開始: v{from_version} -> v{to_version}")
        
        # 将来のマイグレーション処理をここに追加
        # 現在はバージョン1のみなので、マイグレーション処理は不要
        
        self._set_schema_version(conn, to_version)
        self.logger.info("スキーママイグレーションが完了しました")
    
    def health_check(self) -> bool:
        """データベースの健全性チェック
        
        Returns:
            bool: データベースが正常な場合True
        """
        try:
            with self.get_connection() as conn:
                # 基本的なクエリを実行してテスト
                cursor = conn.execute("SELECT COUNT(*) FROM documents")
                cursor.fetchone()
                
                # インデックスの整合性チェック
                conn.execute("PRAGMA integrity_check")
                
                return True
                
        except Exception as e:
            self.logger.error(f"データベース健全性チェック失敗: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """データベースの統計情報を取得
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # ドキュメント数
                cursor = conn.execute("SELECT COUNT(*) FROM documents")
                stats['document_count'] = cursor.fetchone()[0]
                
                # 検索履歴数
                cursor = conn.execute("SELECT COUNT(*) FROM search_history")
                stats['search_history_count'] = cursor.fetchone()[0]
                
                # 保存された検索数
                cursor = conn.execute("SELECT COUNT(*) FROM saved_searches")
                stats['saved_searches_count'] = cursor.fetchone()[0]
                
                # ファイルタイプ別統計
                cursor = conn.execute("""
                    SELECT file_type, COUNT(*) as count, SUM(size) as total_size
                    FROM documents 
                    GROUP BY file_type
                """)
                stats['file_type_stats'] = {row[0]: {'count': row[1], 'size': row[2]} 
                                          for row in cursor.fetchall()}
                
                # データベースファイルサイズ
                stats['db_file_size'] = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                return stats
                
        except Exception as e:
            self.logger.error(f"統計情報取得エラー: {e}")
            raise DatabaseError(f"統計情報の取得に失敗しました: {e}")
    
    def vacuum_database(self):
        """データベースの最適化（VACUUM）を実行"""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                self.logger.info("データベースの最適化が完了しました")
                
        except Exception as e:
            self.logger.error(f"データベース最適化エラー: {e}")
            raise DatabaseError(f"データベースの最適化に失敗しました: {e}")
    
    def close(self):
        """データベース接続を閉じる"""
        if hasattr(self, '_connection_pool'):
            self._connection_pool.close_all()
        self.logger.info("データベース接続を閉じました")