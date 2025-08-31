"""
SearchManager - ハイブリッド検索マネージャー

このモジュールは、全文検索とセマンティック検索を組み合わせたハイブリッド検索機能を提供します。
検索結果のランキング、マージ、スニペット生成、検索提案機能を含みます。
"""

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..data.models import Document, FileType, SearchQuery, SearchResult, SearchType
from ..utils.background_processor import TaskPriority, get_global_task_manager
from ..utils.cache_manager import get_global_cache_manager
from ..utils.error_handler import get_global_error_handler, handle_exceptions
from ..utils.exceptions import SearchError
from ..utils.graceful_degradation import (
    get_global_degradation_manager,
    with_graceful_degradation,
)
from ..utils.logging_config import LoggerMixin
from .embedding_manager import EmbeddingManager
from .index_manager import IndexManager


@dataclass
class SearchWeights:
    """検索重み設定を管理するデータクラス"""

    full_text: float = 0.6  # 全文検索の重み
    semantic: float = 0.4  # セマンティック検索の重み

    def __post_init__(self):
        """重みの合計が1.0になるように正規化"""
        total = self.full_text + self.semantic
        if total > 0:
            self.full_text /= total
            self.semantic /= total


class SearchManager(LoggerMixin):
    """
    ハイブリッド検索マネージャークラス

    全文検索とセマンティック検索を組み合わせ、統合された検索結果を提供します。
    検索結果のランキング、マージ、スニペット生成機能を含みます。
    エラーハンドリングと優雅な劣化機能を統合しています。
    """

    def __init__(
        self,
        index_manager: IndexManager,
        embedding_manager: EmbeddingManager,
        config=None,
    ):
        """
        SearchManagerを初期化

        Args:
            index_manager: 全文検索を担当するIndexManager
            embedding_manager: セマンティック検索を担当するEmbeddingManager
            config: 設定オブジェクト（オプション）
        """
        self.index_manager = index_manager
        self.embedding_manager = embedding_manager
        self.config = config

        # デフォルト検索設定
        self.default_weights = SearchWeights()
        self.min_semantic_similarity = 0.1  # セマンティック検索の最小類似度
        self.snippet_max_length = 200  # スニペットの最大長

        # 検索提案用のキャッシュ
        self._suggestion_cache: dict[str, list[str]] = {}
        self._indexed_terms: set[str] = set()

        # キャッシュマネージャーとタスクマネージャーを取得
        self._cache_manager = get_global_cache_manager()
        self._task_manager = get_global_task_manager()

        # エラーハンドリングと劣化管理の設定
        self._setup_error_handling()

        self.logger.info("SearchManagerを初期化しました")

    def _setup_error_handling(self):
        """エラーハンドリングと劣化管理を設定"""
        degradation_manager = get_global_degradation_manager()
        error_handler = get_global_error_handler()

        # 回復ハンドラーを登録
        def search_recovery_handler(exc: Exception, error_info: dict[str, Any]) -> bool:
            """検索エラーからの回復処理"""
            try:
                self.logger.info("検索機能の回復を試行中...")

                # キャッシュをクリア
                self.clear_suggestion_cache()

                # インデックスマネージャーの状態をチェック
                if (
                    hasattr(self.index_manager, "is_healthy")
                    and not self.index_manager.is_healthy()
                ):
                    self.logger.warning("インデックスマネージャーが不健全な状態です")
                    degradation_manager.mark_component_degraded(
                        "search_manager",
                        ["full_text_search", "hybrid_search"],
                        "インデックスマネージャーの問題により全文検索が無効化されました",
                    )

                # 埋め込みマネージャーの状態をチェック
                if (
                    hasattr(self.embedding_manager, "is_healthy")
                    and not self.embedding_manager.is_healthy()
                ):
                    self.logger.warning("埋め込みマネージャーが不健全な状態です")
                    degradation_manager.mark_component_degraded(
                        "search_manager",
                        ["semantic_search", "hybrid_search"],
                        "埋め込みマネージャーの問題によりセマンティック検索が無効化されました",
                    )

                return True
            except Exception as recovery_exc:
                self.logger.error(f"検索機能の回復に失敗: {recovery_exc}")
                return False

        error_handler.register_recovery_handler(SearchError, search_recovery_handler)

    @handle_exceptions(
        context="検索実行",
        user_message="検索中にエラーが発生しました。検索条件を変更して再試行してください。",
        attempt_recovery=True,
        reraise=True,
    )
    def search(self, query: SearchQuery) -> list[SearchResult]:
        """
        統合検索を実行（キャッシュ機能付き）

        Args:
            query: 検索クエリオブジェクト

        Returns:
            検索結果のリスト（関連度順）

        Raises:
            SearchError: 検索実行に失敗した場合
        """
        degradation_manager = get_global_degradation_manager()

        self.logger.info(
            f"検索開始: '{query.query_text}' (タイプ: {query.search_type.value})"
        )

        # キャッシュから結果を取得を試行
        filters = {
            "file_types": (
                [ft.value for ft in query.file_types] if query.file_types else None
            ),
            "date_from": query.date_from.isoformat() if query.date_from else None,
            "date_to": query.date_to.isoformat() if query.date_to else None,
            "folder_paths": query.folder_paths,
            "limit": query.limit,
            "weights": query.weights,
        }

        cached_results = self._cache_manager.search_cache.get_search_results(
            query.query_text, query.search_type.value, filters
        )

        if cached_results is not None:
            self.logger.debug(f"キャッシュから検索結果を取得: {len(cached_results)}件")
            return cached_results

        # キャッシュにない場合は検索を実行
        results = self._execute_search(query, degradation_manager)

        # 結果をキャッシュに保存
        self._cache_manager.search_cache.cache_search_results(
            query.query_text, query.search_type.value, results, filters
        )

        self.logger.info(f"検索完了: {len(results)}件の結果")
        return results

    def _execute_search(
        self, query: SearchQuery, degradation_manager
    ) -> list[SearchResult]:
        """実際の検索処理を実行"""
        # 検索タイプに応じて機能の可用性をチェック
        if query.search_type == SearchType.FULL_TEXT:
            if not degradation_manager.is_capability_available(
                "search_manager", "full_text_search"
            ):
                raise SearchError("全文検索機能は現在利用できません")
            results = self._full_text_search(query)
        elif query.search_type == SearchType.SEMANTIC:
            if not degradation_manager.is_capability_available(
                "search_manager", "semantic_search"
            ):
                raise SearchError("セマンティック検索機能は現在利用できません")
            results = self._semantic_search(query)
        elif query.search_type == SearchType.HYBRID:
            if not degradation_manager.is_capability_available(
                "search_manager", "hybrid_search"
            ):
                # ハイブリッド検索が利用できない場合、利用可能な検索にフォールバック
                if degradation_manager.is_capability_available(
                    "search_manager", "full_text_search"
                ):
                    self.logger.warning(
                        "ハイブリッド検索が利用できないため、全文検索にフォールバック"
                    )
                    query.search_type = SearchType.FULL_TEXT
                    results = self._full_text_search(query)
                elif degradation_manager.is_capability_available(
                    "search_manager", "semantic_search"
                ):
                    self.logger.warning(
                        "ハイブリッド検索が利用できないため、セマンティック検索にフォールバック"
                    )
                    query.search_type = SearchType.SEMANTIC
                    results = self._semantic_search(query)
                else:
                    raise SearchError("検索機能は現在利用できません")
            else:
                results = self._hybrid_search(query)
        else:
            raise SearchError(f"サポートされていない検索タイプ: {query.search_type}")

        # 結果の後処理
        results = self._post_process_results(results, query)
        return results

    @with_graceful_degradation(
        "search_manager",
        disable_capabilities=["full_text_search", "hybrid_search"],
        fallback_return=[],
    )
    def _full_text_search(self, query: SearchQuery) -> list[SearchResult]:
        """全文検索を実行"""
        try:
            # limitが指定されていない場合は設定から取得
            limit = query.limit
            if limit is None and self.config:
                limit = self.config.get("search.max_results", 100)
            elif limit is None:
                limit = 100

            results = self.index_manager.search_text(
                query_text=query.query_text,
                limit=limit,
                file_types=query.file_types,
                date_from=query.date_from,
                date_to=query.date_to,
            )

            # 検索結果を強化
            enhanced_results = []
            for i, result in enumerate(results):
                enhanced_result = self._enhance_search_result(
                    result, query.query_text, i + 1
                )
                enhanced_results.append(enhanced_result)

            return enhanced_results

        except Exception as e:
            self.logger.error(f"全文検索に失敗しました: {e}")
            raise SearchError(
                f"全文検索エラー: {e}", query=query.query_text, search_type="full_text"
            ) from e

    @with_graceful_degradation(
        "search_manager",
        disable_capabilities=["semantic_search", "hybrid_search"],
        fallback_return=[],
    )
    def _semantic_search(self, query: SearchQuery) -> list[SearchResult]:
        """セマンティック検索を実行"""
        try:
            # limitが指定されていない場合は設定から取得
            limit = query.limit
            if limit is None and self.config:
                limit = self.config.get("search.max_results", 100)
            elif limit is None:
                limit = 100

            similarities = self.embedding_manager.search_similar(
                query_text=query.query_text,
                limit=limit,
                min_similarity=self.min_semantic_similarity,
            )

            results = []
            for i, (doc_id, similarity) in enumerate(similarities):
                document = self._get_document_by_id(doc_id)
                if document:
                    search_result = SearchResult(
                        document=document,
                        score=similarity,
                        search_type=SearchType.SEMANTIC,
                        snippet=self._generate_snippet(
                            document.content, query.query_text
                        ),
                        highlighted_terms=self._extract_query_terms(query.query_text),
                        relevance_explanation=f"セマンティック類似度: {similarity:.2f}",
                        rank=i + 1,
                    )
                    results.append(search_result)

            return results

        except Exception as e:
            self.logger.error(f"セマンティック検索に失敗しました: {e}")
            raise SearchError(
                f"セマンティック検索エラー: {e}",
                query=query.query_text,
                search_type="semantic",
            ) from e

    def _hybrid_search(self, query: SearchQuery) -> list[SearchResult]:
        """ハイブリッド検索を実行"""
        try:
            weights = SearchWeights(
                full_text=query.weights.get(
                    "full_text", self.default_weights.full_text
                ),
                semantic=query.weights.get("semantic", self.default_weights.semantic),
            )

            # limitが指定されていない場合は設定から取得
            limit = query.limit
            if limit is None and self.config:
                limit = self.config.get("search.max_results", 100)
            elif limit is None:
                limit = 100

            # 全文検索を実行
            full_text_query = SearchQuery(
                query_text=query.query_text,
                search_type=SearchType.FULL_TEXT,
                limit=limit * 2,
                file_types=query.file_types,
                date_from=query.date_from,
                date_to=query.date_to,
            )
            full_text_results = self._full_text_search(full_text_query)

            # セマンティック検索を実行
            semantic_query = SearchQuery(
                query_text=query.query_text,
                search_type=SearchType.SEMANTIC,
                limit=limit * 2,
                file_types=query.file_types,
                date_from=query.date_from,
                date_to=query.date_to,
            )
            semantic_results = self._semantic_search(semantic_query)

            # 結果をマージ
            merged_results = self._merge_search_results(
                full_text_results, semantic_results, weights
            )

            return merged_results[:limit]

        except Exception as e:
            self.logger.error(f"ハイブリッド検索に失敗しました: {e}")
            raise SearchError(f"ハイブリッド検索エラー: {e}") from e

    def _merge_search_results(
        self,
        full_text_results: list[SearchResult],
        semantic_results: list[SearchResult],
        weights: SearchWeights,
    ) -> list[SearchResult]:
        """検索結果をマージ"""
        doc_scores = defaultdict(
            lambda: {
                "document": None,
                "full_text_score": 0.0,
                "semantic_score": 0.0,
                "full_text_result": None,
                "semantic_result": None,
            }
        )

        # 全文検索結果を処理
        for result in full_text_results:
            doc_id = result.document.id
            doc_scores[doc_id]["document"] = result.document
            doc_scores[doc_id]["full_text_score"] = result.score
            doc_scores[doc_id]["full_text_result"] = result

        # セマンティック検索結果を処理
        for result in semantic_results:
            doc_id = result.document.id
            if doc_scores[doc_id]["document"] is None:
                doc_scores[doc_id]["document"] = result.document
            doc_scores[doc_id]["semantic_score"] = result.score
            doc_scores[doc_id]["semantic_result"] = result

        # 統合スコアを計算
        merged_results = []
        for _doc_id, scores in doc_scores.items():
            combined_score = (
                scores["full_text_score"] * weights.full_text
                + scores["semantic_score"] * weights.semantic
            )

            snippet = self._select_best_snippet(
                scores["full_text_result"], scores["semantic_result"]
            )

            highlighted_terms = self._merge_highlighted_terms(
                scores["full_text_result"], scores["semantic_result"]
            )

            relevance_explanation = (
                f"ハイブリッドスコア: 全文検索 {scores['full_text_score']:.2f} "
                f"(重み {weights.full_text:.1f}) + "
                f"セマンティック {scores['semantic_score']:.2f} "
                f"(重み {weights.semantic:.1f})"
            )

            merged_result = SearchResult(
                document=scores["document"],
                score=combined_score,
                search_type=SearchType.HYBRID,
                snippet=snippet,
                highlighted_terms=highlighted_terms,
                relevance_explanation=relevance_explanation,
                rank=0,
            )
            merged_results.append(merged_result)

        # スコア順でソート
        merged_results.sort(key=lambda x: x.score, reverse=True)

        # ランクを設定
        for i, result in enumerate(merged_results):
            result.rank = i + 1

        return merged_results

    def _enhance_search_result(
        self, result: SearchResult, query_text: str, rank: int
    ) -> SearchResult:
        """検索結果を強化"""
        enhanced_snippet = self._generate_snippet(result.document.content, query_text)
        enhanced_terms = self._extract_query_terms(query_text)

        result.snippet = enhanced_snippet
        result.highlighted_terms = enhanced_terms
        result.rank = rank

        return result

    def _generate_snippet(self, content: str, query_text: str) -> str:
        """スニペットを生成"""
        if not content:
            return ""

        # 簡単な実装: コンテンツの先頭部分を返す
        if len(content) <= self.snippet_max_length:
            return content
        else:
            return content[: self.snippet_max_length] + "..."

    def _select_best_snippet(
        self,
        full_text_result: SearchResult | None,
        semantic_result: SearchResult | None,
    ) -> str:
        """最適なスニペットを選択"""
        if full_text_result and semantic_result:
            if len(full_text_result.snippet) > len(semantic_result.snippet):
                return full_text_result.snippet
            else:
                return semantic_result.snippet
        elif full_text_result:
            return full_text_result.snippet
        elif semantic_result:
            return semantic_result.snippet
        else:
            return ""

    def _merge_highlighted_terms(
        self,
        full_text_result: SearchResult | None,
        semantic_result: SearchResult | None,
    ) -> list[str]:
        """ハイライト用語をマージ"""
        terms = set()

        if full_text_result:
            terms.update(full_text_result.highlighted_terms)

        if semantic_result:
            terms.update(semantic_result.highlighted_terms)

        return list(terms)

    def _get_document_by_id(self, doc_id: str) -> Document | None:
        """ドキュメントIDからDocumentオブジェクトを取得"""
        try:
            with self.index_manager._index.searcher() as searcher:
                from whoosh.query import Term

                results = searcher.search(Term("id", doc_id), limit=1)

                if results:
                    hit = results[0]
                    # メタデータの復元
                    metadata = {}
                    metadata_str = hit.get("metadata", "")
                    if metadata_str:
                        try:
                            import ast

                            metadata = ast.literal_eval(metadata_str)
                            if not isinstance(metadata, dict):
                                metadata = {}
                        except (ValueError, SyntaxError) as e:
                            self.logger.warning(f"メタデータの復元に失敗しました: {e}")
                            metadata = {}

                    document = Document(
                        id=hit["id"],
                        file_path=hit["file_path"],
                        title=hit["title"],
                        content=hit["content"],
                        file_type=FileType(hit["file_type"]),
                        size=hit["size"],
                        created_date=hit["created_date"],
                        modified_date=hit["modified_date"],
                        indexed_date=hit["indexed_date"],
                        content_hash=hit["content_hash"],
                        metadata=metadata,
                    )
                    return document

        except Exception as e:
            self.logger.error(f"ドキュメント取得に失敗しました: {doc_id} - {e}")

        return None

    def _extract_query_terms(self, query_text: str) -> list[str]:
        """検索クエリから用語を抽出"""
        terms = []

        # 英語の単語を抽出
        english_words = re.findall(r"\b[a-zA-Z]{2,}\b", query_text)
        terms.extend(word.lower() for word in english_words)

        # 日本語の単語を抽出（ひらがな、カタカナ、漢字のUnicode範囲）
        japanese_words = re.findall(
            r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+", query_text
        )
        terms.extend(japanese_words)

        return list(set(terms))

    def _post_process_results(
        self, results: list[SearchResult], query: SearchQuery
    ) -> list[SearchResult]:
        """検索結果の後処理"""
        # 重複除去
        unique_results = self._remove_duplicate_results(results)

        # フォルダパスフィルタリング
        if query.folder_paths:
            unique_results = self._filter_by_folder_paths(
                unique_results, query.folder_paths
            )

        # スコア順でソート
        unique_results.sort(key=lambda x: x.score, reverse=True)

        # 結果数制限を適用
        limit = query.limit
        if limit is None and self.config:
            limit = self.config.get("search.max_results", 100)
        if limit is not None:
            unique_results = unique_results[:limit]

        # ランクを再設定
        for i, result in enumerate(unique_results):
            result.rank = i + 1

        return unique_results

    def _remove_duplicate_results(
        self, results: list[SearchResult]
    ) -> list[SearchResult]:
        """重複する検索結果を除去"""
        seen_docs = set()
        unique_results = []

        for result in results:
            doc_id = result.document.id
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                unique_results.append(result)

        return unique_results

    def _filter_by_folder_paths(
        self, results: list[SearchResult], folder_paths: list[str]
    ) -> list[SearchResult]:
        """フォルダパスで検索結果をフィルタリング"""
        if not folder_paths:
            return results

        filtered_results = []
        for result in results:
            file_path = result.document.file_path
            for folder_path in folder_paths:
                if file_path.startswith(folder_path):
                    filtered_results.append(result)
                    break

        return filtered_results

    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> list[str]:
        """検索提案を生成"""
        try:
            if not partial_query or len(partial_query) < 2:
                return []

            # キャッシュから提案を取得
            cache_key = partial_query.lower()
            if cache_key in self._suggestion_cache:
                return self._suggestion_cache[cache_key][:limit]

            suggestions = []

            # インデックス化された用語から提案を生成
            if not self._indexed_terms:
                self._build_suggestion_index()

            # 部分一致する用語を検索
            partial_lower = partial_query.lower()
            for term in self._indexed_terms:
                if term.startswith(partial_lower):
                    suggestions.append(term)
                    if len(suggestions) >= limit * 2:
                        break

            # 関連度でソート
            suggestions.sort(key=lambda x: (len(x), x))

            # キャッシュに保存
            self._suggestion_cache[cache_key] = suggestions

            return suggestions[:limit]

        except Exception as e:
            self.logger.error(f"検索提案の生成に失敗しました: {e}")
            return []

    def _build_suggestion_index(self) -> None:
        """検索提案用のインデックスを構築"""
        try:
            self.logger.info("検索提案インデックスを構築中...")

            with self.index_manager._index.searcher() as searcher:
                # 全ドキュメントを取得
                from whoosh.query import Every

                results = searcher.search(Every(), limit=None)

                for hit in results:
                    content = hit.get("content", "")
                    title = hit.get("title", "")

                    terms = self._extract_indexable_terms(title + " " + content)
                    self._indexed_terms.update(terms)

            self.logger.info(
                f"検索提案インデックス構築完了: {len(self._indexed_terms)}用語"
            )

        except Exception as e:
            self.logger.error(f"検索提案インデックスの構築に失敗しました: {e}")

    def _extract_indexable_terms(self, text: str) -> set[str]:
        """テキストからインデックス可能な用語を抽出"""
        terms = set()

        # 英語の単語
        english_words = re.findall(r"\b[a-zA-Z]{2,}\b", text)
        terms.update(word.lower() for word in english_words)

        # 日本語の単語（ひらがな、カタカナ、漢字のUnicode範囲）
        japanese_words = re.findall(
            r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]{2,}", text
        )
        terms.update(japanese_words)

        return terms

    def clear_suggestion_cache(self) -> None:
        """検索提案キャッシュをクリア"""
        self._suggestion_cache.clear()
        self._indexed_terms.clear()
        # グローバルキャッシュもクリア
        self._cache_manager.search_cache.invalidate_cache()
        self.logger.info("検索提案キャッシュをクリアしました")

    def search_async(
        self,
        query: SearchQuery,
        completion_callback: Callable[[list[SearchResult]], None] | None = None,
        progress_callback: Callable[[Any], None] | None = None,
    ) -> str:
        """
        非同期検索を実行

        Args:
            query: 検索クエリ
            completion_callback: 完了時のコールバック
            progress_callback: 進捗更新コールバック

        Returns:
            タスクID
        """

        def search_task(progress_tracker=None):
            """検索タスクの実装"""
            if progress_tracker:
                progress_tracker.update(10, "検索を開始しています...")

            results = self.search(query)

            if progress_tracker:
                progress_tracker.complete("検索が完了しました")

            return results

        def task_completion_callback(task):
            """タスク完了時のコールバック"""
            if task.status.value == "completed" and completion_callback:
                completion_callback(task.result)
            elif task.status.value == "failed":
                self.logger.error(f"非同期検索が失敗しました: {task.error}")

        # 検索タスクを送信
        task_id = self._task_manager.submit_search_task(
            name=f"検索: {query.query_text}",
            func=search_task,
            priority=TaskPriority.HIGH,
            progress_callback=progress_callback,
            completion_callback=task_completion_callback,
        )

        self.logger.info(f"非同期検索タスクを送信: {task_id}")
        return task_id

    def get_search_stats(self) -> dict[str, Any]:
        """検索統計情報を取得"""
        return {
            "indexed_documents": self.index_manager.get_document_count(),
            "cached_embeddings": len(self.embedding_manager.embeddings),
            "suggestion_terms": len(self._indexed_terms),
            "suggestion_cache_size": len(self._suggestion_cache),
            "default_weights": {
                "full_text": self.default_weights.full_text,
                "semantic": self.default_weights.semantic,
            },
        }

    def update_search_settings(self, **kwargs) -> None:
        """検索設定を更新"""
        if "full_text_weight" in kwargs and "semantic_weight" in kwargs:
            self.default_weights = SearchWeights(
                full_text=kwargs["full_text_weight"], semantic=kwargs["semantic_weight"]
            )

        if "min_semantic_similarity" in kwargs:
            self.min_semantic_similarity = kwargs["min_semantic_similarity"]

        if "snippet_max_length" in kwargs:
            self.snippet_max_length = kwargs["snippet_max_length"]

        self.logger.info("検索設定を更新しました")
