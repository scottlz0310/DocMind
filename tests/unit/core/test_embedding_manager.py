"""
EmbeddingManager強化テスト

埋め込みベクトル生成・キャッシュ・パフォーマンステスト
"""
import pytest
import numpy as np
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.embedding_manager import EmbeddingManager


class TestEmbeddingManager:
    """埋め込み管理コアロジックテスト"""

    @pytest.fixture
    def temp_cache_dir(self):
        """テスト用一時キャッシュディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_texts(self):
        """テスト用テキストサンプル"""
        return [
            "機械学習は人工知能の重要な分野です",
            "データサイエンスでは統計的手法を使用します",
            "プログラミングは論理的思考が必要です",
            "ソフトウェア開発にはチームワークが重要です",
            "プロジェクト管理は計画と実行が鍵となります"
        ]

    def test_embedding_generation_accuracy(self, temp_cache_dir, sample_texts):
        """埋め込みベクトル生成精度テスト"""
        manager = EmbeddingManager(cache_dir=str(temp_cache_dir))
        
        for text in sample_texts:
            embedding = manager.get_embedding(text)
            
            # 基本検証
            assert isinstance(embedding, np.ndarray)
            assert embedding.shape[0] > 0  # ベクトル次元数
            assert not np.isnan(embedding).any()  # NaN値なし
            assert not np.isinf(embedding).any()  # 無限値なし
            
            # 正規化確認（sentence-transformersは正規化済み）
            norm = np.linalg.norm(embedding)
            assert abs(norm - 1.0) < 0.01  # 正規化済みベクトル

    def test_embedding_cache_performance(self, temp_cache_dir, sample_texts):
        """埋め込みキャッシュパフォーマンステスト"""
        import time
        
        manager = EmbeddingManager(cache_dir=str(temp_cache_dir))
        
        # 初回生成時間測定
        start_time = time.time()
        first_embedding = manager.get_embedding(sample_texts[0])
        first_time = time.time() - start_time
        
        # キャッシュからの取得時間測定
        start_time = time.time()
        cached_embedding = manager.get_embedding(sample_texts[0])
        cache_time = time.time() - start_time
        
        # 検証
        assert np.array_equal(first_embedding, cached_embedding)
        assert cache_time < first_time * 0.1  # キャッシュは10倍以上高速
        assert cache_time < 0.01  # 10ms以内

    def test_batch_embedding_efficiency(self, temp_cache_dir, sample_texts):
        """バッチ埋め込み効率テスト"""
        import time
        
        manager = EmbeddingManager(cache_dir=str(temp_cache_dir))
        
        # 個別処理時間
        start_time = time.time()
        individual_embeddings = []
        for text in sample_texts:
            embedding = manager.get_embedding(text)
            individual_embeddings.append(embedding)
        individual_time = time.time() - start_time
        
        # バッチ処理時間
        start_time = time.time()
        batch_embeddings = manager.get_batch_embeddings(sample_texts)
        batch_time = time.time() - start_time
        
        # 検証
        assert len(batch_embeddings) == len(sample_texts)
        assert batch_time < individual_time * 0.8  # バッチは20%以上高速
        
        # 結果の一致確認
        for i, embedding in enumerate(batch_embeddings):
            assert np.allclose(embedding, individual_embeddings[i], rtol=1e-5)

    def test_similarity_calculation_accuracy(self, temp_cache_dir):
        """類似度計算精度テスト"""
        manager = EmbeddingManager(cache_dir=str(temp_cache_dir))
        
        # 類似テキスト
        text1 = "機械学習は人工知能の分野です"
        text2 = "人工知能における機械学習について"
        
        # 非類似テキスト
        text3 = "今日の天気は晴れです"
        
        embedding1 = manager.get_embedding(text1)
        embedding2 = manager.get_embedding(text2)
        embedding3 = manager.get_embedding(text3)
        
        # 類似度計算
        similarity_12 = manager.calculate_similarity(embedding1, embedding2)
        similarity_13 = manager.calculate_similarity(embedding1, embedding3)
        
        # 検証
        assert 0 <= similarity_12 <= 1
        assert 0 <= similarity_13 <= 1
        assert similarity_12 > similarity_13  # 類似テキストの方が高い類似度

    def test_embedding_persistence(self, temp_cache_dir, sample_texts):
        """埋め込み永続化テスト"""
        # 最初のマネージャーで埋め込み生成
        manager1 = EmbeddingManager(cache_dir=str(temp_cache_dir))
        embeddings1 = []
        
        for text in sample_texts:
            embedding = manager1.get_embedding(text)
            embeddings1.append(embedding)
        
        # 新しいマネージャーでキャッシュから読み込み
        manager2 = EmbeddingManager(cache_dir=str(temp_cache_dir))
        embeddings2 = []
        
        for text in sample_texts:
            embedding = manager2.get_embedding(text)
            embeddings2.append(embedding)
        
        # 検証
        for emb1, emb2 in zip(embeddings1, embeddings2):
            assert np.array_equal(emb1, emb2)

    def test_large_text_handling(self, temp_cache_dir):
        """大きなテキスト処理テスト"""
        manager = EmbeddingManager(cache_dir=str(temp_cache_dir))
        
        # 長いテキスト（モデルの最大長を超える可能性）
        long_text = "これは非常に長いテキストです。" * 1000
        
        embedding = manager.get_embedding(long_text)
        
        # 検証
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] > 0
        assert not np.isnan(embedding).any()

    def test_memory_efficient_processing(self, temp_cache_dir):
        """メモリ効率的処理テスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        manager = EmbeddingManager(cache_dir=str(temp_cache_dir))
        
        # 大量のテキスト処理
        texts = [f"テストテキスト{i}です。" * 10 for i in range(500)]
        
        for text in texts:
            manager.get_embedding(text)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ増加量が200MB以下
        assert memory_increase < 200 * 1024 * 1024

    def test_concurrent_embedding_generation(self, temp_cache_dir):
        """並行埋め込み生成テスト"""
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        manager = EmbeddingManager(cache_dir=str(temp_cache_dir))
        results = []
        
        def generate_embedding(text):
            try:
                embedding = manager.get_embedding(f"並行テスト: {text}")
                results.append(embedding is not None)
            except Exception:
                results.append(False)
        
        # 10スレッドで並行実行
        texts = [f"テキスト{i}" for i in range(50)]
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(generate_embedding, text)
                for text in texts
            ]
            
            for future in futures:
                future.result()
        
        # 検証
        assert all(results)  # 全て成功
        assert len(results) == len(texts)

    def test_error_handling_robustness(self, temp_cache_dir):
        """エラーハンドリング堅牢性テスト"""
        manager = EmbeddingManager(cache_dir=str(temp_cache_dir))
        
        # 空文字列
        embedding = manager.get_embedding("")
        assert embedding is not None
        
        # None入力
        embedding = manager.get_embedding(None)
        assert embedding is not None
        
        # 特殊文字
        embedding = manager.get_embedding("!@#$%^&*()")
        assert embedding is not None
        
        # 非ASCII文字
        embedding = manager.get_embedding("こんにちは世界🌍")
        assert embedding is not None

    def test_cache_size_management(self, temp_cache_dir):
        """キャッシュサイズ管理テスト"""
        manager = EmbeddingManager(
            cache_dir=str(temp_cache_dir),
            max_cache_size=100  # 100エントリ制限
        )
        
        # 制限を超える数の埋め込み生成
        for i in range(150):
            text = f"キャッシュテスト{i}"
            manager.get_embedding(text)
        
        # キャッシュサイズ確認
        cache_size = manager.get_cache_size()
        assert cache_size <= 100  # 制限内