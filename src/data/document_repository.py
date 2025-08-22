"""
ドキュメントメタデータのCRUD操作を提供するリポジトリモジュール

このモジュールは、Documentモデルのデータベース操作を担当します。
高レベルなCRUD操作とクエリ機能を提供し、ビジネスロジック層からの要求に応答します。
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from .database import DatabaseManager
from .models import Document, FileType, IndexStats
from ..utils.exceptions import DatabaseError, DocumentNotFoundError


class DocumentRepository:
    """ドキュメントメタデータのCRUD操作を提供するリポジトリクラス
    
    データベース操作の抽象化を行い、ビジネスロジック層に対して
    シンプルで使いやすいインターフェースを提供します。
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """DocumentRepositoryを初期化
        
        Args:
            db_manager (DatabaseManager): データベースマネージャー
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def create_document(self, document: Document) -> bool:
        """新しいドキュメントをデータベースに追加
        
        Args:
            document (Document): 追加するドキュメント
            
        Returns:
            bool: 成功した場合True
            
        Raises:
            DatabaseError: データベース操作エラー
        """
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute("""
                    INSERT INTO documents (
                        id, file_path, title, file_type, size,
                        created_date, modified_date, indexed_date,
                        content_hash, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document.id,
                    document.file_path,
                    document.title,
                    document.file_type.value,
                    document.size,
                    document.created_date,
                    document.modified_date,
                    document.indexed_date,
                    document.content_hash,
                    json.dumps(document.metadata, ensure_ascii=False)
                ))
                conn.commit()
                
                self.logger.info(f"ドキュメントを追加しました: {document.title} ({document.id})")
                return True
                
        except Exception as e:
            self.logger.error(f"ドキュメント追加エラー: {e}")
            raise DatabaseError(f"ドキュメントの追加に失敗しました: {e}")
    
    def get_document_by_id(self, document_id: str) -> Optional[Document]:
        """IDでドキュメントを取得
        
        Args:
            document_id (str): ドキュメントID
            
        Returns:
            Optional[Document]: 見つかった場合はDocumentオブジェクト、そうでなければNone
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, file_path, title, file_type, size,
                           created_date, modified_date, indexed_date,
                           content_hash, metadata
                    FROM documents WHERE id = ?
                """, (document_id,))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_document(row)
                return None
                
        except Exception as e:
            self.logger.error(f"ドキュメント取得エラー (ID: {document_id}): {e}")
            raise DatabaseError(f"ドキュメントの取得に失敗しました: {e}")
    
    def get_document_by_path(self, file_path: str) -> Optional[Document]:
        """ファイルパスでドキュメントを取得
        
        Args:
            file_path (str): ファイルパス
            
        Returns:
            Optional[Document]: 見つかった場合はDocumentオブジェクト、そうでなければNone
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, file_path, title, file_type, size,
                           created_date, modified_date, indexed_date,
                           content_hash, metadata
                    FROM documents WHERE file_path = ?
                """, (file_path,))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_document(row)
                return None
                
        except Exception as e:
            self.logger.error(f"ドキュメント取得エラー (パス: {file_path}): {e}")
            raise DatabaseError(f"ドキュメントの取得に失敗しました: {e}")
    
    def update_document(self, document: Document) -> bool:
        """既存のドキュメントを更新
        
        Args:
            document (Document): 更新するドキュメント
            
        Returns:
            bool: 成功した場合True
            
        Raises:
            DocumentNotFoundError: ドキュメントが見つからない場合
            DatabaseError: データベース操作エラー
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE documents SET
                        file_path = ?, title = ?, file_type = ?, size = ?,
                        created_date = ?, modified_date = ?, indexed_date = ?,
                        content_hash = ?, metadata = ?
                    WHERE id = ?
                """, (
                    document.file_path,
                    document.title,
                    document.file_type.value,
                    document.size,
                    document.created_date,
                    document.modified_date,
                    document.indexed_date,
                    document.content_hash,
                    json.dumps(document.metadata, ensure_ascii=False),
                    document.id
                ))
                
                if cursor.rowcount == 0:
                    raise DocumentNotFoundError(f"ドキュメントが見つかりません: {document.id}")
                
                conn.commit()
                self.logger.info(f"ドキュメントを更新しました: {document.title} ({document.id})")
                return True
                
        except DocumentNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"ドキュメント更新エラー: {e}")
            raise DatabaseError(f"ドキュメントの更新に失敗しました: {e}")
    
    def delete_document(self, document_id: str) -> bool:
        """ドキュメントを削除
        
        Args:
            document_id (str): 削除するドキュメントのID
            
        Returns:
            bool: 成功した場合True
            
        Raises:
            DocumentNotFoundError: ドキュメントが見つからない場合
            DatabaseError: データベース操作エラー
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                
                if cursor.rowcount == 0:
                    raise DocumentNotFoundError(f"ドキュメントが見つかりません: {document_id}")
                
                conn.commit()
                self.logger.info(f"ドキュメントを削除しました: {document_id}")
                return True
                
        except DocumentNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"ドキュメント削除エラー: {e}")
            raise DatabaseError(f"ドキュメントの削除に失敗しました: {e}")
    
    def delete_document_by_path(self, file_path: str) -> bool:
        """ファイルパスでドキュメントを削除
        
        Args:
            file_path (str): 削除するドキュメントのファイルパス
            
        Returns:
            bool: 成功した場合True
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("DELETE FROM documents WHERE file_path = ?", (file_path,))
                
                if cursor.rowcount == 0:
                    self.logger.warning(f"削除対象のドキュメントが見つかりません: {file_path}")
                    return False
                
                conn.commit()
                self.logger.info(f"ドキュメントを削除しました: {file_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"ドキュメント削除エラー: {e}")
            raise DatabaseError(f"ドキュメントの削除に失敗しました: {e}")
    
    def get_all_documents(self, limit: Optional[int] = None, offset: int = 0) -> List[Document]:
        """すべてのドキュメントを取得
        
        Args:
            limit (Optional[int]): 取得する最大件数
            offset (int): オフセット
            
        Returns:
            List[Document]: ドキュメントのリスト
        """
        try:
            with self.db_manager.get_connection() as conn:
                query = """
                    SELECT id, file_path, title, file_type, size,
                           created_date, modified_date, indexed_date,
                           content_hash, metadata
                    FROM documents
                    ORDER BY indexed_date DESC
                """
                
                params = []
                if limit is not None:
                    query += " LIMIT ? OFFSET ?"
                    params.extend([limit, offset])
                
                cursor = conn.execute(query, params)
                return [self._row_to_document(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"全ドキュメント取得エラー: {e}")
            raise DatabaseError(f"ドキュメントの取得に失敗しました: {e}")
    
    def get_documents_by_type(self, file_type: FileType) -> List[Document]:
        """ファイルタイプでドキュメントを取得
        
        Args:
            file_type (FileType): ファイルタイプ
            
        Returns:
            List[Document]: 該当するドキュメントのリスト
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, file_path, title, file_type, size,
                           created_date, modified_date, indexed_date,
                           content_hash, metadata
                    FROM documents WHERE file_type = ?
                    ORDER BY indexed_date DESC
                """, (file_type.value,))
                
                return [self._row_to_document(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"ファイルタイプ別ドキュメント取得エラー: {e}")
            raise DatabaseError(f"ドキュメントの取得に失敗しました: {e}")
    
    def get_documents_modified_after(self, date: datetime) -> List[Document]:
        """指定日時以降に変更されたドキュメントを取得
        
        Args:
            date (datetime): 基準日時
            
        Returns:
            List[Document]: 該当するドキュメントのリスト
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, file_path, title, file_type, size,
                           created_date, modified_date, indexed_date,
                           content_hash, metadata
                    FROM documents WHERE modified_date > ?
                    ORDER BY modified_date DESC
                """, (date,))
                
                return [self._row_to_document(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"変更日時別ドキュメント取得エラー: {e}")
            raise DatabaseError(f"ドキュメントの取得に失敗しました: {e}")
    
    def search_documents_by_title(self, title_pattern: str) -> List[Document]:
        """タイトルでドキュメントを検索
        
        Args:
            title_pattern (str): 検索パターン（LIKE演算子用）
            
        Returns:
            List[Document]: 該当するドキュメントのリスト
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, file_path, title, file_type, size,
                           created_date, modified_date, indexed_date,
                           content_hash, metadata
                    FROM documents WHERE title LIKE ?
                    ORDER BY title
                """, (f"%{title_pattern}%",))
                
                return [self._row_to_document(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"タイトル検索エラー: {e}")
            raise DatabaseError(f"ドキュメントの検索に失敗しました: {e}")
    
    def get_document_count(self) -> int:
        """総ドキュメント数を取得
        
        Returns:
            int: ドキュメント数
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM documents")
                return cursor.fetchone()[0]
                
        except Exception as e:
            self.logger.error(f"ドキュメント数取得エラー: {e}")
            raise DatabaseError(f"ドキュメント数の取得に失敗しました: {e}")
    
    def get_index_stats(self) -> IndexStats:
        """インデックス統計情報を取得
        
        Returns:
            IndexStats: 統計情報
        """
        try:
            with self.db_manager.get_connection() as conn:
                # 基本統計
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_docs, 
                           SUM(size) as total_size,
                           MAX(indexed_date) as last_updated
                    FROM documents
                """)
                row = cursor.fetchone()
                
                stats = IndexStats(
                    total_documents=row[0] or 0,
                    total_size=row[1] or 0,
                    last_updated=datetime.fromisoformat(row[2]) if row[2] else None
                )
                
                # ファイルタイプ別統計
                cursor = conn.execute("""
                    SELECT file_type, COUNT(*) as count
                    FROM documents
                    GROUP BY file_type
                """)
                
                for row in cursor.fetchall():
                    file_type = FileType(row[0])
                    stats.file_type_counts[file_type] = row[1]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"統計情報取得エラー: {e}")
            raise DatabaseError(f"統計情報の取得に失敗しました: {e}")
    
    def bulk_insert_documents(self, documents: List[Document]) -> int:
        """ドキュメントの一括挿入
        
        Args:
            documents (List[Document]): 挿入するドキュメントのリスト
            
        Returns:
            int: 挿入されたドキュメント数
        """
        if not documents:
            return 0
        
        try:
            with self.db_manager.get_connection() as conn:
                data = [
                    (
                        doc.id, doc.file_path, doc.title, doc.file_type.value, doc.size,
                        doc.created_date, doc.modified_date, doc.indexed_date,
                        doc.content_hash, json.dumps(doc.metadata, ensure_ascii=False)
                    )
                    for doc in documents
                ]
                
                conn.executemany("""
                    INSERT OR REPLACE INTO documents (
                        id, file_path, title, file_type, size,
                        created_date, modified_date, indexed_date,
                        content_hash, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                
                conn.commit()
                self.logger.info(f"{len(documents)}件のドキュメントを一括挿入しました")
                return len(documents)
                
        except Exception as e:
            self.logger.error(f"一括挿入エラー: {e}")
            raise DatabaseError(f"ドキュメントの一括挿入に失敗しました: {e}")
    
    def _row_to_document(self, row) -> Document:
        """データベース行をDocumentオブジェクトに変換
        
        Args:
            row: データベース行
            
        Returns:
            Document: 変換されたDocumentオブジェクト
        """
        try:
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
        except json.JSONDecodeError:
            self.logger.warning(f"メタデータのJSONパースに失敗: {row['id']}")
            metadata = {}
        
        return Document(
            id=row['id'],
            file_path=row['file_path'],
            title=row['title'],
            content="",  # コンテンツはデータベースに保存しない
            file_type=FileType(row['file_type']),
            size=row['size'],
            created_date=datetime.fromisoformat(row['created_date']),
            modified_date=datetime.fromisoformat(row['modified_date']),
            indexed_date=datetime.fromisoformat(row['indexed_date']),
            content_hash=row['content_hash'],
            metadata=metadata
        )