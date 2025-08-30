"""
メモリ管理モジュール

このモジュールは、大規模ドキュメントコレクション用のメモリ管理機能を提供します。
メモリ使用量の監視、制限、最適化を行います。
"""

import gc
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import psutil

from ..utils.logging_config import LoggerMixin


class MemoryPressureLevel(Enum):
    """メモリ圧迫レベル"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemoryStats:
    """メモリ統計情報"""

    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    memory_percent: float
    process_memory_mb: float
    process_memory_percent: float
    pressure_level: MemoryPressureLevel


class MemoryMonitor(LoggerMixin):
    """
    メモリ監視クラス

    システムとプロセスのメモリ使用量を監視し、
    メモリ圧迫時にアラートを発行します。
    """

    """
    メモリ監視クラス

    システムとプロセスのメモリ使用量を監視し、
    メモリ圧迫時にアラートを発行します。
    """

    def __init__(self, check_interval: float = 30.0):
        """
        メモリモニターを初期化

        Args:
            check_interval: 監視間隔（秒）
        """
        self.check_interval = check_interval
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._callbacks: list[Callable[[MemoryStats], None]] = []
        self._lock = threading.RLock()

        # メモリ圧迫レベルの閾値（パーセント）
        self.thresholds = {
            MemoryPressureLevel.LOW: 60,
            MemoryPressureLevel.MEDIUM: 75,
            MemoryPressureLevel.HIGH: 85,
            MemoryPressureLevel.CRITICAL: 95,
        }

        self._last_pressure_level = MemoryPressureLevel.LOW

    def __del__(self):
        """デストラクタでリソースをクリーンアップ"""
        try:
            self.stop_monitoring()
        except Exception:
            pass

    def start_monitoring(self) -> None:
        """メモリ監視を開始"""
        with self._lock:
            if self._monitoring:
                return

            self._monitoring = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self._monitor_thread.start()

            self.logger.info("メモリ監視を開始しました")

    def stop_monitoring(self) -> None:
        """メモリ監視を停止"""
        with self._lock:
            if not self._monitoring:
                return

            self._monitoring = False

        # ロック外でスレッド終了を待機
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)

        self.logger.info("メモリ監視を停止しました")

    def add_callback(self, callback: Callable[[MemoryStats], None]) -> None:
        """メモリ統計更新時のコールバックを追加"""
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[MemoryStats], None]) -> None:
        """コールバックを削除"""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def get_memory_stats(self) -> MemoryStats:
        """現在のメモリ統計を取得"""
        # システムメモリ情報
        system_memory = psutil.virtual_memory()

        # プロセスメモリ情報
        process = psutil.Process()
        process_memory = process.memory_info()

        # メモリ圧迫レベルを判定
        pressure_level = self._determine_pressure_level(system_memory.percent)

        return MemoryStats(
            total_memory_mb=system_memory.total / 1024 / 1024,
            available_memory_mb=system_memory.available / 1024 / 1024,
            used_memory_mb=system_memory.used / 1024 / 1024,
            memory_percent=system_memory.percent,
            process_memory_mb=process_memory.rss / 1024 / 1024,
            process_memory_percent=process.memory_percent(),
            pressure_level=pressure_level,
        )

    def _determine_pressure_level(self, memory_percent: float) -> MemoryPressureLevel:
        """メモリ使用率から圧迫レベルを判定"""
        if memory_percent >= self.thresholds[MemoryPressureLevel.CRITICAL]:
            return MemoryPressureLevel.CRITICAL
        elif memory_percent >= self.thresholds[MemoryPressureLevel.HIGH]:
            return MemoryPressureLevel.HIGH
        elif memory_percent >= self.thresholds[MemoryPressureLevel.MEDIUM]:
            return MemoryPressureLevel.MEDIUM
        else:
            return MemoryPressureLevel.LOW

    def _monitor_loop(self) -> None:
        """メモリ監視ループ"""
        while self._monitoring:
            try:
                stats = self.get_memory_stats()

                # 圧迫レベルが変化した場合はログ出力
                if stats.pressure_level != self._last_pressure_level:
                    self.logger.info(
                        f"メモリ圧迫レベル変化: {self._last_pressure_level.value} -> {stats.pressure_level.value} "
                        f"(使用率: {stats.memory_percent:.1f}%)"
                    )
                    self._last_pressure_level = stats.pressure_level

                # コールバックを呼び出し
                with self._lock:
                    for callback in self._callbacks:
                        try:
                            callback(stats)
                        except Exception as e:
                            self.logger.warning(f"メモリ監視コールバックでエラー: {e}")

                time.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"メモリ監視でエラー: {e}")
                time.sleep(self.check_interval)


class MemoryManager(LoggerMixin):
    """
    メモリ管理クラス

    メモリ使用量の制限、最適化、ガベージコレクションを管理します。
    """

    def __init__(self, max_memory_mb: float | None = None):
        """
        メモリマネージャーを初期化

        Args:
            max_memory_mb: 最大メモリ使用量（MB）、Noneの場合は自動設定
        """
        self.monitor = MemoryMonitor()

        # 最大メモリ使用量を設定
        if max_memory_mb is None:
            # システムメモリの50%を上限とする
            system_memory = psutil.virtual_memory()
            self.max_memory_mb = (system_memory.total / 1024 / 1024) * 0.5
        else:
            self.max_memory_mb = max_memory_mb

        # メモリ最適化コールバック
        self._optimization_callbacks: list[Callable[[], None]] = []

        # 統計情報
        self._gc_count = 0
        self._optimization_count = 0

        # メモリ監視コールバックを登録
        self.monitor.add_callback(self._on_memory_stats_updated)

        self.logger.info(
            f"メモリマネージャーを初期化: 最大メモリ使用量={self.max_memory_mb:.1f}MB"
        )

    def start(self) -> None:
        """メモリ管理を開始"""
        self.monitor.start_monitoring()
        self.logger.info("メモリ管理を開始しました")

    def stop(self) -> None:
        """メモリ管理を停止"""
        self.monitor.stop_monitoring()
        self.logger.info("メモリ管理を停止しました")

    def __del__(self):
        """デストラクタでリソースをクリーンアップ"""
        try:
            self.stop()
        except Exception:
            pass

    def add_optimization_callback(self, callback: Callable[[], None]) -> None:
        """メモリ最適化コールバックを追加"""
        self._optimization_callbacks.append(callback)

    def remove_optimization_callback(self, callback: Callable[[], None]) -> None:
        """メモリ最適化コールバックを削除"""
        if callback in self._optimization_callbacks:
            self._optimization_callbacks.remove(callback)

    def force_garbage_collection(self) -> dict[str, int]:
        """強制的にガベージコレクションを実行"""
        self.logger.debug("強制ガベージコレクションを実行")

        # 各世代のガベージコレクションを実行
        collected = {}
        for generation in range(3):
            collected[f"generation_{generation}"] = gc.collect(generation)

        self._gc_count += 1

        # 統計情報をログ出力
        total_collected = sum(collected.values())
        self.logger.info(
            f"ガベージコレクション完了: {total_collected}オブジェクトを回収"
        )

        return collected

    def optimize_memory(self) -> None:
        """メモリ最適化を実行"""
        self.logger.info("メモリ最適化を開始")

        # ガベージコレクションを実行
        self.force_garbage_collection()

        # 登録されたコールバックを実行
        for callback in self._optimization_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.warning(f"メモリ最適化コールバックでエラー: {e}")

        self._optimization_count += 1
        self.logger.info("メモリ最適化が完了しました")

    def check_memory_limit(self) -> bool:
        """メモリ制限をチェック"""
        stats = self.monitor.get_memory_stats()
        return stats.process_memory_mb <= self.max_memory_mb

    def get_memory_usage_ratio(self) -> float:
        """メモリ使用率を取得（0.0-1.0）"""
        stats = self.monitor.get_memory_stats()
        return stats.process_memory_mb / self.max_memory_mb

    def _on_memory_stats_updated(self, stats: MemoryStats) -> None:
        """メモリ統計更新時のコールバック"""
        # メモリ制限チェック
        if stats.process_memory_mb > self.max_memory_mb:
            self.logger.warning(
                f"メモリ使用量が制限を超過: {stats.process_memory_mb:.1f}MB > {self.max_memory_mb:.1f}MB"
            )
            # 自動的にメモリ最適化を実行
            self.optimize_memory()

        # 高メモリ圧迫時の対応
        if stats.pressure_level in [
            MemoryPressureLevel.HIGH,
            MemoryPressureLevel.CRITICAL,
        ]:
            self.logger.warning(f"高メモリ圧迫状態: {stats.pressure_level.value}")

            if stats.pressure_level == MemoryPressureLevel.CRITICAL:
                # クリティカルレベルでは強制的に最適化
                self.optimize_memory()

    def get_stats(self) -> dict[str, Any]:
        """メモリ管理統計を取得"""
        memory_stats = self.monitor.get_memory_stats()

        return {
            "max_memory_mb": self.max_memory_mb,
            "current_memory_mb": memory_stats.process_memory_mb,
            "memory_usage_ratio": self.get_memory_usage_ratio(),
            "system_memory_percent": memory_stats.memory_percent,
            "pressure_level": memory_stats.pressure_level.value,
            "gc_count": self._gc_count,
            "optimization_count": self._optimization_count,
            "memory_limit_exceeded": not self.check_memory_limit(),
        }


class MemoryOptimizer(LoggerMixin):
    """
    メモリ最適化ユーティリティクラス

    様々なメモリ最適化戦略を提供します。
    """

    @staticmethod
    def optimize_cache_sizes(cache_manager, target_memory_mb: float) -> None:
        """
        キャッシュサイズを最適化

        Args:
            cache_manager: キャッシュマネージャー
            target_memory_mb: 目標メモリ使用量
        """
        logger = logging.getLogger(__name__)

        try:
            # 現在のメモリ使用量を取得
            process = psutil.Process()
            current_memory_mb = process.memory_info().rss / 1024 / 1024

            if current_memory_mb > target_memory_mb:
                # メモリ使用量が目標を超えている場合、キャッシュをクリア
                reduction_needed = current_memory_mb - target_memory_mb

                logger.info(
                    f"キャッシュサイズ最適化: {reduction_needed:.1f}MB削減が必要"
                )

                # 検索キャッシュをクリア
                cache_manager.search_cache.invalidate_cache()

                # ドキュメントキャッシュをクリア
                cache_manager.document_cache.clear()

                logger.info("キャッシュサイズ最適化が完了しました")

        except Exception as e:
            logger.error(f"キャッシュサイズ最適化でエラー: {e}")

    @staticmethod
    def optimize_embedding_cache(embedding_manager, max_embeddings: int) -> None:
        """
        埋め込みキャッシュを最適化

        Args:
            embedding_manager: 埋め込みマネージャー
            max_embeddings: 最大埋め込み数
        """
        logger = logging.getLogger(__name__)

        try:
            if hasattr(embedding_manager, "embeddings"):
                current_count = len(embedding_manager.embeddings)

                if current_count > max_embeddings:
                    # 古い埋め込みを削除
                    excess_count = current_count - max_embeddings

                    logger.info(
                        f"埋め込みキャッシュ最適化: {excess_count}件の埋め込みを削除"
                    )

                    # 最も古い埋め込みを削除（実装は埋め込みマネージャーに依存）
                    if hasattr(embedding_manager, "cleanup_old_embeddings"):
                        embedding_manager.cleanup_old_embeddings(excess_count)

                    logger.info("埋め込みキャッシュ最適化が完了しました")

        except Exception as e:
            logger.error(f"埋め込みキャッシュ最適化でエラー: {e}")

    @staticmethod
    def optimize_index_cache(index_manager) -> None:
        """
        インデックスキャッシュを最適化

        Args:
            index_manager: インデックスマネージャー
        """
        logger = logging.getLogger(__name__)

        try:
            # インデックスの最適化を実行
            if hasattr(index_manager, "optimize_index"):
                logger.info("インデックス最適化を開始")
                index_manager.optimize_index()
                logger.info("インデックス最適化が完了しました")

        except Exception as e:
            logger.error(f"インデックス最適化でエラー: {e}")


# グローバルメモリマネージャーインスタンス
_global_memory_manager: MemoryManager | None = None


def get_global_memory_manager() -> MemoryManager:
    """グローバルメモリマネージャーを取得"""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
    return _global_memory_manager


def initialize_memory_manager(max_memory_mb: float | None = None) -> MemoryManager:
    """メモリマネージャーを初期化"""
    global _global_memory_manager
    _global_memory_manager = MemoryManager(max_memory_mb)
    return _global_memory_manager
