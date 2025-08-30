"""
統計情報収集・分析クラス

検証結果の統計情報を収集し、分析結果を提供します。
"""

import csv
import json
import logging
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
from scipy import stats


@dataclass
class StatisticalSummary:
    """統計サマリーを格納するデータクラス"""
    count: int
    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    percentile_99: float

    def to_dict(self) -> dict[str, float]:
        """辞書形式に変換（JSON serialization対応）"""
        return {
            'count': self.count,
            'mean': self.mean,
            'median': self.median,
            'std_dev': self.std_dev,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'percentile_25': self.percentile_25,
            'percentile_75': self.percentile_75,
            'percentile_95': self.percentile_95,
            'percentile_99': self.percentile_99
        }


@dataclass
class TrendAnalysis:
    """トレンド分析結果を格納するデータクラス"""
    slope: float
    intercept: float
    r_value: float
    p_value: float
    std_err: float
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    confidence_level: float

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換（JSON serialization対応）"""
        return {
            'slope': self.slope,
            'intercept': self.intercept,
            'r_value': self.r_value,
            'p_value': self.p_value,
            'std_err': self.std_err,
            'trend_direction': self.trend_direction,
            'confidence_level': self.confidence_level
        }


class StatisticsCollector:
    """
    統計情報収集・分析クラス

    検証結果の統計情報を収集し、トレンド分析、
    異常値検出、パフォーマンス分析などを行います。
    """

    def __init__(self):
        """統計情報収集クラスの初期化"""
        self.logger = logging.getLogger(f"validation.{self.__class__.__name__}")

        # 検証結果の蓄積
        self.validation_results: list[Any] = []
        self.performance_metrics: list[dict[str, float]] = []
        self.memory_metrics: list[dict[str, float]] = []

        # 時系列データ
        self.time_series_data: dict[str, list[tuple[datetime, float]]] = defaultdict(list)

        # 統計キャッシュ
        self._statistics_cache: dict[str, Any] = {}
        self._cache_timestamp: datetime | None = None
        self._cache_validity_seconds = 300  # 5分間キャッシュ有効

        self.logger.debug("統計情報収集クラスを初期化しました")

    def add_result(self, validation_result: Any) -> None:
        """
        検証結果の追加

        Args:
            validation_result: 検証結果オブジェクト
        """
        self.validation_results.append(validation_result)

        # 時系列データの更新
        timestamp = getattr(validation_result, 'timestamp', datetime.now())
        self.time_series_data['execution_time'].append((timestamp, validation_result.execution_time))
        self.time_series_data['memory_usage'].append((timestamp, validation_result.memory_usage))
        self.time_series_data['success_rate'].append((timestamp, 1.0 if validation_result.success else 0.0))

        # キャッシュの無効化
        self._invalidate_cache()

        self.logger.debug(f"検証結果を追加しました: {validation_result.test_name}")

    def add_performance_metrics(self, metrics: dict[str, float]) -> None:
        """
        パフォーマンス指標の追加

        Args:
            metrics: パフォーマンス指標の辞書
        """
        metrics_with_timestamp = metrics.copy()
        metrics_with_timestamp['timestamp'] = time.time()
        self.performance_metrics.append(metrics_with_timestamp)

        # 時系列データの更新
        timestamp = datetime.now()
        for key, value in metrics.items():
            if isinstance(value, int | float):
                self.time_series_data[f'performance_{key}'].append((timestamp, value))

        self._invalidate_cache()
        self.logger.debug("パフォーマンス指標を追加しました")

    def add_memory_metrics(self, metrics: dict[str, float]) -> None:
        """
        メモリ指標の追加

        Args:
            metrics: メモリ指標の辞書
        """
        metrics_with_timestamp = metrics.copy()
        metrics_with_timestamp['timestamp'] = time.time()
        self.memory_metrics.append(metrics_with_timestamp)

        # 時系列データの更新
        timestamp = datetime.now()
        for key, value in metrics.items():
            if isinstance(value, int | float):
                self.time_series_data[f'memory_{key}'].append((timestamp, value))

        self._invalidate_cache()
        self.logger.debug("メモリ指標を追加しました")

    def get_summary(self) -> dict[str, Any]:
        """
        統計サマリーの取得

        Returns:
            統計サマリーの辞書
        """
        if self._is_cache_valid():
            return self._statistics_cache

        summary = {
            'basic_statistics': self._calculate_basic_statistics(),
            'performance_analysis': self._analyze_performance_trends(),
            'quality_metrics': self._calculate_quality_metrics(),
            'trend_analysis': self._perform_trend_analysis(),
            'anomaly_detection': self._detect_anomalies(),
            'correlation_analysis': self._analyze_correlations(),
            'distribution_analysis': self._analyze_distributions()
        }

        # キャッシュの更新
        self._statistics_cache = summary
        self._cache_timestamp = datetime.now()

        return summary

    def _calculate_basic_statistics(self) -> dict[str, Any]:
        """基本統計量の計算"""
        if not self.validation_results:
            return {}

        # 実行時間の統計
        execution_times = [result.execution_time for result in self.validation_results]
        execution_stats = self._calculate_statistical_summary(execution_times).to_dict()

        # メモリ使用量の統計
        memory_usages = [result.memory_usage for result in self.validation_results]
        memory_stats = self._calculate_statistical_summary(memory_usages).to_dict()

        # 成功率の計算
        total_tests = len(self.validation_results)
        successful_tests = sum(1 for result in self.validation_results if result.success)
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0

        # テストカテゴリ別統計
        category_stats = self._calculate_category_statistics()

        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': total_tests - successful_tests,
            'overall_success_rate': success_rate,
            'execution_time_stats': execution_stats,
            'memory_usage_stats': memory_stats,
            'category_statistics': category_stats
        }

    def _calculate_statistical_summary(self, values: list[float]) -> StatisticalSummary:
        """統計サマリーの計算"""
        if not values:
            return StatisticalSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        np_values = np.array(values)

        return StatisticalSummary(
            count=len(values),
            mean=float(np.mean(np_values)),
            median=float(np.median(np_values)),
            std_dev=float(np.std(np_values)),
            min_value=float(np.min(np_values)),
            max_value=float(np.max(np_values)),
            percentile_25=float(np.percentile(np_values, 25)),
            percentile_75=float(np.percentile(np_values, 75)),
            percentile_95=float(np.percentile(np_values, 95)),
            percentile_99=float(np.percentile(np_values, 99))
        )

    def _calculate_category_statistics(self) -> dict[str, dict[str, Any]]:
        """テストカテゴリ別統計の計算"""
        category_data = defaultdict(list)

        # カテゴリ別にデータを分類
        for result in self.validation_results:
            category = self._extract_category(result.test_name)
            category_data[category].append(result)

        category_stats = {}
        for category, results in category_data.items():
            total = len(results)
            successful = sum(1 for r in results if r.success)

            execution_times = [r.execution_time for r in results]
            memory_usages = [r.memory_usage for r in results]

            category_stats[category] = {
                'total_tests': total,
                'successful_tests': successful,
                'success_rate': (successful / total) * 100 if total > 0 else 0,
                'avg_execution_time': statistics.mean(execution_times) if execution_times else 0,
                'avg_memory_usage': statistics.mean(memory_usages) if memory_usages else 0
            }

        return category_stats

    def _extract_category(self, test_name: str) -> str:
        """テスト名からカテゴリを抽出"""
        if 'startup' in test_name.lower():
            return 'startup'
        elif 'document' in test_name.lower():
            return 'document_processing'
        elif 'search' in test_name.lower():
            return 'search'
        elif 'gui' in test_name.lower():
            return 'gui'
        elif 'performance' in test_name.lower():
            return 'performance'
        elif 'memory' in test_name.lower():
            return 'memory'
        elif 'error' in test_name.lower():
            return 'error_handling'
        else:
            return 'other'

    def _analyze_performance_trends(self) -> dict[str, Any]:
        """パフォーマンストレンドの分析"""
        if not self.performance_metrics:
            return {}

        trends = {}

        # CPU使用率のトレンド
        cpu_values = [m.get('cpu_percent', 0) for m in self.performance_metrics]
        if cpu_values:
            trends['cpu_usage'] = self._calculate_trend(cpu_values)

        # メモリ使用率のトレンド
        memory_values = [m.get('memory_percent', 0) for m in self.performance_metrics]
        if memory_values:
            trends['memory_usage'] = self._calculate_trend(memory_values)

        return trends

    def _calculate_trend(self, values: list[float]) -> TrendAnalysis:
        """トレンドの計算"""
        if len(values) < 2:
            return TrendAnalysis(0, 0, 0, 1, 0, 'stable', 0)

        x = np.arange(len(values))
        y = np.array(values)

        # 線形回帰
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # トレンド方向の判定
        if abs(slope) < 0.01:  # 閾値は調整可能
            trend_direction = 'stable'
        elif slope > 0:
            trend_direction = 'increasing'
        else:
            trend_direction = 'decreasing'

        # 信頼度の計算（R²値）
        confidence_level = r_value ** 2

        return TrendAnalysis(
            slope=slope,
            intercept=intercept,
            r_value=r_value,
            p_value=p_value,
            std_err=std_err,
            trend_direction=trend_direction,
            confidence_level=confidence_level
        )

    def _calculate_quality_metrics(self) -> dict[str, float]:
        """品質指標の計算"""
        if not self.validation_results:
            return {}

        # 基本品質指標
        total_tests = len(self.validation_results)
        successful_tests = sum(1 for result in self.validation_results if result.success)

        # 実行時間の安定性（変動係数）
        execution_times = [result.execution_time for result in self.validation_results]
        execution_cv = (statistics.stdev(execution_times) / statistics.mean(execution_times)) if len(execution_times) > 1 and statistics.mean(execution_times) > 0 else 0

        # メモリ使用量の安定性
        memory_usages = [result.memory_usage for result in self.validation_results]
        memory_cv = (statistics.stdev(memory_usages) / statistics.mean(memory_usages)) if len(memory_usages) > 1 and statistics.mean(memory_usages) > 0 else 0

        # 品質スコアの計算（0-100）
        success_score = (successful_tests / total_tests) * 100
        stability_score = max(0, 100 - (execution_cv * 100))  # 変動係数が小さいほど高スコア

        overall_quality_score = (success_score * 0.7 + stability_score * 0.3)

        return {
            'success_rate': success_score,
            'execution_time_stability': 100 - (execution_cv * 100),
            'memory_usage_stability': 100 - (memory_cv * 100),
            'overall_quality_score': overall_quality_score,
            'execution_time_cv': execution_cv,
            'memory_usage_cv': memory_cv
        }

    def _perform_trend_analysis(self) -> dict[str, Any]:
        """トレンド分析の実行"""
        trends = {}

        for metric_name, time_series in self.time_series_data.items():
            if len(time_series) >= 3:  # 最低3データポイント必要
                values = [value for _, value in time_series]
                trend = self._calculate_trend(values)
                trends[metric_name] = {
                    'direction': trend.trend_direction,
                    'slope': trend.slope,
                    'confidence': trend.confidence_level,
                    'p_value': trend.p_value
                }

        return trends

    def _detect_anomalies(self) -> dict[str, list[dict[str, Any]]]:
        """異常値の検出"""
        anomalies = {}

        # 実行時間の異常値検出
        execution_times = [result.execution_time for result in self.validation_results]
        if execution_times:
            execution_anomalies = self._detect_outliers(execution_times, 'execution_time')
            if execution_anomalies:
                anomalies['execution_time'] = execution_anomalies

        # メモリ使用量の異常値検出
        memory_usages = [result.memory_usage for result in self.validation_results]
        if memory_usages:
            memory_anomalies = self._detect_outliers(memory_usages, 'memory_usage')
            if memory_anomalies:
                anomalies['memory_usage'] = memory_anomalies

        return anomalies

    def _detect_outliers(self, values: list[float], metric_name: str) -> list[dict[str, Any]]:
        """外れ値の検出（IQR法）"""
        if len(values) < 4:
            return []

        np_values = np.array(values)
        q1 = np.percentile(np_values, 25)
        q3 = np.percentile(np_values, 75)
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = []
        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                outliers.append({
                    'index': i,
                    'value': value,
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound,
                    'deviation_factor': max(
                        (lower_bound - value) / iqr if value < lower_bound else 0,
                        (value - upper_bound) / iqr if value > upper_bound else 0
                    )
                })

        return outliers

    def _analyze_correlations(self) -> dict[str, float]:
        """相関分析"""
        if len(self.validation_results) < 3:
            return {}

        correlations = {}

        # 実行時間とメモリ使用量の相関
        execution_times = [result.execution_time for result in self.validation_results]
        memory_usages = [result.memory_usage for result in self.validation_results]

        if execution_times and memory_usages:
            correlation, p_value = stats.pearsonr(execution_times, memory_usages)
            correlations['execution_time_vs_memory'] = {
                'correlation': correlation,
                'p_value': p_value,
                'significance': 'significant' if p_value < 0.05 else 'not_significant'
            }

        return correlations

    def _analyze_distributions(self) -> dict[str, dict[str, Any]]:
        """分布分析"""
        distributions = {}

        # 実行時間の分布分析
        execution_times = [result.execution_time for result in self.validation_results]
        if execution_times:
            distributions['execution_time'] = self._analyze_single_distribution(execution_times)

        # メモリ使用量の分布分析
        memory_usages = [result.memory_usage for result in self.validation_results]
        if memory_usages:
            distributions['memory_usage'] = self._analyze_single_distribution(memory_usages)

        return distributions

    def _analyze_single_distribution(self, values: list[float]) -> dict[str, Any]:
        """単一分布の分析"""
        np_values = np.array(values)

        # 正規性検定（Shapiro-Wilk検定）
        if len(values) >= 3:
            shapiro_stat, shapiro_p = stats.shapiro(np_values)
            is_normal = shapiro_p > 0.05
        else:
            shapiro_stat, shapiro_p = 0, 1
            is_normal = False

        # 歪度と尖度
        skewness = float(stats.skew(np_values))
        kurtosis = float(stats.kurtosis(np_values))

        return {
            'is_normal_distribution': is_normal,
            'shapiro_statistic': shapiro_stat,
            'shapiro_p_value': shapiro_p,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'distribution_type': self._classify_distribution(skewness, kurtosis, is_normal)
        }

    def _classify_distribution(self, skewness: float, kurtosis: float, is_normal: bool) -> str:
        """分布の分類"""
        if is_normal:
            return 'normal'
        elif abs(skewness) > 1:
            return 'highly_skewed'
        elif abs(skewness) > 0.5:
            return 'moderately_skewed'
        elif abs(kurtosis) > 1:
            return 'heavy_tailed' if kurtosis > 0 else 'light_tailed'
        else:
            return 'approximately_normal'

    def _is_cache_valid(self) -> bool:
        """キャッシュの有効性チェック"""
        if not self._cache_timestamp:
            return False

        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_validity_seconds

    def _invalidate_cache(self) -> None:
        """キャッシュの無効化"""
        self._statistics_cache.clear()
        self._cache_timestamp = None

    def export_statistics(self, file_path: str, format: str = 'json') -> None:
        """
        統計情報のエクスポート

        Args:
            file_path: 出力ファイルパス
            format: 出力形式（'json', 'csv'）
        """
        summary = self.get_summary()

        if format.lower() == 'json':
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        elif format.lower() == 'csv':
            # 基本統計のみCSV出力
            basic_stats = summary.get('basic_statistics', {})
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['指標', '値'])
                for key, value in basic_stats.items():
                    if isinstance(value, int | float | str):
                        writer.writerow([key, value])

        self.logger.info(f"統計情報を {format} 形式でエクスポートしました: {file_path}")

    def get_performance_baseline(self) -> dict[str, float]:
        """
        パフォーマンスベースラインの取得

        Returns:
            ベースライン指標の辞書
        """
        if not self.validation_results:
            return {}

        execution_times = [result.execution_time for result in self.validation_results]
        memory_usages = [result.memory_usage for result in self.validation_results]

        return {
            'baseline_execution_time_p95': float(np.percentile(execution_times, 95)) if execution_times else 0,
            'baseline_memory_usage_p95': float(np.percentile(memory_usages, 95)) if memory_usages else 0,
            'baseline_success_rate': (sum(1 for r in self.validation_results if r.success) / len(self.validation_results)) * 100
        }

    def cleanup(self) -> None:
        """統計データのクリーンアップ"""
        self.validation_results.clear()
        self.performance_metrics.clear()
        self.memory_metrics.clear()
        self.time_series_data.clear()
        self._invalidate_cache()

        self.logger.debug("統計データのクリーンアップが完了しました")
