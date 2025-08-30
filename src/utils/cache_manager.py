"""
キャッシュ管理モジュール

このモジュールは、検索結果、ドキュメント、埋め込みなどの
頻繁にアクセスされるデータのキャッシュ機能を提供します。
LRU（Least Recently Used）キャッシュとTTL（Time To Live）機能を実装しています。
"""

import hashlib
import pickle
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

from ..data.models import Document, SearchResult
from ..utils.exceptions import CacheError
from ..utils.logging_config import LoggerMixin

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """キャッシュエントリを表すデータクラス"""

    value: T
    timestamp: float
    access_count: int = 0
    ttl: float | None = None

    def is_expired(self) -> bool:
        """エントリが期限切れかどうかをチェック"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def touch(self) -> None:
        """エントリにアクセスしたことを記録"""
        self.access_count += 1


class LRUCache(Generic[T], LoggerMixin):
    """
    LRU（Least Recently Used）キャッシュの実装

    スレッドセーフで、TTL（Time To Live）機能をサポートします。
    """

    def __init__(self, max_size: int = 1000, default_ttl: float | None = None):
        """
        LRUキャッシュを初期化

        Args:
            max_size: キャッシュの最大サイズ
            default_ttl: デフォルトのTTL（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> T | None:
        """
        キーに対応する値を取得

        Args:
            key: キャッシュキー

        Returns:
            キャッシュされた値、または None
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # 期限切れチェック
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None

            # LRU順序を更新（最後に移動）
            self._cache.move_to_end(key)
            entry.touch()
            self._hits += 1

            return entry.value

    def put(self, key: str, value: T, ttl: float | None = None) -> None:
        """
        キーと値をキャッシュに保存

        Args:
            key: キャッシュキー
            value: 保存する値
            ttl: TTL（秒）、Noneの場合はデフォルトTTLを使用
        """
        with self._lock:
            current_time = time.time()
            effective_ttl = ttl if ttl is not None else self.default_ttl

            entry = CacheEntry(value=value, timestamp=current_time, ttl=effective_ttl)

            if key in self._cache:
                # 既存エントリを更新
                self._cache[key] = entry
                self._cache.move_to_end(key)
            else:
                # 新しいエントリを追加
                self._cache[key] = entry

                # サイズ制限チェック
                if len(self._cache) > self.max_size:
                    # 最も古いエントリを削除
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]

    def remove(self, key: str) -> bool:
        """
        キーをキャッシュから削除

        Args:
            key: 削除するキー

        Returns:
            削除に成功した場合True
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """キャッシュをクリア"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def cleanup_expired(self) -> int:
        """
        期限切れエントリをクリーンアップ

        Returns:
            削除されたエントリ数
        """
        with self._lock:
            expired_keys = []
            time.time()

            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """キャッシュ統計を取得"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "total_requests": total_requests,
            }


