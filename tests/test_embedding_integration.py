"""
EmbeddingManagerの統合テスト

実際のsentence-transformersモデルを使用した統合テストを実行します。
このテストは実際のモデルをダウンロードするため、時間がかかる場合があります。
"""

import os
import shutil
import tempfile

import numpy as np
import pytest

from src.core.embedding_manager import EmbeddingManager


@pytest.mark.integration
class TestEmbeddingManagerIntegration:
    """EmbeddingManagerの統合テストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.embeddings_path = os.path.join(self.temp_dir, "test_embeddings.pkl")

        # テスト用のEmbeddingManagerインスタンスを作成
        self.embedding_manager = EmbeddingManager(
            model_name="all-MiniLM-L6-v2", embeddings_path=self.embeddings_path
        )

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        # 一時ディレクトリを削除
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_real_model_loading_and_embedding_generation(self):
        """実際のモデルを使用した埋め込み生成テスト"""
        # モデルを読み込み
        self.embedding_manager.load_model()

        # 埋め込みを生成
        text = "これはテストドキュメントです。セマンティック検索のテストを行います。"
        embedding = self.embedding_manager.generate_embedding(text)

        # 埋め込みが正しく生成されたことを確認
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == 384  # all-MiniLM-L6-v2の次元数
        assert not np.allclose(embedding, 0)  # ゼロベクトルではない

    def test_real_semantic_search(self):
        """実際のモデルを使用したセマンティック検索テスト"""
        # テストドキュメントを追加
        documents = [
            ("doc1", "犬は忠実な動物です。人間の最良の友と呼ばれています。"),
            ("doc2", "猫は独立心が強い動物です。自由を愛する性格です。"),
            ("doc3", "プログラミングはコンピューターに指示を与える技術です。"),
            ("doc4", "機械学習は人工知能の一分野です。データから学習します。"),
        ]

        for doc_id, text in documents:
            self.embedding_manager.add_document_embedding(doc_id, text)

        # セマンティック検索を実行
        query = "ペットについて教えて"
        results = self.embedding_manager.search_similar(query, limit=4)

        # 結果を検証
        assert len(results) == 4

        # 動物関連のドキュメント（doc1, doc2）が上位に来ることを期待
        top_2_docs = [result[0] for result in results[:2]]
        assert "doc1" in top_2_docs or "doc2" in top_2_docs

        # すべての類似度スコアが0以上1以下であることを確認
        for doc_id, score in results:
            assert 0 <= score <= 1

    def test_embedding_persistence(self):
        """埋め込みの永続化テスト"""
        # ドキュメント埋め込みを追加
        doc_id = "test_doc"
        text = "これは永続化テスト用のドキュメントです。"

        self.embedding_manager.add_document_embedding(doc_id, text)

        # 埋め込みを保存
        self.embedding_manager.save_embeddings()

        # 新しいEmbeddingManagerインスタンスを作成
        new_manager = EmbeddingManager(embeddings_path=self.embeddings_path)

        # 埋め込みが正しく読み込まれたことを確認
        assert doc_id in new_manager.embeddings

        # 元の埋め込みと同じであることを確認
        original_embedding = self.embedding_manager.embeddings[doc_id].embedding
        loaded_embedding = new_manager.embeddings[doc_id].embedding

        np.testing.assert_array_equal(original_embedding, loaded_embedding)

    def test_similarity_consistency(self):
        """類似度計算の一貫性テスト"""
        # 同じテキストの埋め込みを生成
        text = "一貫性テスト用のテキストです。"

        embedding1 = self.embedding_manager.generate_embedding(text)
        embedding2 = self.embedding_manager.generate_embedding(text)

        # 同じテキストの埋め込みは同一であることを確認
        np.testing.assert_array_equal(embedding1, embedding2)

        # 自分自身との類似度は1.0に近いことを確認
        self.embedding_manager.add_document_embedding("test_doc", text)
        results = self.embedding_manager.search_similar(text, limit=1)

        assert len(results) == 1
        assert results[0][0] == "test_doc"
        assert results[0][1] > 0.99  # 自分自身との類似度は非常に高い
