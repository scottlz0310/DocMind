"""
IndexManager強化テスト

大規模インデックス作成・増分更新のパフォーマンステスト
"""
import pytest
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.index_manager import IndexManager
from src.core.document_processor import DocumentProcessor


class TestIndexManager:
    """インデックス管理コアロジックテスト"""

    @pytest.fixture
    def temp_index_dir(self):
        """テスト用一時インデックスディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def large_document_set(self):
        """大規模ドキュメントセット（モック）"""
        documents = []
        for i in range(1000):
            doc = Mock()
            doc.file_path = f"/test/doc_{i}.txt"
            doc.content = f"テストドキュメント{i}の内容です。" * 10
            doc.metadata = {
                'file_size': 1024,
                'modified_time': time.time(),
                'file_type': 'txt'
            }
            documents.append(doc)
        return documents

    @pytest.fixture
    def existing_index(self, temp_index_dir):
        """既存インデックス"""
        manager = IndexManager(str(temp_index_dir))
        # 小規模な既存インデックスを作成
        for i in range(100):
            manager.add_document(
                f"/existing/doc_{i}.txt",
                f"既存ドキュメント{i}",
                {'file_type': 'txt'}
            )
        return manager

    def test_large_scale_indexing(self, temp_index_dir, large_document_set):
        """大規模インデックス作成テスト"""
        manager = IndexManager(str(temp_index_dir))
        
        start_time = time.time()
        success_count = 0
        
        for doc in large_document_set:
            try:
                manager.add_document(
                    doc.file_path,
                    doc.content,
                    doc.metadata
                )
                success_count += 1
            except Exception as e:
                pytest.fail(f"ドキュメント追加失敗: {e}")
        
        end_time = time.time()
        
        # 検証
        assert success_count == len(large_document_set)
        assert (end_time - start_time) < 60  # 1分以内
        assert manager.get_document_count() == len(large_document_set)

    def test_incremental_update_performance(self, existing_index):
        """増分更新パフォーマンステスト"""
        manager = existing_index
        
        # 新しいドキュメントを準備
        new_documents = []
        for i in range(50):
            new_documents.append({
                'path': f"/new/doc_{i}.txt",
                'content': f"新規ドキュメント{i}の内容",
                'metadata': {'file_type': 'txt'}
            })
        
        start_time = time.time()
        
        for doc in new_documents:
            manager.add_document(
                doc['path'],
                doc['content'],
                doc['metadata']
            )
        
        end_time = time.time()
        
        # 検証
        assert (end_time - start_time) < 10  # 10秒以内
        assert manager.get_document_count() == 150  # 100 + 50

    def test_index_optimization_performance(self, existing_index):
        """インデックス最適化パフォーマンステスト"""
        manager = existing_index
        
        start_time = time.time()
        manager.optimize_index()
        end_time = time.time()
        
        # 最適化は30秒以内
        assert (end_time - start_time) < 30

    def test_concurrent_index_operations(self, temp_index_dir):
        """並行インデックス操作テスト"""
        import threading
        
        manager = IndexManager(str(temp_index_dir))
        results = []
        
        def add_documents(start_idx, count):
            """ドキュメント追加スレッド"""
            try:
                for i in range(start_idx, start_idx + count):
                    manager.add_document(
                        f"/concurrent/doc_{i}.txt",
                        f"並行テストドキュメント{i}",
                        {'file_type': 'txt'}
                    )
                results.append(True)
            except Exception:
                results.append(False)
        
        # 5つのスレッドで並行実行
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=add_documents,
                args=(i * 20, 20)
            )
            threads.append(thread)
            thread.start()
        
        # 全スレッド完了を待機
        for thread in threads:
            thread.join()
        
        # 検証
        assert all(results)  # 全スレッド成功
        assert manager.get_document_count() == 100

    def test_index_corruption_recovery(self, temp_index_dir):
        """インデックス破損復旧テスト"""
        manager = IndexManager(str(temp_index_dir))
        
        # 正常なインデックスを作成
        for i in range(10):
            manager.add_document(
                f"/test/doc_{i}.txt",
                f"テストドキュメント{i}",
                {'file_type': 'txt'}
            )
        
        # インデックスファイルを意図的に破損
        index_files = list(temp_index_dir.glob("*"))
        if index_files:
            with open(index_files[0], 'w') as f:
                f.write("破損データ")
        
        # 新しいマネージャーで復旧テスト
        recovery_manager = IndexManager(str(temp_index_dir))
        
        # 復旧後の動作確認
        recovery_manager.add_document(
            "/recovery/doc.txt",
            "復旧テストドキュメント",
            {'file_type': 'txt'}
        )
        
        assert recovery_manager.get_document_count() >= 1

    def test_memory_efficient_indexing(self, temp_index_dir):
        """メモリ効率的インデックス作成テスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        manager = IndexManager(str(temp_index_dir))
        
        # 大量のドキュメントを追加
        for i in range(500):
            large_content = "大きなコンテンツ " * 1000  # 約15KB
            manager.add_document(
                f"/memory_test/doc_{i}.txt",
                large_content,
                {'file_type': 'txt'}
            )
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ増加量が500MB以下
        assert memory_increase < 500 * 1024 * 1024

    def test_index_statistics_accuracy(self, existing_index):
        """インデックス統計情報精度テスト"""
        manager = existing_index
        
        stats = manager.get_statistics()
        
        # 統計情報の検証
        assert 'document_count' in stats
        assert 'total_size' in stats
        assert 'last_updated' in stats
        assert stats['document_count'] == 100
        assert stats['total_size'] > 0
        assert stats['last_updated'] is not None