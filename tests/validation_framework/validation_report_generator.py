"""
検証結果レポート生成システム

ValidationReportGeneratorクラスを実装して検証結果の包括的レポートを生成します。
サマリーレポート、詳細レポート、トレンド分析レポートの生成機能を提供します。
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

# 日本語フォント設定
rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False


@dataclass
class ReportGenerationConfig:
    """レポート生成設定"""

    output_directory: str
    report_name: str = "validation_report"
    include_charts: bool = True
    include_detailed_logs: bool = True
    include_trend_analysis: bool = True
    include_performance_graphs: bool = True
    include_error_analysis: bool = True
    chart_format: str = "png"  # png, svg, pdf
    report_formats: list[str] = None  # html, markdown, json

    def __post_init__(self):
        if self.report_formats is None:
            self.report_formats = ["html"]


@dataclass
class ValidationMetrics:
    """検証メトリクス"""

    test_name: str
    success: bool
    execution_time: float
    memory_usage: float
    cpu_usage: float
    error_message: str | None = None
    timestamp: datetime = None
    category: str = "general"

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""

    peak_cpu_percent: float
    average_cpu_percent: float
    peak_memory_mb: float
    average_memory_mb: float
    disk_read_mb: float
    disk_write_mb: float
    network_sent_mb: float
    network_received_mb: float
    monitoring_duration_seconds: float


@dataclass
class QualityIndicators:
    """品質指標"""

    success_rate: float
    average_execution_time: float
    memory_efficiency: float
    cpu_efficiency: float
    error_rate: float
    stability_score: float
    performance_score: float
    overall_quality_score: float


class ValidationReportGenerator:
    """
    検証結果レポート生成システム

    包括的な検証結果レポートを生成し、サマリーレポート、詳細レポート、
    トレンド分析レポート、パフォーマンスグラフ、エラーログ分析、
    品質指標の可視化機能を提供します。
    """

    def __init__(self, config: ReportGenerationConfig):
        """
        レポート生成システムの初期化

        Args:
            config: レポート生成設定
        """
        self.config = config
        self.logger = logging.getLogger(f"validation.{self.__class__.__name__}")

        # 出力ディレクトリの作成
        os.makedirs(self.config.output_directory, exist_ok=True)

        # 生成されたファイルの追跡
        self.generated_files: list[str] = []

        # 履歴データストレージ
        self.history_file = os.path.join(
            self.config.output_directory, "validation_history.json"
        )

        self.logger.info(
            f"ValidationReportGenerator を初期化しました: {self.config.output_directory}"
        )

    def generate_comprehensive_report(
        self,
        validation_results: list[ValidationMetrics],
        performance_data: PerformanceMetrics | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """
        包括的検証レポートの生成

        Args:
            validation_results: 検証結果のリスト
            performance_data: パフォーマンスデータ
            additional_data: 追加データ

        Returns:
            生成されたレポートファイルのパス辞書
        """
        self.logger.info("包括的検証レポートの生成を開始します")

        # データの分析
        analysis_results = self._analyze_validation_data(
            validation_results, performance_data, additional_data
        )

        # 品質指標の計算
        quality_indicators = self._calculate_quality_indicators(
            validation_results, performance_data
        )
        analysis_results["quality_indicators"] = asdict(quality_indicators)

        # 履歴データの保存
        self._save_to_history(analysis_results)

        generated_files = {}

        # サマリーレポートの生成
        summary_file = self._generate_summary_report(analysis_results)
        generated_files["summary_report"] = summary_file

        # 詳細レポートの生成
        for format_type in self.config.report_formats:
            if format_type == "html":
                detail_file = self._generate_detailed_html_report(analysis_results)
                generated_files["detailed_html_report"] = detail_file
            elif format_type == "markdown":
                detail_file = self._generate_detailed_markdown_report(analysis_results)
                generated_files["detailed_markdown_report"] = detail_file
            elif format_type == "json":
                detail_file = self._generate_detailed_json_report(analysis_results)
                generated_files["detailed_json_report"] = detail_file

        # トレンド分析レポートの生成
        if self.config.include_trend_analysis:
            trend_file = self._generate_trend_analysis_report(analysis_results)
            generated_files["trend_analysis_report"] = trend_file

        # パフォーマンスグラフの生成
        if self.config.include_performance_graphs:
            graph_files = self._generate_performance_graphs(analysis_results)
            generated_files.update(graph_files)

        # エラーログ分析レポートの生成
        if self.config.include_error_analysis:
            error_file = self._generate_error_analysis_report(analysis_results)
            generated_files["error_analysis_report"] = error_file

        # 品質指標可視化の生成
        quality_file = self._generate_quality_indicators_visualization(analysis_results)
        generated_files["quality_indicators_report"] = quality_file

        self.generated_files.extend(generated_files.values())

        self.logger.info(f"包括的レポート生成完了: {len(generated_files)}ファイル")
        return generated_files

    def _analyze_validation_data(
        self,
        validation_results: list[ValidationMetrics],
        performance_data: PerformanceMetrics | None,
        additional_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """検証データの詳細分析"""
        analysis = {
            "metadata": {
                "generation_time": datetime.now().isoformat(),
                "total_tests": len(validation_results),
                "report_name": self.config.report_name,
            },
            "summary": {},
            "test_results": {},
            "performance_analysis": {},
            "error_analysis": {},
            "category_analysis": {},
            "time_series_analysis": {},
        }

        if not validation_results:
            self.logger.warning("検証結果が空です")
            return analysis

        # 基本統計の計算
        total_tests = len(validation_results)
        passed_tests = sum(1 for result in validation_results if result.success)
        failed_tests = total_tests - passed_tests

        total_execution_time = sum(
            result.execution_time for result in validation_results
        )
        average_execution_time = (
            total_execution_time / total_tests if total_tests > 0 else 0
        )

        total_memory_usage = sum(result.memory_usage for result in validation_results)
        average_memory_usage = (
            total_memory_usage / total_tests if total_tests > 0 else 0
        )

        analysis["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (
                (passed_tests / total_tests * 100) if total_tests > 0 else 0
            ),
            "total_execution_time": total_execution_time,
            "average_execution_time": average_execution_time,
            "total_memory_usage": total_memory_usage,
            "average_memory_usage": average_memory_usage,
            "peak_memory_usage": (
                max(result.memory_usage for result in validation_results)
                if validation_results
                else 0
            ),
            "peak_cpu_usage": (
                max(result.cpu_usage for result in validation_results)
                if validation_results
                else 0
            ),
        }

        # カテゴリ別分析
        category_stats = {}
        for result in validation_results:
            category = result.category
            if category not in category_stats:
                category_stats[category] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "total_time": 0,
                    "total_memory": 0,
                }

            category_stats[category]["total"] += 1
            if result.success:
                category_stats[category]["passed"] += 1
            else:
                category_stats[category]["failed"] += 1

            category_stats[category]["total_time"] += result.execution_time
            category_stats[category]["total_memory"] += result.memory_usage

        # カテゴリ別平均値の計算
        for category, stats in category_stats.items():
            if stats["total"] > 0:
                stats["success_rate"] = (stats["passed"] / stats["total"]) * 100
                stats["average_time"] = stats["total_time"] / stats["total"]
                stats["average_memory"] = stats["total_memory"] / stats["total"]

        analysis["category_analysis"] = category_stats

        # 失敗したテストの詳細分析
        failed_tests_details = []
        for result in validation_results:
            if not result.success:
                failed_tests_details.append(
                    {
                        "test_name": result.test_name,
                        "category": result.category,
                        "error_message": result.error_message,
                        "execution_time": result.execution_time,
                        "memory_usage": result.memory_usage,
                        "timestamp": result.timestamp.isoformat(),
                    }
                )

        analysis["test_results"] = {
            "failed_tests": failed_tests_details,
            "failure_rate_by_category": {
                cat: (
                    (stats["failed"] / stats["total"] * 100)
                    if stats["total"] > 0
                    else 0
                )
                for cat, stats in category_stats.items()
            },
        }

        # パフォーマンス分析
        if performance_data:
            analysis["performance_analysis"] = {
                "cpu_usage": {
                    "peak_percent": performance_data.peak_cpu_percent,
                    "average_percent": performance_data.average_cpu_percent,
                    "efficiency": self._calculate_cpu_efficiency(
                        performance_data.average_cpu_percent
                    ),
                },
                "memory_usage": {
                    "peak_mb": performance_data.peak_memory_mb,
                    "average_mb": performance_data.average_memory_mb,
                    "efficiency": self._calculate_memory_efficiency(
                        performance_data.peak_memory_mb
                    ),
                },
                "disk_io": {
                    "read_mb": performance_data.disk_read_mb,
                    "write_mb": performance_data.disk_write_mb,
                    "total_mb": performance_data.disk_read_mb
                    + performance_data.disk_write_mb,
                },
                "network_io": {
                    "sent_mb": performance_data.network_sent_mb,
                    "received_mb": performance_data.network_received_mb,
                    "total_mb": performance_data.network_sent_mb
                    + performance_data.network_received_mb,
                },
                "monitoring_duration": performance_data.monitoring_duration_seconds,
            }

        # エラー分析
        error_patterns = {}
        for result in validation_results:
            if not result.success and result.error_message:
                # エラーメッセージのパターン分析
                error_type = self._classify_error_type(result.error_message)
                if error_type not in error_patterns:
                    error_patterns[error_type] = 0
                error_patterns[error_type] += 1

        analysis["error_analysis"] = {
            "error_patterns": error_patterns,
            "total_errors": len(failed_tests_details),
            "error_rate": (
                (len(failed_tests_details) / total_tests * 100)
                if total_tests > 0
                else 0
            ),
        }

        # 時系列分析
        if len(validation_results) > 1:
            time_series = self._analyze_time_series(validation_results)
            analysis["time_series_analysis"] = time_series

        return analysis

    def _calculate_quality_indicators(
        self,
        validation_results: list[ValidationMetrics],
        performance_data: PerformanceMetrics | None,
    ) -> QualityIndicators:
        """品質指標の計算"""
        if not validation_results:
            return QualityIndicators(0, 0, 0, 0, 0, 0, 0, 0)

        # 基本指標
        total_tests = len(validation_results)
        passed_tests = sum(1 for result in validation_results if result.success)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        average_execution_time = (
            sum(result.execution_time for result in validation_results) / total_tests
        )
        error_rate = 100 - success_rate

        # 効率性指標
        memory_efficiency = self._calculate_memory_efficiency(
            max(result.memory_usage for result in validation_results)
            if validation_results
            else 0
        )

        cpu_efficiency = self._calculate_cpu_efficiency(
            sum(result.cpu_usage for result in validation_results) / total_tests
            if validation_results
            else 0
        )

        # 安定性スコア（実行時間の標準偏差から計算）
        execution_times = [result.execution_time for result in validation_results]
        time_std = np.std(execution_times) if len(execution_times) > 1 else 0
        stability_score = (
            max(0, 100 - (time_std / average_execution_time * 100))
            if average_execution_time > 0
            else 100
        )

        # パフォーマンススコア
        performance_score = self._calculate_performance_score(
            average_execution_time, memory_efficiency, cpu_efficiency
        )

        # 総合品質スコア
        overall_quality_score = (
            success_rate * 0.4  # 成功率の重み: 40%
            + stability_score * 0.2  # 安定性の重み: 20%
            + performance_score * 0.2  # パフォーマンスの重み: 20%
            + (memory_efficiency + cpu_efficiency) / 2 * 0.2  # 効率性の重み: 20%
        )

        return QualityIndicators(
            success_rate=success_rate,
            average_execution_time=average_execution_time,
            memory_efficiency=memory_efficiency,
            cpu_efficiency=cpu_efficiency,
            error_rate=error_rate,
            stability_score=stability_score,
            performance_score=performance_score,
            overall_quality_score=overall_quality_score,
        )

    def _calculate_cpu_efficiency(self, cpu_usage_percent: float) -> float:
        """CPU効率性の計算"""
        if cpu_usage_percent <= 50:
            return 100
        elif cpu_usage_percent <= 70:
            return 100 - (cpu_usage_percent - 50) * 2
        elif cpu_usage_percent <= 90:
            return 60 - (cpu_usage_percent - 70) * 2
        else:
            return max(0, 20 - (cpu_usage_percent - 90) * 2)

    def _calculate_memory_efficiency(self, memory_usage_mb: float) -> float:
        """メモリ効率性の計算"""
        if memory_usage_mb <= 512:
            return 100
        elif memory_usage_mb <= 1024:
            return 100 - (memory_usage_mb - 512) / 512 * 30
        elif memory_usage_mb <= 2048:
            return 70 - (memory_usage_mb - 1024) / 1024 * 40
        else:
            return max(0, 30 - (memory_usage_mb - 2048) / 1024 * 30)

    def _calculate_performance_score(
        self, avg_time: float, memory_eff: float, cpu_eff: float
    ) -> float:
        """パフォーマンススコアの計算"""
        # 実行時間スコア
        if avg_time <= 5:
            time_score = 100
        elif avg_time <= 15:
            time_score = 100 - (avg_time - 5) * 5
        elif avg_time <= 30:
            time_score = 50 - (avg_time - 15) * 2
        else:
            time_score = max(0, 20 - (avg_time - 30) * 0.5)

        # 総合パフォーマンススコア
        return time_score * 0.5 + memory_eff * 0.25 + cpu_eff * 0.25

    def _classify_error_type(self, error_message: str) -> str:
        """エラーメッセージの分類"""
        if not error_message:
            return "Unknown"

        error_message_lower = error_message.lower()

        if "timeout" in error_message_lower or "タイムアウト" in error_message_lower:
            return "Timeout"
        elif "memory" in error_message_lower or "メモリ" in error_message_lower:
            return "Memory"
        elif "connection" in error_message_lower or "接続" in error_message_lower:
            return "Connection"
        elif "file" in error_message_lower or "ファイル" in error_message_lower:
            return "File"
        elif "permission" in error_message_lower or "権限" in error_message_lower:
            return "Permission"
        elif (
            "assertion" in error_message_lower or "アサーション" in error_message_lower
        ):
            return "Assertion"
        else:
            return "Other"

    def _analyze_time_series(
        self, validation_results: list[ValidationMetrics]
    ) -> dict[str, Any]:
        """時系列分析"""
        # タイムスタンプでソート
        sorted_results = sorted(validation_results, key=lambda x: x.timestamp)

        # 時系列データの抽出
        timestamps = [result.timestamp for result in sorted_results]
        execution_times = [result.execution_time for result in sorted_results]
        memory_usages = [result.memory_usage for result in sorted_results]
        success_flags = [1 if result.success else 0 for result in sorted_results]

        # トレンド分析
        time_trend = self._calculate_trend(execution_times)
        memory_trend = self._calculate_trend(memory_usages)
        success_trend = self._calculate_trend(success_flags)

        return {
            "execution_time_trend": time_trend,
            "memory_usage_trend": memory_trend,
            "success_rate_trend": success_trend,
            "data_points": len(sorted_results),
            "time_span_minutes": (
                (timestamps[-1] - timestamps[0]).total_seconds() / 60
                if len(timestamps) > 1
                else 0
            ),
        }

    def _calculate_trend(self, values: list[float]) -> str:
        """トレンドの計算"""
        if len(values) < 2:
            return "insufficient_data"

        # 線形回帰による傾向分析
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]

        if abs(slope) < 0.01:
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"

    def _save_to_history(self, analysis_results: dict[str, Any]) -> None:
        """履歴データの保存"""
        try:
            # 既存の履歴データを読み込み
            history_data = []
            if os.path.exists(self.history_file):
                with open(self.history_file, encoding="utf-8") as f:
                    history_data = json.load(f)

            # 新しいデータを追加
            history_entry = {
                "timestamp": analysis_results["metadata"]["generation_time"],
                "summary": analysis_results["summary"],
                "quality_indicators": analysis_results.get("quality_indicators", {}),
                "category_analysis": analysis_results.get("category_analysis", {}),
                "error_analysis": analysis_results.get("error_analysis", {}),
            }

            history_data.append(history_entry)

            # 履歴データの制限（最新100件まで保持）
            if len(history_data) > 100:
                history_data = history_data[-100:]

            # 履歴データを保存
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)

            self.logger.debug(f"履歴データを保存しました: {len(history_data)}件")

        except Exception as e:
            self.logger.error(f"履歴データの保存に失敗しました: {e}")

    def _generate_summary_report(self, analysis_results: dict[str, Any]) -> str:
        """サマリーレポートの生成"""
        summary = analysis_results.get("summary", {})
        quality = analysis_results.get("quality_indicators", {})

        report_content = f"""DocMind 検証サマリーレポート
{'=' * 50}

