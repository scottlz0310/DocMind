"""
EmbeddingManager - セマンティック検索用の埋め込み管理クラス

このモジュールは、sentence-transformersを使用してドキュメントの埋め込みを生成し、
コサイン類似度を使用したセマンティック検索機能を提供します。
"""

import os
import pickle
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from ..data.models import Document
from ..utils.exceptions import EmbeddingError
from ..utils.config import Config


@dataclass
class DocumentEmbedding:
    """ドキュメント埋め込み情報を格納するデータクラス"""
    doc_id: str
    embedding: np.ndarray
    text_hash: str  # テキストの変更検出用
    created_at: float  # タイムスタンプ


class EmbeddingManager:
    """
    セマンティック検索用の埋め込み管理クラス
    
    sentence-transformersを使用してドキュメントの埋め込みを生成し、
    コサイン類似度を使用したセマンティック検索を実行します。
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", 
                 embeddings_path: Optional[str] = None):
        """
        EmbeddingManagerを初期化
        
        Args:
            model_name: 使用するsentence-transformersモデル名
            embeddings_path: 埋め込みファイルのパス（Noneの場合はデフォルトパスを使用）
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.embeddings: Dict[str, DocumentEmbedding] = {}
        
        # 埋め込みファイルのパスを設定
        if embeddings_path is None:
            config = Config()
            self.embeddings_path = os.path.join(config.data_dir, "embeddings.pkl")
        else:
            self.embeddings_path = embeddings_path
            
        # ログ設定
        self.logger = logging.getLogger(__name__)
        
        # 埋め込みファイルのディレクトリを作成
        os.makedirs(os.path.dirname(self.embeddings_path), exist_ok=True)
        
        # 既存の埋め込みを読み込み
        self.load_embeddings()
    
    def load_model(self) -> None:
        """
        sentence-transformersモデルを読み込み
        
        Raises:
            EmbeddingError: モデルの読み込みに失敗した場合
        """
        try:
            self.logger.info(f"sentence-transformersモデルを読み込み中: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.logger.info("モデルの読み込みが完了しました")
        except Exception as e:
            error_msg = f"モデルの読み込みに失敗しました: {e}"
            self.logger.error(error_msg)
            raise EmbeddingError(error_msg) from e
    
    def _ensure_model_loaded(self) -> None:
        """モデルが読み込まれていることを確認し、必要に応じて読み込み"""
        if self.model is None:
            self.load_model()
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        テキストから埋め込みベクトルを生成
        
        Args:
            text: 埋め込みを生成するテキスト
            
        Returns:
            埋め込みベクトル（numpy配列）
            
        Raises:
            EmbeddingError: 埋め込み生成に失敗した場合
        """
        self._ensure_model_loaded()
        
        try:
            # テキストが空の場合はゼロベクトルを返す
            if not text or not text.strip():
                self.logger.warning("空のテキストが渡されました。ゼロベクトルを返します。")
                return np.zeros(self.model.get_sentence_embedding_dimension())
            
            # 埋め込みを生成
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
            
        except Exception as e:
            error_msg = f"埋め込み生成に失敗しました: {e}"
            self.logger.error(error_msg)
            raise EmbeddingError(error_msg) from e
    
    def add_document_embedding(self, doc_id: str, text: str) -> None:
        """
        ドキュメントの埋め込みを生成してキャッシュに追加
        
        Args:
            doc_id: ドキュメントID
            text: ドキュメントのテキスト内容
        """
        try:
            # テキストのハッシュを計算（変更検出用）
            text_hash = str(hash(text))
            
            # 既存の埋め込みがあり、テキストが変更されていない場合はスキップ
            if doc_id in self.embeddings:
                existing = self.embeddings[doc_id]
                if existing.text_hash == text_hash:
                    self.logger.debug(f"ドキュメント {doc_id} の埋め込みは既に最新です")
                    return
            
            # 埋め込みを生成
            embedding = self.generate_embedding(text)
            
            # キャッシュに保存
            import time
            self.embeddings[doc_id] = DocumentEmbedding(
                doc_id=doc_id,
                embedding=embedding,
                text_hash=text_hash,
                created_at=time.time()
            )
            
            self.logger.info(f"ドキュメント {doc_id} の埋め込みを生成しました")
            
        except Exception as e:
            error_msg = f"ドキュメント {doc_id} の埋め込み追加に失敗しました: {e}"
            self.logger.error(error_msg)
            raise EmbeddingError(error_msg) from e
    
    def remove_document_embedding(self, doc_id: str) -> None:
        """
        ドキュメントの埋め込みをキャッシュから削除
        
        Args:
            doc_id: 削除するドキュメントID
        """
        if doc_id in self.embeddings:
            del self.embeddings[doc_id]
            self.logger.info(f"ドキュメント {doc_id} の埋め込みを削除しました")
    
    def search_similar(self, query_text: str, limit: int = 100, 
                      min_similarity: float = 0.0) -> List[Tuple[str, float]]:
        """
        クエリテキストに類似したドキュメントを検索
        
        Args:
            query_text: 検索クエリテキスト
            limit: 返す結果の最大数
            min_similarity: 最小類似度スコア（0.0-1.0）
            
        Returns:
            (ドキュメントID, 類似度スコア)のタプルのリスト（類似度の降順）
        """
        try:
            if not self.embeddings:
                self.logger.warning("埋め込みキャッシュが空です")
                return []
            
            # クエリの埋め込みを生成
            query_embedding = self.generate_embedding(query_text)
            
            # 各ドキュメントとの類似度を計算
            similarities = []
            for doc_id, doc_embedding in self.embeddings.items():
                # コサイン類似度を計算
                similarity = cosine_similarity(
                    query_embedding.reshape(1, -1),
                    doc_embedding.embedding.reshape(1, -1)
                )[0][0]
                
                # 最小類似度を満たす場合のみ追加
                if similarity >= min_similarity:
                    similarities.append((doc_id, float(similarity)))
            
            # 類似度の降順でソート
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 制限数まで返す
            return similarities[:limit]
            
        except Exception as e:
            error_msg = f"類似度検索に失敗しました: {e}"
            self.logger.error(error_msg)
            raise EmbeddingError(error_msg) from e
    
    def save_embeddings(self) -> None:
        """
        埋め込みキャッシュをファイルに保存
        
        Raises:
            EmbeddingError: 保存に失敗した場合
        """
        try:
            # 一時ファイルに保存してから移動（原子的操作）
            temp_path = self.embeddings_path + ".tmp"
            
            with open(temp_path, 'wb') as f:
                pickle.dump(self.embeddings, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            # 一時ファイルを本来のファイルに移動
            os.replace(temp_path, self.embeddings_path)
            
            self.logger.info(f"埋め込みキャッシュを保存しました: {self.embeddings_path}")
            
        except Exception as e:
            error_msg = f"埋め込みキャッシュの保存に失敗しました: {e}"
            self.logger.error(error_msg)
            raise EmbeddingError(error_msg) from e
    
    def load_embeddings(self) -> None:
        """
        埋め込みキャッシュをファイルから読み込み
        
        ファイルが存在しない場合は空のキャッシュで開始
        """
        try:
            if os.path.exists(self.embeddings_path):
                with open(self.embeddings_path, 'rb') as f:
                    self.embeddings = pickle.load(f)
                
                self.logger.info(f"埋め込みキャッシュを読み込みました: {len(self.embeddings)}件")
            else:
                self.embeddings = {}
                self.logger.info("埋め込みキャッシュファイルが存在しません。空のキャッシュで開始します。")
                
        except Exception as e:
            self.logger.warning(f"埋め込みキャッシュの読み込みに失敗しました: {e}")
            self.logger.info("空のキャッシュで開始します。")
            self.embeddings = {}
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        キャッシュの統計情報を取得
        
        Returns:
            キャッシュ統計情報の辞書
        """
        total_embeddings = len(self.embeddings)
        cache_size_mb = 0
        
        if os.path.exists(self.embeddings_path):
            cache_size_mb = os.path.getsize(self.embeddings_path) / (1024 * 1024)
        
        return {
            "total_embeddings": total_embeddings,
            "cache_file_size_mb": round(cache_size_mb, 2),
            "cache_file_path": self.embeddings_path,
            "model_name": self.model_name,
            "model_loaded": self.model is not None
        }
    
    def clear_cache(self) -> None:
        """
        埋め込みキャッシュをクリア
        """
        self.embeddings.clear()
        if os.path.exists(self.embeddings_path):
            os.remove(self.embeddings_path)
        self.logger.info("埋め込みキャッシュをクリアしました")
    
    def rebuild_embeddings(self, documents: List[Document]) -> None:
        """
        すべてのドキュメントの埋め込みを再構築
        
        Args:
            documents: 埋め込みを生成するドキュメントのリスト
        """
        self.logger.info(f"{len(documents)}件のドキュメントの埋め込みを再構築中...")
        
        # キャッシュをクリア
        self.embeddings.clear()
        
        # 各ドキュメントの埋め込みを生成
        for i, doc in enumerate(documents):
            try:
                self.add_document_embedding(doc.id, doc.content)
                
                # 進捗をログ出力
                if (i + 1) % 100 == 0:
                    self.logger.info(f"進捗: {i + 1}/{len(documents)} 完了")
                    
            except Exception as e:
                self.logger.error(f"ドキュメント {doc.id} の埋め込み生成に失敗: {e}")
                continue
        
        # キャッシュを保存
        self.save_embeddings()
        
        self.logger.info(f"埋め込み再構築が完了しました: {len(self.embeddings)}件")