"""
StorageManagerクラスのユニットテスト

このモジュールは、StorageManagerの統合機能をテストし、
データベース層の各コンポーネントが正しく連携することを検証します。
"""

import tempfile
from pathlib import Path

import pytest

from src.data.models import Document, FileType, SearchType
from src.data.storage import StorageManager


class TestStorageManager:
    """StorageManagerクラスのテスト"""

    @pytest.fixture
    def temp_data_dir(self):
        """テスト用の一時データディレクトリを提供"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def storage_manager(self, temp_data_dir):
        """テスト用のStorageManagerインスタンスを提供"""
        return StorageManager(temp_data_dir)

    @pytest.fixture
    def sample_document(self, tmp_path):
        """テスト用のサンプルドキュメントを作成"""
        test_file = tmp_path / "storage_test.txt"
        test_file.write_text("StorageManagerテスト用のドキュメントです。", encoding='utf-8')

        return Document.create_from_file(str(test_file), "StorageManagerテスト用のコンテンツです。")

    def test_initialization(self, storage_manager, temp_data_dir):
        """StorageManagerの初期化をテスト"""
        # データディレクトリが作成されることを確認
        assert Path(temp_data_dir).exists()

        # データベースファイルが作成されることを確認
        db_path = Path(temp_data_dir) / "documents.db"
        assert db_path.exists()

        # 健全性チェックが成功することを確認
        assert storage_manager.health_check()

    def test_save_and_load_document(self, storage_manager, sample_document):
        """ドキュメントの保存と読み込みをテスト"""
        # ドキュメントを保存
        result = storage_manager.save_document(sample_document)
        assert result is True

        # IDで読み込み
        loaded = storage_manager.load_document(sample_document.id)
        assert loaded is not None
        assert loaded.id == sample_document.id
        assert loaded.title == sample_document.title

        # パスで読み込み
        loaded_by_path = storage_manager.load_document_by_path(sample_document.file_path)
        assert loaded_by_path is not None
        assert loaded_by_path.id == sample_document.id

    def test_update_document(self, storage_manager, sample_document):
        """ドキュメントの更新をテスト"""
        # 初回保存
        storage_manager.save_document(sample_document)

        # タイトルを変更して再保存（更新）
        sample_document.title = "更新されたタイトル"
        result = storage_manager.save_document(sample_document)
        assert result is True

        # 更新されたことを確認
        loaded = storage_manager.load_document(sample_document.id)
        assert loaded.title == "更新されたタイトル"

    def test_delete_document(self, storage_manager, sample_document):
        """ドキュメントの削除をテスト"""
        # ドキュメントを保存
        storage_manager.save_document(sample_document)

        # IDで削除
        result = storage_manager.delete_document(sample_document.id)
        assert result is True

        # 削除されたことを確認
        loaded = storage_manager.load_document(sample_document.id)
        assert loaded is None

    def test_delete_document_by_path(self, storage_manager, sample_document):
        """パスによるドキュメント削除をテスト"""
        # ドキュメントを保存
        storage_manager.save_document(sample_document)

        # パスで削除
        result = storage_manager.delete_document_by_path(sample_document.file_path)
        assert result is True

        # 削除されたことを確認
        loaded = storage_manager.load_document_by_path(sample_document.file_path)
        assert loaded is None

    def test_list_documents(self, storage_manager, tmp_path):
        """ドキュメント一覧取得をテスト"""
        # 複数のドキュメントを作成・保存
        documents = []
        for i in range(5):
            test_file = tmp_path / f"list_test_{i}.txt"
            test_file.write_text(f"リストテスト{i}", encoding='utf-8')
            doc = Document.create_from_file(str(test_file), f"コンテンツ{i}")
            documents.append(doc)
            storage_manager.save_document(doc)

        # 全ドキュメントを取得
        all_docs = storage_manager.list_documents()
        assert len(all_docs) == 5

        # 制限付きで取得
        limited_docs = storage_manager.list_documents(limit=3)
        assert len(limited_docs) == 3

    def test_list_documents_by_type(self, storage_manager, tmp_path):
        """ファイルタイプ別ドキュメント一覧をテスト"""
        # 異なるタイプのファイルを作成
        txt_file = tmp_path / "type_test.txt"
        txt_file.write_text("テキストファイル", encoding='utf-8')
        txt_doc = Document.create_from_file(str(txt_file), "テキストコンテンツ")

        md_file = tmp_path / "type_test.md"
        md_file.write_text("# マークダウンファイル", encoding='utf-8')
        md_doc = Document.create_from_file(str(md_file), "マークダウンコンテンツ")

        storage_manager.save_document(txt_doc)
        storage_manager.save_document(md_doc)

        # テキストファイルのみ取得
        txt_docs = storage_manager.list_documents_by_type(FileType.TEXT)
        assert len(txt_docs) == 1
        assert txt_docs[0].file_type == FileType.TEXT

        # マークダウンファイルのみ取得
        md_docs = storage_manager.list_documents_by_type(FileType.MARKDOWN)
        assert len(md_docs) == 1
        assert md_docs[0].file_type == FileType.MARKDOWN

    def test_search_documents_by_title(self, storage_manager, tmp_path):
        """タイトル検索をテスト"""
        # 異なるタイトルのドキュメントを作成
        titles = ["プロジェクト計画書", "設計書", "テスト計画書", "ユーザーマニュアル"]

        for title in titles:
            test_file = tmp_path / f"{title}.txt"
            test_file.write_text(title, encoding='utf-8')
            doc = Document.create_from_file(str(test_file), title)
            doc.title = title
            storage_manager.save_document(doc)

        # "計画書"を含むドキュメントを検索
        results = storage_manager.search_documents_by_title("計画書")
        assert len(results) == 2

        # "設計"を含むドキュメントを検索
        results = storage_manager.search_documents_by_title("設計")
        assert len(results) == 1
        assert results[0].title == "設計書"

    def test_bulk_save_documents(self, storage_manager, tmp_path):
        """一括保存をテスト"""
        # 複数のドキュメントを準備
        documents = []
        for i in range(10):
            test_file = tmp_path / f"bulk_save_{i}.txt"
            test_file.write_text(f"一括保存テスト{i}", encoding='utf-8')
            doc = Document.create_from_file(str(test_file), f"一括コンテンツ{i}")
            documents.append(doc)

        # 一括保存
        result = storage_manager.bulk_save_documents(documents)
        assert result == 10

        # 保存されたことを確認
        assert storage_manager.get_document_count() == 10

    def test_get_document_count(self, storage_manager, tmp_path):
        """ドキュメント数取得をテスト"""
        # 初期状態では0件
        assert storage_manager.get_document_count() == 0

        # ドキュメントを追加
        for i in range(3):
            test_file = tmp_path / f"count_test_{i}.txt"
            test_file.write_text(f"カウントテスト{i}", encoding='utf-8')
            doc = Document.create_from_file(str(test_file), f"コンテンツ{i}")
            storage_manager.save_document(doc)

        assert storage_manager.get_document_count() == 3

    def test_get_index_stats(self, storage_manager, tmp_path):
        """インデックス統計取得をテスト"""
        # 初期状態の統計
        stats = storage_manager.get_index_stats()
        assert stats.total_documents == 0
        assert stats.total_size == 0

        # ドキュメントを追加
        test_file = tmp_path / "stats_test.txt"
        test_content = "統計テスト用のコンテンツです。"
        test_file.write_text(test_content, encoding='utf-8')

        doc = Document.create_from_file(str(test_file), test_content)
        storage_manager.save_document(doc)

        # 統計を再取得
        stats = storage_manager.get_index_stats()
        assert stats.total_documents == 1
        assert stats.total_size > 0
        assert FileType.TEXT in stats.file_type_counts
        assert stats.file_type_counts[FileType.TEXT] == 1

    def test_record_search(self, storage_manager):
        """検索履歴記録をテスト"""
        result = storage_manager.record_search(
            query="テスト検索",
            search_type=SearchType.FULL_TEXT,
            result_count=5,
            execution_time_ms=150
        )
        assert result is True

    def test_get_recent_searches(self, storage_manager):
        """最近の検索履歴取得をテスト"""
        # 複数の検索履歴を記録
        searches = [
            ("Python プログラミング", SearchType.FULL_TEXT, 10, 120),
            ("機械学習 入門", SearchType.SEMANTIC, 8, 200),
            ("データベース 設計", SearchType.HYBRID, 15, 180)
        ]

        for query, search_type, result_count, exec_time in searches:
            storage_manager.record_search(query, search_type, result_count, exec_time)

        # 最近の検索履歴を取得
        recent = storage_manager.get_recent_searches(limit=5)
        assert len(recent) == 3

        # 最新のものが最初に来ることを確認
        assert recent[0]['query'] == "データベース 設計"
        assert recent[0]['search_type'] == SearchType.HYBRID

    def test_get_popular_queries(self, storage_manager):
        """人気クエリ取得をテスト"""
        # 同じクエリを複数回記録
        for _ in range(3):
            storage_manager.record_search("人気クエリ", SearchType.FULL_TEXT, 5, 100)

        for _ in range(2):
            storage_manager.record_search("普通のクエリ", SearchType.SEMANTIC, 3, 150)

        # 人気クエリを取得
        popular = storage_manager.get_popular_queries(days=30, limit=10)
        assert len(popular) >= 1

        # 最も人気のあるクエリが最初に来ることを確認
        assert popular[0]['query'] == "人気クエリ"
        assert popular[0]['search_count'] == 3

    def test_get_search_suggestions(self, storage_manager):
        """検索提案取得をテスト"""
        # 類似したクエリを記録
        queries = [
            "Python プログラミング基礎",
            "Python 入門",
            "Python データ分析"
        ]

        for query in queries:
            storage_manager.record_search(query, SearchType.FULL_TEXT, 5, 100)

        # "Python"で始まる提案を取得
        suggestions = storage_manager.get_search_suggestions("Python", limit=5)
        assert len(suggestions) == 3

        # すべて"Python"で始まることを確認
        for suggestion in suggestions:
            assert suggestion.startswith("Python")

    def test_get_search_statistics(self, storage_manager):
        """検索統計取得をテスト"""
        # 異なるタイプの検索を記録
        storage_manager.record_search("クエリ1", SearchType.FULL_TEXT, 10, 100)
        storage_manager.record_search("クエリ2", SearchType.SEMANTIC, 5, 200)
        storage_manager.record_search("クエリ3", SearchType.HYBRID, 8, 150)

        # 統計を取得
        stats = storage_manager.get_search_statistics(days=30)

        assert stats['total_searches'] == 3
        assert 'by_search_type' in stats
        assert 'daily_counts' in stats
        assert 'performance' in stats

    def test_clear_old_search_history(self, storage_manager):
        """古い検索履歴削除をテスト"""
        # 検索履歴を記録
        storage_manager.record_search("新しい検索", SearchType.FULL_TEXT, 5, 100)

        # 古い履歴を削除（90日より古いもの）
        deleted_count = storage_manager.clear_old_search_history(days_to_keep=90)
        # 新しい検索なので削除されない
        assert deleted_count == 0

        # 検索履歴が残っていることを確認
        recent = storage_manager.get_recent_searches(limit=10)
        assert len(recent) == 1
        assert recent[0]['query'] == "新しい検索"

    def test_get_system_stats(self, storage_manager, tmp_path):
        """システム統計取得をテスト"""
        # ドキュメントと検索履歴を追加
        test_file = tmp_path / "system_stats_test.txt"
        test_file.write_text("システム統計テスト", encoding='utf-8')
        doc = Document.create_from_file(str(test_file), "システム統計テスト")
        storage_manager.save_document(doc)

        storage_manager.record_search("システムテスト", SearchType.FULL_TEXT, 1, 100)

        # システム統計を取得
        stats = storage_manager.get_system_stats()

        assert 'database' in stats
        assert 'index' in stats
        assert 'search' in stats
        assert 'storage_path' in stats

        # インデックス統計を確認
        assert stats['index']['total_documents'] == 1
        assert stats['index']['total_size'] > 0

        # 検索統計を確認
        assert stats['search']['total_searches'] == 1

    def test_optimize_database(self, storage_manager):
        """データベース最適化をテスト"""
        # 例外が発生しないことを確認
        storage_manager.optimize_database()

    def test_backup_and_restore_database(self, storage_manager, sample_document, tmp_path):
        """データベースのバックアップとリストアをテスト"""
        # ドキュメントを保存
        storage_manager.save_document(sample_document)

        # バックアップを作成
        backup_path = tmp_path / "backup.db"
        result = storage_manager.backup_database(str(backup_path))
        assert result is True
        assert backup_path.exists()

        # ドキュメントを削除
        storage_manager.delete_document(sample_document.id)
        assert storage_manager.get_document_count() == 0

        # バックアップからリストア
        result = storage_manager.restore_database(str(backup_path))
        assert result is True

        # ドキュメントが復元されたことを確認
        assert storage_manager.get_document_count() == 1
        restored = storage_manager.load_document(sample_document.id)
        assert restored is not None
        assert restored.title == sample_document.title

    def test_close(self, storage_manager):
        """StorageManagerのクローズをテスト"""
        # 例外が発生しないことを確認
        storage_manager.close()