生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
レポート名: {self.config.report_name}

【基本統計】
総テスト数: {summary.get('total_tests', 0)}
成功テスト数: {summary.get('passed_tests', 0)}
失敗テスト数: {summary.get('failed_tests', 0)}
成功率: {summary.get('success_rate', 0):.1f}%

【パフォーマンス】
総実行時間: {summary.get('total_execution_time', 0):.2f}秒
平均実行時間: {summary.get('average_execution_time', 0):.2f}秒
最大メモリ使用量: {summary.get('peak_memory_usage', 0):.1f}MB
平均メモリ使用量: {summary.get('average_memory_usage', 0):.1f}MB

【品質指標】
総合品質スコア: {quality.get('overall_quality_score', 0):.1f}/100
安定性スコア: {quality.get('stability_score', 0):.1f}/100
パフォーマンススコア: {quality.get('performance_score', 0):.1f}/100
メモリ効率性: {quality.get('memory_efficiency', 0):.1f}/100
CPU効率性: {quality.get('cpu_efficiency', 0):.1f}/100

【品質評価】
"""

        # 品質評価の判定
        overall_score = quality.get("overall_quality_score", 0)
        if overall_score >= 90:
            report_content += "🟢 優秀 - すべての要件を満たしています\n"
        elif overall_score >= 80:
            report_content += "🟡 良好 - 軽微な改善の余地があります\n"
        elif overall_score >= 70:
            report_content += "🟠 普通 - いくつかの問題があります\n"
        else:
            report_content += "🔴 要改善 - 重要な問題があります\n"

        # カテゴリ別分析
        category_analysis = analysis_results.get("category_analysis", {})
        if category_analysis:
            report_content += "\n【カテゴリ別結果】\n"
            for category, stats in category_analysis.items():
                report_content += f"- {category}: {stats.get('success_rate', 0):.1f}% ({stats.get('passed', 0)}/{stats.get('total', 0)})\n"

        # エラー分析
        error_analysis = analysis_results.get("error_analysis", {})
        if error_analysis.get("error_patterns"):
            report_content += "\n【主要エラーパターン】\n"
            for error_type, count in error_analysis["error_patterns"].items():
                report_content += f"- {error_type}: {count}件\n"

        report_path = os.path.join(
            self.config.output_directory, f"{self.config.report_name}_summary.txt"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        self.logger.info(f"サマリーレポートを生成しました: {report_path}")
        return report_path

    def _generate_detailed_html_report(self, analysis_results: dict[str, Any]) -> str:
        """詳細HTMLレポートの生成"""
        summary = analysis_results.get("summary", {})
        quality = analysis_results.get("quality_indicators", {})
        category_analysis = analysis_results.get("category_analysis", {})
        error_analysis = analysis_results.get("error_analysis", {})
        performance_analysis = analysis_results.get("performance_analysis", {})

        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocMind 詳細検証レポート</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 4px solid #3498db;
            padding-bottom: 15px;
            text-align: center;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        h3 {{
            color: #2c3e50;
            margin-top: 25px;
        }}
        .header-info {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-card {{
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .metric-label {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .excellent {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; }}
        .good {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }}
        .average {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; }}
        .poor {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; }}
        .section-card {{
            background: #ffffff;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background-color: #495057;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .progress-bar {{
            width: 100%;
            height: 20px;
            background-color: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
            transition: width 0.3s ease;
        }}
        .error-item {{
            background: #fff5f5;
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 DocMind 詳細検証レポート</h1>

        <div class="header-info">
            <h3 style="margin: 0; color: white;">検証実行情報</h3>
            <p style="margin: 10px 0 0 0;">
                <strong>生成日時:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')} |
                <strong>レポート名:</strong> {self.config.report_name}
            </p>
        </div>

        <h2>🎯 品質指標ダッシュボード</h2>
        <div class="metrics-grid">
        """

        # 品質指標カードの生成
        overall_score = quality.get("overall_quality_score", 0)
        card_class = self._get_quality_card_class(overall_score)

        html_content += f"""
            <div class="metric-card {card_class}">
                <div class="metric-value">{overall_score:.1f}</div>
                <div class="metric-label">総合品質スコア</div>
            </div>
            <div class="metric-card {self._get_quality_card_class(summary.get('success_rate', 0))}">
                <div class="metric-value">{summary.get('success_rate', 0):.1f}%</div>
                <div class="metric-label">成功率</div>
            </div>
            <div class="metric-card {self._get_quality_card_class(quality.get('stability_score', 0))}">
                <div class="metric-value">{quality.get('stability_score', 0):.1f}</div>
                <div class="metric-label">安定性スコア</div>
            </div>
            <div class="metric-card {self._get_quality_card_class(quality.get('performance_score', 0))}">
                <div class="metric-value">{quality.get('performance_score', 0):.1f}</div>
                <div class="metric-label">パフォーマンススコア</div>
            </div>
        </div>

        <h2>📈 基本統計</h2>
        <div class="section-card">
            <table>
                <tr>
                    <th>項目</th>
                    <th>値</th>
                    <th>評価</th>
                </tr>
                <tr>
                    <td>総テスト数</td>
                    <td>{summary.get('total_tests', 0)}</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td>成功テスト数</td>
                    <td>{summary.get('passed_tests', 0)}</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td>失敗テスト数</td>
                    <td>{summary.get('failed_tests', 0)}</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td>平均実行時間</td>
                    <td>{summary.get('average_execution_time', 0):.2f}秒</td>
                    <td>{'良好' if summary.get('average_execution_time', 0) < 10 else '要改善'}</td>
                </tr>
                <tr>
                    <td>最大メモリ使用量</td>
                    <td>{summary.get('peak_memory_usage', 0):.1f}MB</td>
                    <td>{'良好' if summary.get('peak_memory_usage', 0) < 1024 else '要改善'}</td>
                </tr>
            </table>
        </div>
        """

        # カテゴリ別分析
        if category_analysis:
            html_content += """
        <h2>📂 カテゴリ別分析</h2>
        <div class="section-card">
            """
            for category, stats in category_analysis.items():
                success_rate = stats.get("success_rate", 0)
                html_content += f"""
            <h3>{category}</h3>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {success_rate}%"></div>
            </div>
            <p><strong>成功率:</strong> {success_rate:.1f}% ({stats.get('passed', 0)}/{stats.get('total', 0)})</p>
            <p><strong>平均実行時間:</strong> {stats.get('average_time', 0):.2f}秒</p>
            <p><strong>平均メモリ使用量:</strong> {stats.get('average_memory', 0):.1f}MB</p>
                """
            html_content += """
        </div>
            """

        # パフォーマンス分析
        if performance_analysis:
            cpu_data = performance_analysis.get("cpu_usage", {})
            memory_data = performance_analysis.get("memory_usage", {})

            html_content += f"""
        <h2>⚡ パフォーマンス分析</h2>
        <div class="section-card">
            <h3>CPU使用率</h3>
            <p><strong>最大:</strong> {cpu_data.get('peak_percent', 0):.1f}%</p>
            <p><strong>平均:</strong> {cpu_data.get('average_percent', 0):.1f}%</p>
            <p><strong>効率性:</strong> {cpu_data.get('efficiency', 0):.1f}/100</p>

            <h3>メモリ使用量</h3>
            <p><strong>最大:</strong> {memory_data.get('peak_mb', 0):.1f}MB</p>
            <p><strong>平均:</strong> {memory_data.get('average_mb', 0):.1f}MB</p>
            <p><strong>効率性:</strong> {memory_data.get('efficiency', 0):.1f}/100</p>
        </div>
            """

        # エラー分析
        error_patterns = error_analysis.get("error_patterns", {})
        failed_tests = analysis_results.get("test_results", {}).get("failed_tests", [])

        if error_patterns or failed_tests:
            html_content += """
        <h2>❌ エラー分析</h2>
        <div class="section-card">
            """

            if error_patterns:
                html_content += """
            <h3>エラーパターン分布</h3>
            <table>
                <tr><th>エラータイプ</th><th>発生回数</th><th>割合</th></tr>
                """
                total_errors = sum(error_patterns.values())
                for error_type, count in error_patterns.items():
                    percentage = (count / total_errors * 100) if total_errors > 0 else 0
                    html_content += f"""
                <tr>
                    <td>{error_type}</td>
                    <td>{count}</td>
                    <td>{percentage:.1f}%</td>
                </tr>
                    """
                html_content += "</table>"

            if failed_tests:
                html_content += """
            <h3>失敗したテストの詳細</h3>
                """
                for test in failed_tests[:10]:  # 最大10件表示
                    html_content += f"""
            <div class="error-item">
                <h4>{test.get('test_name', 'Unknown Test')}</h4>
                <p><strong>カテゴリ:</strong> {test.get('category', 'Unknown')}</p>
                <p><strong>エラーメッセージ:</strong> {test.get('error_message', 'No message')}</p>
                <p><strong>実行時間:</strong> {test.get('execution_time', 0):.2f}秒</p>
                <p><strong>メモリ使用量:</strong> {test.get('memory_usage', 0):.2f}MB</p>
            </div>
                    """

            html_content += """
        </div>
            """

        html_content += f"""
        <div class="footer">
            <p>このレポートは DocMind 検証システムによって自動生成されました。</p>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """

        report_path = os.path.join(
            self.config.output_directory, f"{self.config.report_name}_detailed.html"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"詳細HTMLレポートを生成しました: {report_path}")
        return report_path

    def _get_quality_card_class(self, score: float) -> str:
        """品質スコアに基づくカードクラスの取得"""
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "good"
        elif score >= 70:
            return "average"
        else:
            return "poor"

    def _generate_detailed_markdown_report(
        self, analysis_results: dict[str, Any]
    ) -> str:
        """詳細Markdownレポートの生成"""
        summary = analysis_results.get("summary", {})
        quality = analysis_results.get("quality_indicators", {})
        category_analysis = analysis_results.get("category_analysis", {})

        markdown_content = f"""# DocMind 詳細検証レポート

**生成日時:** {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
**レポート名:** {self.config.report_name}

## 📊 品質指標サマリー

| 指標 | 値 | 評価 |
|------|----|----- |
| 総合品質スコア | {quality.get('overall_quality_score', 0):.1f}/100 | {self._get_quality_rating(quality.get('overall_quality_score', 0))} |
| 成功率 | {summary.get('success_rate', 0):.1f}% | {self._get_quality_rating(summary.get('success_rate', 0))} |
| 安定性スコア | {quality.get('stability_score', 0):.1f}/100 | {self._get_quality_rating(quality.get('stability_score', 0))} |
| パフォーマンススコア | {quality.get('performance_score', 0):.1f}/100 | {self._get_quality_rating(quality.get('performance_score', 0))} |

## 📈 基本統計

- **総テスト数:** {summary.get('total_tests', 0)}
- **成功テスト数:** {summary.get('passed_tests', 0)}
- **失敗テスト数:** {summary.get('failed_tests', 0)}
- **成功率:** {summary.get('success_rate', 0):.1f}%
- **総実行時間:** {summary.get('total_execution_time', 0):.2f}秒
- **平均実行時間:** {summary.get('average_execution_time', 0):.2f}秒
- **最大メモリ使用量:** {summary.get('peak_memory_usage', 0):.1f}MB
- **平均メモリ使用量:** {summary.get('average_memory_usage', 0):.1f}MB

"""

        # カテゴリ別分析
        if category_analysis:
            markdown_content += "## 📂 カテゴリ別分析\n\n"
            markdown_content += (
                "| カテゴリ | 成功率 | 成功/総数 | 平均実行時間 | 平均メモリ使用量 |\n"
            )
            markdown_content += (
                "|----------|--------|-----------|--------------|------------------|\n"
            )

            for category, stats in category_analysis.items():
                markdown_content += f"| {category} | {stats.get('success_rate', 0):.1f}% | {stats.get('passed', 0)}/{stats.get('total', 0)} | {stats.get('average_time', 0):.2f}s | {stats.get('average_memory', 0):.1f}MB |\n"

        # エラー分析
        error_analysis = analysis_results.get("error_analysis", {})
        error_patterns = error_analysis.get("error_patterns", {})
        if error_patterns:
            markdown_content += "\n## ❌ エラーパターン分析\n\n"
            markdown_content += "| エラータイプ | 発生回数 | 割合 |\n"
            markdown_content += "|--------------|----------|------|\n"

            total_errors = sum(error_patterns.values())
            for error_type, count in error_patterns.items():
                percentage = (count / total_errors * 100) if total_errors > 0 else 0
                markdown_content += f"| {error_type} | {count} | {percentage:.1f}% |\n"

        # 失敗したテストの詳細
        failed_tests = analysis_results.get("test_results", {}).get("failed_tests", [])
        if failed_tests:
            markdown_content += "\n## 🔍 失敗したテストの詳細\n\n"
            for i, test in enumerate(failed_tests[:5], 1):  # 最大5件表示
                markdown_content += (
                    f"### {i}. {test.get('test_name', 'Unknown Test')}\n\n"
                )
                markdown_content += (
                    f"- **カテゴリ:** {test.get('category', 'Unknown')}\n"
                )
                markdown_content += f"- **エラーメッセージ:** {test.get('error_message', 'No message')}\n"
                markdown_content += (
                    f"- **実行時間:** {test.get('execution_time', 0):.2f}秒\n"
                )
                markdown_content += (
                    f"- **メモリ使用量:** {test.get('memory_usage', 0):.2f}MB\n\n"
                )

        report_path = os.path.join(
            self.config.output_directory, f"{self.config.report_name}_detailed.md"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        self.logger.info(f"詳細Markdownレポートを生成しました: {report_path}")
        return report_path

    def _get_quality_rating(self, score: float) -> str:
        """品質評価の取得"""
        if score >= 90:
            return "優秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "普通"
        else:
            return "要改善"

    def _generate_detailed_json_report(self, analysis_results: dict[str, Any]) -> str:
        """詳細JSONレポートの生成"""
        report_data = {
            "metadata": {
                "report_name": self.config.report_name,
                "generation_time": datetime.now().isoformat(),
                "generator_version": "1.0.0",
                "config": asdict(self.config),
            },
            "analysis_results": analysis_results,
        }

        report_path = os.path.join(
            self.config.output_directory, f"{self.config.report_name}_detailed.json"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(f"詳細JSONレポートを生成しました: {report_path}")
        return report_path

    def _generate_trend_analysis_report(self, analysis_results: dict[str, Any]) -> str:
        """トレンド分析レポートの生成"""
        # 履歴データの読み込み
        historical_data = self._load_historical_data()

        if len(historical_data) < 2:
            self.logger.warning("トレンド分析に十分な履歴データがありません")
            return self._generate_insufficient_data_report("trend_analysis")

        # トレンド分析の実行
        trend_analysis = self._perform_trend_analysis(historical_data, analysis_results)

        # HTMLレポートの生成
        html_content = self._create_trend_analysis_html(trend_analysis)

        report_path = os.path.join(
            self.config.output_directory,
            f"{self.config.report_name}_trend_analysis.html",
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"トレンド分析レポートを生成しました: {report_path}")
        return report_path

    def _load_historical_data(self) -> list[dict[str, Any]]:
        """履歴データの読み込み"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, encoding="utf-8") as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"履歴データの読み込みに失敗しました: {e}")
            return []

    def _perform_trend_analysis(
        self, historical_data: list[dict[str, Any]], current_data: dict[str, Any]
    ) -> dict[str, Any]:
        """トレンド分析の実行"""
        # 時系列データの抽出
        timestamps = []
        success_rates = []
        execution_times = []
        memory_usages = []
        quality_scores = []

        for data in historical_data:
            timestamps.append(data.get("timestamp", ""))
            summary = data.get("summary", {})
            quality = data.get("quality_indicators", {})

            success_rates.append(summary.get("success_rate", 0))
            execution_times.append(summary.get("average_execution_time", 0))
            memory_usages.append(summary.get("peak_memory_usage", 0))
            quality_scores.append(quality.get("overall_quality_score", 0))

        # 現在のデータを追加
        timestamps.append(current_data["metadata"]["generation_time"])
        current_summary = current_data.get("summary", {})
        current_quality = current_data.get("quality_indicators", {})

        success_rates.append(current_summary.get("success_rate", 0))
        execution_times.append(current_summary.get("average_execution_time", 0))
        memory_usages.append(current_summary.get("peak_memory_usage", 0))
        quality_scores.append(current_quality.get("overall_quality_score", 0))

        # トレンド計算
        success_trend = self._calculate_trend(success_rates)
        time_trend = self._calculate_trend(execution_times)
        memory_trend = self._calculate_trend(memory_usages)
        quality_trend = self._calculate_trend(quality_scores)

        # 変化率の計算
        def calculate_change_rate(values):
            if len(values) < 2:
                return 0
            return ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0

        return {
            "data_points": len(timestamps),
            "time_span_days": self._calculate_time_span_days(timestamps),
            "trends": {
                "success_rate": success_trend,
                "execution_time": time_trend,
                "memory_usage": memory_trend,
                "quality_score": quality_trend,
            },
            "change_rates": {
                "success_rate": calculate_change_rate(success_rates),
                "execution_time": calculate_change_rate(execution_times),
                "memory_usage": calculate_change_rate(memory_usages),
                "quality_score": calculate_change_rate(quality_scores),
            },
            "time_series": {
                "timestamps": timestamps,
                "success_rates": success_rates,
                "execution_times": execution_times,
                "memory_usages": memory_usages,
                "quality_scores": quality_scores,
            },
            "summary": self._generate_trend_summary(
                success_rates, execution_times, memory_usages, quality_scores
            ),
        }

    def _calculate_time_span_days(self, timestamps: list[str]) -> float:
        """時間スパンの計算（日数）"""
        if len(timestamps) < 2:
            return 0

        try:
            start_time = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
            return (end_time - start_time).total_seconds() / 86400  # 秒を日数に変換
        except Exception:
            return 0

    def _generate_trend_summary(
        self,
        success_rates: list[float],
        execution_times: list[float],
        memory_usages: list[float],
        quality_scores: list[float],
    ) -> str:
        """トレンドサマリーの生成"""
        if len(success_rates) < 2:
            return "データポイントが不足しているため、トレンド分析を実行できません。"

        summary_parts = []

        # 成功率のトレンド
        success_change = success_rates[-1] - success_rates[0]
        if abs(success_change) > 1:
            if success_change > 0:
                summary_parts.append(f"成功率が{success_change:.1f}%向上")
            else:
                summary_parts.append(f"成功率が{abs(success_change):.1f}%低下")

        # 実行時間のトレンド
        time_change = execution_times[-1] - execution_times[0]
        if abs(time_change) > 1:
            if time_change > 0:
                summary_parts.append(f"実行時間が{time_change:.1f}秒増加")
            else:
                summary_parts.append(f"実行時間が{abs(time_change):.1f}秒短縮")

        # 品質スコアのトレンド
        quality_change = quality_scores[-1] - quality_scores[0]
        if abs(quality_change) > 2:
            if quality_change > 0:
                summary_parts.append(f"品質スコアが{quality_change:.1f}ポイント向上")
            else:
                summary_parts.append(
                    f"品質スコアが{abs(quality_change):.1f}ポイント低下"
                )

        if not summary_parts:
            return (
                "主要な指標に大きな変化は見られません。安定した状態を維持しています。"
            )

        return "。".join(summary_parts) + "しています。"

    def _create_trend_analysis_html(self, trend_analysis: dict[str, Any]) -> str:
        """トレンド分析HTMLの作成"""
        time_series = trend_analysis.get("time_series", {})
        trends = trend_analysis.get("trends", {})
        change_rates = trend_analysis.get("change_rates", {})

        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocMind トレンド分析レポート</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 4px solid #e67e22;
            padding-bottom: 15px;
            text-align: center;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
        }}
        .trend-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .trend-card {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .improving {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; }}
        .stable {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }}
        .degrading {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .chart-title {{
            text-align: center;
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 20px;
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 DocMind トレンド分析レポート</h1>

        <div class="summary-card">
            <h3 style="margin: 0; color: white;">分析期間情報</h3>
            <p style="margin: 10px 0 0 0;">
                <strong>データポイント数:</strong> {trend_analysis.get('data_points', 0)} |
                <strong>分析期間:</strong> {trend_analysis.get('time_span_days', 0):.1f}日間
            </p>
            <p style="margin: 10px 0 0 0; font-size: 1.1em;">{trend_analysis.get('summary', '')}</p>
        </div>

        <h2>🎯 トレンド指標</h2>
        <div class="trend-grid">
        """

        # トレンド指標カードの生成
        trend_indicators = [
            (
                "成功率",
                trends.get("success_rate", "stable"),
                change_rates.get("success_rate", 0),
            ),
            (
                "実行時間",
                trends.get("execution_time", "stable"),
                change_rates.get("execution_time", 0),
            ),
            (
                "メモリ使用量",
                trends.get("memory_usage", "stable"),
                change_rates.get("memory_usage", 0),
            ),
            (
                "品質スコア",
                trends.get("quality_score", "stable"),
                change_rates.get("quality_score", 0),
            ),
        ]

        for name, trend, change_rate in trend_indicators:
            card_class = self._get_trend_card_class(trend, change_rate, name)
            trend_icon = self._get_trend_icon(trend)

            html += f"""
            <div class="trend-card {card_class}">
                <h3>{name}</h3>
                <p>{trend_icon} {self._get_trend_description(trend)}</p>
                <p><strong>変化率:</strong> {change_rate:+.1f}%</p>
            </div>
            """

        html += """
        </div>

        <h2>📊 時系列チャート</h2>
        """

        # チャートデータの準備
        timestamps = time_series.get("timestamps", [])
        dates = [ts[:10] for ts in timestamps]  # 日付部分のみ

        # 成功率チャート
        success_rates = time_series.get("success_rates", [])
        if success_rates:
            html += f"""
        <div class="chart-container">
            <div class="chart-title">成功率推移</div>
            <canvas id="successRateChart" width="400" height="200"></canvas>
        </div>

        <script>
        const successCtx = document.getElementById('successRateChart').getContext('2d');
        new Chart(successCtx, {{
            type: 'line',
            data: {{
                labels: {dates},
                datasets: [{{
                    label: '成功率 (%)',
                    data: {success_rates},
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }}
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: true
                    }}
                }}
            }}
        }});
        </script>
            """

        # 品質スコアチャート
        quality_scores = time_series.get("quality_scores", [])
        if quality_scores:
            html += f"""
        <div class="chart-container">
            <div class="chart-title">品質スコア推移</div>
            <canvas id="qualityScoreChart" width="400" height="200"></canvas>
        </div>

        <script>
        const qualityCtx = document.getElementById('qualityScoreChart').getContext('2d');
        new Chart(qualityCtx, {{
            type: 'line',
            data: {{
                labels: {dates},
                datasets: [{{
                    label: '品質スコア',
                    data: {quality_scores},
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    tension: 0.4,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: true
                    }}
                }}
            }}
        }});
        </script>
            """

        html += f"""
        <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d;">
            <p>このレポートは DocMind 検証システムによって自動生成されました。</p>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """

        return html

    def _get_trend_card_class(
        self, trend: str, change_rate: float, metric_name: str
    ) -> str:
        """トレンドカードクラスの取得"""
        if trend == "increasing":
            # 成功率と品質スコアの増加は良い、実行時間とメモリの増加は悪い
            if metric_name in ["成功率", "品質スコア"]:
                return "improving"
            else:
                return "degrading"
        elif trend == "decreasing":
            # 成功率と品質スコアの減少は悪い、実行時間とメモリの減少は良い
            if metric_name in ["成功率", "品質スコア"]:
                return "degrading"
            else:
                return "improving"
        else:
            return "stable"

    def _get_trend_icon(self, trend: str) -> str:
        """トレンドアイコンの取得"""
        if trend == "increasing":
            return "📈"
        elif trend == "decreasing":
            return "📉"
        else:
            return "📊"

    def _get_trend_description(self, trend: str) -> str:
        """トレンド説明の取得"""
        if trend == "increasing":
            return "増加傾向"
        elif trend == "decreasing":
            return "減少傾向"
        else:
            return "安定"

    def _generate_insufficient_data_report(self, report_type: str) -> str:
        """データ不足レポートの生成"""
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>DocMind {report_type.replace('_', ' ').title()} レポート</title>
</head>
<body>
    <h1>{report_type.replace('_', ' ').title()} レポート</h1>
    <p>このレポートを生成するには十分な履歴データがありません。</p>
    <p>複数回の検証実行後に再度お試しください。</p>
</body>
</html>
        """

        report_path = os.path.join(
            self.config.output_directory,
            f"{self.config.report_name}_{report_type}.html",
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return report_path

    def _generate_performance_graphs(
        self, analysis_results: dict[str, Any]
    ) -> dict[str, str]:
        """パフォーマンスグラフの生成"""
        graph_files = {}

        if not self.config.include_charts:
            return graph_files

        # グラフ出力ディレクトリの作成
        graph_dir = os.path.join(self.config.output_directory, "performance_graphs")
        os.makedirs(graph_dir, exist_ok=True)

        try:
            # カテゴリ別成功率グラフ
            category_analysis = analysis_results.get("category_analysis", {})
            if category_analysis:
                graph_path = self._create_category_success_rate_graph(
                    category_analysis, graph_dir
                )
                graph_files["category_success_rate"] = graph_path

            # 実行時間分布グラフ
            summary = analysis_results.get("summary", {})
            if summary:
                graph_path = self._create_execution_time_distribution_graph(
                    analysis_results, graph_dir
                )
                graph_files["execution_time_distribution"] = graph_path

            # メモリ使用量グラフ
            graph_path = self._create_memory_usage_graph(analysis_results, graph_dir)
            graph_files["memory_usage"] = graph_path

            # エラーパターン分布グラフ
            error_analysis = analysis_results.get("error_analysis", {})
            if error_analysis.get("error_patterns"):
                graph_path = self._create_error_pattern_graph(error_analysis, graph_dir)
                graph_files["error_patterns"] = graph_path

            # 品質指標レーダーチャート
            quality_indicators = analysis_results.get("quality_indicators", {})
            if quality_indicators:
                graph_path = self._create_quality_radar_chart(
                    quality_indicators, graph_dir
                )
                graph_files["quality_radar"] = graph_path

            # パフォーマンス推移グラフ（履歴データがある場合）
            historical_data = self._load_historical_data()
            if len(historical_data) >= 2:
                graph_path = self._create_performance_trend_graph(
                    historical_data, analysis_results, graph_dir
                )
                graph_files["performance_trend"] = graph_path

        except Exception as e:
            self.logger.error(f"パフォーマンスグラフ生成中にエラーが発生しました: {e}")

        return graph_files

    def _create_category_success_rate_graph(
        self, category_analysis: dict[str, Any], output_dir: str
    ) -> str:
        """カテゴリ別成功率グラフの作成"""
        fig, ax = plt.subplots(figsize=(12, 8))

        categories = list(category_analysis.keys())
        success_rates = [
            stats.get("success_rate", 0) for stats in category_analysis.values()
        ]

        # カラーマップの設定
        colors = plt.cm.RdYlGn([rate / 100 for rate in success_rates])

        bars = ax.bar(categories, success_rates, color=colors)

        # グラフの装飾
        ax.set_title("カテゴリ別成功率", fontsize=16, fontweight="bold", pad=20)
        ax.set_ylabel("成功率 (%)", fontsize=12)
        ax.set_xlabel("カテゴリ", fontsize=12)
        ax.set_ylim(0, 100)

        # 閾値線の追加
        ax.axhline(y=95, color="green", linestyle="--", alpha=0.7, label="目標値 (95%)")
        ax.axhline(
            y=80, color="orange", linestyle="--", alpha=0.7, label="警告値 (80%)"
        )

        # 値をバーの上に表示
        for bar, rate in zip(bars, success_rates, strict=False):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"{rate:.1f}%",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        # X軸ラベルの回転
        plt.xticks(rotation=45, ha="right")
        ax.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        graph_path = os.path.join(
            output_dir, f"category_success_rate.{self.config.chart_format}"
        )
        plt.savefig(graph_path, dpi=300, bbox_inches="tight")
        plt.close()

        return graph_path

    def _create_execution_time_distribution_graph(
        self, analysis_results: dict[str, Any], output_dir: str
    ) -> str:
        """実行時間分布グラフの作成"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # カテゴリ別平均実行時間
        category_analysis = analysis_results.get("category_analysis", {})
        if category_analysis:
            categories = list(category_analysis.keys())
            avg_times = [
                stats.get("average_time", 0) for stats in category_analysis.values()
            ]

            bars = ax1.bar(categories, avg_times, color="skyblue", alpha=0.7)
            ax1.set_title("カテゴリ別平均実行時間", fontsize=14, fontweight="bold")
            ax1.set_ylabel("実行時間 (秒)", fontsize=12)
            ax1.set_xlabel("カテゴリ", fontsize=12)

            # 値をバーの上に表示
            for bar, time in zip(bars, avg_times, strict=False):
                ax1.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    f"{time:.2f}s",
                    ha="center",
                    va="bottom",
                )

            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")

        # 実行時間の統計情報
        summary = analysis_results.get("summary", {})
        stats_data = [
            ("平均", summary.get("average_execution_time", 0)),
            ("総計", summary.get("total_execution_time", 0)),
        ]

        labels, values = zip(*stats_data, strict=False)
        ax2.bar(labels, values, color=["lightcoral", "lightgreen"])
        ax2.set_title("実行時間統計", fontsize=14, fontweight="bold")
        ax2.set_ylabel("時間 (秒)", fontsize=12)

        # 値をバーの上に表示
        for i, (_label, value) in enumerate(stats_data):
            ax2.text(
                i,
                value + max(values) * 0.01,
                f"{value:.2f}s",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        plt.tight_layout()

        graph_path = os.path.join(
            output_dir, f"execution_time_distribution.{self.config.chart_format}"
        )
        plt.savefig(graph_path, dpi=300, bbox_inches="tight")
        plt.close()

        return graph_path

    def _create_memory_usage_graph(
        self, analysis_results: dict[str, Any], output_dir: str
    ) -> str:
        """メモリ使用量グラフの作成"""
        fig, ax = plt.subplots(figsize=(10, 6))

        summary = analysis_results.get("summary", {})
        category_analysis = analysis_results.get("category_analysis", {})

        if category_analysis:
            categories = list(category_analysis.keys())
            avg_memory = [
                stats.get("average_memory", 0) for stats in category_analysis.values()
            ]

            bars = ax.bar(
                categories,
                avg_memory,
                color="lightblue",
                alpha=0.7,
                label="平均メモリ使用量",
            )

            # 全体の最大メモリ使用量を水平線で表示
            peak_memory = summary.get("peak_memory_usage", 0)
            ax.axhline(
                y=peak_memory,
                color="red",
                linestyle="-",
                alpha=0.8,
                label=f"最大メモリ使用量 ({peak_memory:.1f}MB)",
            )

            # 値をバーの上に表示
            for bar, memory in zip(bars, avg_memory, strict=False):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + peak_memory * 0.01,
                    f"{memory:.1f}MB",
                    ha="center",
                    va="bottom",
                )

            ax.set_title(
                "カテゴリ別メモリ使用量", fontsize=16, fontweight="bold", pad=20
            )
            ax.set_ylabel("メモリ使用量 (MB)", fontsize=12)
            ax.set_xlabel("カテゴリ", fontsize=12)

            plt.xticks(rotation=45, ha="right")
            ax.legend()
            plt.grid(True, alpha=0.3)

        plt.tight_layout()

        graph_path = os.path.join(
            output_dir, f"memory_usage.{self.config.chart_format}"
        )
        plt.savefig(graph_path, dpi=300, bbox_inches="tight")
        plt.close()

        return graph_path

    def _create_error_pattern_graph(
        self, error_analysis: dict[str, Any], output_dir: str
    ) -> str:
        """エラーパターン分布グラフの作成"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        error_patterns = error_analysis.get("error_patterns", {})

        # 円グラフ
        labels = list(error_patterns.keys())
        sizes = list(error_patterns.values())
        colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))

        wedges, texts, autotexts = ax1.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 10},
        )
        ax1.set_title("エラーパターン分布", fontsize=14, fontweight="bold")

        # 棒グラフ
        bars = ax2.bar(labels, sizes, color=colors)
        ax2.set_title("エラーパターン発生回数", fontsize=14, fontweight="bold")
        ax2.set_ylabel("発生回数", fontsize=12)
        ax2.set_xlabel("エラータイプ", fontsize=12)

        # 値をバーの上に表示
        for bar, size in zip(bars, sizes, strict=False):
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.1,
                str(size),
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha="right")
        plt.tight_layout()

        graph_path = os.path.join(
            output_dir, f"error_patterns.{self.config.chart_format}"
        )
        plt.savefig(graph_path, dpi=300, bbox_inches="tight")
        plt.close()

        return graph_path

    def _create_quality_radar_chart(
        self, quality_indicators: dict[str, Any], output_dir: str
    ) -> str:
        """品質指標レーダーチャートの作成"""
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"projection": "polar"})

        # 品質指標の設定
        categories = [
            "成功率",
            "安定性スコア",
            "パフォーマンススコア",
            "メモリ効率性",
            "CPU効率性",
        ]

        values = [
            quality_indicators.get("success_rate", 0),
            quality_indicators.get("stability_score", 0),
            quality_indicators.get("performance_score", 0),
            quality_indicators.get("memory_efficiency", 0),
            quality_indicators.get("cpu_efficiency", 0),
        ]

        # 角度の計算
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values += values[:1]  # 円を閉じるために最初の値を追加
        angles += angles[:1]

        # レーダーチャートの描画
        ax.plot(angles, values, "o-", linewidth=2, label="現在の品質指標", color="blue")
        ax.fill(angles, values, alpha=0.25, color="blue")

        # 目標値の線を追加
        target_values = [90] * (len(categories) + 1)
        ax.plot(
            angles,
            target_values,
            "--",
            linewidth=1,
            label="目標値 (90)",
            color="green",
            alpha=0.7,
        )

        # 軸の設定
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=12)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=10)
        ax.grid(True)

        # タイトルと凡例
        ax.set_title("品質指標レーダーチャート", fontsize=16, fontweight="bold", pad=30)
        ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.0))

        plt.tight_layout()

        graph_path = os.path.join(
            output_dir, f"quality_radar.{self.config.chart_format}"
        )
        plt.savefig(graph_path, dpi=300, bbox_inches="tight")
        plt.close()

        return graph_path

    def _create_performance_trend_graph(
        self,
        historical_data: list[dict[str, Any]],
        current_data: dict[str, Any],
        output_dir: str,
    ) -> str:
        """パフォーマンス推移グラフの作成"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

        # データの準備
        timestamps = []
        success_rates = []
        execution_times = []
        memory_usages = []
        quality_scores = []

        for data in historical_data:
            timestamps.append(datetime.fromisoformat(data.get("timestamp", "")))
            summary = data.get("summary", {})
            quality = data.get("quality_indicators", {})

            success_rates.append(summary.get("success_rate", 0))
            execution_times.append(summary.get("average_execution_time", 0))
            memory_usages.append(summary.get("peak_memory_usage", 0))
            quality_scores.append(quality.get("overall_quality_score", 0))

        # 現在のデータを追加
        timestamps.append(datetime.now())
        current_summary = current_data.get("summary", {})
        current_quality = current_data.get("quality_indicators", {})

        success_rates.append(current_summary.get("success_rate", 0))
        execution_times.append(current_summary.get("average_execution_time", 0))
        memory_usages.append(current_summary.get("peak_memory_usage", 0))
        quality_scores.append(current_quality.get("overall_quality_score", 0))

        # 成功率推移
        ax1.plot(
            timestamps, success_rates, "o-", color="green", linewidth=2, markersize=6
        )
        ax1.set_title("成功率推移", fontsize=14, fontweight="bold")
        ax1.set_ylabel("成功率 (%)")
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 100)

        # 実行時間推移
        ax2.plot(
            timestamps, execution_times, "o-", color="blue", linewidth=2, markersize=6
        )
        ax2.set_title("平均実行時間推移", fontsize=14, fontweight="bold")
        ax2.set_ylabel("実行時間 (秒)")
        ax2.grid(True, alpha=0.3)

        # メモリ使用量推移
        ax3.plot(
            timestamps, memory_usages, "o-", color="red", linewidth=2, markersize=6
        )
        ax3.set_title("最大メモリ使用量推移", fontsize=14, fontweight="bold")
        ax3.set_ylabel("メモリ使用量 (MB)")
        ax3.grid(True, alpha=0.3)

        # 品質スコア推移
        ax4.plot(
            timestamps, quality_scores, "o-", color="purple", linewidth=2, markersize=6
        )
        ax4.set_title("総合品質スコア推移", fontsize=14, fontweight="bold")
        ax4.set_ylabel("品質スコア")
        ax4.grid(True, alpha=0.3)
        ax4.set_ylim(0, 100)

        # 日付フォーマットの設定
        for ax in [ax1, ax2, ax3, ax4]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax.xaxis.set_major_locator(
                mdates.DayLocator(interval=max(1, len(timestamps) // 5))
            )
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        graph_path = os.path.join(
            output_dir, f"performance_trend.{self.config.chart_format}"
        )
        plt.savefig(graph_path, dpi=300, bbox_inches="tight")
        plt.close()

        return graph_path

    def _generate_error_analysis_report(self, analysis_results: dict[str, Any]) -> str:
        """エラーログ分析レポートの生成"""
        error_analysis = analysis_results.get("error_analysis", {})
        failed_tests = analysis_results.get("test_results", {}).get("failed_tests", [])

        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocMind エラー分析レポート</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 4px solid #e74c3c;
            padding-bottom: 15px;
            text-align: center;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            border-left: 4px solid #e74c3c;
            padding-left: 15px;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
        }}
        .error-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #e74c3c;
        }}
        .error-item {{
            background: #fff5f5;
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        .error-type {{
            font-weight: bold;
            color: #c0392b;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background-color: #e74c3c;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #fff5f5;
        }}
        .recommendations {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 20px;
            margin: 25px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚨 DocMind エラー分析レポート</h1>

        <div class="summary-card">
            <h3 style="margin: 0; color: white;">エラー分析サマリー</h3>
            <p style="margin: 10px 0 0 0;">
                <strong>総エラー数:</strong> {error_analysis.get('total_errors', 0)} |
                <strong>エラー率:</strong> {error_analysis.get('error_rate', 0):.1f}%
            </p>
            <p style="margin: 10px 0 0 0;">
                <strong>生成日時:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
            </p>
        </div>

        <h2>📊 エラー統計</h2>
        <div class="error-stats">
            <div class="stat-card">
                <div class="stat-value">{error_analysis.get('total_errors', 0)}</div>
                <div>総エラー数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{error_analysis.get('error_rate', 0):.1f}%</div>
                <div>エラー率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(error_analysis.get('error_patterns', {}))}</div>
                <div>エラータイプ数</div>
            </div>
        </div>
        """

        # エラーパターン分析
        error_patterns = error_analysis.get("error_patterns", {})
        if error_patterns:
            html_content += """
        <h2>🔍 エラーパターン分析</h2>
        <table>
            <tr>
                <th>エラータイプ</th>
                <th>発生回数</th>
                <th>割合</th>
                <th>重要度</th>
            </tr>
            """

            total_errors = sum(error_patterns.values())
            sorted_patterns = sorted(
                error_patterns.items(), key=lambda x: x[1], reverse=True
            )

            for error_type, count in sorted_patterns:
                percentage = (count / total_errors * 100) if total_errors > 0 else 0
                severity = self._get_error_severity(error_type, percentage)

                html_content += f"""
            <tr>
                <td><span class="error-type">{error_type}</span></td>
                <td>{count}</td>
                <td>{percentage:.1f}%</td>
                <td>{severity}</td>
            </tr>
                """

            html_content += "</table>"

        # 失敗したテストの詳細
        if failed_tests:
            html_content += f"""
        <h2>📋 失敗したテストの詳細 (上位{min(10, len(failed_tests))}件)</h2>
            """

            for i, test in enumerate(failed_tests[:10], 1):
                error_type = self._classify_error_type(test.get("error_message", ""))

                html_content += f"""
        <div class="error-item">
            <h4>{i}. {test.get('test_name', 'Unknown Test')}</h4>
            <p><strong>カテゴリ:</strong> {test.get('category', 'Unknown')}</p>
            <p><strong>エラータイプ:</strong> <span class="error-type">{error_type}</span></p>
            <p><strong>エラーメッセージ:</strong> {test.get('error_message', 'No message')}</p>
            <p><strong>実行時間:</strong> {test.get('execution_time', 0):.2f}秒 |
               <strong>メモリ使用量:</strong> {test.get('memory_usage', 0):.2f}MB</p>
            <p><strong>発生時刻:</strong> {test.get('timestamp', 'Unknown')}</p>
        </div>
                """

        # 推奨事項
        recommendations = self._generate_error_recommendations(
            error_analysis, failed_tests
        )

        html_content += """
        <div class="recommendations">
            <h3>💡 エラー対策推奨事項</h3>
            <ul>
        """

        for recommendation in recommendations:
            html_content += f"<li>{recommendation}</li>"

        html_content += f"""
            </ul>
        </div>

        <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d;">
            <p>このレポートは DocMind 検証システムによって自動生成されました。</p>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """

        report_path = os.path.join(
            self.config.output_directory,
            f"{self.config.report_name}_error_analysis.html",
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"エラー分析レポートを生成しました: {report_path}")
        return report_path

    def _get_error_severity(self, error_type: str, percentage: float) -> str:
        """エラーの重要度判定"""
        if percentage > 30:
            return "🔴 高"
        elif percentage > 15:
            return "🟡 中"
        elif error_type in ["Memory", "Timeout", "Connection"]:
            return "🟡 中"
        else:
            return "🟢 低"

    def _generate_error_recommendations(
        self, error_analysis: dict[str, Any], failed_tests: list[dict[str, Any]]
    ) -> list[str]:
        """エラー対策推奨事項の生成"""
        recommendations = []
        error_patterns = error_analysis.get("error_patterns", {})

        # エラーパターンに基づく推奨事項
        for error_type, _count in error_patterns.items():
            if error_type == "Timeout":
                recommendations.append(
                    "タイムアウトエラーが多発しています。処理時間の最適化やタイムアウト値の調整を検討してください。"
                )
            elif error_type == "Memory":
                recommendations.append(
                    "メモリ関連エラーが発生しています。メモリリークの調査とメモリ使用量の最適化を実施してください。"
                )
            elif error_type == "Connection":
                recommendations.append(
                    "接続エラーが発生しています。ネットワーク設定や接続プールの設定を見直してください。"
                )
            elif error_type == "File":
                recommendations.append(
                    "ファイル関連エラーが発生しています。ファイルパスの確認とファイルアクセス権限を確認してください。"
                )
            elif error_type == "Permission":
                recommendations.append(
                    "権限エラーが発生しています。実行権限とファイルアクセス権限を確認してください。"
                )

        # エラー率に基づく推奨事項
        error_rate = error_analysis.get("error_rate", 0)
        if error_rate > 20:
            recommendations.append(
                "エラー率が20%を超えています。システム全体の安定性向上を優先的に実施してください。"
            )
        elif error_rate > 10:
            recommendations.append(
                "エラー率が10%を超えています。主要なエラーパターンの対策を実施してください。"
            )

        # 失敗テスト数に基づく推奨事項
        if len(failed_tests) > 10:
            recommendations.append(
                "多数のテストが失敗しています。テストケースの見直しと基本機能の安定化を実施してください。"
            )

        if not recommendations:
            recommendations.append(
                "エラー発生率は許容範囲内です。現在の品質レベルを維持してください。"
            )

        return recommendations

    def _generate_quality_indicators_visualization(
        self, analysis_results: dict[str, Any]
    ) -> str:
        """品質指標可視化レポートの生成"""
        quality_indicators = analysis_results.get("quality_indicators", {})
        analysis_results.get("summary", {})

        html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocMind 品質指標可視化レポート</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 4px solid #9b59b6;
            padding-bottom: 15px;
            text-align: center;
        }
        .quality-dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .quality-card {
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: relative;
            overflow: hidden;
        }
        .quality-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
        }
        .excellent { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; }
        .excellent::before { background: #27ae60; }
        .good { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }
        .good::before { background: #3498db; }
        .average { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; }
        .average::before { background: #e67e22; }
        .poor { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; }
        .poor::before { background: #e74c3c; }
        .quality-score {
            font-size: 3em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .quality-label {
            font-size: 1.2em;
            margin-bottom: 5px;
        }
        .quality-description {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .chart-title {
            text-align: center;
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 20px;
            color: #2c3e50;
        }
        .progress-section {
            margin: 30px 0;
        }
        .progress-item {
            margin: 20px 0;
        }
        .progress-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .progress-bar {
            width: 100%;
            height: 25px;
            background-color: #e9ecef;
            border-radius: 12px;
            overflow: hidden;
            position: relative;
        }
        .progress-fill {
            height: 100%;
            border-radius: 12px;
            transition: width 0.8s ease;
            position: relative;
        }
        .progress-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-weight: bold;
            font-size: 0.9em;
        }
        .benchmark-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .benchmark-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .benchmark-item {
            background: white;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
            border-left: 4px solid #3498db;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 DocMind 品質指標可視化レポート</h1>

        <h2>🎯 品質指標ダッシュボード</h2>
        <div class="quality-dashboard">
        """

        # 品質指標カードの生成
        quality_metrics = [
            (
                "総合品質スコア",
                quality_indicators.get("overall_quality_score", 0),
                "全体的な品質レベル",
            ),
            ("成功率", quality_indicators.get("success_rate", 0), "テスト成功の割合"),
            (
                "安定性スコア",
                quality_indicators.get("stability_score", 0),
                "実行時間の安定性",
            ),
            (
                "パフォーマンススコア",
                quality_indicators.get("performance_score", 0),
                "処理性能の評価",
            ),
            (
                "メモリ効率性",
                quality_indicators.get("memory_efficiency", 0),
                "メモリ使用の効率性",
            ),
            (
                "CPU効率性",
                quality_indicators.get("cpu_efficiency", 0),
                "CPU使用の効率性",
            ),
        ]

        for label, score, description in quality_metrics:
            card_class = self._get_quality_card_class(score)

            html_content += f"""
            <div class="quality-card {card_class}">
                <div class="quality-score">{score:.1f}</div>
                <div class="quality-label">{label}</div>
                <div class="quality-description">{description}</div>
            </div>
            """

        html_content += """
        </div>

        <h2>📈 品質指標プログレスバー</h2>
        <div class="progress-section">
        """

        # プログレスバーの生成
        for label, score, description in quality_metrics:
            color = self._get_progress_color(score)

            html_content += f"""
        <div class="progress-item">
            <div class="progress-label">
                <span>{label}</span>
                <span>{score:.1f}/100</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {score}%; background: {color};">
                    <div class="progress-text">{score:.1f}%</div>
                </div>
            </div>
        </div>
            """

        html_content += """
        </div>

        <h2>🎯 ベンチマーク比較</h2>
        <div class="benchmark-section">
            <div class="benchmark-grid">
        """

        # ベンチマーク比較の生成
        benchmarks = [
            ("優秀レベル", 90, "業界トップクラス"),
            ("良好レベル", 80, "標準以上の品質"),
            ("普通レベル", 70, "最低限の品質"),
            ("要改善レベル", 60, "改善が必要"),
        ]

        current_overall = quality_indicators.get("overall_quality_score", 0)

        for level, threshold, description in benchmarks:
            status = "✅ 達成" if current_overall >= threshold else "❌ 未達成"

            html_content += f"""
                <div class="benchmark-item">
                    <h4>{level}</h4>
                    <p><strong>閾値:</strong> {threshold}以上</p>
                    <p><strong>現在:</strong> {current_overall:.1f}</p>
                    <p><strong>ステータス:</strong> {status}</p>
                    <p style="font-size: 0.9em; color: #6c757d;">{description}</p>
                </div>
            """

        html_content += """
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-title">品質指標レーダーチャート</div>
            <canvas id="qualityRadarChart" width="400" height="400"></canvas>
        </div>

        <script>
        const ctx = document.getElementById('qualityRadarChart').getContext('2d');
        new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['成功率', '安定性', 'パフォーマンス', 'メモリ効率', 'CPU効率'],
                datasets: [{
                    label: '現在の品質指標',
                    data: [
        """

        # レーダーチャートデータの追加
        radar_data = [
            quality_indicators.get("success_rate", 0),
            quality_indicators.get("stability_score", 0),
            quality_indicators.get("performance_score", 0),
            quality_indicators.get("memory_efficiency", 0),
            quality_indicators.get("cpu_efficiency", 0),
        ]

        html_content += f"""
                        {', '.join(map(str, radar_data))}
                    ],
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(54, 162, 235, 1)'
                }}, {{
                    label: '目標値',
                    data: [90, 90, 90, 90, 90],
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    pointBackgroundColor: 'rgba(75, 192, 192, 1)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(75, 192, 192, 1)'
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    r: {{
                        beginAtZero: true,
                        max: 100,
                        ticks: {{
                            stepSize: 20
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        position: 'top'
                    }}
                }}
            }}
        }});
        </script>

        <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d;">
            <p>このレポートは DocMind 検証システムによって自動生成されました。</p>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """

        report_path = os.path.join(
            self.config.output_directory,
            f"{self.config.report_name}_quality_indicators.html",
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"品質指標可視化レポートを生成しました: {report_path}")
        return report_path

    def _get_progress_color(self, score: float) -> str:
        """プログレスバーの色を取得"""
        if score >= 90:
            return "linear-gradient(90deg, #11998e 0%, #38ef7d 100%)"
        elif score >= 80:
            return "linear-gradient(90deg, #4facfe 0%, #00f2fe 100%)"
        elif score >= 70:
            return "linear-gradient(90deg, #f093fb 0%, #f5576c 100%)"
        else:
            return "linear-gradient(90deg, #ff6b6b 0%, #ee5a24 100%)"

    def generate_comparison_with_historical_results(
        self, current_results: dict[str, Any]
    ) -> str:
        """過去の検証結果との比較レポート生成"""
        historical_data = self._load_historical_data()

        if len(historical_data) < 1:
            self.logger.warning("比較に十分な履歴データがありません")
            return self._generate_insufficient_data_report("comparison")

        # 比較分析の実行
        comparison_analysis = self._perform_comparison_analysis(
            historical_data, current_results
        )

        # HTMLレポートの生成
        html_content = self._create_comparison_html_report(comparison_analysis)

        report_path = os.path.join(
            self.config.output_directory,
            f"{self.config.report_name}_historical_comparison.html",
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"過去結果比較レポートを生成しました: {report_path}")
        return report_path

    def _perform_comparison_analysis(
        self, historical_data: list[dict[str, Any]], current_data: dict[str, Any]
    ) -> dict[str, Any]:
        """比較分析の実行"""
        if not historical_data:
            return {"comparison_available": False}

        # 過去データの平均値計算
        avg_success_rate = sum(
            h.get("summary", {}).get("success_rate", 0) for h in historical_data
        ) / len(historical_data)
        avg_execution_time = sum(
            h.get("summary", {}).get("average_execution_time", 0)
            for h in historical_data
        ) / len(historical_data)
        avg_memory_usage = sum(
            h.get("summary", {}).get("peak_memory_usage", 0) for h in historical_data
        ) / len(historical_data)
        avg_quality_score = sum(
            h.get("quality_indicators", {}).get("overall_quality_score", 0)
            for h in historical_data
        ) / len(historical_data)

        # 現在の値
        current_summary = current_data.get("summary", {})
        current_quality = current_data.get("quality_indicators", {})

        current_success_rate = current_summary.get("success_rate", 0)
        current_execution_time = current_summary.get("average_execution_time", 0)
        current_memory_usage = current_summary.get("peak_memory_usage", 0)
        current_quality_score = current_quality.get("overall_quality_score", 0)

        # 変化の計算
        success_rate_change = current_success_rate - avg_success_rate
        execution_time_change = current_execution_time - avg_execution_time
        memory_usage_change = current_memory_usage - avg_memory_usage
        quality_score_change = current_quality_score - avg_quality_score

        # 総合評価
        overall_rating = self._calculate_overall_comparison_rating(
            success_rate_change,
            execution_time_change,
            memory_usage_change,
            quality_score_change,
        )

        return {
            "comparison_available": True,
            "historical_count": len(historical_data),
            "averages": {
                "success_rate": avg_success_rate,
                "execution_time": avg_execution_time,
                "memory_usage": avg_memory_usage,
                "quality_score": avg_quality_score,
            },
            "current": {
                "success_rate": current_success_rate,
                "execution_time": current_execution_time,
                "memory_usage": current_memory_usage,
                "quality_score": current_quality_score,
            },
            "changes": {
                "success_rate": success_rate_change,
                "execution_time": execution_time_change,
                "memory_usage": memory_usage_change,
                "quality_score": quality_score_change,
            },
            "overall_rating": overall_rating,
            "recommendations": self._generate_comparison_recommendations(
                success_rate_change,
                execution_time_change,
                memory_usage_change,
                quality_score_change,
            ),
        }

    def _calculate_overall_comparison_rating(
        self,
        success_change: float,
        time_change: float,
        memory_change: float,
        quality_change: float,
    ) -> str:
        """総合比較評価の計算"""
        score = 0

        # 成功率の評価 (最重要)
        if success_change > 5:
            score += 3
        elif success_change > 0:
            score += 1
        elif success_change < -5:
            score -= 3
        elif success_change < 0:
            score -= 1

        # 実行時間の評価 (短縮は良い)
        if time_change < -2:
            score += 2
        elif time_change < 0:
            score += 1
        elif time_change > 5:
            score -= 2
        elif time_change > 2:
            score -= 1

        # メモリ使用量の評価 (削減は良い)
        if memory_change < -100:
            score += 1
        elif memory_change > 200:
            score -= 1

        # 品質スコアの評価
        if quality_change > 5:
            score += 2
        elif quality_change > 0:
            score += 1
        elif quality_change < -5:
            score -= 2
        elif quality_change < 0:
            score -= 1

        if score >= 4:
            return "大幅改善"
        elif score >= 2:
            return "改善"
        elif score <= -4:
            return "大幅劣化"
        elif score <= -2:
            return "劣化"
        else:
            return "安定"

    def _generate_comparison_recommendations(
        self,
        success_change: float,
        time_change: float,
        memory_change: float,
        quality_change: float,
    ) -> list[str]:
        """比較推奨事項の生成"""
        recommendations = []

        if success_change < -5:
            recommendations.append(
                "成功率が大幅に低下しています。最近の変更を見直し、品質保証プロセスを強化してください。"
            )
        elif success_change > 5:
            recommendations.append(
                "成功率が大幅に向上しています。この改善を維持するための施策を継続してください。"
            )

        if time_change > 5:
            recommendations.append(
                "実行時間が大幅に増加しています。パフォーマンスの最適化を優先的に実施してください。"
            )
        elif time_change < -2:
            recommendations.append(
                "実行時間が大幅に短縮されています。この最適化手法を他の処理にも適用を検討してください。"
            )

        if memory_change > 200:
            recommendations.append(
                "メモリ使用量が大幅に増加しています。メモリリークの調査とメモリ効率の改善を実施してください。"
            )
        elif memory_change < -100:
            recommendations.append(
                "メモリ使用量が大幅に削減されています。この効率化手法を他のコンポーネントにも適用を検討してください。"
            )

        if quality_change < -5:
            recommendations.append(
                "品質スコアが大幅に低下しています。品質管理プロセス全体の見直しを実施してください。"
            )
        elif quality_change > 5:
            recommendations.append(
                "品質スコアが大幅に向上しています。現在の品質向上施策を継続し、さらなる改善を目指してください。"
            )

        if not recommendations:
            recommendations.append(
                "全体的に安定したパフォーマンスを維持しています。現在の品質レベルを継続してください。"
            )

        return recommendations

    def _create_comparison_html_report(self, analysis: dict[str, Any]) -> str:
        """比較HTMLレポートの作成"""
        if not analysis.get("comparison_available", False):
            return """
<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"><title>比較レポート</title></head>
<body><h1>比較レポート</h1><p>比較対象となる過去のデータがありません。</p></body>
</html>
            """

        averages = analysis.get("averages", {})
        current = analysis.get("current", {})
        changes = analysis.get("changes", {})

        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocMind 過去結果比較レポート</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 4px solid #9b59b6; padding-bottom: 15px; text-align: center; }}
        .rating-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; margin: 20px 0; text-align: center; }}
        .comparison-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }}
        .metric-comparison {{ background: white; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .metric-title {{ font-size: 1.2em; font-weight: bold; margin-bottom: 15px; color: #2c3e50; }}
        .metric-row {{ display: flex; justify-content: space-between; margin: 10px 0; padding: 8px 0; border-bottom: 1px solid #f1f3f4; }}
        .change-positive {{ color: #27ae60; font-weight: bold; }}
        .change-negative {{ color: #e74c3c; font-weight: bold; }}
        .change-neutral {{ color: #7f8c8d; }}
        .recommendations {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; margin: 25px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 DocMind 過去結果比較レポート</h1>

        <div class="rating-card">
            <h3 style="margin: 0; color: white;">総合パフォーマンス評価</h3>
            <p style="margin: 10px 0 0 0; font-size: 1.5em; font-weight: bold;">{analysis.get('overall_rating', '不明')}</p>
            <p style="margin: 10px 0 0 0;">過去 {analysis.get('historical_count', 0)} 回の検証結果との比較</p>
        </div>

        <h2>📊 主要指標の比較</h2>
        <div class="comparison-grid">
        """

        # 比較メトリクスの表示
        metrics = [
            ("成功率", "success_rate", "%"),
            ("実行時間", "execution_time", "秒"),
            ("メモリ使用量", "memory_usage", "MB"),
            ("品質スコア", "quality_score", ""),
        ]

        for name, key, unit in metrics:
            avg_value = averages.get(key, 0)
            current_value = current.get(key, 0)
            change_value = changes.get(key, 0)

            # 変化の方向性を判定
            if key in ["success_rate", "quality_score"]:
                # 高い方が良い指標
                change_class = (
                    "change-positive"
                    if change_value > 0
                    else "change-negative" if change_value < 0 else "change-neutral"
                )
            else:
                # 低い方が良い指標
                change_class = (
                    "change-negative"
                    if change_value > 0
                    else "change-positive" if change_value < 0 else "change-neutral"
                )

            html += f"""
            <div class="metric-comparison">
                <div class="metric-title">{name}</div>
                <div class="metric-row">
                    <span>過去平均:</span>
                    <span>{avg_value:.1f}{unit}</span>
                </div>
                <div class="metric-row">
                    <span>現在:</span>
                    <span>{current_value:.1f}{unit}</span>
                </div>
                <div class="metric-row">
                    <span>変化:</span>
                    <span class="{change_class}">
                        {'+' if change_value > 0 else ''}{change_value:.1f}{unit}
                    </span>
                </div>
            </div>
            """

        html += """
        </div>

        <div class="recommendations">
            <h3>💡 推奨事項</h3>
            <ul>
        """

        for recommendation in analysis.get("recommendations", []):
            html += f"<li>{recommendation}</li>"

        html += f"""
            </ul>
        </div>

        <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d;">
            <p>このレポートは DocMind 検証システムによって自動生成されました。</p>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """

        return html

    def cleanup_generated_files(self) -> None:
        """生成されたファイルのクリーンアップ"""
        self.logger.info("生成されたファイルのクリーンアップを開始します")

        for file_path in self.generated_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.debug(f"ファイルを削除しました: {file_path}")
            except Exception as e:
                self.logger.warning(f"ファイル削除に失敗しました: {file_path} - {e}")

        self.generated_files.clear()
        self.logger.info("ファイルクリーンアップが完了しました")

    def get_generated_files(self) -> list[str]:
        """生成されたファイルのリストを取得"""
        return self.generated_files.copy()
