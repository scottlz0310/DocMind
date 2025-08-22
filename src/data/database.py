"""
DocMindアプリケーション用のデータベース管理モジュール

このモジュールは、SQLiteデータベースの接続、スキーマ管理、マイグレーション機能を提供します。
ドキュメントメタデータと検索履歴の永続化を担当します。
"""

import sqlite3
import logging
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import Document, FileType, SearchType, IndexStats
from ..utils.exceptions import DatabaseError, DocumentNotFoundError


class DatabaseManager:
    """SQLiteデータベースの管理を行うクラス
    
    データベース接続、スキーマ作成、マイグレーション、基本的なCRUD操作を提供します。
    スレッドセーフな操作とトランザクション管理をサポートします。
    """
    
    # データベーススキーマのバージョン
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: str):
        """DatabaseManagerを初期化
        
        Args:
            db_path (str): データベースファイルのパス
        """
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        
        # データベースディレクトリを作成
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # データベースを初期化
        self._initialize_database()
    
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
    
    @contextmanager
    def get_connection(self):
        """データベース接続のコンテキストマネージャー
        
        Yields:
            sqlite3.Connection: データベース接続オブジェクト
        """
        conn = None
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,  # 30秒のタイムアウト
                check_same_thread=False  # マルチスレッド対応
            )
            
            # 外部キー制約を有効化
            conn.execute("PRAGMA foreign_keys = ON")
            
            # WALモードを有効化（パフォーマンス向上）
            conn.execute("PRAGMA journal_mode = WAL")
            
            # 行ファクトリを設定（辞書形式でアクセス可能）
            conn.row_factory = sqlite3.Row
            
            yield conn
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"データベース接続エラー: {e}")
            raise DatabaseError(f"データベース操作に失敗しました: {e}")
        finally:
            if conn:
                conn.close()
    
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