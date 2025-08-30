"""
EmbeddingManagerのテストモジュール

セマンティック検索用の埋め込み管理機能の包括的なテストを提供します。
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.embedding_manager import EmbeddingManager
from src.data.models import Document, FileType
from src.utils.exceptions import EmbeddingError


class TestEmbeddingManager:
    """EmbeddingManagerのテストクラス"""

    @pytest.fixture
    def temp_embedding_dir(self):
        """一時埋め込みディレクトリを作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            embedding_dir = Path(temp_dir) / "test_embeddings"
            yield str(embedding_dir)

    @pytest.fixture
    def embedding_manager(self, temp_embedding_dir):
        """EmbeddingManagerインスタンスを作成"""
        with patch('sentence_transformers.SentenceTransformer'):
            return EmbeddingManager(temp_embedding_dir)

    @pytest.fixture
    def sample_document(self):
        """サンプルドキュメントを作成"""
        from datetime import datetime
        return Document(
            id="test_doc_1",
            file_path="/test/sample.txt",
            title="テストドキュメント",
            content="これはテスト用のドキュメントです。機械学習と自然言語処理について説明します。",
            file_type=FileType.TEXT,
            size=1024,
            created_date=datetime.now(),
            modified_date=datetime.now(),
            indexed_date=datetime.now(),
            content_hash="test_hash_123"
        )

    def test_initialization(self, embedding_manager):
        """初期化テスト"""
        assert embedding_manager is not None
        assert hasattr(embedding_manager, 'model')
        assert hasattr(embedding_manager, 'embeddings')

    @patch('sentence_transformers.SentenceTransformer')
    def test_model_loading(self, mock_transformer, temp_embedding_dir):
        """モデル読み込みテスト"""
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        manager = EmbeddingManager(temp_embedding_dir)
        
        assert manager.model == mock_model
        mock_transformer.assert_called_once()

    def test_add_document_embedding(self, embedding_manager, sample_document):
        """ドキュメント埋め込み追加テスト"""
        # モックの埋め込みベクトルを設定
        mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        embedding_manager.model.encode.return_value = mock_embedding
        
        embedding_manager.add_document_embedding(sample_document)
        
        assert sample_document.id in embedding_manager.embeddings
        assert embedding_manager.embeddings[sample_document.id] == mock_embedding

    def test_remove_document_embedding(self, embedding_manager, sample_document):
        """ドキュメント埋め込み削除テスト"""
        # 埋め込みを追加
        embedding_manager.embeddings[sample_document.id] = [0.1, 0.2, 0.3]
        
        embedding_manager.remove_document_embedding(sample_document.id)
        
        assert sample_document.id not in embedding_manager.embeddings

    def test_search_similar_basic(self, embedding_manager):
        """基本的な類似検索テスト"""
        # テストデータを設定
        embedding_manager.embeddings = {
            "doc1": [0.1, 0.2, 0.3],
            "doc2": [0.2, 0.3, 0.4],
            "doc3": [0.9, 0.8, 0.7]
        }
        
        # クエリの埋め込みをモック
        query_embedding = [0.15, 0.25, 0.35]
        embedding_manager.model.encode.return_value = query_embedding
        
        # 類似度計算をモック
        with patch('numpy.dot') as mock_dot, \
             patch('numpy.linalg.norm') as mock_norm:
            
            # 類似度スコアを設定
            mock_dot.side_effect = [0.8, 0.6, 0.2]  # doc1, doc2, doc3との内積
            mock_norm.return_value = 1.0  # 正規化
            
            results = embedding_manager.search_similar("テストクエリ", limit=2)
            
            assert len(results) <= 2
            # 結果が類似度順でソートされていることを確認
            if len(results) > 1:
                assert results[0][1] >= results[1][1]

    def test_search_similar_with_min_similarity(self, embedding_manager):
        """最小類似度フィルター付き類似検索テスト"""
        embedding_manager.embeddings = {
            "doc1": [0.1, 0.2, 0.3],
            "doc2": [0.2, 0.3, 0.4]
        }
        
        query_embedding = [0.15, 0.25, 0.35]
        embedding_manager.model.encode.return_value = query_embedding
        
        with patch('numpy.dot') as mock_dot, \
             patch('numpy.linalg.norm') as mock_norm:
            
            # 低い類似度スコアを設定
            mock_dot.side_effect = [0.3, 0.1]
            mock_norm.return_value = 1.0
            
            results = embedding_manager.search_similar(
                "テストクエリ", 
                min_similarity=0.5  # 高い閾値
            )
            
            # 閾値を下回る結果は除外される
            assert len(results) == 0

    def test_save_embeddings(self, embedding_manager):
        """埋め込み保存テスト"""
        # テストデータを設定
        embedding_manager.embeddings = {
            "doc1": [0.1, 0.2, 0.3],
            "doc2": [0.2, 0.3, 0.4]
        }
        
        embedding_manager.save_embeddings()
        
        # ファイルが作成されることを確認
        embedding_file = Path(embedding_manager.embedding_path) / "embeddings.pkl"
        assert embedding_file.exists()

    def test_load_embeddings(self, embedding_manager):
        """埋め込み読み込みテスト"""
        # テストデータを保存
        test_embeddings = {
            "doc1": [0.1, 0.2, 0.3],
            "doc2": [0.2, 0.3, 0.4]
        }
        
        embedding_manager.embeddings = test_embeddings
        embedding_manager.save_embeddings()
        
        # 埋め込みをクリアして読み込み
        embedding_manager.embeddings = {}
        embedding_manager.load_embeddings()
        
        assert embedding_manager.embeddings == test_embeddings

    def test_clear_embeddings(self, embedding_manager):
        """埋め込みクリアテスト"""
        # テストデータを設定
        embedding_manager.embeddings = {
            "doc1": [0.1, 0.2, 0.3],
            "doc2": [0.2, 0.3, 0.4]
        }
        
        embedding_manager.clear_embeddings()
        
        assert len(embedding_manager.embeddings) == 0

    def test_get_embedding_stats(self, embedding_manager):
        """埋め込み統計情報取得テスト"""
        # テストデータを設定
        embedding_manager.embeddings = {
            "doc1": [0.1, 0.2, 0.3],
            "doc2": [0.2, 0.3, 0.4]
        }
        
        stats = embedding_manager.get_embedding_stats()
        
        assert isinstance(stats, dict)
        assert stats["total_embeddings"] == 2
        assert "embedding_dimension" in stats
        assert "memory_usage_mb" in stats

    def test_update_document_embedding(self, embedding_manager, sample_document):
        """ドキュメント埋め込み更新テスト"""
        # 最初の埋め込みを追加
        old_embedding = [0.1, 0.2, 0.3]
        embedding_manager.embeddings[sample_document.id] = old_embedding
        
        # 新しい埋め込みを設定
        new_embedding = [0.4, 0.5, 0.6]
        embedding_manager.model.encode.return_value = new_embedding
        
        embedding_manager.update_document_embedding(sample_document)
        
        assert embedding_manager.embeddings[sample_document.id] == new_embedding
        assert embedding_manager.embeddings[sample_document.id] != old_embedding

    def test_batch_add_embeddings(self, embedding_manager):
        """バッチ埋め込み追加テスト"""
        from datetime import datetime
        
        # 複数のドキュメントを作成
        documents = []
        for i in range(3):
            doc = Document(
                id=f"doc_{i}",
                file_path=f"/test/file_{i}.txt",
                title=f"ドキュメント{i}",
                content=f"これは{i}番目のテストドキュメントです。",
                file_type=FileType.TEXT,
                size=1024,
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                content_hash=f"hash_{i}"
            )
            documents.append(doc)
        
        # バッチエンコーディングをモック
        batch_embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        embedding_manager.model.encode.return_value = batch_embeddings
        
        embedding_manager.batch_add_embeddings(documents)
        
        assert len(embedding_manager.embeddings) == 3
        for i, doc in enumerate(documents):
            assert doc.id in embedding_manager.embeddings

    def test_error_handling_model_loading_failure(self, temp_embedding_dir):
        """モデル読み込み失敗のエラーハンドリングテスト"""
        with patch('sentence_transformers.SentenceTransformer', side_effect=Exception("モデル読み込みエラー")):
            with pytest.raises(EmbeddingError):
                EmbeddingManager(temp_embedding_dir)

    def test_error_handling_encoding_failure(self, embedding_manager, sample_document):
        """エンコーディング失敗のエラーハンドリングテスト"""
        # エンコーディングで例外を発生させる
        embedding_manager.model.encode.side_effect = Exception("エンコーディングエラー")
        
        with pytest.raises(EmbeddingError):
            embedding_manager.add_document_embedding(sample_document)

    def test_error_handling_save_failure(self, embedding_manager):
        """保存失敗のエラーハンドリングテスト"""
        # 無効なパスを設定
        embedding_manager.embedding_path = "/invalid/path"
        
        with pytest.raises(EmbeddingError):
            embedding_manager.save_embeddings()

    def test_document_exists_in_embeddings(self, embedding_manager):
        """埋め込み内ドキュメント存在確認テスト"""
        doc_id = "test_doc_1"
        
        assert not embedding_manager.document_exists(doc_id)
        
        embedding_manager.embeddings[doc_id] = [0.1, 0.2, 0.3]
        assert embedding_manager.document_exists(doc_id)

    def test_get_document_embedding(self, embedding_manager):
        """ドキュメント埋め込み取得テスト"""
        doc_id = "test_doc_1"
        test_embedding = [0.1, 0.2, 0.3]
        
        embedding_manager.embeddings[doc_id] = test_embedding
        
        retrieved_embedding = embedding_manager.get_document_embedding(doc_id)
        assert retrieved_embedding == test_embedding
        
        # 存在しないドキュメント
        assert embedding_manager.get_document_embedding("nonexistent") is None

    def test_similarity_calculation(self, embedding_manager):
        """類似度計算テスト"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        vec3 = [1.0, 0.0, 0.0]  # vec1と同じ
        
        # 直交ベクトルの類似度は0
        similarity_orthogonal = embedding_manager._calculate_similarity(vec1, vec2)
        assert abs(similarity_orthogonal) < 0.001
        
        # 同じベクトルの類似度は1
        similarity_same = embedding_manager._calculate_similarity(vec1, vec3)
        assert abs(similarity_same - 1.0) < 0.001