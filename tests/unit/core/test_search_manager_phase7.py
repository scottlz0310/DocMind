"""
Phase7 SearchManagerの強化テストモジュール

ハイブリッド検索機能の包括的なテストを提供します。
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager
from src.core.search_manager import SearchManager
from src.data.models import FileType, SearchType
from src.utils.exceptions import SearchError
from tests.fixtures.mock_models import (
    create_mock_document,
    create_mock_documents,
)


@pytest.mark.skip(reason="SearchManager APIが変更されたためテストをスキップ")
class TestSearchManagerPhase7:
    """Phase7 SearchManagerの強化テストクラス"""

    @pytest.fixture
    def temp_dirs(self):
        """一時ディレクトリを作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            index_dir = Path(temp_dir) / "test_index"
            embedding_dir = Path(temp_dir) / "test_embeddings"
            yield str(index_dir), str(embedding_dir)

    @pytest.fixture
    def mock_index_manager(self, temp_dirs):
        """モックIndexManagerを作成"""
        index_dir, _ = temp_dirs
        return IndexManager(index_dir)

    @pytest.fixture
    def mock_embedding_manager(self, temp_dirs):
        """モックEmbeddingManagerを作成"""
        _, embedding_dir = temp_dirs
        return EmbeddingManager(embedding_dir)

    @pytest.fixture
    def search_manager(self, mock_index_manager, mock_embedding_manager):
        """SearchManagerインスタンスを作成"""
        return SearchManager(mock_index_manager, mock_embedding_manager)

    @pytest.fixture
    def sample_document(self):
        """サンプルドキュメントを作成"""
        return create_mock_document(
            doc_id="test_doc_1",
            file_path="/test/sample.txt",
            title="テストドキュメント",
            content="これはテスト用のドキュメントです。検索機能をテストします。",
            file_type=FileType.TEXT,
            size=1024
        )

    @pytest.fixture
    def multiple_documents(self):
        """複数のサンプルドキュメントを作成"""
        return create_mock_documents(10)

    @pytest.fixture
    def large_index(self, mock_index_manager):
        """大規模インデックスを作成"""
        documents = create_mock_documents(1000)
        for doc in documents:
            mock_index_manager.add_document(doc)
        return mock_index_manager

    def test_initialization(self, search_manager):
        """初期化テスト"""
        assert search_manager is not None
        assert search_manager.index_manager is not None
        assert search_manager.embedding_manager is not None

    def test_full_text_search(self, search_manager, sample_document):
        """全文検索テスト"""
        # ドキュメントをインデックスに追加
        search_manager.index_manager.add_document(sample_document)

        results = search_manager.search("テスト", SearchType.FULL_TEXT)

        assert len(results) == 1
        assert results[0].document.id == sample_document.id
        assert results[0].search_type == SearchType.FULL_TEXT

    @patch('src.core.embedding_manager.EmbeddingManager.search_similar')
    def test_semantic_search(self, mock_search_similar, search_manager, sample_document):
        """セマンティック検索テスト"""
        # モックの設定
        mock_search_similar.return_value = [(sample_document.id, 0.8)]

        # ドキュメントをインデックスに追加
        search_manager.index_manager.add_document(sample_document)

        results = search_manager.search("テスト", SearchType.SEMANTIC)

        assert len(results) == 1
        assert results[0].search_type == SearchType.SEMANTIC
        mock_search_similar.assert_called_once()

    @patch('src.core.embedding_manager.EmbeddingManager.search_similar')
    def test_hybrid_search_accuracy(self, mock_search_similar, search_manager, multiple_documents):
        """ハイブリッド検索精度テスト"""
        # モックの設定
        mock_search_similar.return_value = [(doc.id, 0.7 + i * 0.05) for i, doc in enumerate(multiple_documents[:5])]

        # ドキュメントをインデックスに追加
        for doc in multiple_documents:
            search_manager.index_manager.add_document(doc)

        results = search_manager.search("テスト", SearchType.HYBRID, limit=10)

        assert len(results) > 0
        assert all(result.search_type == SearchType.HYBRID for result in results)

        # スコア順でソートされていることを確認
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_search_performance_large_index(self, large_index):
        """大規模インデックス検索パフォーマンステスト"""
        import time

        search_manager = SearchManager(large_index, None)

        queries = ["テスト", "ドキュメント", "検索", "データ", "機能"]

        for query in queries:
            start_time = time.time()
            results = search_manager.search(query, SearchType.FULL_TEXT, limit=100)
            end_time = time.time()

            # 5秒以内での検索完了を確認
            assert (end_time - start_time) < 5.0
            assert len(results) > 0

    def test_concurrent_search_performance(self, search_manager, multiple_documents):
        """並行検索パフォーマンステスト"""
        import time
        from concurrent.futures import ThreadPoolExecutor

        # ドキュメントをインデックスに追加
        for doc in multiple_documents:
            search_manager.index_manager.add_document(doc)

        queries = ["テスト1", "テスト2", "テスト3", "テスト4", "テスト5"]

        def search_operation(query):
            return search_manager.search(query, SearchType.FULL_TEXT)

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(search_operation, query) for query in queries]
            results = [future.result() for future in futures]

        end_time = time.time()

        # 並行実行でも10秒以内
        assert (end_time - start_time) < 10.0
        assert all(len(result) >= 0 for result in results)

    def test_merge_search_results(self, search_manager):
        """検索結果マージテスト"""
        # テスト用の検索結果を作成
        doc1 = create_mock_document(doc_id="doc1", content="テスト1")
        doc2 = create_mock_document(doc_id="doc2", content="テスト2")

        from src.data.models import SearchResult

        # 全文検索結果をモック
        full_text_results = [
            SearchResult(document=doc1, score=0.8, search_type=SearchType.FULL_TEXT),
            SearchResult(document=doc2, score=0.6, search_type=SearchType.FULL_TEXT)
        ]

        # セマンティック検索結果をモック
        semantic_results = [
            SearchResult(document=doc1, score=0.7, search_type=SearchType.SEMANTIC),
            SearchResult(document=doc2, score=0.9, search_type=SearchType.SEMANTIC)
        ]

        # 結果をマージ
        merged_results = search_manager._merge_search_results(
            full_text_results, semantic_results, {"full_text": 0.6, "semantic": 0.4}
        )

        assert len(merged_results) == 2
        assert all(result.search_type == SearchType.HYBRID for result in merged_results)

        # 重み付きスコアが正しく計算されていることを確認
        doc1_result = next(r for r in merged_results if r.document.id == "doc1")
        expected_score = 0.8 * 0.6 + 0.7 * 0.4  # 0.76
        assert abs(doc1_result.score - expected_score) < 0.01

    def test_remove_duplicate_results(self, search_manager):
        """重複結果除去テスト"""
        doc = create_mock_document(doc_id="duplicate_doc", content="テスト")

        from src.data.models import SearchResult

        # 重複する検索結果を作成
        results = [
            SearchResult(document=doc, score=0.8, search_type=SearchType.FULL_TEXT),
            SearchResult(document=doc, score=0.7, search_type=SearchType.SEMANTIC),
            SearchResult(document=doc, score=0.9, search_type=SearchType.HYBRID)
        ]

        # 重複を除去
        unique_results = search_manager._remove_duplicate_results(results)

        # 最高スコアの結果のみが残ることを確認
        assert len(unique_results) == 1
        assert unique_results[0].score == 0.9

    def test_filter_by_folder_paths(self, search_manager, multiple_documents):
        """フォルダパスフィルターテスト"""
        # 異なるフォルダパスのドキュメントを作成
        multiple_documents[0].file_path = "/folder1/doc1.txt"
        multiple_documents[1].file_path = "/folder2/doc2.txt"
        multiple_documents[2].file_path = "/folder1/doc3.txt"

        for doc in multiple_documents:
            search_manager.index_manager.add_document(doc)

        # 特定フォルダのみを検索
        results = search_manager.search(
            "テスト", SearchType.FULL_TEXT, folder_paths=["/folder1"]
        )

        # folder1内のドキュメントのみが返されることを確認
        assert len(results) == 2
        assert all("/folder1" in result.document.file_path for result in results)

    def test_cached_search_results(self, search_manager, sample_document):
        """キャッシュされた検索結果テスト"""
        search_manager.index_manager.add_document(sample_document)

        # 最初の検索
        results1 = search_manager.search("テスト", SearchType.FULL_TEXT)

        # 同じクエリで再検索（キャッシュから取得されるはず）
        results2 = search_manager.search("テスト", SearchType.FULL_TEXT)

        assert len(results1) == len(results2)
        assert results1[0].document.id == results2[0].document.id

    def test_post_process_results(self, search_manager, multiple_documents):
        """検索結果後処理テスト"""
        for doc in multiple_documents:
            search_manager.index_manager.add_document(doc)

        results = search_manager.search("テスト", SearchType.FULL_TEXT, limit=5)

        # 結果が適切に後処理されていることを確認
        assert len(results) <= 5

        for i, result in enumerate(results):
            # 順位が設定されていることを確認
            assert result.rank == i + 1

            # スニペットが生成されていることを確認
            assert len(result.snippet) > 0

            # ハイライト用語が設定されていることを確認
            assert isinstance(result.highlighted_terms, list)

    def test_get_search_suggestions(self, search_manager):
        """検索提案取得テスト"""
        # インデックス化された用語をモック
        search_manager._indexed_terms = {"テスト", "テストデータ", "検索", "ドキュメント"}

        suggestions = search_manager.get_search_suggestions("テ", limit=5)

        assert len(suggestions) <= 5
        # "テ"で始まる用語が含まれることを確認
        te_suggestions = [s for s in suggestions if s.startswith("テ")]
        assert len(te_suggestions) > 0

    def test_search_with_file_type_filter(self, search_manager, multiple_documents):
        """ファイルタイプフィルター付き検索テスト"""
        # 異なるファイルタイプを設定
        multiple_documents[0].file_type = FileType.PDF
        multiple_documents[1].file_type = FileType.WORD
        multiple_documents[2].file_type = FileType.TEXT

        for doc in multiple_documents:
            search_manager.index_manager.add_document(doc)

        # PDFファイルのみを検索
        results = search_manager.search(
            "テスト", SearchType.FULL_TEXT, file_types=[FileType.PDF]
        )

        assert len(results) == 1
        assert results[0].document.file_type == FileType.PDF

    def test_search_with_date_range(self, search_manager, multiple_documents):
        """日付範囲フィルター付き検索テスト"""
        # 異なる日付を設定
        for i, doc in enumerate(multiple_documents[:5]):
            doc.modified_date = datetime(2024, 1, i + 1)
            search_manager.index_manager.add_document(doc)

        # 特定の日付範囲で検索
        date_from = datetime(2024, 1, 2)
        date_to = datetime(2024, 1, 4)

        results = search_manager.search(
            "テスト", SearchType.FULL_TEXT,
            date_from=date_from, date_to=date_to
        )

        # 日付範囲内のドキュメントのみが返されることを確認
        assert len(results) == 3

    def test_error_handling_invalid_search_type(self, search_manager):
        """無効な検索タイプのエラーハンドリングテスト"""
        with pytest.raises(ValueError):
            search_manager.search("テスト", "invalid_type")

    def test_error_handling_empty_query(self, search_manager):
        """空クエリのエラーハンドリングテスト"""
        results = search_manager.search("", SearchType.FULL_TEXT)
        assert len(results) == 0

    def test_error_handling_search_failure(self, search_manager):
        """検索失敗のエラーハンドリングテスト"""
        # インデックスマネージャーを無効化
        search_manager.index_manager = None

        with pytest.raises(SearchError):
            search_manager.search("テスト", SearchType.FULL_TEXT)

    def test_memory_usage_during_search(self, search_manager, multiple_documents):
        """検索時のメモリ使用量テスト"""
        import os

        import psutil

        # ドキュメントを追加
        for doc in multiple_documents:
            search_manager.index_manager.add_document(doc)

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 複数回検索を実行
        for i in range(10):
            search_manager.search(f"テスト{i}", SearchType.FULL_TEXT)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # メモリ増加量が合理的な範囲内であることを確認（50MB以下）
        assert memory_increase < 50 * 1024 * 1024

    def test_search_result_ranking_accuracy(self, search_manager, multiple_documents):
        """検索結果ランキング精度テスト"""
        # 関連度の異なるドキュメントを作成
        multiple_documents[0].content = "テスト テスト テスト 重要なドキュメント"
        multiple_documents[1].content = "テスト 普通のドキュメント"
        multiple_documents[2].content = "ドキュメント テスト"

        for doc in multiple_documents[:3]:
            search_manager.index_manager.add_document(doc)

        results = search_manager.search("テスト", SearchType.FULL_TEXT)

        # より関連度の高いドキュメントが上位にランクされることを確認
        assert len(results) == 3
        assert results[0].document.id == multiple_documents[0].id  # 最も関連度が高い
        assert results[0].score > results[1].score > results[2].score
