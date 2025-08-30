"""
データストレージの統合管理モジュール

このモジュールは、データベース層の各コンポーネントを統合し、
アプリケーション全体で使用される統一されたデータアクセスインターフェースを提供します。
"""

import logging
from pathlib import Path
from typing import Any

from ..utils.exceptions import DatabaseError
from .database import DatabaseManager
from .document_repository import DocumentRepository
from .models import Document, FileType, IndexStats, SearchType
from .search_history_repository import SearchHistoryRepository


class StorageManager:
    """データストレージの統合管理クラス

    データベース、ドキュメントリポジトリ、検索履歴リポジトリを統合し、
    アプリケーション全体で使用される統一されたデータアクセスインターフェースを提供します。
    """

    def __init__(self, data_dir: str):
        """StorageManagerを初期化

        Args:
            data_dir (str): データディレクトリのパス
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)

        # データベースマネージャーを初期化
        db_path = self.data_dir / "documents.db"
        self.db_manager = DatabaseManager(str(db_path))

        # リポジトリを初期化
        self.document_repository = DocumentRepository(self.db_manager)
        self.search_history_repository = SearchHistoryRepository(self.db_manager)

        self.logger.info(f"StorageManagerを初期化しました: {data_dir}")

    # ドキュメント関連操作
    def save_document(self, document: Document) -> bool:
        """ドキュメントを保存

        Args:
            document (Document): 保存するドキュメント

        Returns:
            bool: 成功した場合True
        """
        try:
            # 既存のドキュメントをチェック
            existing = self.document_repository.get_document_by_id(document.id)

            if existing:
                # 更新
                return self.document_repository.update_document(document)
            else:
                # 新規作成
                return self.document_repository.create_document(document)

        except Exception as e:
            self.logger.error(f"ドキュメント保存エラー: {e}")
            raise DatabaseError(f"ドキュメントの保存に失敗しました: {e}") from e

    def load_document(self, document_id: str) -> Document | None:
        """ドキュメントを読み込み

        Args:
            document_id (str): ドキュメントID

        Returns:
            Optional[Document]: 見つかった場合はDocumentオブジェクト
        """
        return self.document_repository.get_document_by_id(document_id)

    def load_document_by_path(self, file_path: str) -> Document | None:
        """ファイルパスでドキュメントを読み込み

        Args:
            file_path (str): ファイルパス

        Returns:
            Optional[Document]: 見つかった場合はDocumentオブジェクト
        """
        return self.document_repository.get_document_by_path(file_path)

    def delete_document(self, document_id: str) -> bool:
        """ドキュメントを削除

        Args:
            document_id (str): ドキュメントID

        Returns:
            bool: 成功した場合True
        """
        return self.document_repository.delete_document(document_id)

    def delete_document_by_path(self, file_path: str) -> bool:
        """ファイルパスでドキュメントを削除

        Args:
            file_path (str): ファイルパス

        Returns:
            bool: 成功した場合True
        """
        return self.document_repository.delete_document_by_path(file_path)

    def list_documents(
        self, limit: int | None = None, offset: int = 0
    ) -> list[Document]:
        """ドキュメントをリスト

        Args:
            limit (Optional[int]): 取得する最大件数
            offset (int): オフセット

        Returns:
            List[Document]: ドキュメントのリスト
        """
        return self.document_repository.get_all_documents(limit, offset)

    def list_documents_by_type(self, file_type: FileType) -> list[Document]:
        """ファイルタイプでドキュメントをリスト

        Args:
            file_type (FileType): ファイルタイプ

        Returns:
            List[Document]: 該当するドキュメントのリスト
        """
        return self.document_repository.get_documents_by_type(file_type)

    def search_documents_by_title(self, title_pattern: str) -> list[Document]:
        """タイトルでドキュメントを検索

        Args:
            title_pattern (str): 検索パターン

        Returns:
            List[Document]: 該当するドキュメントのリスト
        """
        return self.document_repository.search_documents_by_title(title_pattern)

    def bulk_save_documents(self, documents: list[Document]) -> int:
        """ドキュメントの一括保存

        Args:
            documents (List[Document]): 保存するドキュメントのリスト

        Returns:
            int: 保存されたドキュメント数
        """
        return self.document_repository.bulk_insert_documents(documents)

    def get_document_count(self) -> int:
        """総ドキュメント数を取得

        Returns:
            int: ドキュメント数
        """
        return self.document_repository.get_document_count()

    def get_index_stats(self) -> IndexStats:
        """インデックス統計情報を取得

        Returns:
            IndexStats: 統計情報
        """
        return self.document_repository.get_index_stats()

    # 検索履歴関連操作
    def record_search(
        self,
        query: str,
        search_type: SearchType,
        result_count: int,
        execution_time_ms: int,
    ) -> bool:
        """検索履歴を記録

        Args:
            query (str): 検索クエリ
            search_type (SearchType): 検索タイプ
            result_count (int): 結果数
            execution_time_ms (int): 実行時間（ミリ秒）

        Returns:
            bool: 成功した場合True
        """
        return self.search_history_repository.add_search_record(
            query, search_type, result_count, execution_time_ms
        )

    def get_recent_searches(self, limit: int = 50) -> list[dict[str, Any]]:
        """最近の検索履歴を取得

        Args:
            limit (int): 取得する最大件数

        Returns:
            List[Dict[str, Any]]: 検索履歴のリスト
        """
        return self.search_history_repository.get_recent_searches(limit)

    def get_popular_queries(
        self, days: int = 30, limit: int = 20
    ) -> list[dict[str, Any]]:
        """人気の検索クエリを取得

        Args:
            days (int): 対象期間（日数）
            limit (int): 取得する最大件数

        Returns:
            List[Dict[str, Any]]: 人気クエリのリスト
        """
        return self.search_history_repository.get_popular_queries(days, limit)

    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> list[str]:
        """検索提案を取得

        Args:
            partial_query (str): 部分的な検索クエリ
            limit (int): 取得する最大件数

        Returns:
            List[str]: 検索提案のリスト
        """
        return self.search_history_repository.get_search_suggestions(
            partial_query, limit
        )

    def get_search_statistics(self, days: int = 30) -> dict[str, Any]:
        """検索統計情報を取得

        Args:
            days (int): 対象期間（日数）

        Returns:
            Dict[str, Any]: 統計情報
        """
        return self.search_history_repository.get_search_statistics(days)

    def clear_old_search_history(self, days_to_keep: int = 90) -> int:
        """古い検索履歴を削除

        Args:
            days_to_keep (int): 保持する日数

        Returns:
            int: 削除されたレコード数
        """
        return self.search_history_repository.clear_old_history(days_to_keep)

    # システム管理操作
    def health_check(self) -> bool:
        """システムの健全性チェック

        Returns:
            bool: システムが正常な場合True
        """
        return self.db_manager.health_check()

    def get_system_stats(self) -> dict[str, Any]:
        """システム統計情報を取得

        Returns:
            Dict[str, Any]: システム統計情報
        """
        try:
            db_stats = self.db_manager.get_database_stats()
            index_stats = self.get_index_stats()
            search_stats = self.get_search_statistics()

            return {
                "database": db_stats,
                "index": {
                    "total_documents": index_stats.total_documents,
                    "total_size": index_stats.total_size,
                    "formatted_size": index_stats.get_formatted_size(),
                    "last_updated": index_stats.last_updated,
                    "file_type_counts": {
                        ft.value: count
                        for ft, count in index_stats.file_type_counts.items()
                    },
                },
                "search": search_stats,
                "storage_path": str(self.data_dir),
            }

        except Exception as e:
            self.logger.error(f"システム統計取得エラー: {e}")
            raise DatabaseError(f"システム統計の取得に失敗しました: {e}")

    def optimize_database(self):
        """データベースの最適化を実行"""
        try:
            self.db_manager.vacuum_database()
            self.logger.info("データベースの最適化が完了しました")

        except Exception as e:
            self.logger.error(f"データベース最適化エラー: {e}")
            raise DatabaseError(f"データベースの最適化に失敗しました: {e}")

    def backup_database(self, backup_path: str) -> bool:
        """データベースのバックアップを作成

        Args:
            backup_path (str): バックアップファイルのパス

        Returns:
            bool: 成功した場合True
        """
        try:
            import shutil

            db_path = self.data_dir / "documents.db"
            if db_path.exists():
                shutil.copy2(str(db_path), backup_path)
                self.logger.info(f"データベースをバックアップしました: {backup_path}")
                return True
            else:
                self.logger.warning(
                    "バックアップ対象のデータベースファイルが見つかりません"
                )
                return False

        except Exception as e:
            self.logger.error(f"データベースバックアップエラー: {e}")
            raise DatabaseError(f"データベースのバックアップに失敗しました: {e}")

    def restore_database(self, backup_path: str) -> bool:
        """データベースのリストアを実行

        Args:
            backup_path (str): バックアップファイルのパス

        Returns:
            bool: 成功した場合True
        """
        try:
            import shutil

            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise FileNotFoundError(
                    f"バックアップファイルが見つかりません: {backup_path}"
                )

            db_path = self.data_dir / "documents.db"

            # 現在のデータベースをバックアップ
            if db_path.exists():
                backup_current = db_path.with_suffix(".db.backup")
                shutil.copy2(str(db_path), str(backup_current))

            # バックアップからリストア
            shutil.copy2(backup_path, str(db_path))

            # 新しいデータベースで再初期化
            self.db_manager = DatabaseManager(str(db_path))
            self.document_repository = DocumentRepository(self.db_manager)
            self.search_history_repository = SearchHistoryRepository(self.db_manager)

            self.logger.info(f"データベースをリストアしました: {backup_path}")
            return True

        except Exception as e:
            self.logger.error(f"データベースリストアエラー: {e}")
            raise DatabaseError(f"データベースのリストアに失敗しました: {e}")

    def close(self):
        """リソースのクリーンアップ"""
        # 現在は特別なクリーンアップ処理は不要
        # 将来的にコネクションプールなどを使用する場合はここで処理
        self.logger.info("StorageManagerをクローズしました")
