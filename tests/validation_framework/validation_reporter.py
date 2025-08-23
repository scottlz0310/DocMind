# -*- coding: utf-8 -*-
"""
検証結果レポート生成クラス

検証結果を分析し、包括的なレポートを生成します。
"""

import os
import json
import csv
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
import seaborn as sns
import pandas as pd

# 日本語フォント設定
rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False


@dataclass
class ReportConfig:
    """レポート生成設定"""
    output_directory: str
    report_name: str = "validation_report"
    include_charts: bool = True
    include_detailed_logs: bool = True
    chart_format: str = "png"  # png, svg, pdf
    report_format: str = "html"  # html, markdown, json


class ValidationReporter:
    """
    検証結果レポート生成クラス
    
    検証結果を分析し、HTML、Markdown、JSONなどの
    形式で包括的なレポートを生成します。
    """
    
    def __init__(self, output_directory: Optional[str] = None):
        """レポート生成クラスの初期化"""
        self.logger = logging.getLogger(f"validation.{self.__class__.__name__}")
        self.output_directory = output_directory or "validation_results"
        
        # 出力ディレクトリの作成
        os.makedirs(self.output_directory, exist_ok=True)
    
    def generate_html_report(self, report_data: Dict[str, Any], filename: str) -> str:
        """HTMLレポートの生成"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DocMind 検証レポート</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; }}
                .summary {{ margin: 20px 0; }}
                .test-result {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; }}
                .success {{ background-color: #d4edda; }}
                .failure {{ background-color: #f8d7da; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>DocMind パフォーマンス検証レポート</h1>
                <p>実行日時: {report_data.get('execution_time', 'N/A')}</p>
            </div>
            
            <div class="summary">
                <h2>検証サマリー</h2>
                <p>全体成功: {'✓' if report_data.get('overall_success', False) else '✗'}</p>
            </div>
            
            <div class="test-results">
                <h2>テスト結果</h2>
        """
        
        for test in report_data.get('test_results', []):
            status_class = 'success' if test.get('success', False) else 'failure'
            html_content += f"""
                <div class="test-result {status_class}">
                    <h3>{test.get('test_name', 'Unknown Test')}</h3>
                    <p>成功: {'✓' if test.get('success', False) else '✗'}</p>
                    <p>実行時間: {test.get('execution_time', 0):.2f}秒</p>
                    <p>メモリ使用量: {test.get('memory_usage', 0):.1f}MB</p>
                    {f"<p>エラー: {test.get('error_message', '')}</p>" if test.get('error_message') else ""}
                </div>
            """
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        report_path = os.path.join(self.output_directory, filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTMLレポートを生成しました: {report_path}")
        return report_path
    
    def generate_json_report(self, report_data: Dict[str, Any], filename: str) -> str:
        """JSONレポートの生成"""
        report_path = os.path.join(self.output_directory, filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
        
        self.logger.info(f"JSONレポートを生成しました: {report_path}")
        return report_path
    
    def generate_compatibility_report(self, 
                                    validation_results: List[Any],
                                    compatibility_metrics: List[Any],
                                    statistics: Dict[str, Any]) -> str:
        """
        互換性検証レポートの生成
        
        Args:
            validation_results: 検証結果のリスト
            compatibility_metrics: 互換性メトリクスのリスト
            statistics: 統計情報
        
        Returns:
            生成されたHTMLレポートの内容
        """
        self.logger.info("互換性検証レポートを生成します")
        
        # 互換性レベルの集計
        compatibility_levels = {}
        for metric in compatibility_metrics:
            level = getattr(metric, 'compatibility_level', 'UNKNOWN')
            compatibility_levels[level] = compatibility_levels.get(level, 0) + 1
        
        # 成功率の計算
        successful_tests = sum(1 for result in validation_results if result.success)
        total_tests = len(validation_results)
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        # システム情報の取得
        system_info = {}
        if compatibility_metrics:
            first_metric = compatibility_metrics[0]
            system_info = {
                'os_version': getattr(first_metric, 'os_version', '不明'),
                'python_version': getattr(first_metric, 'python_version', '不明'),
                'memory_available_mb': getattr(first_metric, 'memory_available_mb', 0),
                'disk_space_available_mb': getattr(first_metric, 'disk_space_available_mb', 0),
                'screen_resolution': getattr(first_metric, 'screen_resolution', (0, 0)),
                'filesystem_type': getattr(first_metric, 'filesystem_type', '不明')
            }
        
        # HTMLレポートの生成
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>DocMind 互換性検証レポート</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                    color: #333;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 2.5em;
                    font-weight: 300;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    opacity: 0.9;
                }}
                .content {{
                    padding: 30px;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .summary-card {{
                    background: #f8f9fa;
                    border-left: 4px solid #007bff;
                    padding: 20px;
                    border-radius: 4px;
                }}
                .summary-card h3 {{
                    margin: 0 0 10px 0;
                    color: #495057;
                    font-size: 1.1em;
                }}
                .summary-card .value {{
                    font-size: 2em;
                    font-weight: bold;
                    color: #007bff;
                }}
                .compatibility-levels {{
                    margin: 30px 0;
                }}
                .level-bar {{
                    display: flex;
                    align-items: center;
                    margin: 10px 0;
                }}
                .level-label {{
                    width: 120px;
                    font-weight: bold;
                }}
                .level-progress {{
                    flex: 1;
                    height: 20px;
                    background: #e9ecef;
                    border-radius: 10px;
                    margin: 0 10px;
                    overflow: hidden;
                }}
                .level-fill {{
                    height: 100%;
                    border-radius: 10px;
                }}
                .compatible {{ background-color: #28a745; }}
                .limited {{ background-color: #ffc107; }}
                .incompatible {{ background-color: #dc3545; }}
                .system-info {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .system-info h3 {{
                    margin-top: 0;
                    color: #495057;
                }}
                .info-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                }}
                .info-item {{
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0;
                    border-bottom: 1px solid #dee2e6;
                }}
                .test-results {{
                    margin: 30px 0;
                }}
                .test-item {{
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    margin: 10px 0;
                    overflow: hidden;
                }}
                .test-header {{
                    padding: 15px 20px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #dee2e6;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .test-name {{
                    font-weight: bold;
                    font-size: 1.1em;
                }}
                .test-status {{
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 0.9em;
                    font-weight: bold;
                }}
                .status-success {{
                    background: #d4edda;
                    color: #155724;
                }}
                .status-failure {{
                    background: #f8d7da;
                    color: #721c24;
                }}
                .test-details {{
                    padding: 20px;
                }}
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                    margin: 15px 0;
                }}
                .metric {{
                    text-align: center;
                    padding: 10px;
                    background: #f8f9fa;
                    border-radius: 4px;
                }}
                .metric-value {{
                    font-size: 1.5em;
                    font-weight: bold;
                    color: #007bff;
                }}
                .metric-label {{
                    font-size: 0.9em;
                    color: #6c757d;
                    margin-top: 5px;
                }}
                .recommendations {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .recommendations h4 {{
                    margin-top: 0;
                    color: #856404;
                }}
                .recommendations ul {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
                .recommendations li {{
                    margin: 5px 0;
                    color: #856404;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #6c757d;
                    border-top: 1px solid #dee2e6;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>DocMind 互換性検証レポート</h1>
                    <p>実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
                </div>
                
                <div class="content">
                    <div class="summary-grid">
                        <div class="summary-card">
                            <h3>総合成功率</h3>
                            <div class="value">{success_rate:.1f}%</div>
                        </div>
                        <div class="summary-card">
                            <h3>実行テスト数</h3>
                            <div class="value">{total_tests}</div>
                        </div>
                        <div class="summary-card">
                            <h3>成功テスト数</h3>
                            <div class="value">{successful_tests}</div>
                        </div>
                        <div class="summary-card">
                            <h3>互換性カテゴリ数</h3>
                            <div class="value">{len(compatibility_metrics)}</div>
                        </div>
                    </div>
                    
                    <div class="system-info">
                        <h3>システム情報</h3>
                        <div class="info-grid">
                            <div class="info-item">
                                <span>OS版本:</span>
                                <span>{system_info.get('os_version', '不明')}</span>
                            </div>
                            <div class="info-item">
                                <span>Python版本:</span>
                                <span>{system_info.get('python_version', '不明')}</span>
                            </div>
                            <div class="info-item">
                                <span>利用可能メモリ:</span>
                                <span>{system_info.get('memory_available_mb', 0):,} MB</span>
                            </div>
                            <div class="info-item">
                                <span>利用可能ディスク:</span>
                                <span>{system_info.get('disk_space_available_mb', 0):,} MB</span>
                            </div>
                            <div class="info-item">
                                <span>画面解像度:</span>
                                <span>{system_info.get('screen_resolution', (0, 0))[0]} x {system_info.get('screen_resolution', (0, 0))[1]}</span>
                            </div>
                            <div class="info-item">
                                <span>ファイルシステム:</span>
                                <span>{system_info.get('filesystem_type', '不明')}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="compatibility-levels">
                        <h3>互換性レベル分布</h3>
        """
        
        # 互換性レベルの表示
        total_metrics = len(compatibility_metrics)
        for level, count in compatibility_levels.items():
            percentage = (count / total_metrics * 100) if total_metrics > 0 else 0
            level_class = level.lower() if level in ['COMPATIBLE', 'LIMITED', 'INCOMPATIBLE'] else 'compatible'
            level_name = {
                'COMPATIBLE': '互換性あり',
                'LIMITED': '制限付き互換性',
                'INCOMPATIBLE': '互換性なし'
            }.get(level, level)
            
            html_content += f"""
                        <div class="level-bar">
                            <div class="level-label">{level_name}:</div>
                            <div class="level-progress">
                                <div class="level-fill {level_class}" style="width: {percentage}%"></div>
                            </div>
                            <div>{count}件 ({percentage:.1f}%)</div>
                        </div>
            """
        
        html_content += """
                    </div>
                    
                    <div class="test-results">
                        <h3>詳細テスト結果</h3>
        """
        
        # 各テスト結果の表示
        for i, result in enumerate(validation_results):
            status_class = 'status-success' if result.success else 'status-failure'
            status_text = '成功' if result.success else '失敗'
            
            # 対応する互換性メトリクスを取得
            metric = None
            if i < len(compatibility_metrics):
                metric = compatibility_metrics[i]
            
            html_content += f"""
                        <div class="test-item">
                            <div class="test-header">
                                <div class="test-name">{result.test_name}</div>
                                <div class="test-status {status_class}">{status_text}</div>
                            </div>
                            <div class="test-details">
                                <div class="metrics-grid">
                                    <div class="metric">
                                        <div class="metric-value">{result.execution_time:.2f}s</div>
                                        <div class="metric-label">実行時間</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-value">{result.memory_usage:.1f}MB</div>
                                        <div class="metric-label">メモリ使用量</div>
                                    </div>
            """
            
            if metric:
                html_content += f"""
                                    <div class="metric">
                                        <div class="metric-value">{getattr(metric, 'compatibility_level', 'N/A')}</div>
                                        <div class="metric-label">互換性レベル</div>
                                    </div>
                """
            
            html_content += """
                                </div>
            """
            
            # エラーメッセージの表示
            if result.error_message:
                html_content += f"""
                                <div style="margin-top: 15px;">
                                    <strong>エラー:</strong> {result.error_message}
                                </div>
                """
            
            # 推奨事項の表示
            if metric and hasattr(metric, 'recommendations') and metric.recommendations:
                html_content += f"""
                                <div class="recommendations">
                                    <h4>推奨事項</h4>
                                    <ul>
                """
                for recommendation in metric.recommendations[:3]:  # 最大3件
                    html_content += f"<li>{recommendation}</li>"
                
                html_content += """
                                    </ul>
                                </div>
                """
            
            html_content += """
                            </div>
                        </div>
            """
        
        # 全体的な推奨事項
        all_recommendations = []
        for metric in compatibility_metrics:
            if hasattr(metric, 'recommendations'):
                all_recommendations.extend(metric.recommendations)
        
        unique_recommendations = list(set(all_recommendations))[:5]  # 最大5件のユニークな推奨事項
        
        if unique_recommendations:
            html_content += f"""
                    <div class="recommendations">
                        <h4>全体的な推奨事項</h4>
                        <ul>
            """
            for recommendation in unique_recommendations:
                html_content += f"<li>{recommendation}</li>"
            
            html_content += """
                        </ul>
                    </div>
            """
        
        html_content += f"""
                    </div>
                </div>
                
                <div class="footer">
                    <p>DocMind 互換性検証システム - 生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        self.logger.info("互換性検証レポートの生成が完了しました")
        return html_content
        
        # 生成されたレポートファイルの追跡
        self.generated_reports: List[str] = []
        
        # スタイル設定
        sns.set_style("whitegrid")
        plt.style.use('seaborn-v0_8')
        
        self.logger.debug("検証結果レポート生成クラスを初期化しました")
    
    def generate_comprehensive_report(self, 
                                    validation_results: List[Any],
                                    performance_data: Dict[str, Any],
                                    memory_data: Dict[str, Any],
                                    error_injection_data: Dict[str, Any],
                                    config: ReportConfig) -> Dict[str, str]:
        """
        包括的検証レポートの生成
        
        Args:
            validation_results: 検証結果のリスト
            performance_data: パフォーマンスデータ
            memory_data: メモリ使用量データ
            error_injection_data: エラー注入データ
            config: レポート設定
        
        Returns:
            生成されたレポートファイルのパス辞書
        """
        self.logger.info(f"包括的検証レポート '{config.report_name}' の生成を開始します")
        
        # 出力ディレクトリの作成
        os.makedirs(config.output_directory, exist_ok=True)
        
        # データの分析
        analysis_results = self._analyze_validation_data(
            validation_results, performance_data, memory_data, error_injection_data
        )
        
        generated_files = {}
        
        # チャートの生成
        if config.include_charts:
            chart_files = self._generate_charts(analysis_results, config)
            generated_files.update(chart_files)
        
        # レポートの生成
        if config.report_format == "html":
            report_file = self._generate_html_report(analysis_results, config)
            generated_files['html_report'] = report_file
        elif config.report_format == "markdown":
            report_file = self._generate_markdown_report(analysis_results, config)
            generated_files['markdown_report'] = report_file
        elif config.report_format == "json":
            report_file = self._generate_json_report(analysis_results, config)
            generated_files['json_report'] = report_file
        
        # 詳細ログの生成
        if config.include_detailed_logs:
            log_files = self._generate_detailed_logs(validation_results, config)
            generated_files.update(log_files)
        
        # サマリーレポートの生成
        summary_file = self._generate_summary_report(analysis_results, config)
        generated_files['summary_report'] = summary_file
        
        self.generated_reports.extend(generated_files.values())
        
        self.logger.info(f"レポート生成完了: {len(generated_files)}ファイル")
        return generated_files
    
    def _analyze_validation_data(self, 
                               validation_results: List[Any],
                               performance_data: Dict[str, Any],
                               memory_data: Dict[str, Any],
                               error_injection_data: Dict[str, Any]) -> Dict[str, Any]:
        """検証データの分析"""
        analysis = {
            'summary': {},
            'test_results': {},
            'performance_analysis': {},
            'memory_analysis': {},
            'error_analysis': {},
            'trends': {},
            'recommendations': []
        }
        
        # テスト結果の分析
        if validation_results:
            total_tests = len(validation_results)
            passed_tests = sum(1 for result in validation_results if result.success)
            failed_tests = total_tests - passed_tests
            
            analysis['summary'] = {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'total_execution_time': sum(result.execution_time for result in validation_results),
                'average_execution_time': sum(result.execution_time for result in validation_results) / total_tests if total_tests > 0 else 0
            }
            
            # テストカテゴリ別分析
            test_categories = {}
            for result in validation_results:
                category = result.test_name.split('_')[1] if '_' in result.test_name else 'other'
                if category not in test_categories:
                    test_categories[category] = {'total': 0, 'passed': 0, 'failed': 0}
                
                test_categories[category]['total'] += 1
                if result.success:
                    test_categories[category]['passed'] += 1
                else:
                    test_categories[category]['failed'] += 1
            
            analysis['test_results'] = {
                'by_category': test_categories,
                'failed_tests': [
                    {
                        'name': result.test_name,
                        'error': result.error_message,
                        'execution_time': result.execution_time
                    }
                    for result in validation_results if not result.success
                ]
            }
        
        # パフォーマンス分析
        if performance_data:
            analysis['performance_analysis'] = {
                'cpu_usage': {
                    'peak': performance_data.get('cpu_usage', {}).get('peak_percent', 0),
                    'average': performance_data.get('cpu_usage', {}).get('average_percent', 0),
                    'threshold_exceeded': performance_data.get('cpu_usage', {}).get('peak_percent', 0) > 80
                },
                'disk_io': performance_data.get('disk_io', {}),
                'network_io': performance_data.get('network_io', {}),
                'monitoring_duration': performance_data.get('monitoring_duration_seconds', 0)
            }
        
        # メモリ分析
        if memory_data:
            analysis['memory_analysis'] = {
                'peak_usage_mb': memory_data.get('rss_memory', {}).get('peak_mb', 0),
                'average_usage_mb': memory_data.get('rss_memory', {}).get('average_mb', 0),
                'growth_rate': memory_data.get('rss_memory', {}).get('growth_rate_mb_per_sec', 0),
                'memory_leak_detected': memory_data.get('memory_leak_detected', False),
                'threshold_exceeded': memory_data.get('rss_memory', {}).get('peak_mb', 0) > 2048
            }
        
        # エラー注入分析
        if error_injection_data:
            analysis['error_analysis'] = {
                'total_injections': error_injection_data.get('total_injections', 0),
                'successful_injections': error_injection_data.get('successful_injections', 0),
                'success_rate': error_injection_data.get('success_rate', 0),
                'error_types': error_injection_data.get('error_types', {})
            }
        
        # 推奨事項の生成
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """分析結果に基づく推奨事項の生成"""
        recommendations = []
        
        # テスト結果に基づく推奨事項
        summary = analysis.get('summary', {})
        if summary.get('success_rate', 100) < 95:
            recommendations.append("テスト成功率が95%を下回っています。失敗したテストの原因を調査し、修正してください。")
        
        if summary.get('average_execution_time', 0) > 30:
            recommendations.append("平均実行時間が30秒を超えています。パフォーマンスの最適化を検討してください。")
        
        # パフォーマンスに基づく推奨事項
        perf = analysis.get('performance_analysis', {})
        if perf.get('cpu_usage', {}).get('threshold_exceeded', False):
            recommendations.append("CPU使用率が閾値を超過しています。処理の最適化やリソース配分の見直しを行ってください。")
        
        # メモリに基づく推奨事項
        memory = analysis.get('memory_analysis', {})
        if memory.get('memory_leak_detected', False):
            recommendations.append("メモリリークが検出されました。メモリ管理の見直しとリソースの適切な解放を行ってください。")
        
        if memory.get('threshold_exceeded', False):
            recommendations.append("メモリ使用量が閾値を超過しています。メモリ効率の改善を検討してください。")
        
        # エラー処理に基づく推奨事項
        error_analysis = analysis.get('error_analysis', {})
        if error_analysis.get('success_rate', 1.0) < 0.8:
            recommendations.append("エラー注入の成功率が低いです。エラーハンドリング機能の改善を検討してください。")
        
        if not recommendations:
            recommendations.append("すべての検証項目が基準を満たしています。現在の品質レベルを維持してください。")
        
        return recommendations
    
    def _generate_charts(self, analysis: Dict[str, Any], config: ReportConfig) -> Dict[str, str]:
        """チャートの生成"""
        chart_files = {}
        chart_dir = os.path.join(config.output_directory, "charts")
        os.makedirs(chart_dir, exist_ok=True)
        
        try:
            # テスト結果円グラフ
            if analysis.get('summary'):
                chart_path = self._create_test_results_pie_chart(analysis['summary'], chart_dir, config.chart_format)
                chart_files['test_results_pie'] = chart_path
            
            # パフォーマンス棒グラフ
            if analysis.get('performance_analysis'):
                chart_path = self._create_performance_bar_chart(analysis['performance_analysis'], chart_dir, config.chart_format)
                chart_files['performance_bar'] = chart_path
            
            # メモリ使用量グラフ
            if analysis.get('memory_analysis'):
                chart_path = self._create_memory_usage_chart(analysis['memory_analysis'], chart_dir, config.chart_format)
                chart_files['memory_usage'] = chart_path
            
            # エラー注入結果グラフ
            if analysis.get('error_analysis'):
                chart_path = self._create_error_injection_chart(analysis['error_analysis'], chart_dir, config.chart_format)
                chart_files['error_injection'] = chart_path
            
        except Exception as e:
            self.logger.error(f"チャート生成中にエラーが発生しました: {e}")
        
        return chart_files
    
    def _create_test_results_pie_chart(self, summary: Dict[str, Any], chart_dir: str, format: str) -> str:
        """テスト結果円グラフの作成"""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        labels = ['成功', '失敗']
        sizes = [summary.get('passed_tests', 0), summary.get('failed_tests', 0)]
        colors = ['#2ecc71', '#e74c3c']
        
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.set_title('テスト結果分布', fontsize=16, fontweight='bold')
        
        chart_path = os.path.join(chart_dir, f"test_results_pie.{format}")
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def _create_performance_bar_chart(self, perf_data: Dict[str, Any], chart_dir: str, format: str) -> str:
        """パフォーマンス棒グラフの作成"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        metrics = ['CPU使用率(Peak)', 'CPU使用率(Avg)']
        values = [
            perf_data.get('cpu_usage', {}).get('peak', 0),
            perf_data.get('cpu_usage', {}).get('average', 0)
        ]
        
        bars = ax.bar(metrics, values, color=['#3498db', '#9b59b6'])
        ax.set_ylabel('使用率 (%)')
        ax.set_title('パフォーマンス指標', fontsize=16, fontweight='bold')
        ax.set_ylim(0, 100)
        
        # 閾値線の追加
        ax.axhline(y=80, color='red', linestyle='--', alpha=0.7, label='閾値 (80%)')
        ax.legend()
        
        # 値をバーの上に表示
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{value:.1f}%', ha='center', va='bottom')
        
        chart_path = os.path.join(chart_dir, f"performance_bar.{format}")
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def _create_memory_usage_chart(self, memory_data: Dict[str, Any], chart_dir: str, format: str) -> str:
        """メモリ使用量グラフの作成"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        metrics = ['Peak使用量', '平均使用量']
        values = [
            memory_data.get('peak_usage_mb', 0),
            memory_data.get('average_usage_mb', 0)
        ]
        
        bars = ax.bar(metrics, values, color=['#e67e22', '#f39c12'])
        ax.set_ylabel('メモリ使用量 (MB)')
        ax.set_title('メモリ使用量分析', fontsize=16, fontweight='bold')
        
        # 閾値線の追加
        ax.axhline(y=2048, color='red', linestyle='--', alpha=0.7, label='閾値 (2048MB)')
        ax.legend()
        
        # 値をバーの上に表示
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                   f'{value:.1f}MB', ha='center', va='bottom')
        
        chart_path = os.path.join(chart_dir, f"memory_usage.{format}")
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def _create_error_injection_chart(self, error_data: Dict[str, Any], chart_dir: str, format: str) -> str:
        """エラー注入結果グラフの作成"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        error_types = list(error_data.get('error_types', {}).keys())
        error_counts = list(error_data.get('error_types', {}).values())
        
        if error_types:
            bars = ax.bar(error_types, error_counts, color='#34495e')
            ax.set_ylabel('注入回数')
            ax.set_title('エラー注入結果', fontsize=16, fontweight='bold')
            ax.tick_params(axis='x', rotation=45)
            
            # 値をバーの上に表示
            for bar, count in zip(bars, error_counts):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                       str(count), ha='center', va='bottom')
        
        chart_path = os.path.join(chart_dir, f"error_injection.{format}")
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def _generate_html_report(self, analysis: Dict[str, Any], config: ReportConfig) -> str:
        """HTMLレポートの生成"""
        html_content = self._create_html_template(analysis, config)
        
        report_path = os.path.join(config.output_directory, f"{config.report_name}.html")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return report_path
    
    def _create_html_template(self, analysis: Dict[str, Any], config: ReportConfig) -> str:
        """HTMLテンプレートの作成"""
        summary = analysis.get('summary', {})
        
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocMind 包括的検証レポート</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; }}
        .metric-label {{ font-size: 0.9em; opacity: 0.9; }}
        .success {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .warning {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .info {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        .recommendations {{ background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin: 20px 0; }}
        .chart-container {{ text-align: center; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>DocMind 包括的検証レポート</h1>
        <p><strong>生成日時:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        
        <h2>検証サマリー</h2>
        <div class="summary-grid">
            <div class="metric-card {'success' if summary.get('success_rate', 0) >= 95 else 'warning'}">
                <div class="metric-value">{summary.get('success_rate', 0):.1f}%</div>
                <div class="metric-label">成功率</div>
            </div>
            <div class="metric-card info">
                <div class="metric-value">{summary.get('total_tests', 0)}</div>
                <div class="metric-label">総テスト数</div>
            </div>
            <div class="metric-card info">
                <div class="metric-value">{summary.get('total_execution_time', 0):.1f}s</div>
                <div class="metric-label">総実行時間</div>
            </div>
        </div>
        
        <h2>推奨事項</h2>
        <div class="recommendations">
            <ul>
        """
        
        for recommendation in analysis.get('recommendations', []):
            html += f"<li>{recommendation}</li>"
        
        html += """
            </ul>
        </div>
        
        <h2>詳細分析結果</h2>
        """
        
        # 失敗したテストの詳細
        failed_tests = analysis.get('test_results', {}).get('failed_tests', [])
        if failed_tests:
            html += """
            <h3>失敗したテスト</h3>
            <table>
                <tr><th>テスト名</th><th>エラーメッセージ</th><th>実行時間</th></tr>
            """
            for test in failed_tests:
                html += f"""
                <tr>
                    <td>{test['name']}</td>
                    <td>{test['error']}</td>
                    <td>{test['execution_time']:.2f}s</td>
                </tr>
                """
            html += "</table>"
        
        html += """
    </div>
</body>
</html>
        """
        
        return html
    
    def _generate_markdown_report(self, analysis: Dict[str, Any], config: ReportConfig) -> str:
        """Markdownレポートの生成"""
        summary = analysis.get('summary', {})
        
        markdown_content = f"""# DocMind 包括的検証レポート

**生成日時:** {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

## 検証サマリー

- **総テスト数:** {summary.get('total_tests', 0)}
- **成功テスト数:** {summary.get('passed_tests', 0)}
- **失敗テスト数:** {summary.get('failed_tests', 0)}
- **成功率:** {summary.get('success_rate', 0):.1f}%
- **総実行時間:** {summary.get('total_execution_time', 0):.1f}秒

## 推奨事項

"""
        
        for recommendation in analysis.get('recommendations', []):
            markdown_content += f"- {recommendation}\n"
        
        # 失敗したテストの詳細
        failed_tests = analysis.get('test_results', {}).get('failed_tests', [])
        if failed_tests:
            markdown_content += "\n## 失敗したテスト\n\n"
            markdown_content += "| テスト名 | エラーメッセージ | 実行時間 |\n"
            markdown_content += "|----------|------------------|----------|\n"
            
            for test in failed_tests:
                markdown_content += f"| {test['name']} | {test['error']} | {test['execution_time']:.2f}s |\n"
        
        report_path = os.path.join(config.output_directory, f"{config.report_name}.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return report_path
    
    def _generate_json_report(self, analysis: Dict[str, Any], config: ReportConfig) -> str:
        """JSONレポートの生成"""
        report_data = {
            'report_metadata': {
                'name': config.report_name,
                'generation_time': datetime.now().isoformat(),
                'version': '1.0'
            },
            'analysis_results': analysis
        }
        
        report_path = os.path.join(config.output_directory, f"{config.report_name}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return report_path
    
    def _generate_detailed_logs(self, validation_results: List[Any], config: ReportConfig) -> Dict[str, str]:
        """詳細ログの生成"""
        log_files = {}
        
        # CSV形式の詳細ログ
        csv_path = os.path.join(config.output_directory, f"{config.report_name}_detailed.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['テスト名', '成功/失敗', '実行時間', 'メモリ使用量', 'エラーメッセージ', 'タイムスタンプ'])
            
            for result in validation_results:
                writer.writerow([
                    result.test_name,
                    '成功' if result.success else '失敗',
                    f"{result.execution_time:.4f}",
                    f"{result.memory_usage:.2f}",
                    result.error_message or '',
                    result.timestamp.isoformat()
                ])
        
        log_files['detailed_csv'] = csv_path
        
        return log_files
    
    def _generate_summary_report(self, analysis: Dict[str, Any], config: ReportConfig) -> str:
        """サマリーレポートの生成"""
        summary = analysis.get('summary', {})
        
        summary_content = f"""DocMind 検証サマリー
==================

生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

基本統計:
- 総テスト数: {summary.get('total_tests', 0)}
- 成功率: {summary.get('success_rate', 0):.1f}%
- 総実行時間: {summary.get('total_execution_time', 0):.1f}秒

品質評価:
"""
        
        success_rate = summary.get('success_rate', 0)
        if success_rate >= 95:
            summary_content += "✅ 優秀 - すべての要件を満たしています\n"
        elif success_rate >= 90:
            summary_content += "⚠️  良好 - 軽微な問題があります\n"
        else:
            summary_content += "❌ 要改善 - 重要な問題があります\n"
        
        summary_content += "\n主要な推奨事項:\n"
        for i, recommendation in enumerate(analysis.get('recommendations', [])[:3], 1):
            summary_content += f"{i}. {recommendation}\n"
        
        summary_path = os.path.join(config.output_directory, f"{config.report_name}_summary.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        return summary_path
    
    def generate_error_handling_report(self, validation_results: Dict[str, Any]) -> str:
        """
        エラーハンドリング検証専用レポートの生成
        
        Args:
            validation_results: エラーハンドリング検証結果
            
        Returns:
            生成されたレポートファイルのパス
        """
        self.logger.info("エラーハンドリング検証レポートの生成を開始します")
        
        # 出力ディレクトリの作成
        report_dir = Path(self.output_directory) / "error_handling"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # タイムスタンプ付きファイル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"error_handling_report_{timestamp}.html"
        
        # HTMLレポートの生成
        html_content = self._create_error_handling_html_report(validation_results)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.generated_reports.append(str(report_path))
        self.logger.info(f"エラーハンドリング検証レポートを生成しました: {report_path}")
        
        return str(report_path)
    
    def _create_error_handling_html_report(self, results: Dict[str, Any]) -> str:
        """エラーハンドリング検証用HTMLレポートの作成"""
        summary = results.get('summary', {})
        exception_handling = summary.get('exception_handling', {})
        recovery_mechanisms = summary.get('recovery_mechanisms', {})
        graceful_degradation = summary.get('graceful_degradation', {})
        system_health = summary.get('system_health', {})
        
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocMind エラーハンドリング・回復機能検証レポート</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f8f9fa; 
            line-height: 1.6;
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
            margin-bottom: 30px;
            text-align: center;
        }}
        h2 {{ 
            color: #34495e; 
            margin-top: 40px; 
            margin-bottom: 20px;
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
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .summary-grid {{ 
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
        .success {{ 
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
            color: white;
        }}
        .warning {{ 
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
            color: white;
        }}
        .info {{ 
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
            color: white;
        }}
        .error {{ 
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); 
            color: white;
        }}
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
        .status-badge {{
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status-success {{
            background-color: #d4edda;
            color: #155724;
        }}
        .status-warning {{
            background-color: #fff3cd;
            color: #856404;
        }}
        .status-error {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .recommendations {{ 
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
            border: 1px solid #ffeaa7; 
            border-radius: 8px; 
            padding: 20px; 
            margin: 25px 0; 
        }}
        .recommendations h3 {{
            color: #856404;
            margin-top: 0;
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
        .test-details {{
            background: #f8f9fa;
            border-radius: 6px;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #6c757d;
        }}
        .error-details {{
            background: #fff5f5;
            border-left-color: #e74c3c;
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
        <h1>🛡️ DocMind エラーハンドリング・回復機能検証レポート</h1>
        
        <div class="header-info">
            <h3 style="margin: 0; color: white;">検証実行情報</h3>
            <p style="margin: 10px 0 0 0;"><strong>生成日時:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
            <p style="margin: 5px 0 0 0;"><strong>検証タイプ:</strong> エラーハンドリング・回復機能包括検証</p>
        </div>
        
        <h2>📊 検証サマリー</h2>
        <div class="summary-grid">
            <div class="metric-card {'success' if summary.get('success_rate', 0) >= 0.95 else 'warning' if summary.get('success_rate', 0) >= 0.8 else 'error'}">
                <div class="metric-value">{summary.get('success_rate', 0):.1%}</div>
                <div class="metric-label">総合成功率</div>
            </div>
            <div class="metric-card info">
                <div class="metric-value">{summary.get('total_tests', 0)}</div>
                <div class="metric-label">総テスト数</div>
            </div>
            <div class="metric-card info">
                <div class="metric-value">{summary.get('average_execution_time', 0):.2f}s</div>
                <div class="metric-label">平均実行時間</div>
            </div>
            <div class="metric-card info">
                <div class="metric-value">{summary.get('peak_memory_usage', 0):.1f}MB</div>
                <div class="metric-label">最大メモリ使用量</div>
            </div>
        </div>
        
        <h2>🔍 機能別検証結果</h2>
        
        <div class="section-card">
            <h3>例外処理機能</h3>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {(exception_handling.get('successful_handling', 0) / max(exception_handling.get('total_tests', 1), 1)) * 100}%"></div>
            </div>
            <p><strong>成功率:</strong> {exception_handling.get('successful_handling', 0)}/{exception_handling.get('total_tests', 0)} 
               ({(exception_handling.get('successful_handling', 0) / max(exception_handling.get('total_tests', 1), 1)) * 100:.1f}%)</p>
        </div>
        
        <div class="section-card">
            <h3>自動回復機能</h3>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {(recovery_mechanisms.get('successful_recovery', 0) / max(recovery_mechanisms.get('total_tests', 1), 1)) * 100}%"></div>
            </div>
            <p><strong>成功率:</strong> {recovery_mechanisms.get('successful_recovery', 0)}/{recovery_mechanisms.get('total_tests', 0)} 
               ({(recovery_mechanisms.get('successful_recovery', 0) / max(recovery_mechanisms.get('total_tests', 1), 1)) * 100:.1f}%)</p>
        </div>
        
        <div class="section-card">
            <h3>優雅な劣化機能</h3>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {(graceful_degradation.get('successful_degradation', 0) / max(graceful_degradation.get('total_tests', 1), 1)) * 100}%"></div>
            </div>
            <p><strong>成功率:</strong> {graceful_degradation.get('successful_degradation', 0)}/{graceful_degradation.get('total_tests', 0)} 
               ({(graceful_degradation.get('successful_degradation', 0) / max(graceful_degradation.get('total_tests', 1), 1)) * 100:.1f}%)</p>
        </div>
        
        <h2>🏥 システム健全性</h2>
        <div class="section-card">
            <table>
                <tr>
                    <th>項目</th>
                    <th>値</th>
                    <th>ステータス</th>
                </tr>
                <tr>
                    <td>総コンポーネント数</td>
                    <td>{system_health.get('total_components', 0)}</td>
                    <td><span class="status-badge status-success">正常</span></td>
                </tr>
                <tr>
                    <td>正常コンポーネント</td>
                    <td>{system_health.get('healthy', 0)}</td>
                    <td><span class="status-badge status-success">正常</span></td>
                </tr>
                <tr>
                    <td>劣化コンポーネント</td>
                    <td>{system_health.get('degraded', 0)}</td>
                    <td><span class="status-badge {'status-warning' if system_health.get('degraded', 0) > 0 else 'status-success'}">{'注意' if system_health.get('degraded', 0) > 0 else '正常'}</span></td>
                </tr>
                <tr>
                    <td>失敗コンポーネント</td>
                    <td>{system_health.get('failed', 0)}</td>
                    <td><span class="status-badge {'status-error' if system_health.get('failed', 0) > 0 else 'status-success'}">{'エラー' if system_health.get('failed', 0) > 0 else '正常'}</span></td>
                </tr>
                <tr>
                    <td>全体的な健全性</td>
                    <td>{system_health.get('overall_health', 'unknown').upper()}</td>
                    <td><span class="status-badge {'status-success' if system_health.get('overall_health') == 'healthy' else 'status-warning' if system_health.get('overall_health') == 'degraded' else 'status-error'}">
                        {'正常' if system_health.get('overall_health') == 'healthy' else '劣化' if system_health.get('overall_health') == 'degraded' else '重大'}
                    </span></td>
                </tr>
            </table>
        </div>
        """
        
        # 失敗したテストの詳細
        failed_tests = []
        for result in results.get('results', {}).get('test_results', []):
            if not result.get('success', True):
                failed_tests.append(result)
        
        if failed_tests:
            html += """
        <h2>❌ 失敗したテスト</h2>
        <div class="section-card">
            """
            for test in failed_tests:
                html += f"""
            <div class="test-details error-details">
                <h4>{test.get('test_name', 'Unknown Test')}</h4>
                <p><strong>エラーメッセージ:</strong> {test.get('error_message', 'No error message')}</p>
                <p><strong>実行時間:</strong> {test.get('execution_time', 0):.2f}秒</p>
                <p><strong>メモリ使用量:</strong> {test.get('memory_usage', 0):.2f}MB</p>
            </div>
                """
            html += """
        </div>
            """
        
        # パフォーマンス問題
        performance_issues = results.get('performance_issues', [])
        if performance_issues:
            html += """
        <h2>⚠️ パフォーマンス問題</h2>
        <div class="section-card">
            <table>
                <tr>
                    <th>テスト名</th>
                    <th>問題の種類</th>
                    <th>実際の値</th>
                    <th>制限値</th>
                </tr>
            """
            for issue in performance_issues:
                html += f"""
                <tr>
                    <td>{issue.get('test_name', 'Unknown')}</td>
                    <td>{issue.get('issue', 'Unknown Issue')}</td>
                    <td>{issue.get('actual', 0)}</td>
                    <td>{issue.get('limit', 0)}</td>
                </tr>
                """
            html += """
            </table>
        </div>
            """
        
        # 推奨事項（仮の推奨事項を生成）
        recommendations = []
        if summary.get('success_rate', 1.0) < 0.95:
            recommendations.append("テスト成功率が95%を下回っています。失敗したテストの原因を調査し、エラーハンドリング機能を改善してください。")
        if system_health.get('failed', 0) > 0:
            recommendations.append("失敗したコンポーネントがあります。コンポーネントの回復機能を強化してください。")
        if len(performance_issues) > 0:
            recommendations.append("パフォーマンス要件を満たしていないテストがあります。処理の最適化を検討してください。")
        if not recommendations:
            recommendations.append("すべての検証項目が基準を満たしています。現在のエラーハンドリング品質を維持してください。")
        
        html += """
        <div class="recommendations">
            <h3>💡 推奨事項</h3>
            <ul>
        """
        for recommendation in recommendations:
            html += f"<li>{recommendation}</li>"
        
        html += f"""
            </ul>
        </div>
        
        <div class="footer">
            <p>このレポートは DocMind エラーハンドリング検証システムによって自動生成されました。</p>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html

    def generate_trend_analysis_report(self, 
                                      historical_data: List[Dict[str, Any]], 
                                      current_results: Dict[str, Any],
                                      config: ReportConfig) -> str:
        """
        トレンド分析レポートの生成
        
        Args:
            historical_data: 過去の検証結果データのリスト
            current_results: 現在の検証結果
            config: レポート設定
            
        Returns:
            生成されたトレンド分析レポートのパス
        """
        self.logger.info("トレンド分析レポートの生成を開始します")
        
        # 出力ディレクトリの作成
        os.makedirs(config.output_directory, exist_ok=True)
        
        # トレンド分析の実行
        trend_analysis = self._analyze_trends(historical_data, current_results)
        
        # HTMLレポートの生成
        html_content = self._create_trend_analysis_html(trend_analysis, config)
        
        report_path = os.path.join(config.output_directory, f"{config.report_name}_trend_analysis.html")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # チャートの生成
        if config.include_charts:
            self._generate_trend_charts(trend_analysis, config)
        
        self.generated_reports.append(report_path)
        self.logger.info(f"トレンド分析レポートを生成しました: {report_path}")
        
        return report_path
    
    def _analyze_trends(self, historical_data: List[Dict[str, Any]], current_results: Dict[str, Any]) -> Dict[str, Any]:
        """トレンドデータの分析"""
        if not historical_data:
            return {
                'success_rate_trend': [],
                'execution_time_trend': [],
                'memory_usage_trend': [],
                'error_rate_trend': [],
                'performance_degradation': False,
                'quality_improvement': False,
                'trend_summary': "履歴データが不足しているため、トレンド分析を実行できません。"
            }
        
        # 成功率のトレンド
        success_rates = []
        execution_times = []
        memory_usages = []
        error_rates = []
        dates = []
        
        for data in historical_data:
            summary = data.get('summary', {})
            success_rates.append(summary.get('success_rate', 0))
            execution_times.append(summary.get('average_execution_time', 0))
            memory_usages.append(summary.get('peak_memory_usage', 0))
            error_rates.append(100 - summary.get('success_rate', 0))
            dates.append(data.get('timestamp', datetime.now().isoformat()))
        
        # 現在の結果を追加
        current_summary = current_results.get('summary', {})
        success_rates.append(current_summary.get('success_rate', 0))
        execution_times.append(current_summary.get('average_execution_time', 0))
        memory_usages.append(current_summary.get('peak_memory_usage', 0))
        error_rates.append(100 - current_summary.get('success_rate', 0))
        dates.append(datetime.now().isoformat())
        
        # トレンド分析
        performance_degradation = False
        quality_improvement = False
        
        if len(success_rates) >= 2:
            recent_avg = sum(success_rates[-3:]) / min(3, len(success_rates))
            older_avg = sum(success_rates[:-3]) / max(1, len(success_rates) - 3) if len(success_rates) > 3 else success_rates[0]
            
            if recent_avg > older_avg + 5:
                quality_improvement = True
            elif recent_avg < older_avg - 5:
                performance_degradation = True
        
        # トレンドサマリーの生成
        trend_summary = self._generate_trend_summary(success_rates, execution_times, memory_usages)
        
        return {
            'success_rate_trend': list(zip(dates, success_rates)),
            'execution_time_trend': list(zip(dates, execution_times)),
            'memory_usage_trend': list(zip(dates, memory_usages)),
            'error_rate_trend': list(zip(dates, error_rates)),
            'performance_degradation': performance_degradation,
            'quality_improvement': quality_improvement,
            'trend_summary': trend_summary,
            'data_points': len(historical_data) + 1
        }
    
    def _generate_trend_summary(self, success_rates: List[float], execution_times: List[float], memory_usages: List[float]) -> str:
        """トレンドサマリーの生成"""
        if len(success_rates) < 2:
            return "データポイントが不足しているため、トレンド分析を実行できません。"
        
        # 最新と最古の比較
        latest_success = success_rates[-1]
        oldest_success = success_rates[0]
        success_change = latest_success - oldest_success
        
        latest_time = execution_times[-1]
        oldest_time = execution_times[0]
        time_change = latest_time - oldest_time
        
        latest_memory = memory_usages[-1]
        oldest_memory = memory_usages[0]
        memory_change = latest_memory - oldest_memory
        
        summary_parts = []
        
        if abs(success_change) > 1:
            if success_change > 0:
                summary_parts.append(f"成功率が{success_change:.1f}%向上しました")
            else:
                summary_parts.append(f"成功率が{abs(success_change):.1f}%低下しました")
        
        if abs(time_change) > 1:
            if time_change > 0:
                summary_parts.append(f"実行時間が{time_change:.1f}秒増加しました")
            else:
                summary_parts.append(f"実行時間が{abs(time_change):.1f}秒短縮されました")
        
        if abs(memory_change) > 50:
            if memory_change > 0:
                summary_parts.append(f"メモリ使用量が{memory_change:.1f}MB増加しました")
            else:
                summary_parts.append(f"メモリ使用量が{abs(memory_change):.1f}MB削減されました")
        
        if not summary_parts:
            return "主要な指標に大きな変化は見られません。"
        
        return "。".join(summary_parts) + "。"
    
    def _create_trend_analysis_html(self, trend_analysis: Dict[str, Any], config: ReportConfig) -> str:
        """トレンド分析HTMLレポートの作成"""
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
            border-bottom: 4px solid #3498db; 
            padding-bottom: 15px; 
            text-align: center;
        }}
        h2 {{ 
            color: #34495e; 
            margin-top: 40px; 
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
        }}
        .trend-indicators {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .indicator-card {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .improving {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
        }}
        .degrading {{
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
            color: white;
        }}
        .stable {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
        }}
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
                <strong>生成日時:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
            </p>
            <p style="margin: 10px 0 0 0; font-size: 1.1em;">{trend_analysis.get('trend_summary', '')}</p>
        </div>
        
        <h2>🎯 トレンド指標</h2>
        <div class="trend-indicators">
            <div class="indicator-card {'improving' if trend_analysis.get('quality_improvement') else 'degrading' if trend_analysis.get('performance_degradation') else 'stable'}">
                <h3>品質トレンド</h3>
                <p>{'📈 改善傾向' if trend_analysis.get('quality_improvement') else '📉 劣化傾向' if trend_analysis.get('performance_degradation') else '📊 安定'}</p>
            </div>
        </div>
        
        <h2>📊 パフォーマンス推移</h2>
        """
        
        # 成功率トレンドチャート
        success_data = trend_analysis.get('success_rate_trend', [])
        if success_data:
            dates = [item[0][:10] for item in success_data]  # 日付部分のみ
            values = [item[1] for item in success_data]
            
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
                    data: {values},
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
        
        # 実行時間トレンドチャート
        time_data = trend_analysis.get('execution_time_trend', [])
        if time_data:
            dates = [item[0][:10] for item in time_data]
            values = [item[1] for item in time_data]
            
            html += f"""
        <div class="chart-container">
            <div class="chart-title">実行時間推移</div>
            <canvas id="executionTimeChart" width="400" height="200"></canvas>
        </div>
        
        <script>
        const timeCtx = document.getElementById('executionTimeChart').getContext('2d');
        new Chart(timeCtx, {{
            type: 'line',
            data: {{
                labels: {dates},
                datasets: [{{
                    label: '実行時間 (秒)',
                    data: {values},
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
                        ticks: {{
                            callback: function(value) {{
                                return value + 's';
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
        
        # メモリ使用量トレンドチャート
        memory_data = trend_analysis.get('memory_usage_trend', [])
        if memory_data:
            dates = [item[0][:10] for item in memory_data]
            values = [item[1] for item in memory_data]
            
            html += f"""
        <div class="chart-container">
            <div class="chart-title">メモリ使用量推移</div>
            <canvas id="memoryUsageChart" width="400" height="200"></canvas>
        </div>
        
        <script>
        const memoryCtx = document.getElementById('memoryUsageChart').getContext('2d');
        new Chart(memoryCtx, {{
            type: 'line',
            data: {{
                labels: {dates},
                datasets: [{{
                    label: 'メモリ使用量 (MB)',
                    data: {values},
                    borderColor: '#f39c12',
                    backgroundColor: 'rgba(243, 156, 18, 0.1)',
                    tension: 0.4,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return value + 'MB';
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
    
    def _generate_trend_charts(self, trend_analysis: Dict[str, Any], config: ReportConfig) -> None:
        """トレンド分析用チャートの生成"""
        chart_dir = os.path.join(config.output_directory, "trend_charts")
        os.makedirs(chart_dir, exist_ok=True)
        
        try:
            # 成功率トレンドチャート
            success_data = trend_analysis.get('success_rate_trend', [])
            if success_data:
                self._create_trend_line_chart(
                    success_data, 
                    "成功率推移", 
                    "成功率 (%)", 
                    os.path.join(chart_dir, f"success_rate_trend.{config.chart_format}")
                )
            
            # 実行時間トレンドチャート
            time_data = trend_analysis.get('execution_time_trend', [])
            if time_data:
                self._create_trend_line_chart(
                    time_data, 
                    "実行時間推移", 
                    "実行時間 (秒)", 
                    os.path.join(chart_dir, f"execution_time_trend.{config.chart_format}")
                )
            
            # メモリ使用量トレンドチャート
            memory_data = trend_analysis.get('memory_usage_trend', [])
            if memory_data:
                self._create_trend_line_chart(
                    memory_data, 
                    "メモリ使用量推移", 
                    "メモリ使用量 (MB)", 
                    os.path.join(chart_dir, f"memory_usage_trend.{config.chart_format}")
                )
                
        except Exception as e:
            self.logger.error(f"トレンドチャート生成中にエラーが発生しました: {e}")
    
    def _create_trend_line_chart(self, data: List[tuple], title: str, ylabel: str, output_path: str) -> None:
        """トレンド線グラフの作成"""
        if not data:
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        dates = [datetime.fromisoformat(item[0].replace('Z', '+00:00')) for item in data]
        values = [item[1] for item in data]
        
        ax.plot(dates, values, marker='o', linewidth=2, markersize=6)
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_xlabel('日付', fontsize=12)
        
        # 日付フォーマットの設定
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
        
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def compare_with_historical_results(self, 
                                      current_results: Dict[str, Any], 
                                      historical_results: List[Dict[str, Any]],
                                      config: ReportConfig) -> str:
        """
        過去の検証結果との比較レポート生成
        
        Args:
            current_results: 現在の検証結果
            historical_results: 過去の検証結果のリスト
            config: レポート設定
            
        Returns:
            生成された比較レポートのパス
        """
        self.logger.info("過去の検証結果との比較レポートを生成します")
        
        # 比較分析の実行
        comparison_analysis = self._perform_historical_comparison(current_results, historical_results)
        
        # HTMLレポートの生成
        html_content = self._create_comparison_html_report(comparison_analysis, config)
        
        report_path = os.path.join(config.output_directory, f"{config.report_name}_comparison.html")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.generated_reports.append(report_path)
        self.logger.info(f"比較レポートを生成しました: {report_path}")
        
        return report_path
    
    def _perform_historical_comparison(self, current: Dict[str, Any], historical: List[Dict[str, Any]]) -> Dict[str, Any]:
        """過去の結果との比較分析"""
        if not historical:
            return {
                'comparison_available': False,
                'message': '比較対象となる過去のデータがありません。'
            }
        
        # 最新の過去データを取得
        latest_historical = historical[-1] if historical else {}
        
        # 平均値の計算
        avg_success_rate = sum(h.get('summary', {}).get('success_rate', 0) for h in historical) / len(historical)
        avg_execution_time = sum(h.get('summary', {}).get('average_execution_time', 0) for h in historical) / len(historical)
        avg_memory_usage = sum(h.get('summary', {}).get('peak_memory_usage', 0) for h in historical) / len(historical)
        
        # 現在の結果
        current_summary = current.get('summary', {})
        current_success_rate = current_summary.get('success_rate', 0)
        current_execution_time = current_summary.get('average_execution_time', 0)
        current_memory_usage = current_summary.get('peak_memory_usage', 0)
        
        # 比較結果の計算
        success_rate_change = current_success_rate - avg_success_rate
        execution_time_change = current_execution_time - avg_execution_time
        memory_usage_change = current_memory_usage - avg_memory_usage
        
        # パフォーマンス評価
        performance_rating = self._calculate_performance_rating(
            success_rate_change, execution_time_change, memory_usage_change
        )
        
        return {
            'comparison_available': True,
            'historical_count': len(historical),
            'averages': {
                'success_rate': avg_success_rate,
                'execution_time': avg_execution_time,
                'memory_usage': avg_memory_usage
            },
            'current': {
                'success_rate': current_success_rate,
                'execution_time': current_execution_time,
                'memory_usage': current_memory_usage
            },
            'changes': {
                'success_rate': success_rate_change,
                'execution_time': execution_time_change,
                'memory_usage': memory_usage_change
            },
            'performance_rating': performance_rating,
            'latest_historical': latest_historical.get('summary', {}),
            'recommendations': self._generate_comparison_recommendations(
                success_rate_change, execution_time_change, memory_usage_change
            )
        }
    
    def _calculate_performance_rating(self, success_change: float, time_change: float, memory_change: float) -> str:
        """パフォーマンス評価の計算"""
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
        
        # 実行時間の評価
        if time_change < -2:  # 2秒以上短縮
            score += 2
        elif time_change < 0:
            score += 1
        elif time_change > 5:  # 5秒以上増加
            score -= 2
        elif time_change > 2:
            score -= 1
        
        # メモリ使用量の評価
        if memory_change < -100:  # 100MB以上削減
            score += 1
        elif memory_change > 200:  # 200MB以上増加
            score -= 1
        
        if score >= 3:
            return "大幅改善"
        elif score >= 1:
            return "改善"
        elif score <= -3:
            return "大幅劣化"
        elif score <= -1:
            return "劣化"
        else:
            return "安定"
    
    def _generate_comparison_recommendations(self, success_change: float, time_change: float, memory_change: float) -> List[str]:
        """比較結果に基づく推奨事項の生成"""
        recommendations = []
        
        if success_change < -5:
            recommendations.append("成功率が大幅に低下しています。最近の変更を見直し、品質保証プロセスを強化してください。")
        elif success_change < 0:
            recommendations.append("成功率がわずかに低下しています。テストケースの見直しを検討してください。")
        elif success_change > 5:
            recommendations.append("成功率が大幅に向上しています。この改善を維持するための施策を継続してください。")
        
        if time_change > 5:
            recommendations.append("実行時間が大幅に増加しています。パフォーマンスの最適化を優先的に実施してください。")
        elif time_change > 2:
            recommendations.append("実行時間が増加傾向にあります。処理効率の改善を検討してください。")
        elif time_change < -2:
            recommendations.append("実行時間が大幅に短縮されています。この最適化手法を他の処理にも適用を検討してください。")
        
        if memory_change > 200:
            recommendations.append("メモリ使用量が大幅に増加しています。メモリリークの調査とメモリ効率の改善を実施してください。")
        elif memory_change < -100:
            recommendations.append("メモリ使用量が大幅に削減されています。この効率化手法を他のコンポーネントにも適用を検討してください。")
        
        if not recommendations:
            recommendations.append("全体的に安定したパフォーマンスを維持しています。現在の品質レベルを継続してください。")
        
        return recommendations
    
    def _create_comparison_html_report(self, analysis: Dict[str, Any], config: ReportConfig) -> str:
        """比較レポートのHTML生成"""
        if not analysis.get('comparison_available', False):
            return f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>DocMind 比較レポート</title>
</head>
<body>
    <h1>比較レポート</h1>
    <p>{analysis.get('message', '比較データが利用できません。')}</p>
</body>
</html>
            """
        
        averages = analysis.get('averages', {})
        current = analysis.get('current', {})
        changes = analysis.get('changes', {})
        
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocMind 過去結果比較レポート</title>
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
            border-bottom: 4px solid #9b59b6; 
            padding-bottom: 15px; 
            text-align: center;
        }}
        .rating-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-comparison {{
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .metric-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #2c3e50;
        }}
        .metric-row {{
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #f1f3f4;
        }}
        .change-positive {{ color: #27ae60; font-weight: bold; }}
        .change-negative {{ color: #e74c3c; font-weight: bold; }}
        .change-neutral {{ color: #7f8c8d; }}
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
        <h1>🔍 DocMind 過去結果比較レポート</h1>
        
        <div class="rating-card">
            <h3 style="margin: 0; color: white;">総合パフォーマンス評価</h3>
            <p style="margin: 10px 0 0 0; font-size: 1.5em; font-weight: bold;">
                {analysis.get('performance_rating', '不明')}
            </p>
            <p style="margin: 10px 0 0 0;">
                過去 {analysis.get('historical_count', 0)} 回の検証結果との比較 | 
                生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
            </p>
        </div>
        
        <h2>📊 主要指標の比較</h2>
        <div class="comparison-grid">
            <div class="metric-comparison">
                <div class="metric-title">成功率</div>
                <div class="metric-row">
                    <span>過去平均:</span>
                    <span>{averages.get('success_rate', 0):.1f}%</span>
                </div>
                <div class="metric-row">
                    <span>現在:</span>
                    <span>{current.get('success_rate', 0):.1f}%</span>
                </div>
                <div class="metric-row">
                    <span>変化:</span>
                    <span class="{'change-positive' if changes.get('success_rate', 0) > 0 else 'change-negative' if changes.get('success_rate', 0) < 0 else 'change-neutral'}">
                        {'+' if changes.get('success_rate', 0) > 0 else ''}{changes.get('success_rate', 0):.1f}%
                    </span>
                </div>
            </div>
            
            <div class="metric-comparison">
                <div class="metric-title">実行時間</div>
                <div class="metric-row">
                    <span>過去平均:</span>
                    <span>{averages.get('execution_time', 0):.2f}秒</span>
                </div>
                <div class="metric-row">
                    <span>現在:</span>
                    <span>{current.get('execution_time', 0):.2f}秒</span>
                </div>
                <div class="metric-row">
                    <span>変化:</span>
                    <span class="{'change-negative' if changes.get('execution_time', 0) > 0 else 'change-positive' if changes.get('execution_time', 0) < 0 else 'change-neutral'}">
                        {'+' if changes.get('execution_time', 0) > 0 else ''}{changes.get('execution_time', 0):.2f}秒
                    </span>
                </div>
            </div>
            
            <div class="metric-comparison">
                <div class="metric-title">メモリ使用量</div>
                <div class="metric-row">
                    <span>過去平均:</span>
                    <span>{averages.get('memory_usage', 0):.1f}MB</span>
                </div>
                <div class="metric-row">
                    <span>現在:</span>
                    <span>{current.get('memory_usage', 0):.1f}MB</span>
                </div>
                <div class="metric-row">
                    <span>変化:</span>
                    <span class="{'change-negative' if changes.get('memory_usage', 0) > 0 else 'change-positive' if changes.get('memory_usage', 0) < 0 else 'change-neutral'}">
                        {'+' if changes.get('memory_usage', 0) > 0 else ''}{changes.get('memory_usage', 0):.1f}MB
                    </span>
                </div>
            </div>
        </div>
        
        <div class="recommendations">
            <h3>💡 推奨事項</h3>
            <ul>
        """
        
        for recommendation in analysis.get('recommendations', []):
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

    def cleanup(self) -> None:
        """生成されたレポートファイルのクリーンアップ"""
        self.logger.info("レポートファイルのクリーンアップを開始します")
        
        for report_file in self.generated_reports:
            try:
                if os.path.exists(report_file):
                    os.remove(report_file)
                    self.logger.debug(f"レポートファイルを削除しました: {report_file}")
            except Exception as e:
                self.logger.warning(f"レポートファイル削除に失敗しました: {report_file} - {e}")
        
        self.generated_reports.clear()
        self.logger.info("レポートファイルのクリーンアップが完了しました")