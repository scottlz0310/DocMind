"""
SearchManagerのテストモジュール

ハイブリッド検索機能の包括的なテストを提供します。
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.core.search_manager import SearchManager, SearchWeights
from src.data.models import Document, FileType, SearchQuery, SearchResult, SearchType
from src.utils.exceptions import SearchError


class TestSearchManager:
    """SearchManagerのテストクラス"""

    @pytest.fixture
    def mock_index_manager(self):
        """モックIndexManagerを作成"""
        mock_manager = Mock()
        mock_manager.search_text.return_value = []
        mock_manager.get_document_count.return_value = 0
        mock_manager._index = Mock()
        return mock_manager

    @pytest.fixture
    def mock_embedding_manager(self):
        """モックEmbeddingManagerを作成"""
        mock_manager = Mock()
        mock_manager.search_similar.return_value = []
        mock_manager.embeddings = {}
        return mock_manager

    @pytest.fixture
    def search_manager(self, mock_index_manager, mock_embedding_manager):
        """SearchManagerインスタンスを作成"""
        return SearchManager(mock_index_manager, mock_embedding_manager)

    @pytest.fixture
    def sample_document(self):
        """サンプルドキュメントを作成"""
        return Document(
            id="test_doc_1",
            file_path="/test/sample.txt",
            title="テストドキュメント",
            content="これはテスト用のドキュメントです。検索機能をテストします。",
            file_type=FileType.TEXT,
            size=1024,
            created_date=datetime.now(),
            modified_date=datetime.now(),
            indexed_date=datetime.now(),
            content_hash="test_hash_123"
        )

    @pytest.fixture
    def sample_search_result(self, sample_document):
        """サンプル検索結果を作成"""
        return SearchResult(
            document=sample_document,
            score=0.85,
            search_type=SearchType.FULL_TEXT,
            snippet="これはテスト用のドキュメント...",
            highlighted_terms=["テスト", "ドキュメント"],
            relevance_explanation="全文検索スコア: 0.85",
            rank=1
        )

    @pytest.fixture
    def sample_search_query(self):
        """サンプル検索クエリを作成"""
        return SearchQuery(
            query_text="テスト",
            search_type=SearchType.FULL_TEXT,
            limit=10
        )

    def test_initialization(self, search_manager):
        """初期化テスト"""
        assert search_manager is not None
        assert search_manager.index_manager is not None
        assert search_manager.embedding_manager is not None
        assert isinstance(search_manager.default_weights, SearchWeights)

    def test_search_weights_initialization(self):
        """SearchWeights初期化テスト"""
        weights = SearchWeights(full_text=0.7, semantic=0.3)
        
        assert weights.full_text == 0.7
        assert weights.semantic == 0.3

    def test_search_weights_normalization(self):
        """SearchWeights正規化テスト"""
        weights = SearchWeights(full_text=2.0, semantic=1.0)
        
        # 合計が1.0になるように正規化されることを確認
        assert abs(weights.full_text + weights.semantic - 1.0) < 0.001

    @patch('src.utils.cache_manager.get_global_cache_manager')
    def test_full_text_search(self, mock_cache_manager, search_manager, sample_search_query, sample_search_result):
        """全文検索テスト"""
        # キャッシュマネージャーのモック設定
        mock_cache = Mock()
        mock_cache.search_cache.get_search_results.return_value = None
        mock_cache_manager.return_value = mock_cache
        search_manager._cache_manager = mock_cache
        
        # IndexManagerのモック設定
        search_manager.index_manager.search_text.return_value = [sample_search_result]
        
        results = search_manager._full_text_search(sample_search_query)
        
        assert len(results) == 1
        assert results[0].search_type == SearchType.FULL_TEXT
        search_manager.index_manager.search_text.assert_called_once()

    @patch('src.utils.cache_manager.get_global_cache_manager')
    def test_semantic_search(self, mock_cache_manager, search_manager, sample_search_query, sample_document):
        """セマンティック検索テスト"""
        # キャッシュマネージャーのモック設定
        mock_cache = Mock()
        mock_cache.search_cache.get_search_results.return_value = None
        mock_cache_manager.return_value = mock_cache
        search_manager._cache_manager = mock_cache
        
        # EmbeddingManagerのモック設定
        search_manager.embedding_manager.search_similar.return_value = [("test_doc_1", 0.8)]
        
        # _get_document_by_idのモック
        search_manager._get_document_by_id = Mock(return_value=sample_document)
        
        sample_search_query.search_type = SearchType.SEMANTIC
        results = search_manager._semantic_search(sample_search_query)
        
        assert len(results) == 1
        assert results[0].search_type == SearchType.SEMANTIC
        search_manager.embedding_manager.search_similar.assert_called_once()

    @patch('src.utils.cache_manager.get_global_cache_manager')
    def test_hybrid_search(self, mock_cache_manager, search_manager, sample_search_query, sample_search_result, sample_document):
        """ハイブリッド検索テスト"""
        # キャッシュマネージャーのモック設定
        mock_cache = Mock()
        mock_cache.search_cache.get_search_results.return_value = None
        mock_cache_manager.return_value = mock_cache
        search_manager._cache_manager = mock_cache
        
        # 全文検索とセマンティック検索の結果をモック
        search_manager._full_text_search = Mock(return_value=[sample_search_result])
        search_manager._semantic_search = Mock(return_value=[sample_search_result])
        
        sample_search_query.search_type = SearchType.HYBRID
        results = search_manager._hybrid_search(sample_search_query)
        
        assert len(results) >= 1
        # ハイブリッド検索では両方の検索が呼ばれることを確認
        search_manager._full_text_search.assert_called_once()
        search_manager._semantic_search.assert_called_once()

    def test_merge_search_results(self, search_manager, sample_search_result):
        """検索結果マージテスト"""
        # 異なるスコアの結果を作成
        result1 = sample_search_result
        result1.score = 0.8
        
        result2 = SearchResult(
            document=sample_search_result.document,
            score=0.6,
            search_type=SearchType.SEMANTIC,
            snippet="セマンティック検索結果",
            highlighted_terms=["検索"],
            relevance_explanation="セマンティック類似度: 0.6",
            rank=1
        )
        
        weights = SearchWeights(full_text=0.6, semantic=0.4)
        merged = search_manager._merge_search_results([result1], [result2], weights)
        
        assert len(merged) == 1
        # 統合スコアが計算されていることを確認
        expected_score = 0.8 * 0.6 + 0.6 * 0.4
        assert abs(merged[0].score - expected_score) < 0.001

    def test_generate_snippet(self, search_manager):
        """スニペット生成テスト"""
        content = "これは非常に長いテキストコンテンツです。" * 20
        query = "テスト"
        
        snippet = search_manager._generate_snippet(content, query)
        
        assert len(snippet) <= search_manager.snippet_max_length + 3  # "..."を考慮

    def test_extract_query_terms(self, search_manager):
        """クエリ用語抽出テスト"""
        query = "テスト search 検索"
        
        terms = search_manager._extract_query_terms(query)
        
        assert "テスト" in terms
        assert "search" in terms
        assert "検索" in terms

    def test_remove_duplicate_results(self, search_manager, sample_search_result):
        """重複結果除去テスト"""
        # 同じドキュメントIDの結果を複数作成
        result1 = sample_search_result
        result2 = SearchResult(
            document=sample_search_result.document,  # 同じドキュメント
            score=0.7,
            search_type=SearchType.SEMANTIC,
            snippet="別のスニペット",
            highlighted_terms=["別の", "用語"],
            relevance_explanation="別の説明",
            rank=2
        )
        
        unique_results = search_manager._remove_duplicate_results([result1, result2])
        
        assert len(unique_results) == 1

    def test_filter_by_folder_paths(self, search_manager, sample_search_result):
        """フォルダパスフィルタリングテスト"""
        # 異なるパスのドキュメントを作成
        doc1 = sample_search_result.document
        doc1.file_path = "/folder1/file1.txt"
        
        doc2 = Document(
            id="test_doc_2",
            file_path="/folder2/file2.txt",
            title="別のドキュメント",
            content="別のコンテンツ",
            file_type=FileType.TEXT,
            size=1024,
            created_date=datetime.now(),
            modified_date=datetime.now(),
            indexed_date=datetime.now(),
            content_hash="test_hash_456"
        )
        
        result2 = SearchResult(
            document=doc2,
            score=0.7,
            search_type=SearchType.FULL_TEXT,
            snippet="別のスニペット",
            highlighted_terms=["別の"],
            relevance_explanation="別の説明",
            rank=2
        )
        
        results = [sample_search_result, result2]
        filtered = search_manager._filter_by_folder_paths(results, ["/folder1"])
        
        assert len(filtered) == 1
        assert filtered[0].document.file_path.startswith("/folder1")

    def test_get_search_suggestions(self, search_manager):
        """検索提案取得テスト"""
        # インデックス化された用語をモック
        search_manager._indexed_terms = {"テスト", "テストデータ", "検索", "ドキュメント"}
        
        suggestions = search_manager.get_search_suggestions("テ", limit=5)
        
        assert len(suggestions) <= 5
        # "テ"で始まる用語が含まれることを確認
        te_suggestions = [s for s in suggestions if s.startswith("テ")]
        assert len(te_suggestions) > 0

    def test_clear_suggestion_cache(self, search_manager):
        """検索提案キャッシュクリアテスト"""
        # キャッシュにデータを追加
        search_manager._suggestion_cache["test"] = ["suggestion1", "suggestion2"]
        search_manager._indexed_terms = {"term1", "term2"}
        
        search_manager.clear_suggestion_cache()
        
        assert len(search_manager._suggestion_cache) == 0
        assert len(search_manager._indexed_terms) == 0

    def test_get_search_stats(self, search_manager):
        """検索統計情報取得テスト"""
        stats = search_manager.get_search_stats()
        
        assert isinstance(stats, dict)
        assert "indexed_documents" in stats
        assert "cached_embeddings" in stats
        assert "default_weights" in stats

    def test_update_search_settings(self, search_manager):
        """検索設定更新テスト"""
        search_manager.update_search_settings(
            full_text_weight=0.8,
            semantic_weight=0.2,
            min_semantic_similarity=0.2,
            snippet_max_length=300
        )
        
        assert search_manager.default_weights.full_text == 0.8
        assert search_manager.default_weights.semantic == 0.2
        assert search_manager.min_semantic_similarity == 0.2
        assert search_manager.snippet_max_length == 300

    def test_error_handling_search_failure(self, search_manager, sample_search_query):
        """検索失敗のエラーハンドリングテスト"""
        # IndexManagerで例外を発生させる
        search_manager.index_manager.search_text.side_effect = Exception("検索エラー")
        
        with pytest.raises(SearchError):
            search_manager._full_text_search(sample_search_query)

    @patch('src.utils.cache_manager.get_global_cache_manager')
    def test_cached_search_results(self, mock_cache_manager, search_manager, sample_search_query, sample_search_result):
        """キャッシュされた検索結果テスト"""
        # キャッシュから結果を返すモック
        mock_cache = Mock()
        mock_cache.search_cache.get_search_results.return_value = [sample_search_result]
        mock_cache_manager.return_value = mock_cache
        search_manager._cache_manager = mock_cache
        
        results = search_manager.search(sample_search_query)
        
        assert len(results) == 1
        assert results[0] == sample_search_result
        # キャッシュから取得されたため、実際の検索は呼ばれない
        search_manager.index_manager.search_text.assert_not_called()

    def test_post_process_results(self, search_manager, sample_search_result, sample_search_query):
        """検索結果後処理テスト"""
        results = [sample_search_result]
        
        processed = search_manager._post_process_results(results, sample_search_query)
        
        assert len(processed) == 1
        assert processed[0].rank == 1