class SearchResultCache(LoggerMixin):
    """
    検索結果専用のキャッシュクラス

    検索クエリをキーとして検索結果をキャッシュします。
    """

    def __init__(self, max_size: int = 500, ttl: float = 300.0):  # 5分のTTL
        """
        検索結果キャッシュを初期化

        Args:
            max_size: 最大キャッシュサイズ
            ttl: TTL（秒）
        """
        self._cache = LRUCache[list[SearchResult]](max_size=max_size, default_ttl=ttl)
        self._cleanup_interval = 60.0  # 1分間隔でクリーンアップ
        self._last_cleanup = time.time()

    def _generate_cache_key(
        self, query_text: str, search_type: str, filters: dict[str, Any] | None = None
    ) -> str:
        """
        検索パラメータからキャッシュキーを生成

        Args:
            query_text: 検索クエリ
            search_type: 検索タイプ
            filters: 検索フィルター

        Returns:
            ハッシュ化されたキャッシュキー
        """
        # キャッシュキーの構成要素
        key_components = [
            query_text.lower().strip(),
            search_type,
            str(sorted(filters.items()) if filters else ""),
        ]

        # ハッシュ化してキーを生成
        key_string = "|".join(key_components)
        return hashlib.sha256(key_string.encode("utf-8")).hexdigest()

    def get_search_results(
        self, query_text: str, search_type: str, filters: dict[str, Any] | None = None
    ) -> list[SearchResult] | None:
        """
        キャッシュから検索結果を取得

        Args:
            query_text: 検索クエリ
            search_type: 検索タイプ
            filters: 検索フィルター

        Returns:
            キャッシュされた検索結果、またはNone
        """
        self._maybe_cleanup()

        cache_key = self._generate_cache_key(query_text, search_type, filters)
        results = self._cache.get(cache_key)

        if results is not None:
            self.logger.debug(f"検索結果をキャッシュから取得: {query_text}")

        return results

    def cache_search_results(
        self,
        query_text: str,
        search_type: str,
        results: list[SearchResult],
        filters: dict[str, Any] | None = None,
    ) -> None:
        """
        検索結果をキャッシュに保存

        Args:
            query_text: 検索クエリ
            search_type: 検索タイプ
            results: 検索結果
            filters: 検索フィルター
        """
        cache_key = self._generate_cache_key(query_text, search_type, filters)
        self._cache.put(cache_key, results)

        self.logger.debug(
            f"検索結果をキャッシュに保存: {query_text} ({len(results)}件)"
        )

    def invalidate_cache(self) -> None:
        """キャッシュを無効化（クリア）"""
        self._cache.clear()
        self.logger.info("検索結果キャッシュを無効化しました")

    def _maybe_cleanup(self) -> None:
        """必要に応じて期限切れエントリをクリーンアップ"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            expired_count = self._cache.cleanup_expired()
            if expired_count > 0:
                self.logger.debug(
                    f"期限切れキャッシュエントリを削除: {expired_count}件"
                )
            self._last_cleanup = current_time

    def get_stats(self) -> dict[str, Any]:
        """キャッシュ統計を取得"""
        return self._cache.get_stats()


class DocumentCache(LoggerMixin):
    """
    ドキュメント専用のキャッシュクラス

    頻繁にアクセスされるドキュメントをメモリにキャッシュします。
    """

    def __init__(self, max_size: int = 200, ttl: float = 600.0):  # 10分のTTL
        """
        ドキュメントキャッシュを初期化

        Args:
            max_size: 最大キャッシュサイズ
            ttl: TTL（秒）
        """
        self._cache = LRUCache[Document](max_size=max_size, default_ttl=ttl)

    def get_document(self, doc_id: str) -> Document | None:
        """
        ドキュメントをキャッシュから取得

        Args:
            doc_id: ドキュメントID

        Returns:
            キャッシュされたドキュメント、またはNone
        """
        return self._cache.get(doc_id)

    def cache_document(self, document: Document) -> None:
        """
        ドキュメントをキャッシュに保存

        Args:
            document: キャッシュするドキュメント
        """
        self._cache.put(document.id, document)
        self.logger.debug(f"ドキュメントをキャッシュに保存: {document.title}")

    def remove_document(self, doc_id: str) -> bool:
        """
        ドキュメントをキャッシュから削除

        Args:
            doc_id: ドキュメントID

        Returns:
            削除に成功した場合True
        """
        removed = self._cache.remove(doc_id)
        if removed:
            self.logger.debug(f"ドキュメントをキャッシュから削除: {doc_id}")
        return removed

    def clear(self) -> None:
        """キャッシュをクリア"""
        self._cache.clear()
        self.logger.info("ドキュメントキャッシュをクリアしました")

    def get_stats(self) -> dict[str, Any]:
        """キャッシュ統計を取得"""
        return self._cache.get_stats()


class PersistentCache(LoggerMixin):
    """
    永続化キャッシュクラス

    キャッシュデータをディスクに保存し、アプリケーション再起動後も利用可能にします。
    """

    def __init__(self, cache_dir: str, cache_name: str):
        """
        永続化キャッシュを初期化

        Args:
            cache_dir: キャッシュディレクトリ
            cache_name: キャッシュ名
        """
        self.cache_dir = Path(cache_dir)
        self.cache_name = cache_name
        self.cache_file = self.cache_dir / f"{cache_name}.cache"

        # キャッシュディレクトリを作成
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._data: dict[str, Any] = {}
        self._lock = threading.RLock()

        # 既存のキャッシュを読み込み
        self._load_cache()

    def _load_cache(self) -> None:
        """ディスクからキャッシュを読み込み"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "rb") as f:
                    self._data = pickle.load(f)
                self.logger.info(
                    f"永続化キャッシュを読み込み: {self.cache_name} ({len(self._data)}件)"
                )
        except Exception as e:
            self.logger.warning(f"永続化キャッシュの読み込みに失敗: {e}")
            self._data = {}

    def _save_cache(self) -> None:
        """キャッシュをディスクに保存"""
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(self._data, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            self.logger.error(f"永続化キャッシュの保存に失敗: {e}")
            raise CacheError(f"キャッシュの保存に失敗しました: {e}") from e

    def get(self, key: str) -> Any | None:
        """値を取得"""
        with self._lock:
            return self._data.get(key)

    def put(self, key: str, value: Any, save_immediately: bool = False) -> None:
        """
        値を保存

        Args:
            key: キー
            value: 値
            save_immediately: 即座にディスクに保存するかどうか
        """
        with self._lock:
            self._data[key] = value
            if save_immediately:
                self._save_cache()

    def remove(self, key: str) -> bool:
        """キーを削除"""
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def clear(self) -> None:
        """キャッシュをクリア"""
        with self._lock:
            self._data.clear()
            self._save_cache()

    def save(self) -> None:
        """キャッシュをディスクに保存"""
        with self._lock:
            self._save_cache()

    def get_size(self) -> int:
        """キャッシュサイズを取得"""
        with self._lock:
            return len(self._data)


class CacheManager(LoggerMixin):
    """
    統合キャッシュ管理クラス

    アプリケーション全体のキャッシュを統合管理します。
    """

    def __init__(self, cache_dir: str):
        """
        キャッシュマネージャーを初期化

        Args:
            cache_dir: キャッシュディレクトリ
        """
        self.cache_dir = Path(cache_dir)

        # 各種キャッシュを初期化
        self.search_cache = SearchResultCache()
        self.document_cache = DocumentCache()

        # 永続化キャッシュ
        self.embedding_cache = PersistentCache(str(self.cache_dir), "embeddings")
        self.suggestion_cache = PersistentCache(str(self.cache_dir), "suggestions")

        self.logger.info("キャッシュマネージャーを初期化しました")

    def clear_all_caches(self) -> None:
        """すべてのキャッシュをクリア"""
        self.search_cache.invalidate_cache()
        self.document_cache.clear()
        self.embedding_cache.clear()
        self.suggestion_cache.clear()

        self.logger.info("すべてのキャッシュをクリアしました")

    def get_cache_stats(self) -> dict[str, Any]:
        """すべてのキャッシュの統計情報を取得"""
        return {
            "search_cache": self.search_cache.get_stats(),
            "document_cache": self.document_cache.get_stats(),
            "embedding_cache_size": self.embedding_cache.get_size(),
            "suggestion_cache_size": self.suggestion_cache.get_size(),
        }

    def save_persistent_caches(self) -> None:
        """永続化キャッシュを保存"""
        self.embedding_cache.save()
        self.suggestion_cache.save()
        self.logger.info("永続化キャッシュを保存しました")


# グローバルキャッシュマネージャーインスタンス
_global_cache_manager: CacheManager | None = None


def get_global_cache_manager() -> CacheManager:
    """グローバルキャッシュマネージャーを取得"""
    global _global_cache_manager
    if _global_cache_manager is None:
        from ..utils.config import get_config

        config = get_config()
        cache_dir = config.get("cache_directory", "docmind_data/cache")
        _global_cache_manager = CacheManager(cache_dir)
    return _global_cache_manager


def initialize_cache_manager(cache_dir: str) -> None:
    """キャッシュマネージャーを初期化"""
    global _global_cache_manager
    _global_cache_manager = CacheManager(cache_dir)
