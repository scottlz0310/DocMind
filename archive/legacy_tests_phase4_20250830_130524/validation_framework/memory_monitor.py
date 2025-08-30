"""
メモリ監視クラス

アプリケーションのメモリ使用量を詳細に監視し、
メモリリークの検出や使用量の最適化に役立つ情報を提供します。
"""

import gc
import logging
import threading
import time
import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psutil


@dataclass
class MemorySnapshot:
    """メモリスナップショットを格納するデータクラス"""

    timestamp: datetime
    rss_mb: float  # Resident Set Size (物理メモリ使用量)
    vms_mb: float  # Virtual Memory Size (仮想メモリ使用量)
    percent: float  # システム全体のメモリ使用率
    python_objects: int  # Pythonオブジェクト数
    gc_collections: dict[int, int]  # ガベージコレクション回数


class MemoryMonitor:
    """
    メモリ監視クラス

    アプリケーションのメモリ使用量を継続的に監視し、
    メモリリークの検出や使用量分析を行います。
    """

    def __init__(self, sampling_interval: float = 1.0, enable_tracemalloc: bool = True):
        """
        メモリ監視の初期化

        Args:
            sampling_interval: サンプリング間隔（秒）
            enable_tracemalloc: tracemalloc使用の有効/無効
        """
        self.sampling_interval = sampling_interval
        self.enable_tracemalloc = enable_tracemalloc
        self.logger = logging.getLogger(f"validation.{self.__class__.__name__}")

        # 監視状態
        self.is_monitoring = False
        self.monitor_thread: threading.Thread | None = None

        # 測定データ
        self.memory_snapshots: list[MemorySnapshot] = []
        self.start_time: float | None = None

        # プロセス情報
        self.process = psutil.Process()

        # tracemalloc初期化
        if self.enable_tracemalloc and not tracemalloc.is_tracing():
            tracemalloc.start()
            self.logger.debug("tracemalloc監視を開始しました")

        self.logger.debug("メモリ監視を初期化しました")

    def start_monitoring(self) -> None:
        """メモリ監視の開始"""
        if self.is_monitoring:
            self.logger.warning("メモリ監視は既に開始されています")
            return

        self.is_monitoring = True
        self.start_time = time.time()
        self.memory_snapshots.clear()

        # 監視スレッドの開始
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitor_thread.start()

        self.logger.info("メモリ監視を開始しました")

    def stop_monitoring(self) -> None:
        """メモリ監視の停止"""
        if not self.is_monitoring:
            self.logger.warning("メモリ監視は開始されていません")
            return

        self.is_monitoring = False

        # スレッドの終了を待機
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)

        self.logger.info(
            f"メモリ監視を停止しました（スナップショット数: {len(self.memory_snapshots)}）"
        )

    def _monitoring_loop(self) -> None:
        """監視ループ（別スレッドで実行）"""
        while self.is_monitoring:
            try:
                snapshot = self._take_memory_snapshot()
                self.memory_snapshots.append(snapshot)

                time.sleep(self.sampling_interval)

            except Exception as e:
                self.logger.error(
                    f"メモリスナップショットの取得中にエラーが発生しました: {e}"
                )
                time.sleep(self.sampling_interval)

    def _take_memory_snapshot(self) -> MemorySnapshot:
        """現在のメモリスナップショットを取得"""
        # プロセスメモリ情報
        memory_info = self.process.memory_info()
        rss_mb = memory_info.rss / (1024 * 1024)
        vms_mb = memory_info.vms / (1024 * 1024)

        # システムメモリ使用率
        system_memory = psutil.virtual_memory()
        memory_percent = system_memory.percent

        # Pythonオブジェクト数
        python_objects = len(gc.get_objects())

        # ガベージコレクション統計
        gc_stats = gc.get_stats()
        gc_collections = {i: stats["collections"] for i, stats in enumerate(gc_stats)}

        return MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=rss_mb,
            vms_mb=vms_mb,
            percent=memory_percent,
            python_objects=python_objects,
            gc_collections=gc_collections,
        )

    def get_current_memory_usage(self) -> dict[str, float]:
        """
        現在のメモリ使用量を取得

        Returns:
            メモリ使用量の辞書
        """
        snapshot = self._take_memory_snapshot()

        return {
            "rss_mb": snapshot.rss_mb,
            "vms_mb": snapshot.vms_mb,
            "percent": snapshot.percent,
            "python_objects": snapshot.python_objects,
        }

    def get_peak_memory(self) -> float:
        """
        監視期間中の最大メモリ使用量を取得

        Returns:
            最大RSS（MB）
        """
        if not self.memory_snapshots:
            current = self._take_memory_snapshot()
            return current.rss_mb

        return max(snapshot.rss_mb for snapshot in self.memory_snapshots)

    def get_memory_growth_rate(self) -> float:
        """
        メモリ使用量の増加率を計算

        Returns:
            メモリ増加率（MB/秒）。負の値は減少を示す
        """
        if len(self.memory_snapshots) < 2:
            return 0.0

        first_snapshot = self.memory_snapshots[0]
        last_snapshot = self.memory_snapshots[-1]

        memory_diff = last_snapshot.rss_mb - first_snapshot.rss_mb
        time_diff = (last_snapshot.timestamp - first_snapshot.timestamp).total_seconds()

        if time_diff <= 0:
            return 0.0

        return memory_diff / time_diff

    def detect_memory_leak(self, threshold_mb_per_minute: float = 10.0) -> bool:
        """
        メモリリークの検出

        Args:
            threshold_mb_per_minute: メモリリーク判定の閾値（MB/分）

        Returns:
            メモリリークが検出された場合True
        """
        growth_rate = self.get_memory_growth_rate()
        growth_rate_per_minute = growth_rate * 60  # 秒から分に変換

        is_leak = growth_rate_per_minute > threshold_mb_per_minute

        if is_leak:
            self.logger.warning(
                f"メモリリークの可能性を検出: {growth_rate_per_minute:.2f}MB/分 "
                f"(閾値: {threshold_mb_per_minute}MB/分)"
            )

        return is_leak

    def get_memory_statistics(self) -> dict[str, Any]:
        """
        メモリ使用量の統計情報を取得

        Returns:
            統計情報の辞書
        """
        if not self.memory_snapshots:
            return {}

        rss_values = [s.rss_mb for s in self.memory_snapshots]
        vms_values = [s.vms_mb for s in self.memory_snapshots]
        object_counts = [s.python_objects for s in self.memory_snapshots]

        monitoring_duration = time.time() - (self.start_time or 0)

        return {
            "monitoring_duration_seconds": monitoring_duration,
            "snapshot_count": len(self.memory_snapshots),
            "rss_memory": {
                "peak_mb": max(rss_values),
                "average_mb": sum(rss_values) / len(rss_values),
                "min_mb": min(rss_values),
                "growth_rate_mb_per_sec": self.get_memory_growth_rate(),
            },
            "virtual_memory": {
                "peak_mb": max(vms_values),
                "average_mb": sum(vms_values) / len(vms_values),
                "min_mb": min(vms_values),
            },
            "python_objects": {
                "peak_count": max(object_counts),
                "average_count": sum(object_counts) / len(object_counts),
                "min_count": min(object_counts),
            },
            "memory_leak_detected": self.detect_memory_leak(),
        }

    def get_top_memory_consumers(self, limit: int = 10) -> list[tuple[str, int, float]]:
        """
        メモリ使用量上位のオブジェクトを取得（tracemalloc使用）

        Args:
            limit: 取得する上位オブジェクト数

        Returns:
            (ファイル名, 行番号, サイズMB)のタプルのリスト
        """
        if not self.enable_tracemalloc or not tracemalloc.is_tracing():
            self.logger.warning(
                "tracemalloc が有効でないため、詳細なメモリ分析はできません"
            )
            return []

        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics("lineno")

            result = []
            for stat in top_stats[:limit]:
                size_mb = stat.size / (1024 * 1024)
                result.append((stat.traceback.format()[0], stat.count, size_mb))

            return result

        except Exception as e:
            self.logger.error(f"メモリ使用量分析中にエラーが発生しました: {e}")
            return []

    def force_garbage_collection(self) -> dict[str, int]:
        """
        強制的なガベージコレクションの実行

        Returns:
            各世代で回収されたオブジェクト数
        """
        self.logger.debug("強制ガベージコレクションを実行します")

        # 各世代のガベージコレクションを実行
        collected = {}
        for generation in range(3):
            collected[f"generation_{generation}"] = gc.collect(generation)

        total_collected = sum(collected.values())
        self.logger.info(
            f"ガベージコレクションで {total_collected} オブジェクトを回収しました"
        )

        return collected

    def check_memory_thresholds(
        self, max_rss_mb: float = 2048.0, max_growth_rate_mb_per_min: float = 50.0
    ) -> dict[str, bool]:
        """
        メモリ使用量の閾値チェック

        Args:
            max_rss_mb: 最大RSS使用量（MB）
            max_growth_rate_mb_per_min: 最大メモリ増加率（MB/分）

        Returns:
            閾値チェック結果
        """
        peak_memory = self.get_peak_memory()
        growth_rate = self.get_memory_growth_rate() * 60  # 分単位に変換

        results = {
            "memory_within_threshold": peak_memory <= max_rss_mb,
            "growth_rate_within_threshold": growth_rate <= max_growth_rate_mb_per_min,
            "peak_memory_mb": peak_memory,
            "growth_rate_mb_per_min": growth_rate,
        }

        if not results["memory_within_threshold"]:
            self.logger.warning(
                f"メモリ使用量が閾値を超過: {peak_memory:.1f}MB > {max_rss_mb}MB"
            )

        if not results["growth_rate_within_threshold"]:
            self.logger.warning(
                f"メモリ増加率が閾値を超過: {growth_rate:.1f}MB/分 > {max_growth_rate_mb_per_min}MB/分"
            )

        return results

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        if self.is_monitoring:
            self.stop_monitoring()

        # tracemalloc停止
        if self.enable_tracemalloc and tracemalloc.is_tracing():
            tracemalloc.stop()
            self.logger.debug("tracemalloc監視を停止しました")

        self.memory_snapshots.clear()
        self.logger.debug("メモリ監視のクリーンアップが完了しました")
