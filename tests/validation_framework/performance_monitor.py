# -*- coding: utf-8 -*-
"""
パフォーマンス監視クラス

システムのパフォーマンス指標を監視し、測定結果を提供します。
"""

import time
import psutil
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging


@dataclass
class PerformanceMetrics:
    """パフォーマンス指標を格納するデータクラス"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float


class PerformanceMonitor:
    """
    パフォーマンス監視クラス
    
    CPU使用率、メモリ使用量、ディスクI/O、ネットワークI/Oなどの
    システムパフォーマンス指標を継続的に監視します。
    """
    
    def __init__(self, sampling_interval: float = 1.0):
        """
        パフォーマンス監視の初期化
        
        Args:
            sampling_interval: サンプリング間隔（秒）
        """
        self.sampling_interval = sampling_interval
        self.logger = logging.getLogger(f"validation.{self.__class__.__name__}")
        
        # 監視状態
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # 測定データ
        self.metrics_history: List[PerformanceMetrics] = []
        self.start_time: Optional[float] = None
        
        # 初期値の取得（差分計算用）
        self._initial_disk_io = psutil.disk_io_counters()
        self._initial_network_io = psutil.net_io_counters()
        
        self.logger.debug("パフォーマンス監視を初期化しました")
    
    def start_monitoring(self) -> None:
        """パフォーマンス監視の開始"""
        if self.is_monitoring:
            self.logger.warning("パフォーマンス監視は既に開始されています")
            return
        
        self.is_monitoring = True
        self.start_time = time.time()
        self.metrics_history.clear()
        
        # 初期値の更新
        self._initial_disk_io = psutil.disk_io_counters()
        self._initial_network_io = psutil.net_io_counters()
        
        # 監視スレッドの開始
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("パフォーマンス監視を開始しました")
    
    def stop_monitoring(self) -> None:
        """パフォーマンス監視の停止"""
        if not self.is_monitoring:
            self.logger.warning("パフォーマンス監視は開始されていません")
            return
        
        self.is_monitoring = False
        
        # スレッドの終了を待機
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info(f"パフォーマンス監視を停止しました（測定データ数: {len(self.metrics_history)}）")
    
    def _monitoring_loop(self) -> None:
        """監視ループ（別スレッドで実行）"""
        while self.is_monitoring:
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                self.logger.error(f"パフォーマンス指標の収集中にエラーが発生しました: {e}")
                time.sleep(self.sampling_interval)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """現在のパフォーマンス指標を収集"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent()
        
        # メモリ使用量
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        
        # ディスクI/O
        current_disk_io = psutil.disk_io_counters()
        if current_disk_io and self._initial_disk_io:
            disk_read_bytes = current_disk_io.read_bytes - self._initial_disk_io.read_bytes
            disk_write_bytes = current_disk_io.write_bytes - self._initial_disk_io.write_bytes
            disk_io_read_mb = disk_read_bytes / (1024 * 1024)
            disk_io_write_mb = disk_write_bytes / (1024 * 1024)
        else:
            disk_io_read_mb = 0.0
            disk_io_write_mb = 0.0
        
        # ネットワークI/O
        current_network_io = psutil.net_io_counters()
        if current_network_io and self._initial_network_io:
            network_sent_bytes = current_network_io.bytes_sent - self._initial_network_io.bytes_sent
            network_recv_bytes = current_network_io.bytes_recv - self._initial_network_io.bytes_recv
            network_sent_mb = network_sent_bytes / (1024 * 1024)
            network_recv_mb = network_recv_bytes / (1024 * 1024)
        else:
            network_sent_mb = 0.0
            network_recv_mb = 0.0
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            disk_io_read_mb=disk_io_read_mb,
            disk_io_write_mb=disk_io_write_mb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb
        )
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """
        現在のパフォーマンス指標を取得
        
        Returns:
            現在の指標。監視中でない場合はNone
        """
        if not self.is_monitoring:
            return None
        
        return self._collect_metrics()
    
    def get_peak_cpu_usage(self) -> float:
        """
        監視期間中の最大CPU使用率を取得
        
        Returns:
            最大CPU使用率（%）
        """
        if not self.metrics_history:
            return 0.0
        
        return max(metrics.cpu_percent for metrics in self.metrics_history)
    
    def get_average_cpu_usage(self) -> float:
        """
        監視期間中の平均CPU使用率を取得
        
        Returns:
            平均CPU使用率（%）
        """
        if not self.metrics_history:
            return 0.0
        
        total_cpu = sum(metrics.cpu_percent for metrics in self.metrics_history)
        return total_cpu / len(self.metrics_history)
    
    def get_peak_memory_usage(self) -> float:
        """
        監視期間中の最大メモリ使用量を取得
        
        Returns:
            最大メモリ使用量（MB）
        """
        if not self.metrics_history:
            return 0.0
        
        return max(metrics.memory_used_mb for metrics in self.metrics_history)
    
    def get_total_disk_io(self) -> Dict[str, float]:
        """
        監視期間中の総ディスクI/O量を取得
        
        Returns:
            {'read_mb': 読み込み量, 'write_mb': 書き込み量}
        """
        if not self.metrics_history:
            return {'read_mb': 0.0, 'write_mb': 0.0}
        
        latest_metrics = self.metrics_history[-1]
        return {
            'read_mb': latest_metrics.disk_io_read_mb,
            'write_mb': latest_metrics.disk_io_write_mb
        }
    
    def get_total_network_io(self) -> Dict[str, float]:
        """
        監視期間中の総ネットワークI/O量を取得
        
        Returns:
            {'sent_mb': 送信量, 'recv_mb': 受信量}
        """
        if not self.metrics_history:
            return {'sent_mb': 0.0, 'recv_mb': 0.0}
        
        latest_metrics = self.metrics_history[-1]
        return {
            'sent_mb': latest_metrics.network_sent_mb,
            'recv_mb': latest_metrics.network_recv_mb
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        パフォーマンス監視の要約を取得
        
        Returns:
            パフォーマンス要約の辞書
        """
        if not self.metrics_history:
            return {}
        
        monitoring_duration = time.time() - (self.start_time or 0)
        
        return {
            'monitoring_duration_seconds': monitoring_duration,
            'sample_count': len(self.metrics_history),
            'cpu_usage': {
                'peak_percent': self.get_peak_cpu_usage(),
                'average_percent': self.get_average_cpu_usage()
            },
            'memory_usage': {
                'peak_mb': self.get_peak_memory_usage(),
                'peak_percent': max(m.memory_percent for m in self.metrics_history) if self.metrics_history else 0.0
            },
            'disk_io': self.get_total_disk_io(),
            'network_io': self.get_total_network_io()
        }
    
    def check_performance_thresholds(self, 
                                   max_cpu_percent: float = 80.0,
                                   max_memory_mb: float = 2048.0) -> Dict[str, bool]:
        """
        パフォーマンス閾値のチェック
        
        Args:
            max_cpu_percent: 最大CPU使用率（%）
            max_memory_mb: 最大メモリ使用量（MB）
        
        Returns:
            各指標の閾値チェック結果
        """
        peak_cpu = self.get_peak_cpu_usage()
        peak_memory = self.get_peak_memory_usage()
        
        results = {
            'cpu_within_threshold': peak_cpu <= max_cpu_percent,
            'memory_within_threshold': peak_memory <= max_memory_mb,
            'peak_cpu_percent': peak_cpu,
            'peak_memory_mb': peak_memory
        }
        
        if not results['cpu_within_threshold']:
            self.logger.warning(f"CPU使用率が閾値を超過: {peak_cpu:.1f}% > {max_cpu_percent}%")
        
        if not results['memory_within_threshold']:
            self.logger.warning(f"メモリ使用量が閾値を超過: {peak_memory:.1f}MB > {max_memory_mb}MB")
        
        return results
    
    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        if self.is_monitoring:
            self.stop_monitoring()
        
        self.metrics_history.clear()
        self.logger.debug("パフォーマンス監視のクリーンアップが完了しました")