"""
EmbeddingManager拡張 - 不足メソッドの追加

テストで必要な不足メソッドを追加したEmbeddingManagerの拡張版
"""

from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .embedding_manager import EmbeddingManager


class EmbeddingManagerExtended(EmbeddingManager):
    """テスト用に拡張されたEmbeddingManager"""

    def clear_embeddings(self) -> None:
        """埋め込みをクリア（clear_cacheのエイリアス）"""
        self.clear_cache()

    def get_embedding_stats(self) -> dict[str, Any]:
        """埋め込み統計情報を取得（get_cache_infoのエイリアス）"""
        return self.get_cache_info()

    def document_exists(self, doc_id: str) -> bool:
        """ドキュメントが埋め込みに存在するかチェック

        Args:
            doc_id: ドキュメントID

        Returns:
            存在する場合True
        """
        return doc_id in self.embeddings

    def get_document_embedding(self, doc_id: str) -> np.ndarray | None:
        """ドキュメントの埋め込みを取得

        Args:
            doc_id: ドキュメントID

        Returns:
            埋め込みベクトル、存在しない場合はNone
        """
        if doc_id in self.embeddings:
            return self.embeddings[doc_id].embedding
        return None

    def _calculate_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """2つのベクトル間の類似度を計算

        Args:
            vec1: ベクトル1
            vec2: ベクトル2

        Returns:
            コサイン類似度
        """
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)

        return cosine_similarity(vec1_np.reshape(1, -1), vec2_np.reshape(1, -1))[0][0]

    def update_document_embedding(self, doc_id: str, text: str) -> None:
        """ドキュメントの埋め込みを更新（add_document_embeddingのエイリアス）

        Args:
            doc_id: ドキュメントID
            text: 新しいテキスト内容
        """
        self.add_document_embedding(doc_id, text)

    def batch_add_embeddings(self, documents: list) -> None:
        """複数のドキュメントの埋め込みをバッチで追加

        Args:
            documents: ドキュメントのリスト
        """
        for doc in documents:
            try:
                self.add_document_embedding(doc.id, doc.content)
            except Exception as e:
                self.logger.error(f"ドキュメント {doc.id} の埋め込み追加に失敗: {e}")
                continue
