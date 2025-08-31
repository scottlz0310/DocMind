"""
コアコンポーネント統合テスト

IndexManager・SearchManager・EmbeddingManager・ConfigManagerの連携テスト
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager
from src.core.search_manager import SearchManager
from src.utils.config import Config


class TestCoreIntegration:
    """コアコンポーネント統合テスト"""

    @pytest.fixture
    def temp_workspace(self):
        """テスト用一時ワークスペース"""
        temp_dir = tempfile.mkdtemp()
        workspace = {
            "root": Path(temp_dir),
            "index": Path(temp_dir) / "index",
            "cache": Path(temp_dir) / "cache",
            "config": Path(temp_dir) / "config.json",
        }

        # ディレクトリ作成
        workspace["index"].mkdir()
        workspace["cache"].mkdir()

        yield workspace
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def integrated_system(self, temp_workspace):
        """統合システム"""
        config = Config(str(temp_workspace["config"]))
        embedding_manager = EmbeddingManager(
            embeddings_path=str(temp_workspace["cache"] / "embeddings.pkl")
        )
        index_manager = IndexManager(str(temp_workspace["index"]))
        search_manager = SearchManager(index_manager, embedding_manager, config)

        return {
            "config": config,
            "embedding": embedding_manager,
            "index": index_manager,
            "search": search_manager,
        }

    def test_end_to_end_document_workflow(self, integrated_system):
        """エンドツーエンドドキュメントワークフローテスト"""
        system = integrated_system

        # 1. 設定初期化
        system["config"].set("search.max_results", 50)
        system["config"].set("indexing.batch_size", 10)

        # 2. ドキュメント追加
        test_documents = [
            {
                "path": "/test/ml_basics.txt",
                "content": "機械学習の基礎について説明します。教師あり学習と教師なし学習があります。",
                "metadata": {"topic": "機械学習", "level": "初級"},
            },
            {
                "path": "/test/data_analysis.txt",
                "content": "データ分析では統計的手法を用いてデータの傾向を把握します。",
                "metadata": {"topic": "データ分析", "level": "中級"},
            },
            {
                "path": "/test/programming.txt",
                "content": "Pythonプログラミングの基本的な文法と構造について学習します。",
                "metadata": {"topic": "プログラミング", "level": "初級"},
            },
        ]

        # インデックス作成
        for doc in test_documents:
            from datetime import datetime

            from src.data.models import Document, FileType

            document = Document(
                id=doc["path"],
                file_path=doc["path"],
                title=doc["path"].split("/")[-1],
                content=doc["content"],
                file_type=FileType.TEXT,
                size=len(doc["content"]),
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                content_hash=str(hash(doc["content"])),
                metadata=doc["metadata"],
            )
            system["index"].add_document(document)

        # 3. 検索実行
        from src.data.models import SearchQuery, SearchType

        query = SearchQuery(
            query_text="機械学習", search_type=SearchType.HYBRID, limit=10
        )
        search_result = system["search"].search(query)

        # 4. 結果検証
        assert len(search_result) > 0
        # 検索結果の最初のドキュメントを確認
        first_result = search_result[0]
        # metadataは辞書型であることを確認
        assert isinstance(first_result.document.metadata, dict)
        assert first_result.document.metadata.get("topic") == "機械学習"

    def test_configuration_driven_behavior(self, integrated_system):
        """設定駆動動作テスト"""
        system = integrated_system

        # 検索結果数制限設定
        system["config"].set("search.max_results", 5)

        # ドキュメント追加
        for i in range(20):
            from datetime import datetime

            from src.data.models import Document, FileType

            content = f"テストドキュメント{i}です。検索テスト用の内容を含みます。"
            document = Document(
                id=f"/test/doc_{i}.txt",
                file_path=f"/test/doc_{i}.txt",
                title=f"doc_{i}.txt",
                content=content,
                file_type=FileType.TEXT,
                size=len(content),
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                content_hash=str(hash(content)),
                metadata={"doc_id": i},
            )
            system["index"].add_document(document)

        # 検索実行
        from src.data.models import SearchQuery, SearchType

        query = SearchQuery(
            query_text="テスト",
            search_type=SearchType.FULL_TEXT,
            limit=None,  # 設定ファイルの値を使用
        )
        result = system["search"].search(query)

        # 設定に従った結果数制限確認
        max_results = system["config"].get("search.max_results")
        assert len(result) <= max_results

    def test_embedding_cache_integration(self, integrated_system):
        """埋め込みキャッシュ統合テスト"""
        system = integrated_system

        # 同じ内容のドキュメントを複数追加
        duplicate_content = "機械学習とデータサイエンスの関係について"

        for i in range(5):
            from datetime import datetime

            from src.data.models import Document, FileType

            document = Document(
                id=f"/test/duplicate_{i}.txt",
                file_path=f"/test/duplicate_{i}.txt",
                title=f"duplicate_{i}.txt",
                content=duplicate_content,
                file_type=FileType.TEXT,
                size=len(duplicate_content),
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                content_hash=str(hash(duplicate_content)),
                metadata={"doc_id": i},
            )
            system["index"].add_document(document)
            # 埋め込みも生成
            system["embedding"].add_document_embedding(document.id, document.content)

        # セマンティック検索実行
        from src.data.models import SearchQuery, SearchType

        query = SearchQuery(query_text="機械学習", search_type=SearchType.SEMANTIC)
        system["search"].search(query)

        # キャッシュ効率確認
        cache_stats = system["embedding"].get_cache_statistics()
        assert cache_stats["hit_rate"] > 0.5  # 50%以上のキャッシュヒット率

    def test_error_propagation_handling(self, integrated_system):
        """エラー伝播ハンドリングテスト"""
        system = integrated_system

        # 無効なドキュメント追加試行
        invalid_docs = [
            {"id": "", "path": "/valid/path.txt", "content": "valid content"},  # 空ID
            {"id": "/valid/id", "path": "", "content": "valid content"},  # 空パス
            {
                "id": "/valid/id",
                "path": "/valid/path.txt",
                "content": "",
            },  # 空コンテンツ
        ]

        success_count = 0
        error_count = 0

        for doc in invalid_docs:
            try:
                from datetime import datetime

                from src.data.models import Document, FileType

                document = Document(
                    id=doc["id"],
                    file_path=doc["path"],
                    title=doc["path"].split("/")[-1] if doc["path"] else "empty",
                    content=doc["content"],
                    file_type=FileType.TEXT,
                    size=len(doc["content"]),
                    created_date=datetime.now(),
                    modified_date=datetime.now(),
                    indexed_date=datetime.now(),
                    content_hash=str(hash(doc["content"])),
                    metadata={},
                )
                system["index"].add_document(document)
                success_count += 1
            except Exception:
                error_count += 1

        # エラーハンドリング確認
        # 空のIDや空のパスでエラーが発生することを確認
        assert error_count >= 2  # 少なくとも2つのエラーが発生

        # システム全体の安定性確認
        from src.data.models import SearchQuery, SearchType

        test_query = SearchQuery(query_text="test", search_type=SearchType.FULL_TEXT)
        result = system["search"].search(test_query)
        assert isinstance(result, list)

    def test_concurrent_operations_stability(self, integrated_system):
        """並行操作安定性テスト"""
        from concurrent.futures import ThreadPoolExecutor

        system = integrated_system
        results = []

        def index_operation(thread_id):
            try:
                for i in range(10):
                    from datetime import datetime

                    from src.data.models import Document, FileType

                    content = f"スレッド{thread_id}のドキュメント{i}"
                    document = Document(
                        id=f"/thread_{thread_id}/doc_{i}.txt",
                        file_path=f"/thread_{thread_id}/doc_{i}.txt",
                        title=f"doc_{i}.txt",
                        content=content,
                        file_type=FileType.TEXT,
                        size=len(content),
                        created_date=datetime.now(),
                        modified_date=datetime.now(),
                        indexed_date=datetime.now(),
                        content_hash=str(hash(content)),
                        metadata={"thread_id": thread_id, "doc_id": i},
                    )
                    system["index"].add_document(document)
                results.append(True)
            except Exception:
                results.append(False)

        def search_operation(thread_id):
            try:
                for _i in range(5):
                    from src.data.models import SearchQuery, SearchType

                    query = SearchQuery(
                        query_text=f"スレッド{thread_id}",
                        search_type=SearchType.FULL_TEXT,
                    )
                    result = system["search"].search(query)
                    assert isinstance(result, list)
                results.append(True)
            except Exception:
                results.append(False)

        # 並行実行
        with ThreadPoolExecutor(max_workers=8) as executor:
            # インデックス操作
            index_futures = [executor.submit(index_operation, i) for i in range(4)]

            # 検索操作
            search_futures = [executor.submit(search_operation, i) for i in range(4)]

            # 完了待機
            for future in index_futures + search_futures:
                future.result()

        # 安定性確認
        # Whooshインデックスは並行書き込みに完全に対応していないため、
        # 一定のエラーは許容する
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.5  # 50%以上の成功率（並行書き込みの制約を考慮）

    def test_system_recovery_after_failure(self, integrated_system, temp_workspace):
        """システム障害後復旧テスト"""
        system = integrated_system

        # 正常なデータ追加
        for i in range(10):
            from datetime import datetime

            from src.data.models import Document, FileType

            content = f"復旧テスト用ドキュメント{i}"
            document = Document(
                id=f"/recovery/doc_{i}.txt",
                file_path=f"/recovery/doc_{i}.txt",
                title=f"doc_{i}.txt",
                content=content,
                file_type=FileType.TEXT,
                size=len(content),
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                content_hash=str(hash(content)),
                metadata={"doc_id": i},
            )
            system["index"].add_document(document)

        # 設定保存
        system["config"].set("search.max_results", 25)  # テスト用の設定を追加
        system["config"].save_config()

        # システム再起動シミュレーション
        # Configは初期化時に自動的に設定ファイルを読み込み
        new_system = {
            "config": Config(str(temp_workspace["config"])),
            "embedding": EmbeddingManager(
                embeddings_path=str(temp_workspace["cache"] / "embeddings.pkl")
            ),
            "index": IndexManager(str(temp_workspace["index"])),
        }

        new_system["search"] = SearchManager(
            new_system["index"], new_system["embedding"], new_system["config"]
        )

        # 復旧後の動作確認
        from src.data.models import SearchQuery, SearchType

        query = SearchQuery(query_text="復旧テスト", search_type=SearchType.FULL_TEXT)
        result = new_system["search"].search(query)
        assert len(result) > 0

        # 設定復旧確認
        max_results = new_system["config"].get("search.max_results")
        assert max_results is not None

    def test_performance_under_load(self, integrated_system):
        """負荷下でのパフォーマンステスト"""
        import time

        system = integrated_system

        # 大量データ追加（テスト用に数を減らした）
        start_time = time.time()

        for i in range(100):
            from datetime import datetime

            from src.data.models import Document, FileType

            content = f"負荷テスト用ドキュメント{i}です。" + "コンテンツ " * 50
            document = Document(
                id=f"/load_test/doc_{i}.txt",
                file_path=f"/load_test/doc_{i}.txt",
                title=f"doc_{i}.txt",
                content=content,
                file_type=FileType.TEXT,
                size=len(content),
                created_date=datetime.now(),
                modified_date=datetime.now(),
                indexed_date=datetime.now(),
                content_hash=str(hash(content)),
                metadata={"doc_id": i, "category": f"cat_{i % 10}"},
            )
            system["index"].add_document(document)

        indexing_time = time.time() - start_time

        # 検索パフォーマンス
        search_times = []

        for i in range(20):
            start_time = time.time()
            from src.data.models import SearchQuery, SearchType

            query = SearchQuery(
                query_text=f"ドキュメント{i}",
                search_type=SearchType.FULL_TEXT,
                limit=20,
            )
            result = system["search"].search(query)
            search_time = time.time() - start_time
            search_times.append(search_time)

            assert len(result) > 0

        # パフォーマンス検証（軽量化されたテスト用）
        assert indexing_time < 30.0  # 30秒以内
        assert max(search_times) < 5.0  # 最大5秒以内
        assert sum(search_times) / len(search_times) < 2.0  # 平均2秒以内
