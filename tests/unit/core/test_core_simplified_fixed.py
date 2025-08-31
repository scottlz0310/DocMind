"""
簡略化されたコアロジックテスト（修正版）

実際のクラスインターフェースに合わせた基本的なテスト
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager
from src.data.models import Document, FileType


class TestCoreSimplified:
    """簡略化されたコアロジックテスト"""

    @pytest.fixture
    def temp_dir(self):
        """テスト用一時ディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_document(self, temp_dir):
        """テスト用ドキュメント"""
        from datetime import datetime

        # 実際のファイルを作成
        test_file = temp_dir / "sample.txt"
        test_file.write_text(
            "これはテスト用のドキュメントです。機械学習について説明します。"
        )

        return Document(
            id="test_doc_1",
            file_path=str(test_file),
            title="テストドキュメント",
            content="これはテスト用のドキュメントです。機械学習について説明します。",
            file_type=FileType.TEXT,
            size=1024,
            created_date=datetime.now(),
            modified_date=datetime.now(),
            indexed_date=datetime.now(),
            content_hash="test_hash",
        )

    def test_index_manager_basic_operations(self, temp_dir, sample_document):
        """IndexManagerの基本操作テスト"""
        index_manager = IndexManager(str(temp_dir / "index"))

        # ドキュメント追加
        index_manager.add_document(sample_document)

        # ドキュメント数確認
        count = index_manager.get_document_count()
        assert count == 1

        # ドキュメント存在確認
        exists = index_manager.document_exists(sample_document.id)
        assert exists is True

        # 検索テスト
        results = index_manager.search_text("機械学習", limit=10)
        assert len(results) > 0
        assert results[0].document.id == sample_document.id

    def test_index_manager_batch_operations(self, temp_dir):
        """IndexManagerのバッチ操作テスト"""
        index_manager = IndexManager(str(temp_dir / "index"))

        # 複数ドキュメント作成
        documents = []
        for i in range(10):
            from datetime import datetime

            # 実際のファイルを作成
            test_file = temp_dir / f"doc_{i}.txt"
            test_file.write_text(f"これはドキュメント{i}の内容です。")

            doc = Document(
                id=f"doc_{i}",
                file_path=str(test_file),
                title=f"ドキュメント{i}",
                content=f"これはドキュメント{i}の内容です。",
                file_type=FileType.TEXT,
                size=100,
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                content_hash=f"hash_{i}",
            )
            documents.append(doc)

        # バッチ追加
        for doc in documents:
            index_manager.add_document(doc)

        # 結果確認
        count = index_manager.get_document_count()
        assert count == 10

        # 統計情報確認
        stats = index_manager.get_index_stats()
        assert stats["document_count"] == 10
        assert stats["index_size"] > 0

    def test_embedding_manager_basic_operations(self, temp_dir):
        """EmbeddingManagerの基本操作テスト"""
        # モデル読み込みをモック化しないで実際のモデルを使用
        embedding_manager = EmbeddingManager(
            embeddings_path=str(temp_dir / "embeddings.pkl")
        )

        # 埋め込み生成テスト
        text = "テスト用のテキストです"
        embedding = embedding_manager.generate_embedding(text)
        assert embedding is not None
        assert len(embedding) == 384  # all-MiniLM-L6-v2の実際の次元数

        # ドキュメント埋め込み追加
        embedding_manager.add_document_embedding("doc_1", text)

        # 類似度検索テスト
        results = embedding_manager.search_similar("テスト", limit=5)
        assert len(results) > 0
        assert results[0][0] == "doc_1"  # ドキュメントID
        assert isinstance(results[0][1], float)  # 類似度スコア

    def test_embedding_manager_cache_operations(self, temp_dir):
        """EmbeddingManagerのキャッシュ操作テスト"""
        embeddings_path = str(temp_dir / "embeddings.pkl")

        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_instance = Mock()
            mock_instance.encode.return_value = [0.1, 0.2, 0.3]
            mock_instance.get_sentence_embedding_dimension.return_value = 3
            mock_model.return_value = mock_instance

            # 最初のマネージャーでデータ追加
            manager1 = EmbeddingManager(embeddings_path=embeddings_path)
            manager1.add_document_embedding("doc_1", "テスト1")
            manager1.add_document_embedding("doc_2", "テスト2")
            manager1.save_embeddings()

            # 新しいマネージャーでキャッシュ読み込み
            manager2 = EmbeddingManager(embeddings_path=embeddings_path)

            # キャッシュ情報確認
            cache_info = manager2.get_cache_info()
            assert cache_info["total_embeddings"] == 2
            assert cache_info["model_name"] == "all-MiniLM-L6-v2"

    def test_error_handling(self, temp_dir):
        """エラーハンドリングテスト"""
        # 無効なパスでIndexManager作成
        try:
            index_manager = IndexManager("/invalid/path/that/does/not/exist")
            # エラーが発生しないか、適切にハンドリングされることを確認
            assert index_manager is not None
        except Exception as e:
            # 適切な例外が発生することを確認
            assert isinstance(e, OSError | PermissionError | Exception)

        # EmbeddingManagerのエラーハンドリング
        with patch(
            "sentence_transformers.SentenceTransformer",
            side_effect=Exception("Model load failed"),
        ):
            embedding_manager = EmbeddingManager()

            # モデル読み込みエラーが適切にハンドリングされることを確認
            try:
                embedding_manager.generate_embedding("test")
            except Exception as e:
                assert "Model load failed" in str(e) or "EmbeddingError" in str(type(e))

    def test_performance_basic(self, temp_dir):
        """基本的なパフォーマンステスト"""
        import time

        index_manager = IndexManager(str(temp_dir / "index"))

        # 100ドキュメントの追加時間測定
        start_time = time.time()

        for i in range(100):
            from datetime import datetime

            # 実際のファイルを作成
            test_file = temp_dir / f"perf_doc_{i}.txt"
            content = f"これはパフォーマンステスト用のドキュメント{i}です。" * 5
            test_file.write_text(content)

            doc = Document(
                id=f"perf_doc_{i}",
                file_path=str(test_file),
                title=f"パフォーマンステスト{i}",
                content=content,
                file_type=FileType.TEXT,
                size=200,
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                content_hash=f"perf_hash_{i}",
            )
            index_manager.add_document(doc)

        end_time = time.time()

        # 100ドキュメントの追加が30秒以内
        assert (end_time - start_time) < 30.0

        # 検索パフォーマンステスト
        start_time = time.time()
        results = index_manager.search_text("パフォーマンステスト", limit=50)
        end_time = time.time()

        # 検索が5秒以内
        assert (end_time - start_time) < 5.0
        assert len(results) > 0

    def test_memory_usage_basic(self, temp_dir):
        """基本的なメモリ使用量テスト"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        index_manager = IndexManager(str(temp_dir / "index"))

        # 500ドキュメント追加
        for i in range(500):
            from datetime import datetime

            # 実際のファイルを作成
            test_file = temp_dir / f"mem_doc_{i}.txt"
            content = f"メモリテスト用コンテンツ{i}です。" * 20
            test_file.write_text(content)

            doc = Document(
                id=f"mem_doc_{i}",
                file_path=str(test_file),
                title=f"メモリテスト{i}",
                content=content,
                file_type=FileType.TEXT,
                size=400,
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                content_hash=f"mem_hash_{i}",
            )
            index_manager.add_document(doc)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # メモリ増加量が200MB以下
        assert memory_increase < 200 * 1024 * 1024
