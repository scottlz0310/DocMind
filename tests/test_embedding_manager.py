"""
EmbeddingManagerクラスのユニットテスト

このモジュールは、セマンティック検索機能を提供するEmbeddingManagerクラスの
すべての機能をテストします。
"""

import os
import pickle
import shutil
import tempfile
from unittest.mock import Mock, patch

import numpy as np
import pytest

from src.core.embedding_manager import DocumentEmbedding, EmbeddingManager
from src.data.models import Document
from src.utils.exceptions import EmbeddingError


class TestEmbeddingManager:
    """EmbeddingManagerクラスのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.embeddings_path = os.path.join(self.temp_dir, "test_embeddings.pkl")

        # テスト用のEmbeddingManagerインスタンスを作成
        self.embedding_manager = EmbeddingManager(
            model_name="all-MiniLM-L6-v2",
            embeddings_path=self.embeddings_path
        )

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        # 一時ディレクトリを削除
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('src.core.embedding_manager.SentenceTransformer')
    def test_load_model_success(self, mock_sentence_transformer):
        """モデルの正常な読み込みをテスト"""
        # モックの設定
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        # モデルを読み込み
        self.embedding_manager.load_model()

        # 検証
        assert self.embedding_manager.model == mock_model
        mock_sentence_transformer.assert_called_once_with("all-MiniLM-L6-v2")

    @patch('src.core.embedding_manager.SentenceTransformer')
    def test_load_model_failure(self, mock_sentence_transformer):
        """モデル読み込み失敗時の例外処理をテスト"""
        # モックの設定（例外を発生させる）
        mock_sentence_transformer.side_effect = Exception("モデル読み込みエラー")

        # 例外が発生することを確認
        with pytest.raises(EmbeddingError) as exc_info:
            self.embedding_manager.load_model()

        assert "モデルの読み込みに失敗しました" in str(exc_info.value)

    @patch('src.core.embedding_manager.SentenceTransformer')
    def test_generate_embedding_success(self, mock_sentence_transformer):
        """埋め込み生成の正常動作をテスト"""
        # モックの設定
        mock_model = Mock()
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        mock_model.encode.return_value = mock_embedding
        mock_model.get_sentence_embedding_dimension.return_value = 4
        mock_sentence_transformer.return_value = mock_model

        # 埋め込みを生成
        result = self.embedding_manager.generate_embedding("テストテキスト")

        # 検証
        np.testing.assert_array_equal(result, mock_embedding)
        mock_model.encode.assert_called_once_with("テストテキスト", convert_to_numpy=True)

    @patch('src.core.embedding_manager.SentenceTransformer')
    def test_generate_embedding_empty_text(self, mock_sentence_transformer):
        """空のテキストに対する埋め込み生成をテスト"""
        # モックの設定
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 4
        mock_sentence_transformer.return_value = mock_model

        # 空のテキストで埋め込みを生成
        result = self.embedding_manager.generate_embedding("")

        # ゼロベクトルが返されることを確認
        expected = np.zeros(4)
        np.testing.assert_array_equal(result, expected)

    @patch('src.core.embedding_manager.SentenceTransformer')
    def test_add_document_embedding(self, mock_sentence_transformer):
        """ドキュメント埋め込みの追加をテスト"""
        # モックの設定
        mock_model = Mock()
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        mock_model.encode.return_value = mock_embedding
        mock_sentence_transformer.return_value = mock_model

        # ドキュメント埋め込みを追加
        doc_id = "test_doc_1"
        text = "これはテストドキュメントです"

        self.embedding_manager.add_document_embedding(doc_id, text)

        # 検証
        assert doc_id in self.embedding_manager.embeddings
        doc_embedding = self.embedding_manager.embeddings[doc_id]
        assert doc_embedding.doc_id == doc_id
        np.testing.assert_array_equal(doc_embedding.embedding, mock_embedding)
        assert doc_embedding.text_hash == str(hash(text))

    @patch('src.core.embedding_manager.SentenceTransformer')
    def test_add_document_embedding_duplicate_skip(self, mock_sentence_transformer):
        """同じテキストの重複埋め込み追加をスキップすることをテスト"""
        # モックの設定
        mock_model = Mock()
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        mock_model.encode.return_value = mock_embedding
        mock_sentence_transformer.return_value = mock_model

        doc_id = "test_doc_1"
        text = "これはテストドキュメントです"

        # 最初の追加
        self.embedding_manager.add_document_embedding(doc_id, text)

        # 同じテキストで再度追加
        self.embedding_manager.add_document_embedding(doc_id, text)

        # encodeが一度だけ呼ばれることを確認
        assert mock_model.encode.call_count == 1

    def test_remove_document_embedding(self):
        """ドキュメント埋め込みの削除をテスト"""
        # テスト用の埋め込みを追加
        doc_id = "test_doc_1"
        embedding = DocumentEmbedding(
            doc_id=doc_id,
            embedding=np.array([0.1, 0.2, 0.3]),
            text_hash="test_hash",
            created_at=1234567890.0
        )
        self.embedding_manager.embeddings[doc_id] = embedding

        # 削除を実行
        self.embedding_manager.remove_document_embedding(doc_id)

        # 削除されたことを確認
        assert doc_id not in self.embedding_manager.embeddings

    @patch('src.core.embedding_manager.SentenceTransformer')
    @patch('src.core.embedding_manager.cosine_similarity')
    def test_search_similar(self, mock_cosine_similarity, mock_sentence_transformer):
        """類似度検索をテスト"""
        # モックの設定
        mock_model = Mock()
        query_embedding = np.array([0.5, 0.5, 0.5, 0.5])
        mock_model.encode.return_value = query_embedding
        mock_sentence_transformer.return_value = mock_model

        # コサイン類似度のモック設定（各呼び出しで異なる値を返す）
        mock_cosine_similarity.side_effect = [
            np.array([[0.8]]),  # doc1との類似度
            np.array([[0.6]]),  # doc2との類似度
            np.array([[0.9]])   # doc3との類似度
        ]

        # テスト用の埋め込みを追加
        embeddings_data = [
            ("doc1", np.array([0.1, 0.2, 0.3, 0.4])),
            ("doc2", np.array([0.2, 0.3, 0.4, 0.5])),
            ("doc3", np.array([0.4, 0.5, 0.6, 0.7]))
        ]

        for doc_id, embedding in embeddings_data:
            self.embedding_manager.embeddings[doc_id] = DocumentEmbedding(
                doc_id=doc_id,
                embedding=embedding,
                text_hash="test_hash",
                created_at=1234567890.0
            )

        # 類似度検索を実行
        results = self.embedding_manager.search_similar("テストクエリ", limit=10)

        # 結果を検証（類似度の降順でソートされているはず）
        assert len(results) == 3
        assert results[0] == ("doc3", 0.9)  # 最も類似度が高い
        assert results[1] == ("doc1", 0.8)
        assert results[2] == ("doc2", 0.6)

    @patch('src.core.embedding_manager.SentenceTransformer')
    def test_search_similar_empty_cache(self, mock_sentence_transformer):
        """空のキャッシュでの類似度検索をテスト"""
        # モックの設定
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        # 空のキャッシュで検索
        results = self.embedding_manager.search_similar("テストクエリ")

        # 空の結果が返されることを確認
        assert results == []

    @patch('src.core.embedding_manager.SentenceTransformer')
    @patch('src.core.embedding_manager.cosine_similarity')
    def test_search_similar_with_min_similarity(self, mock_cosine_similarity, mock_sentence_transformer):
        """最小類似度フィルターでの類似度検索をテスト"""
        # モックの設定
        mock_model = Mock()
        query_embedding = np.array([0.5, 0.5, 0.5, 0.5])
        mock_model.encode.return_value = query_embedding
        mock_sentence_transformer.return_value = mock_model

        # コサイン類似度のモック設定（一つは閾値以下）
        mock_cosine_similarity.side_effect = [
            np.array([[0.8]]),  # doc1との類似度（閾値以上）
            np.array([[0.3]])   # doc2との類似度（閾値以下）
        ]

        # テスト用の埋め込みを追加
        embeddings_data = [
            ("doc1", np.array([0.1, 0.2, 0.3, 0.4])),
            ("doc2", np.array([0.2, 0.3, 0.4, 0.5]))
        ]

        for doc_id, embedding in embeddings_data:
            self.embedding_manager.embeddings[doc_id] = DocumentEmbedding(
                doc_id=doc_id,
                embedding=embedding,
                text_hash="test_hash",
                created_at=1234567890.0
            )

        # 最小類似度0.5で検索
        results = self.embedding_manager.search_similar("テストクエリ", min_similarity=0.5)

        # 閾値以上の結果のみ返されることを確認
        assert len(results) == 1
        assert results[0] == ("doc1", 0.8)

    def test_save_embeddings(self):
        """埋め込みキャッシュの保存をテスト"""
        # テスト用の埋め込みを追加
        doc_embedding = DocumentEmbedding(
            doc_id="test_doc",
            embedding=np.array([0.1, 0.2, 0.3]),
            text_hash="test_hash",
            created_at=1234567890.0
        )
        self.embedding_manager.embeddings["test_doc"] = doc_embedding

        # 保存を実行
        self.embedding_manager.save_embeddings()

        # ファイルが作成されたことを確認
        assert os.path.exists(self.embeddings_path)

        # ファイルの内容を確認
        with open(self.embeddings_path, 'rb') as f:
            loaded_embeddings = pickle.load(f)

        assert "test_doc" in loaded_embeddings
        loaded_embedding = loaded_embeddings["test_doc"]
        assert loaded_embedding.doc_id == "test_doc"
        np.testing.assert_array_equal(loaded_embedding.embedding, np.array([0.1, 0.2, 0.3]))

    def test_load_embeddings_existing_file(self):
        """既存ファイルからの埋め込み読み込みをテスト"""
        # テスト用の埋め込みデータを作成
        test_embeddings = {
            "test_doc": DocumentEmbedding(
                doc_id="test_doc",
                embedding=np.array([0.1, 0.2, 0.3]),
                text_hash="test_hash",
                created_at=1234567890.0
            )
        }

        # ファイルに保存
        with open(self.embeddings_path, 'wb') as f:
            pickle.dump(test_embeddings, f)

        # 新しいEmbeddingManagerインスタンスを作成（読み込みが実行される）
        new_manager = EmbeddingManager(embeddings_path=self.embeddings_path)

        # 読み込まれたことを確認
        assert "test_doc" in new_manager.embeddings
        loaded_embedding = new_manager.embeddings["test_doc"]
        assert loaded_embedding.doc_id == "test_doc"
        np.testing.assert_array_equal(loaded_embedding.embedding, np.array([0.1, 0.2, 0.3]))

    def test_load_embeddings_no_file(self):
        """ファイルが存在しない場合の読み込みをテスト"""
        # 存在しないパスでEmbeddingManagerを作成
        non_existent_path = os.path.join(self.temp_dir, "non_existent.pkl")
        manager = EmbeddingManager(embeddings_path=non_existent_path)

        # 空のキャッシュで初期化されることを確認
        assert manager.embeddings == {}

    def test_get_cache_info(self):
        """キャッシュ情報の取得をテスト"""
        # テスト用の埋め込みを追加
        doc_embedding = DocumentEmbedding(
            doc_id="test_doc",
            embedding=np.array([0.1, 0.2, 0.3]),
            text_hash="test_hash",
            created_at=1234567890.0
        )
        self.embedding_manager.embeddings["test_doc"] = doc_embedding

        # キャッシュを保存
        self.embedding_manager.save_embeddings()

        # キャッシュ情報を取得
        info = self.embedding_manager.get_cache_info()

        # 情報を検証
        assert info["total_embeddings"] == 1
        assert info["cache_file_size_mb"] >= 0  # ファイルサイズは0以上
        assert info["cache_file_path"] == self.embeddings_path
        assert info["model_name"] == "all-MiniLM-L6-v2"
        assert info["model_loaded"] is False  # まだモデルは読み込まれていない

    def test_clear_cache(self):
        """キャッシュクリアをテスト"""
        # テスト用の埋め込みを追加
        doc_embedding = DocumentEmbedding(
            doc_id="test_doc",
            embedding=np.array([0.1, 0.2, 0.3]),
            text_hash="test_hash",
            created_at=1234567890.0
        )
        self.embedding_manager.embeddings["test_doc"] = doc_embedding

        # キャッシュを保存
        self.embedding_manager.save_embeddings()

        # キャッシュをクリア
        self.embedding_manager.clear_cache()

        # キャッシュが空になったことを確認
        assert self.embedding_manager.embeddings == {}
        assert not os.path.exists(self.embeddings_path)

    @patch('src.core.embedding_manager.SentenceTransformer')
    @patch('os.path.exists')
    def test_rebuild_embeddings(self, mock_exists, mock_sentence_transformer):
        """埋め込み再構築をテスト"""
        # ファイル存在チェックをモック
        mock_exists.return_value = True

        # モックの設定
        mock_model = Mock()
        mock_embeddings = [
            np.array([0.1, 0.2, 0.3]),
            np.array([0.4, 0.5, 0.6])
        ]
        mock_model.encode.side_effect = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        # テスト用のドキュメントを作成
        from datetime import datetime

        from src.data.models import FileType
        documents = [
            Document(
                id="doc1",
                file_path="/path/to/doc1.txt",
                title="ドキュメント1",
                content="これは最初のドキュメントです",
                file_type=FileType.TEXT,
                size=100,
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                metadata={}
            ),
            Document(
                id="doc2",
                file_path="/path/to/doc2.txt",
                title="ドキュメント2",
                content="これは二番目のドキュメントです",
                file_type=FileType.TEXT,
                size=150,
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                metadata={}
            )
        ]

        # 埋め込みを再構築
        self.embedding_manager.rebuild_embeddings(documents)

        # 結果を検証
        assert len(self.embedding_manager.embeddings) == 2
        assert "doc1" in self.embedding_manager.embeddings
        assert "doc2" in self.embedding_manager.embeddings

        # モデルが正しく呼ばれたことを確認
        assert mock_model.encode.call_count == 2

    @patch('src.core.embedding_manager.SentenceTransformer')
    def test_ensure_model_loaded(self, mock_sentence_transformer):
        """モデルの自動読み込みをテスト"""
        # モックの設定
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        # モデルが読み込まれていない状態で埋め込み生成を実行
        assert self.embedding_manager.model is None

        # 埋め込み生成（内部でモデルが自動読み込みされるはず）
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        self.embedding_manager.generate_embedding("テスト")

        # モデルが読み込まれたことを確認
        assert self.embedding_manager.model == mock_model
