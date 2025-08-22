# -*- coding: utf-8 -*-
"""
パフォーマンステストモジュール

このモジュールは、DocMindアプリケーションのパフォーマンス要件を検証するテストを提供します。
5秒検索要件、メモリ使用量、キャッシュ効率などをテストします。
"""

import pytest
import time
import threading
import tempfile
import shutil
import psutil
import os
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.core.search_manager import SearchManager
from src.core.index_manager import IndexManager
from src.core.embedding_manager import EmbeddingManager
from src.data.models import Document, SearchQuery, SearchType, FileType
from src.data.database import DatabaseManager
from src.utils.cache_manager import CacheManager, SearchResultCache
from src.utils.background_processor import TaskManager, TaskPriority


class PerformanceTestBase:
    """パフォーマンステストの基底クラス"""
    
    @pytest.fixture(autouse=True)
    def setup_performance_test(self):
        """パフォーマンステスト用のセットアップ"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(self.temp_dir)
        
        # テスト用のコンポーネントを初期化
        self.db_manager = DatabaseManager(str(self.test_data_dir / "test.db"))
        self.index_manager = IndexManager(str(self.test_data_dir / "index"))
        self.embedding_manager = EmbeddingManager(str(self.test_data_dir / "embeddings"))
        self.search_manager = SearchManager(self.index_manager, self.embedding_manager)
        self.cache_manager = CacheManager(str(self.test_data_dir / "cache"))
        
        # プロセス監視を開始
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
        
        yield
        
        # クリーンアップ
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_documents(self, count: int) -> List[Document]:
        """テスト用ドキュメントを作成"""
        documents = []
        
        for i in range(count):
            # 様々なサイズのコンテンツを生成
            content_size = 100 + (i % 1000)  # 100-1100文字
            content = f"テストドキュメント{i} " * (content_size // 20)
            content += f"キーワード{i % 10} 検索テスト データ{i}"
            
            doc = Document(
                id=f"doc_{i}",
                file_path=f"/test/document_{i}.txt",
                title=f"テストドキュメント {i}",
                content=content,
                file_type=FileType.TEXT,
                size=len(content.encode('utf-8')),
                created_date=datetime.now() - timedelta(days=i % 365),
                modified_date=datetime.now() - timedelta(days=i % 30),
                indexed_date=datetime.now(),
                content_hash=f"hash_{i}"
            )
            documents.append(doc)
        
        return documents
    
    def measure_memory_usage(self) -> Dict[str, float]:
        """メモリ使用量を測定"""
        current_memory = self.process.memory_info().rss
        memory_increase = current_memory - self.initial_memory
        
        return {
            "current_memory_mb": current_memory / 1024 / 1024,
            "memory_increase_mb": memory_increase / 1024 / 1024,
            "memory_percent": self.process.memory_percent()
        }


class TestSearchPerformance(PerformanceTestBase):
    """検索パフォーマンステスト"""
    
    def test_search_performance_5_second_requirement(self):
        """5秒検索要件のテスト"""
        # 50,000ドキュメントを作成してインデックス化
        document_count = 50000
        documents = self.create_test_documents(document_count)
        
        # インデックス化の時間を測定
        start_time = time.time()
        
        # バッチでインデックス化（メモリ効率のため）
        batch_size = 1000
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            for doc in batch:
                self.index_manager.add_document(doc)
                self.embedding_manager.add_document_embedding(doc.id, doc.content)
        
        indexing_time = time.time() - start_time
        print(f"インデックス化時間: {indexing_time:.2f}秒 ({document_count}ドキュメント)")
        
        # 様々な検索クエリでパフォーマンスをテスト
        test_queries = [
            "テストドキュメント",
            "キーワード5",
            "検索テスト データ",
            "存在しないキーワード",
            "テスト AND ドキュメント"
        ]
        
        search_times = []
        
        for query_text in test_queries:
            query = SearchQuery(
                query_text=query_text,
                search_type=SearchType.FULL_TEXT,
                limit=100
            )
            
            # 検索時間を測定
            start_time = time.time()
            results = self.search_manager.search(query)
            search_time = time.time() - start_time
            
            search_times.append(search_time)
            
            print(f"検索: '{query_text}' - {search_time:.3f}秒 ({len(results)}件)")
            
            # 5秒要件をチェック
            assert search_time < 5.0, f"検索時間が5秒を超過: {search_time:.3f}秒"
        
        # 平均検索時間をチェック
        avg_search_time = sum(search_times) / len(search_times)
        print(f"平均検索時間: {avg_search_time:.3f}秒")
        
        assert avg_search_time < 2.0, f"平均検索時間が2秒を超過: {avg_search_time:.3f}秒"
    
    def test_hybrid_search_performance(self):
        """ハイブリッド検索のパフォーマンステスト"""
        # 10,000ドキュメントでテスト
        documents = self.create_test_documents(10000)
        
        for doc in documents:
            self.index_manager.add_document(doc)
            self.embedding_manager.add_document_embedding(doc.id, doc.content)
        
        query = SearchQuery(
            query_text="テストドキュメント データ",
            search_type=SearchType.HYBRID,
            limit=50
        )
        
        # ハイブリッド検索の時間を測定
        start_time = time.time()
        results = self.search_manager.search(query)
        search_time = time.time() - start_time
        
        print(f"ハイブリッド検索時間: {search_time:.3f}秒 ({len(results)}件)")
        
        # ハイブリッド検索は通常の検索より時間がかかるが、5秒以内であること
        assert search_time < 5.0, f"ハイブリッド検索時間が5秒を超過: {search_time:.3f}秒"
        assert len(results) > 0, "ハイブリッド検索で結果が取得できませんでした"
    
    def test_concurrent_search_performance(self):
        """並行検索のパフォーマンステスト"""
        # 5,000ドキュメントでテスト
        documents = self.create_test_documents(5000)
        
        for doc in documents:
            self.index_manager.add_document(doc)
        
        # 並行検索を実行
        num_threads = 10
        queries_per_thread = 5
        results = []
        errors = []
        
        def search_worker(thread_id: int):
            """検索ワーカー関数"""
            try:
                thread_results = []
                for i in range(queries_per_thread):
                    query = SearchQuery(
                        query_text=f"テスト{thread_id}_{i}",
                        search_type=SearchType.FULL_TEXT,
                        limit=20
                    )
                    
                    start_time = time.time()
                    search_results = self.search_manager.search(query)
                    search_time = time.time() - start_time
                    
                    thread_results.append({
                        "thread_id": thread_id,
                        "query_id": i,
                        "search_time": search_time,
                        "result_count": len(search_results)
                    })
                
                results.extend(thread_results)
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
        
        # スレッドを開始
        threads = []
        start_time = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(target=search_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # すべてのスレッドの完了を待機
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # 結果を検証
        assert len(errors) == 0, f"並行検索でエラーが発生: {errors}"
        assert len(results) == num_threads * queries_per_thread, "期待される検索結果数と一致しません"
        
        # 各検索が5秒以内に完了していることを確認
        max_search_time = max(result["search_time"] for result in results)
        avg_search_time = sum(result["search_time"] for result in results) / len(results)
        
        print(f"並行検索 - 総時間: {total_time:.3f}秒, 最大検索時間: {max_search_time:.3f}秒, 平均検索時間: {avg_search_time:.3f}秒")
        
        assert max_search_time < 5.0, f"並行検索で5秒を超過した検索があります: {max_search_time:.3f}秒"


class TestCachePerformance(PerformanceTestBase):
    """キャッシュパフォーマンステスト"""
    
    def test_search_cache_performance(self):
        """検索結果キャッシュのパフォーマンステスト"""
        # テストデータを準備
        documents = self.create_test_documents(1000)
        for doc in documents:
            self.index_manager.add_document(doc)
        
        query = SearchQuery(
            query_text="テストドキュメント",
            search_type=SearchType.FULL_TEXT,
            limit=50
        )
        
        # 初回検索（キャッシュなし）
        start_time = time.time()
        results1 = self.search_manager.search(query)
        first_search_time = time.time() - start_time
        
        # 2回目検索（キャッシュあり）
        start_time = time.time()
        results2 = self.search_manager.search(query)
        cached_search_time = time.time() - start_time
        
        print(f"初回検索時間: {first_search_time:.4f}秒")
        print(f"キャッシュ検索時間: {cached_search_time:.4f}秒")
        print(f"速度向上: {first_search_time / cached_search_time:.1f}倍")
        
        # キャッシュが効果的に動作していることを確認
        assert cached_search_time < first_search_time / 2, "キャッシュによる速度向上が不十分です"
        assert len(results1) == len(results2), "キャッシュされた結果が元の結果と一致しません"
        
        # キャッシュ統計を確認
        cache_stats = self.cache_manager.search_cache.get_stats()
        assert cache_stats["hits"] > 0, "キャッシュヒットが記録されていません"
        assert cache_stats["hit_rate"] > 0, "キャッシュヒット率が0です"
    
    def test_cache_memory_efficiency(self):
        """キャッシュのメモリ効率テスト"""
        initial_memory = self.measure_memory_usage()
        
        # 大量の検索結果をキャッシュ
        documents = self.create_test_documents(5000)
        for doc in documents:
            self.index_manager.add_document(doc)
        
        # 様々なクエリで検索してキャッシュを蓄積
        queries = [f"テスト{i}" for i in range(100)]
        
        for query_text in queries:
            query = SearchQuery(
                query_text=query_text,
                search_type=SearchType.FULL_TEXT,
                limit=20
            )
            self.search_manager.search(query)
        
        # メモリ使用量を測定
        final_memory = self.measure_memory_usage()
        memory_increase = final_memory["memory_increase_mb"]
        
        print(f"キャッシュによるメモリ増加: {memory_increase:.2f}MB")
        
        # メモリ使用量が合理的な範囲内であることを確認
        assert memory_increase < 500, f"キャッシュのメモリ使用量が過大: {memory_increase:.2f}MB"
        
        # キャッシュ統計を確認
        cache_stats = self.cache_manager.get_cache_stats()
        print(f"キャッシュ統計: {cache_stats}")


class TestBackgroundProcessingPerformance(PerformanceTestBase):
    """バックグラウンド処理パフォーマンステスト"""
    
    def test_background_indexing_performance(self):
        """バックグラウンドインデックス化のパフォーマンステスト"""
        task_manager = TaskManager()
        task_manager.start_all()
        
        try:
            documents = self.create_test_documents(1000)
            completed_tasks = []
            
            def completion_callback(task):
                completed_tasks.append(task)
            
            # バックグラウンドでインデックス化タスクを送信
            start_time = time.time()
            
            for i, doc in enumerate(documents):
                task_id = task_manager.submit_indexing_task(
                    name=f"インデックス化: {doc.title}",
                    func=self.index_manager.add_document,
                    args=(doc,),
                    priority=TaskPriority.NORMAL,
                    completion_callback=completion_callback
                )
            
            # すべてのタスクの完了を待機
            while len(completed_tasks) < len(documents):
                time.sleep(0.1)
                if time.time() - start_time > 60:  # 60秒でタイムアウト
                    break
            
            total_time = time.time() - start_time
            
            print(f"バックグラウンドインデックス化時間: {total_time:.2f}秒 ({len(documents)}ドキュメント)")
            print(f"完了タスク数: {len(completed_tasks)}")
            
            # パフォーマンス要件をチェック
            assert len(completed_tasks) == len(documents), "すべてのインデックス化タスクが完了していません"
            assert total_time < 30, f"バックグラウンドインデックス化が30秒を超過: {total_time:.2f}秒"
            
            # タスクマネージャーの統計を確認
            stats = task_manager.get_all_stats()
            print(f"タスクマネージャー統計: {stats}")
            
        finally:
            task_manager.stop_all()
    
    def test_concurrent_background_tasks(self):
        """並行バックグラウンドタスクのパフォーマンステスト"""
        task_manager = TaskManager()
        task_manager.start_all()
        
        try:
            completed_tasks = []
            
            def dummy_task(task_id: int, duration: float = 0.1):
                """ダミータスク"""
                time.sleep(duration)
                return f"Task {task_id} completed"
            
            def completion_callback(task):
                completed_tasks.append(task)
            
            # 大量のタスクを送信
            num_tasks = 100
            start_time = time.time()
            
            for i in range(num_tasks):
                task_manager.submit_file_task(
                    name=f"ダミータスク {i}",
                    func=dummy_task,
                    args=(i, 0.05),  # 50ms のタスク
                    completion_callback=completion_callback
                )
            
            # すべてのタスクの完了を待機
            while len(completed_tasks) < num_tasks:
                time.sleep(0.01)
                if time.time() - start_time > 30:  # 30秒でタイムアウト
                    break
            
            total_time = time.time() - start_time
            
            print(f"並行タスク実行時間: {total_time:.2f}秒 ({num_tasks}タスク)")
            print(f"完了タスク数: {len(completed_tasks)}")
            
            # 並行処理の効果を確認
            sequential_time = num_tasks * 0.05  # 順次実行した場合の時間
            speedup = sequential_time / total_time
            
            print(f"理論的順次実行時間: {sequential_time:.2f}秒")
            print(f"並行処理による速度向上: {speedup:.1f}倍")
            
            assert len(completed_tasks) == num_tasks, "すべてのタスクが完了していません"
            assert speedup > 2, f"並行処理の速度向上が不十分: {speedup:.1f}倍"
            
        finally:
            task_manager.stop_all()


class TestDatabasePerformance(PerformanceTestBase):
    """データベースパフォーマンステスト"""
    
    def test_database_query_performance(self):
        """データベースクエリのパフォーマンステスト"""
        # テストデータを挿入
        documents = self.create_test_documents(10000)
        
        # バッチ挿入のパフォーマンスを測定
        start_time = time.time()
        
        with self.db_manager.get_connection() as conn:
            for doc in documents:
                conn.execute("""
                    INSERT INTO documents 
                    (id, file_path, title, file_type, size, created_date, modified_date, indexed_date, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc.id, doc.file_path, doc.title, doc.file_type.value,
                    doc.size, doc.created_date, doc.modified_date, doc.indexed_date, doc.content_hash
                ))
            conn.commit()
        
        insert_time = time.time() - start_time
        print(f"データベース挿入時間: {insert_time:.2f}秒 ({len(documents)}レコード)")
        
        # クエリパフォーマンスを測定
        test_queries = [
            "SELECT COUNT(*) FROM documents",
            "SELECT * FROM documents WHERE file_type = 'text' LIMIT 100",
            "SELECT * FROM documents WHERE size > 1000 ORDER BY modified_date DESC LIMIT 50",
            "SELECT file_type, COUNT(*) FROM documents GROUP BY file_type"
        ]
        
        query_times = []
        
        for query in test_queries:
            start_time = time.time()
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute(query)
                results = cursor.fetchall()
            
            query_time = time.time() - start_time
            query_times.append(query_time)
            
            print(f"クエリ実行時間: {query_time:.4f}秒 ({len(results)}件) - {query[:50]}...")
            
            # 各クエリが1秒以内に完了することを確認
            assert query_time < 1.0, f"クエリが1秒を超過: {query_time:.4f}秒"
        
        avg_query_time = sum(query_times) / len(query_times)
        print(f"平均クエリ時間: {avg_query_time:.4f}秒")
        
        # パフォーマンス統計を確認
        perf_stats = self.db_manager.get_performance_stats()
        print(f"データベースパフォーマンス統計: {perf_stats}")
    
    def test_database_connection_pool_performance(self):
        """データベースコネクションプールのパフォーマンステスト"""
        # 並行データベースアクセスをテスト
        num_threads = 20
        queries_per_thread = 10
        results = []
        errors = []
        
        def db_worker(thread_id: int):
            """データベースワーカー関数"""
            try:
                thread_results = []
                for i in range(queries_per_thread):
                    start_time = time.time()
                    
                    with self.db_manager.get_connection() as conn:
                        cursor = conn.execute("SELECT COUNT(*) FROM documents")
                        result = cursor.fetchone()
                    
                    query_time = time.time() - start_time
                    thread_results.append({
                        "thread_id": thread_id,
                        "query_id": i,
                        "query_time": query_time,
                        "result": result[0] if result else 0
                    })
                
                results.extend(thread_results)
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
        
        # スレッドを開始
        threads = []
        start_time = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(target=db_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # すべてのスレッドの完了を待機
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # 結果を検証
        assert len(errors) == 0, f"並行データベースアクセスでエラーが発生: {errors}"
        assert len(results) == num_threads * queries_per_thread, "期待されるクエリ結果数と一致しません"
        
        max_query_time = max(result["query_time"] for result in results)
        avg_query_time = sum(result["query_time"] for result in results) / len(results)
        
        print(f"並行データベースアクセス - 総時間: {total_time:.3f}秒")
        print(f"最大クエリ時間: {max_query_time:.4f}秒, 平均クエリ時間: {avg_query_time:.4f}秒")
        
        # コネクションプールの効果を確認
        assert max_query_time < 1.0, f"並行アクセスで1秒を超過したクエリがあります: {max_query_time:.4f}秒"
        assert avg_query_time < 0.1, f"平均クエリ時間が0.1秒を超過: {avg_query_time:.4f}秒"


if __name__ == "__main__":
    # パフォーマンステストを実行
    pytest.main([__file__, "-v", "-s"])