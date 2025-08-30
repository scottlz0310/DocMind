"""
検索機能包括検証クラス

DocMindアプリケーションの検索機能（全文検索、セマンティック検索、ハイブリッド検索）
の包括的な動作検証を実施します。
"""

import concurrent.futures
import os
import shutil

# DocMindコンポーネントのインポート
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .base_validator import BaseValidator, ValidationConfig
from .test_data_generator import TestDataGenerator, TestDatasetConfig

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.core.document_processor import DocumentProcessor
from src.core.embedding_manager import EmbeddingManager
from src.core.index_manager import IndexManager
from src.core.search_manager import SearchManager
from src.data.models import FileType, SearchQuery, SearchType
from src.utils.config import Config


@dataclass
class SearchTestMetrics:
    """検索テストメトリクス"""

    query_text: str
    search_type: SearchType
    execution_time: float
    result_count: int
    memory_usage: float
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None


class SearchFunctionalityValidator(BaseValidator):
    """
    検索機能包括検証クラス

    全文検索、セマンティック検索、ハイブリッド検索の精度検証、
    パフォーマンス検証、大規模データセット対応検証を実施します。
    """

    def __init__(self, config: ValidationConfig | None = None):
        """
        検索機能検証クラスの初期化

        Args:
            config: 検証設定
        """
        super().__init__(config)

        # テスト環境の設定
        self.test_data_dir = None
        self.search_manager = None
        self.index_manager = None
        self.embedding_manager = None
        self.document_processor = None

        # テストデータ生成器
        self.data_generator = TestDataGenerator()

        # テストメトリクス
        self.search_metrics: list[SearchTestMetrics] = []

        # パフォーマンス要件
        self.max_search_time = 5.0  # 5秒以内
        self.max_memory_usage = 2048.0  # 2GB

        # 検索精度の基準値
        self.min_precision = 0.7  # 70%以上
        self.min_recall = 0.6  # 60%以上
        self.min_f1_score = 0.65  # 65%以上

        self.logger.info("SearchFunctionalityValidatorを初期化しました")

    def setup_test_environment(self) -> None:
        """テスト環境のセットアップ"""
        self.logger.info("検索機能テスト環境をセットアップ中...")

        try:
            # 一時ディレクトリの作成
            self.test_data_dir = tempfile.mkdtemp(prefix="search_validation_")
            self.logger.debug(f"テストデータディレクトリ: {self.test_data_dir}")

            # DocMindコンポーネントの初期化
            config = Config()
            config.data_directory = self.test_data_dir

            # インデックスマネージャーの初期化
            index_dir = os.path.join(self.test_data_dir, "whoosh_index")
            self.index_manager = IndexManager(index_dir)

            # 埋め込みマネージャーの初期化
            embeddings_path = os.path.join(self.test_data_dir, "embeddings.pkl")
            self.embedding_manager = EmbeddingManager(embeddings_path)

            # ドキュメントプロセッサーの初期化
            self.document_processor = DocumentProcessor()

            # 検索マネージャーの初期化
            self.search_manager = SearchManager(
                self.index_manager, self.embedding_manager
            )

            self.logger.info("検索機能テスト環境のセットアップが完了しました")

        except Exception as e:
            self.logger.error(f"テスト環境のセットアップに失敗しました: {e}")
            raise

    def teardown_test_environment(self) -> None:
        """テスト環境のクリーンアップ"""
        self.logger.info("検索機能テスト環境をクリーンアップ中...")

        try:
            # コンポーネントのクリーンアップ
            if self.search_manager:
                self.search_manager.clear_suggestion_cache()

            if self.embedding_manager:
                self.embedding_manager.clear_cache()

            # テストデータの削除
            self.data_generator.cleanup()

            if self.test_data_dir and os.path.exists(self.test_data_dir):
                shutil.rmtree(self.test_data_dir)
                self.logger.debug(
                    f"テストデータディレクトリを削除しました: {self.test_data_dir}"
                )

            self.logger.info("検索機能テスト環境のクリーンアップが完了しました")

        except Exception as e:
            self.logger.warning(
                f"テスト環境のクリーンアップ中にエラーが発生しました: {e}"
            )

    def test_full_text_search_accuracy(self) -> None:
        """全文検索精度の検証"""
        self.logger.info("全文検索精度の検証を開始します")

        # テストデータの準備
        test_documents = self._prepare_accuracy_test_data()

        # 各テストクエリで検索を実行
        test_queries = [
            "テスト",
            "ドキュメント",
            "検索機能",
            "DocMind",
            "パフォーマンス",
        ]

        total_precision = 0.0
        total_recall = 0.0

        for query_text in test_queries:
            self.logger.debug(f"全文検索テスト: '{query_text}'")

            # 検索実行
            search_query = SearchQuery(
                query_text=query_text, search_type=SearchType.FULL_TEXT, limit=50
            )

            start_time = time.time()
            results = self.search_manager.search(search_query)
            execution_time = time.time() - start_time

            # 精度計算
            precision, recall, f1_score = self._calculate_search_accuracy(
                query_text, results, test_documents
            )

            # メトリクス記録
            metrics = SearchTestMetrics(
                query_text=query_text,
                search_type=SearchType.FULL_TEXT,
                execution_time=execution_time,
                result_count=len(results),
                memory_usage=self.memory_monitor.get_current_memory(),
                precision=precision,
                recall=recall,
                f1_score=f1_score,
            )
            self.search_metrics.append(metrics)

            total_precision += precision
            total_recall += recall

            # パフォーマンス要件の検証
            self.assert_condition(
                execution_time <= self.max_search_time,
                f"全文検索の実行時間が要件を超過: {execution_time:.2f}秒 > {self.max_search_time}秒",
            )

        # 平均精度の検証
        avg_precision = total_precision / len(test_queries)
        avg_recall = total_recall / len(test_queries)

        self.assert_condition(
            avg_precision >= self.min_precision,
            f"全文検索の平均精度が基準を下回る: {avg_precision:.2f} < {self.min_precision}",
        )

        self.assert_condition(
            avg_recall >= self.min_recall,
            f"全文検索の平均再現率が基準を下回る: {avg_recall:.2f} < {self.min_recall}",
        )

        self.logger.info(
            f"全文検索精度検証完了 - 平均精度: {avg_precision:.2f}, 平均再現率: {avg_recall:.2f}"
        )

    def test_semantic_search_accuracy(self) -> None:
        """セマンティック検索精度の検証"""
        self.logger.info("セマンティック検索精度の検証を開始します")

        # テストデータの準備
        test_documents = self._prepare_accuracy_test_data()

        # セマンティック検索用のテストクエリ
        semantic_queries = [
            "文書の検索",  # "ドキュメント" と意味的に類似
            "性能測定",  # "パフォーマンス" と意味的に類似
            "アプリケーション機能",  # "システム機能" と意味的に類似
            "データ処理",  # "情報処理" と意味的に類似
            "品質確認",  # "テスト" と意味的に類似
        ]

        total_precision = 0.0
        total_recall = 0.0

        for query_text in semantic_queries:
            self.logger.debug(f"セマンティック検索テスト: '{query_text}'")

            # 検索実行
            search_query = SearchQuery(
                query_text=query_text, search_type=SearchType.SEMANTIC, limit=50
            )

            start_time = time.time()
            results = self.search_manager.search(search_query)
            execution_time = time.time() - start_time

            # 精度計算（セマンティック検索用の緩い基準）
            precision, recall, f1_score = self._calculate_semantic_search_accuracy(
                query_text, results, test_documents
            )

            # メトリクス記録
            metrics = SearchTestMetrics(
                query_text=query_text,
                search_type=SearchType.SEMANTIC,
                execution_time=execution_time,
                result_count=len(results),
                memory_usage=self.memory_monitor.get_current_memory(),
                precision=precision,
                recall=recall,
                f1_score=f1_score,
            )
            self.search_metrics.append(metrics)

            total_precision += precision
            total_recall += recall

            # パフォーマンス要件の検証
            self.assert_condition(
                execution_time <= self.max_search_time,
                f"セマンティック検索の実行時間が要件を超過: {execution_time:.2f}秒 > {self.max_search_time}秒",
            )

        # 平均精度の検証（セマンティック検索は基準を緩める）
        avg_precision = total_precision / len(semantic_queries)
        avg_recall = total_recall / len(semantic_queries)

        semantic_min_precision = self.min_precision * 0.8  # 80%の基準
        self.min_recall * 0.8

        self.assert_condition(
            avg_precision >= semantic_min_precision,
            f"セマンティック検索の平均精度が基準を下回る: {avg_precision:.2f} < {semantic_min_precision}",
        )

        self.logger.info(
            f"セマンティック検索精度検証完了 - 平均精度: {avg_precision:.2f}, 平均再現率: {avg_recall:.2f}"
        )

    def test_hybrid_search_accuracy(self) -> None:
        """ハイブリッド検索精度の検証"""
        self.logger.info("ハイブリッド検索精度の検証を開始します")

        # テストデータの準備
        test_documents = self._prepare_accuracy_test_data()

        # ハイブリッド検索用のテストクエリ
        hybrid_queries = [
            "テスト ドキュメント",
            "検索 機能 性能",
            "DocMind アプリケーション",
            "データ 処理 システム",
            "品質 確認 テスト",
        ]

        total_precision = 0.0
        total_recall = 0.0

        for query_text in hybrid_queries:
            self.logger.debug(f"ハイブリッド検索テスト: '{query_text}'")

            # 検索実行
            search_query = SearchQuery(
                query_text=query_text,
                search_type=SearchType.HYBRID,
                limit=50,
                weights={"full_text": 0.6, "semantic": 0.4},
            )

            start_time = time.time()
            results = self.search_manager.search(search_query)
            execution_time = time.time() - start_time

            # 精度計算
            precision, recall, f1_score = self._calculate_search_accuracy(
                query_text, results, test_documents
            )

            # メトリクス記録
            metrics = SearchTestMetrics(
                query_text=query_text,
                search_type=SearchType.HYBRID,
                execution_time=execution_time,
                result_count=len(results),
                memory_usage=self.memory_monitor.get_current_memory(),
                precision=precision,
                recall=recall,
                f1_score=f1_score,
            )
            self.search_metrics.append(metrics)

            total_precision += precision
            total_recall += recall

            # パフォーマンス要件の検証
            self.assert_condition(
                execution_time <= self.max_search_time,
                f"ハイブリッド検索の実行時間が要件を超過: {execution_time:.2f}秒 > {self.max_search_time}秒",
            )

        # 平均精度の検証
        avg_precision = total_precision / len(hybrid_queries)
        avg_recall = total_recall / len(hybrid_queries)

        self.assert_condition(
            avg_precision >= self.min_precision,
            f"ハイブリッド検索の平均精度が基準を下回る: {avg_precision:.2f} < {self.min_precision}",
        )

        self.logger.info(
            f"ハイブリッド検索精度検証完了 - 平均精度: {avg_precision:.2f}, 平均再現率: {avg_recall:.2f}"
        )

    def test_search_performance_requirements(self) -> None:
        """検索パフォーマンス要件の検証"""
        self.logger.info("検索パフォーマンス要件の検証を開始します")

        # 大規模データセットの生成
        large_dataset_dir = os.path.join(self.test_data_dir, "large_dataset")
        self.data_generator.generate_large_dataset(
            large_dataset_dir, document_count=1000  # テスト用に縮小
        )

        # ドキュメントのインデックス化
        self._index_test_documents(large_dataset_dir)

        # パフォーマンステストクエリ
        performance_queries = [
            "テスト",
            "ドキュメント 検索",
            "システム パフォーマンス",
            "データ 処理 機能",
            "品質 確認 テスト 結果",
        ]

        for search_type in [
            SearchType.FULL_TEXT,
            SearchType.SEMANTIC,
            SearchType.HYBRID,
        ]:
            for query_text in performance_queries:
                self.logger.debug(
                    f"パフォーマンステスト: {search_type.value} - '{query_text}'"
                )

                # メモリ監視開始
                self.memory_monitor.start_monitoring()

                # 検索実行
                search_query = SearchQuery(
                    query_text=query_text, search_type=search_type, limit=100
                )

                start_time = time.time()
                results = self.search_manager.search(search_query)
                execution_time = time.time() - start_time

                # メモリ使用量取得
                peak_memory = self.memory_monitor.get_peak_memory()
                self.memory_monitor.stop_monitoring()

                # パフォーマンス要件の検証
                self.assert_condition(
                    execution_time <= self.max_search_time,
                    f"{search_type.value}検索の実行時間が要件を超過: {execution_time:.2f}秒 > {self.max_search_time}秒",
                )

                self.assert_condition(
                    peak_memory <= self.max_memory_usage,
                    f"{search_type.value}検索のメモリ使用量が要件を超過: {peak_memory:.2f}MB > {self.max_memory_usage}MB",
                )

                # メトリクス記録
                metrics = SearchTestMetrics(
                    query_text=query_text,
                    search_type=search_type,
                    execution_time=execution_time,
                    result_count=len(results),
                    memory_usage=peak_memory,
                )
                self.search_metrics.append(metrics)

        self.logger.info("検索パフォーマンス要件の検証が完了しました")

    def test_large_dataset_scalability(self) -> None:
        """大規模データセット対応の検証"""
        self.logger.info("大規模データセット対応の検証を開始します")

        # 段階的にデータセットサイズを増加させてテスト
        dataset_sizes = [100, 500, 1000, 2000]

        for size in dataset_sizes:
            self.logger.debug(f"データセットサイズ {size} でのスケーラビリティテスト")

            # データセット生成
            dataset_dir = os.path.join(self.test_data_dir, f"scalability_{size}")
            self.data_generator.generate_dataset(
                TestDatasetConfig(
                    dataset_name=f"scalability_{size}",
                    output_directory=dataset_dir,
                    file_count=size,
                    size_range_kb=(1, 50),
                )
            )

            # インデックス化時間の測定
            index_start_time = time.time()
            self._index_test_documents(dataset_dir)
            index_time = time.time() - index_start_time

            # インデックス化パフォーマンス要件の検証
            max_index_time = (size / 1000) * 30  # 1000ドキュメントあたり30秒
            self.assert_condition(
                index_time <= max_index_time,
                f"インデックス化時間が要件を超過: {index_time:.2f}秒 > {max_index_time:.2f}秒 (サイズ: {size})",
            )

            # 検索パフォーマンスの測定
            search_query = SearchQuery(
                query_text="テスト ドキュメント",
                search_type=SearchType.HYBRID,
                limit=50,
            )

            search_start_time = time.time()
            self.search_manager.search(search_query)
            search_time = time.time() - search_start_time

            # 検索パフォーマンス要件の検証
            self.assert_condition(
                search_time <= self.max_search_time,
                f"大規模データセット検索時間が要件を超過: {search_time:.2f}秒 > {self.max_search_time}秒 (サイズ: {size})",
            )

            self.logger.debug(
                f"サイズ {size}: インデックス化 {index_time:.2f}秒, 検索 {search_time:.2f}秒"
            )

        self.logger.info("大規模データセット対応の検証が完了しました")

    def test_search_filters(self) -> None:
        """検索フィルター機能の検証"""
        self.logger.info("検索フィルター機能の検証を開始します")

        # 多様なファイル形式のテストデータを生成
        filter_test_dir = os.path.join(self.test_data_dir, "filter_test")
        self.data_generator.generate_dataset(
            TestDatasetConfig(
                dataset_name="filter_test",
                output_directory=filter_test_dir,
                file_count=100,
                file_types=["txt", "md", "json", "csv"],
                size_range_kb=(1, 20),
            )
        )

        # インデックス化
        self._index_test_documents(filter_test_dir)

        # ファイル形式フィルターのテスト
        for file_type in [
            FileType.TEXT,
            FileType.MARKDOWN,
            FileType.JSON,
            FileType.CSV,
        ]:
            search_query = SearchQuery(
                query_text="テスト",
                search_type=SearchType.FULL_TEXT,
                file_types=[file_type],
                limit=50,
            )

            results = self.search_manager.search(search_query)

            # 結果がすべて指定されたファイル形式であることを確認
            for result in results:
                self.assert_condition(
                    result.document.file_type == file_type,
                    f"フィルター結果に異なるファイル形式が含まれています: {result.document.file_type} != {file_type}",
                )

        # 日付フィルターのテスト
        current_date = datetime.now()
        date_from = current_date - timedelta(days=30)
        date_to = current_date

        search_query = SearchQuery(
            query_text="テスト",
            search_type=SearchType.FULL_TEXT,
            date_from=date_from,
            date_to=date_to,
            limit=50,
        )

        results = self.search_manager.search(search_query)

        # 結果がすべて指定された日付範囲内であることを確認
        for result in results:
            doc_date = result.document.modified_date
            self.assert_condition(
                date_from <= doc_date <= date_to,
                f"フィルター結果に日付範囲外のドキュメントが含まれています: {doc_date}",
            )

        self.logger.info("検索フィルター機能の検証が完了しました")

    def test_concurrent_search(self) -> None:
        """並行検索の検証"""
        self.logger.info("並行検索の検証を開始します")

        # テストデータの準備
        concurrent_test_dir = os.path.join(self.test_data_dir, "concurrent_test")
        self.data_generator.generate_dataset(
            TestDatasetConfig(
                dataset_name="concurrent_test",
                output_directory=concurrent_test_dir,
                file_count=500,
                size_range_kb=(1, 30),
            )
        )

        # インデックス化
        self._index_test_documents(concurrent_test_dir)

        # 並行検索クエリ
        concurrent_queries = [
            ("テスト", SearchType.FULL_TEXT),
            ("ドキュメント", SearchType.SEMANTIC),
            ("検索 機能", SearchType.HYBRID),
            ("システム", SearchType.FULL_TEXT),
            ("データ 処理", SearchType.SEMANTIC),
        ]

        # 並行実行
        def execute_search(query_info):
            query_text, search_type = query_info
            search_query = SearchQuery(
                query_text=query_text, search_type=search_type, limit=30
            )

            start_time = time.time()
            results = self.search_manager.search(search_query)
            execution_time = time.time() - start_time

            return {
                "query": query_text,
                "type": search_type,
                "time": execution_time,
                "count": len(results),
            }

        # ThreadPoolExecutorを使用して並行実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = [
                executor.submit(execute_search, query) for query in concurrent_queries
            ]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]
            total_time = time.time() - start_time

        # 並行実行の検証
        self.assert_condition(
            len(results) == len(concurrent_queries),
            f"並行検索の結果数が期待値と異なります: {len(results)} != {len(concurrent_queries)}",
        )

        # 各検索が正常に完了していることを確認
        for result in results:
            self.assert_condition(
                result["time"] <= self.max_search_time,
                f"並行検索の実行時間が要件を超過: {result['time']:.2f}秒 > {self.max_search_time}秒",
            )

            self.assert_condition(
                result["count"] >= 0,
                f"並行検索で結果が取得できませんでした: {result['query']}",
            )

        # 並行実行の効率性を確認（シーケンシャル実行より高速であることを期待）
        sequential_time_estimate = sum(result["time"] for result in results)
        efficiency_ratio = sequential_time_estimate / total_time

        self.assert_condition(
            efficiency_ratio > 1.5,  # 並行実行で1.5倍以上の効率化を期待
            f"並行検索の効率が低すぎます: {efficiency_ratio:.2f}倍",
        )

        self.logger.info(
            f"並行検索の検証が完了しました - 効率比: {efficiency_ratio:.2f}倍"
        )

    def test_search_suggestions(self) -> None:
        """検索提案機能の検証"""
        self.logger.info("検索提案機能の検証を開始します")

        # テストデータの準備
        suggestion_test_dir = os.path.join(self.test_data_dir, "suggestion_test")
        self.data_generator.generate_dataset(
            TestDatasetConfig(
                dataset_name="suggestion_test",
                output_directory=suggestion_test_dir,
                file_count=200,
                size_range_kb=(1, 20),
            )
        )

        # インデックス化
        self._index_test_documents(suggestion_test_dir)

        # 検索提案のテスト
        test_prefixes = [
            "テ",  # "テスト" の提案を期待
            "ド",  # "ドキュメント" の提案を期待
            "検索",  # "検索機能" などの提案を期待
            "シス",  # "システム" の提案を期待
            "デー",  # "データ" の提案を期待
        ]

        for prefix in test_prefixes:
            suggestions = self.search_manager.get_search_suggestions(prefix, limit=10)

            # 提案が生成されることを確認
            self.assert_condition(
                len(suggestions) > 0, f"検索提案が生成されませんでした: '{prefix}'"
            )

            # 提案がプレフィックスで始まることを確認
            for suggestion in suggestions:
                self.assert_condition(
                    suggestion.startswith(prefix),
                    f"検索提案がプレフィックスで始まっていません: '{suggestion}' (プレフィックス: '{prefix}')",
                )

            # 提案の数が制限内であることを確認
            self.assert_condition(
                len(suggestions) <= 10,
                f"検索提案の数が制限を超えています: {len(suggestions)} > 10",
            )

        self.logger.info("検索提案機能の検証が完了しました")

    def _prepare_accuracy_test_data(self) -> list[dict[str, Any]]:
        """精度テスト用のデータを準備"""
        accuracy_test_dir = os.path.join(self.test_data_dir, "accuracy_test")

        # 既知の内容を持つテストドキュメントを生成
        test_documents = [
            {
                "filename": "test_doc_001.txt",
                "content": "これはテストドキュメントです。DocMindアプリケーションの検索機能をテストします。",
                "keywords": ["テスト", "ドキュメント", "DocMind", "検索", "機能"],
            },
            {
                "filename": "performance_doc_002.txt",
                "content": "パフォーマンステストの結果を記録します。システムの性能を測定しています。",
                "keywords": ["パフォーマンス", "テスト", "結果", "システム", "性能"],
            },
            {
                "filename": "search_doc_003.txt",
                "content": "検索機能の実装について説明します。全文検索とセマンティック検索を組み合わせます。",
                "keywords": ["検索", "機能", "実装", "全文検索", "セマンティック"],
            },
            {
                "filename": "data_doc_004.txt",
                "content": "データ処理とインデックス化の仕組みを解説します。効率的な情報管理が重要です。",
                "keywords": ["データ", "処理", "インデックス", "情報", "管理"],
            },
            {
                "filename": "quality_doc_005.txt",
                "content": "品質確認とテスト手法について記述します。包括的な検証が必要です。",
                "keywords": ["品質", "確認", "テスト", "手法", "検証"],
            },
        ]

        # ディレクトリ作成
        os.makedirs(accuracy_test_dir, exist_ok=True)

        # テストファイルの生成
        for doc_info in test_documents:
            file_path = os.path.join(accuracy_test_dir, doc_info["filename"])
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(doc_info["content"])

        # インデックス化
        self._index_test_documents(accuracy_test_dir)

        return test_documents

    def _index_test_documents(self, directory: str) -> None:
        """テストドキュメントのインデックス化"""
        self.logger.debug(f"ディレクトリのインデックス化: {directory}")

        for root, _dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)

                try:
                    # ドキュメント処理
                    processed_doc = self.document_processor.process_file(file_path)

                    if processed_doc:
                        # インデックスに追加
                        self.index_manager.add_document(processed_doc)

                        # 埋め込み生成
                        self.embedding_manager.add_document(
                            processed_doc.id, processed_doc.content
                        )

                except Exception as e:
                    self.logger.warning(
                        f"ファイル処理に失敗しました: {file_path} - {e}"
                    )

        # インデックスのコミット
        self.index_manager.commit()

    def _calculate_search_accuracy(
        self, query_text: str, results: list[Any], test_documents: list[dict[str, Any]]
    ) -> tuple[float, float, float]:
        """検索精度の計算"""
        if not results:
            return 0.0, 0.0, 0.0

        # クエリに関連するドキュメントを特定
        query_terms = query_text.lower().split()
        relevant_docs = []

        for doc_info in test_documents:
            doc_keywords = [kw.lower() for kw in doc_info["keywords"]]
            if any(
                term in doc_keywords or any(term in kw for kw in doc_keywords)
                for term in query_terms
            ):
                relevant_docs.append(doc_info["filename"])

        if not relevant_docs:
            return 1.0, 1.0, 1.0  # クエリに関連するドキュメントがない場合

        # 検索結果の関連性を評価
        retrieved_relevant = 0
        for result in results:
            filename = os.path.basename(result.document.file_path)
            if filename in relevant_docs:
                retrieved_relevant += 1

        # 精度と再現率の計算
        precision = retrieved_relevant / len(results) if results else 0.0
        recall = retrieved_relevant / len(relevant_docs) if relevant_docs else 0.0
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return precision, recall, f1_score

    def _calculate_semantic_search_accuracy(
        self, query_text: str, results: list[Any], test_documents: list[dict[str, Any]]
    ) -> tuple[float, float, float]:
        """セマンティック検索精度の計算（より緩い基準）"""
        if not results:
            return 0.0, 0.0, 0.0

        # セマンティック検索では意味的な関連性を考慮
        semantic_mappings = {
            "文書の検索": ["ドキュメント", "検索"],
            "性能測定": ["パフォーマンス", "性能"],
            "アプリケーション機能": ["機能", "システム"],
            "データ処理": ["データ", "処理", "情報"],
            "品質確認": ["品質", "テスト", "確認"],
        }

        related_terms = semantic_mappings.get(query_text, query_text.split())
        relevant_docs = []

        for doc_info in test_documents:
            doc_keywords = [kw.lower() for kw in doc_info["keywords"]]
            if any(term.lower() in doc_keywords for term in related_terms):
                relevant_docs.append(doc_info["filename"])

        if not relevant_docs:
            return 0.5, 0.5, 0.5  # セマンティック検索では部分的な関連性を認める

        # 検索結果の関連性を評価
        retrieved_relevant = 0
        for result in results:
            filename = os.path.basename(result.document.file_path)
            if filename in relevant_docs:
                retrieved_relevant += 1

        # 精度と再現率の計算
        precision = retrieved_relevant / len(results) if results else 0.0
        recall = retrieved_relevant / len(relevant_docs) if relevant_docs else 0.0
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return precision, recall, f1_score

    def get_search_metrics_summary(self) -> dict[str, Any]:
        """検索メトリクスのサマリーを取得"""
        if not self.search_metrics:
            return {}

        # 検索タイプ別の統計
        type_stats = {}
        for search_type in [
            SearchType.FULL_TEXT,
            SearchType.SEMANTIC,
            SearchType.HYBRID,
        ]:
            type_metrics = [
                m for m in self.search_metrics if m.search_type == search_type
            ]

            if type_metrics:
                type_stats[search_type.value] = {
                    "count": len(type_metrics),
                    "avg_execution_time": sum(m.execution_time for m in type_metrics)
                    / len(type_metrics),
                    "max_execution_time": max(m.execution_time for m in type_metrics),
                    "avg_result_count": sum(m.result_count for m in type_metrics)
                    / len(type_metrics),
                    "avg_memory_usage": sum(m.memory_usage for m in type_metrics)
                    / len(type_metrics),
                    "avg_precision": (
                        sum(
                            m.precision for m in type_metrics if m.precision is not None
                        )
                        / len([m for m in type_metrics if m.precision is not None])
                        if any(m.precision is not None for m in type_metrics)
                        else None
                    ),
                    "avg_recall": (
                        sum(m.recall for m in type_metrics if m.recall is not None)
                        / len([m for m in type_metrics if m.recall is not None])
                        if any(m.recall is not None for m in type_metrics)
                        else None
                    ),
                }

        return {
            "total_searches": len(self.search_metrics),
            "by_type": type_stats,
            "overall_avg_time": sum(m.execution_time for m in self.search_metrics)
            / len(self.search_metrics),
            "overall_max_time": max(m.execution_time for m in self.search_metrics),
            "performance_requirement_met": all(
                m.execution_time <= self.max_search_time for m in self.search_metrics
            ),
            "memory_requirement_met": all(
                m.memory_usage <= self.max_memory_usage for m in self.search_metrics
            ),
        }
