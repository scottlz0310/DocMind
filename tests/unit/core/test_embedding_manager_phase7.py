"""
Phase7 EmbeddingManagerの強化テストモジュール

セマンティック検索機能の包括的なテストを提供します。
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from src.core.embedding_manager_extended import EmbeddingManagerExtended
from src.utils.exceptions import EmbeddingError
from tests.fixtures.mock_models import (
    create_mock_documents,
)


class TestEmbeddingManagerPhase7:
    """Phase7 EmbeddingManagerの強化テストクラス"""

    @pytest.fixture
    def temp_embedding_dir(self):
        """一時埋め込みディレクトリを作成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            embedding_dir = Path(temp_dir) / "test_embeddings"
            embedding_dir.mkdir(exist_ok=True)
            yield str(embedding_dir)

    @pytest.fixture
    def embedding_manager(self, temp_embedding_dir):
        """EmbeddingManagerインスタンスを作成"""
        embeddings_path = str(Path(temp_embedding_dir) / "embeddings.pkl")
        return EmbeddingManagerExtended(embeddings_path=embeddings_path)

    @pytest.fixture
    def mock_model(self):
        """モックSentenceTransformerを作成"""
        mock = Mock()
        mock.encode.return_value = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        mock.get_sentence_embedding_dimension.return_value = 5
        return mock

    def test_initialization(self, embedding_manager):
        """初期化テスト"""
        assert embedding_manager is not None
        assert embedding_manager.embeddings == {}
        assert embedding_manager.model is None

    @patch('src.core.embedding_manager.SentenceTransformer')
    def test_model_loading(self, mock_transformer, temp_embedding_dir):
        """モデル読み込みテスト"""
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        embeddings_path = str(Path(temp_embedding_dir) / "embeddings.pkl")
        manager = EmbeddingManagerExtended(embeddings_path=embeddings_path)
        manager.load_model()

        # モデルが正しく設定されていることを確認
        assert manager.model is not None
        mock_transformer.assert_called_once_with("all-MiniLM-L6-v2")

    def test_add_document_embedding(self, embedding_manager, mock_model):
        """ドキュメント埋め込み追加テスト"""
        embedding_manager.model = mock_model

        doc_id = "test_doc_1"
        text = "これはテスト用のドキュメントです。"

        embedding_manager.add_document_embedding(doc_id, text)

        assert doc_id in embedding_manager.embeddings
        assert embedding_manager.embeddings[doc_id].doc_id == doc_id
        mock_model.encode.assert_called_once_with(text, convert_to_numpy=True)

    def test_remove_document_embedding(self, embedding_manager, mock_model):
        """ドキュメント埋め込み削除テスト"""
        embedding_manager.model = mock_model

        doc_id = "test_doc_1"
        text = "テストドキュメント"

        # 埋め込みを追加
        embedding_manager.add_document_embedding(doc_id, text)
        assert doc_id in embedding_manager.embeddings

        # 埋め込みを削除
        embedding_manager.remove_document_embedding(doc_id)
        assert doc_id not in embedding_manager.embeddings

    def test_update_document_embedding(self, embedding_manager, mock_model):
        """ドキュメント埋め込み更新テスト"""
        embedding_manager.model = mock_model

        doc_id = "test_doc_1"
        original_text = "元のテキスト"
        updated_text = "更新されたテキスト"

        # 最初の埋め込みを追加
        embedding_manager.add_document_embedding(doc_id, original_text)

        # 埋め込みを更新
        embedding_manager.update_document_embedding(doc_id, updated_text)

        assert doc_id in embedding_manager.embeddings
        # encode が2回呼ばれることを確認（追加時と更新時）
        assert mock_model.encode.call_count == 2

    def test_search_similar_basic(self, embedding_manager, mock_model):
        """基本的な類似検索テスト"""
        embedding_manager.model = mock_model

        # テストデータを設定
        embedding_manager.embeddings = {
            "doc1": Mock(embedding=np.array([0.1, 0.2, 0.3])),
            "doc2": Mock(embedding=np.array([0.2, 0.3, 0.4])),
            "doc3": Mock(embedding=np.array([0.9, 0.8, 0.7]))
        }

        # クエリの埋め込みをモック
        query_embedding = np.array([0.15, 0.25, 0.35])
        mock_model.encode.return_value = query_embedding

        results = embedding_manager.search_similar("テストクエリ", limit=3)

        assert len(results) <= 3
        assert all(isinstance(result, tuple) for result in results)
        assert all(len(result) == 2 for result in results)  # (doc_id, score)

        # スコア順でソートされていることを確認
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i][1] >= results[i + 1][1]

    def test_search_similar_with_min_similarity(self, embedding_manager, mock_model):
        """最小類似度フィルター付き類似検索テスト"""
        embedding_manager.model = mock_model

        embedding_manager.embeddings = {
            "doc1": Mock(embedding=np.array([0.1, 0.2, 0.3])),
            "doc2": Mock(embedding=np.array([0.2, 0.3, 0.4]))
        }

        query_embedding = np.array([0.15, 0.25, 0.35])
        mock_model.encode.return_value = query_embedding

        # 高い最小類似度を設定
        results = embedding_manager.search_similar("テストクエリ", min_similarity=0.9)

        # 高い類似度を満たすドキュメントがない場合は空の結果
        assert isinstance(results, list)

    def test_save_embeddings(self, embedding_manager, mock_model):
        """埋め込み保存テスト"""
        embedding_manager.model = mock_model

        # テストデータを設定
        doc_id = "test_doc"
        text = "テストテキスト"
        embedding_manager.add_document_embedding(doc_id, text)

        embedding_manager.save_embeddings()

        # ファイルが作成されることを確認
        embedding_file = Path(embedding_manager.embeddings_path)
        assert embedding_file.exists()

    def test_load_embeddings(self, embedding_manager, mock_model):
        """埋め込み読み込みテスト"""
        embedding_manager.model = mock_model

        # テストデータを保存
        doc_id = "test_doc"
        text = "テストテキスト"
        embedding_manager.add_document_embedding(doc_id, text)
        embedding_manager.save_embeddings()

        # 新しいマネージャーインスタンスで読み込み
        new_manager = EmbeddingManagerExtended(embeddings_path=embedding_manager.embeddings_path)

        assert doc_id in new_manager.embeddings

    def test_clear_embeddings(self, embedding_manager, mock_model):
        """埋め込みクリアテスト"""
        embedding_manager.model = mock_model

        # テストデータを設定
        doc_id = "test_doc"
        text = "テストテキスト"
        embedding_manager.add_document_embedding(doc_id, text)

        assert len(embedding_manager.embeddings) == 1

        embedding_manager.clear_embeddings()

        assert len(embedding_manager.embeddings) == 0

    def test_get_embedding_stats(self, embedding_manager, mock_model):
        """埋め込み統計情報取得テスト"""
        embedding_manager.model = mock_model

        # テストデータを設定
        doc_id = "test_doc"
        text = "テストテキスト"
        embedding_manager.add_document_embedding(doc_id, text)

        stats = embedding_manager.get_embedding_stats()

        assert isinstance(stats, dict)
        assert "total_embeddings" in stats
        assert stats["total_embeddings"] == 1
        assert "model_name" in stats
        assert "model_loaded" in stats

    def test_batch_add_embeddings(self, embedding_manager, mock_model):
        """バッチ埋め込み追加テスト"""
        embedding_manager.model = mock_model

        # 複数のドキュメントを作成
        documents = create_mock_documents(3)

        embedding_manager.batch_add_embeddings(documents)

        assert len(embedding_manager.embeddings) == 3
        for doc in documents:
            assert doc.id in embedding_manager.embeddings

    def test_document_exists_in_embeddings(self, embedding_manager, mock_model):
        """埋め込み内ドキュメント存在確認テスト"""
        embedding_manager.model = mock_model

        doc_id = "test_doc_1"

        assert not embedding_manager.document_exists(doc_id)

        embedding_manager.add_document_embedding(doc_id, "テストテキスト")
        assert embedding_manager.document_exists(doc_id)

    def test_get_document_embedding(self, embedding_manager, mock_model):
        """ドキュメント埋め込み取得テスト"""
        embedding_manager.model = mock_model

        doc_id = "test_doc_1"
        text = "テストテキスト"

        # 埋め込みが存在しない場合
        assert embedding_manager.get_document_embedding(doc_id) is None

        # 埋め込みを追加
        embedding_manager.add_document_embedding(doc_id, text)

        retrieved_embedding = embedding_manager.get_document_embedding(doc_id)
        assert retrieved_embedding is not None
        assert isinstance(retrieved_embedding, np.ndarray)

    def test_similarity_calculation(self, embedding_manager):
        """類似度計算テスト"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        vec3 = [1.0, 0.0, 0.0]  # vec1と同じ

        # 直交ベクトルの類似度は0
        similarity_orthogonal = embedding_manager._calculate_similarity(vec1, vec2)
        assert abs(similarity_orthogonal - 0.0) < 0.01

        # 同じベクトルの類似度は1
        similarity_same = embedding_manager._calculate_similarity(vec1, vec3)
        assert abs(similarity_same - 1.0) < 0.01

    @patch('src.core.embedding_manager.SentenceTransformer')
    def test_error_handling_model_loading_failure(self, mock_transformer, temp_embedding_dir):
        """モデル読み込み失敗のエラーハンドリングテスト"""
        mock_transformer.side_effect = Exception("モデル読み込みエラー")
        
        embeddings_path = str(Path(temp_embedding_dir) / "embeddings.pkl")
        manager = EmbeddingManagerExtended(embeddings_path=embeddings_path)

        with pytest.raises(EmbeddingError):
            manager.load_model()

    def test_error_handling_save_failure(self, embedding_manager):
        """保存失敗のエラーハンドリングテスト"""
        # 無効なパスを設定
        embedding_manager.embeddings_path = "/invalid/path/embeddings.pkl"

        with pytest.raises(EmbeddingError):
            embedding_manager.save_embeddings()

    def test_error_handling_encoding_failure(self, embedding_manager):
        """エンコード失敗のエラーハンドリングテスト"""
        # モデルのencodeメソッドが例外を発生させるようにモック
        mock_model = Mock()
        mock_model.encode.side_effect = Exception("エンコードエラー")
        embedding_manager.model = mock_model

        with pytest.raises(EmbeddingError):
            embedding_manager.add_document_embedding("test_doc", "テストテキスト")

    def test_empty_text_handling(self, embedding_manager, mock_model):
        """空テキストのハンドリングテスト"""
        mock_model.get_sentence_embedding_dimension.return_value = 5
        embedding_manager.model = mock_model

        # 空テキストの埋め込み生成
        embedding = embedding_manager.generate_embedding("")

        # ゼロベクトルが返されることを確認
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 5
        assert np.all(embedding == 0)

    def test_large_scale_embedding_generation(self, embedding_manager, mock_model):
        """大規模埋め込み生成テスト"""
        import time

        embedding_manager.model = mock_model

        # 大量のドキュメントを作成
        documents = create_mock_documents(100)

        start_time = time.time()
        embedding_manager.batch_add_embeddings(documents)
        end_time = time.time()

        # パフォーマンス検証（30秒以内）
        assert (end_time - start_time) < 30
        assert len(embedding_manager.embeddings) == 100

    def test_memory_usage_monitoring(self, embedding_manager, mock_model):
        """メモリ使用量監視テスト"""
        import os

        import psutil

        embedding_manager.model = mock_model

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 大量の埋め込みを生成
        documents = create_mock_documents(50)
        embedding_manager.batch_add_embeddings(documents)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # メモリ増加量が合理的な範囲内であることを確認（100MB以下）
        assert memory_increase < 100 * 1024 * 1024

    def test_concurrent_embedding_operations(self, embedding_manager, mock_model):
        """並行埋め込み操作テスト"""
        import threading
        import time

        embedding_manager.model = mock_model

        def add_embeddings(doc_ids):
            for doc_id in doc_ids:
                embedding_manager.add_document_embedding(doc_id, f"テキスト{doc_id}")
                time.sleep(0.01)  # 少し待機

        # 複数スレッドで同時に埋め込みを追加
        threads = []
        doc_id_chunks = [["doc1", "doc2"], ["doc3", "doc4"], ["doc5", "doc6"]]

        for chunk in doc_id_chunks:
            thread = threading.Thread(target=add_embeddings, args=(chunk,))
            threads.append(thread)
            thread.start()

        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()

        # 全埋め込みが正常に追加されたことを確認
        assert len(embedding_manager.embeddings) == 6

    def test_embedding_persistence_across_sessions(self, temp_embedding_dir, mock_model):
        """セッション間での埋め込み永続化テスト"""
        embeddings_path = str(Path(temp_embedding_dir) / "embeddings.pkl")

        # 最初のセッション
        manager1 = EmbeddingManagerExtended(embeddings_path=embeddings_path)
        manager1.model = mock_model

        doc_id = "persistent_doc"
        text = "永続化テストドキュメント"
        manager1.add_document_embedding(doc_id, text)
        manager1.save_embeddings()

        # 2番目のセッション（新しいインスタンス）
        manager2 = EmbeddingManagerExtended(embeddings_path=embeddings_path)

        # 埋め込みが永続化されていることを確認
        assert doc_id in manager2.embeddings
        assert manager2.document_exists(doc_id)
