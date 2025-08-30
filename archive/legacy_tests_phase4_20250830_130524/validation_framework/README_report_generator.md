# ValidationReportGenerator 使用ガイド

## 概要

ValidationReportGeneratorは、DocMind検証フレームワークの包括的なレポート生成システムです。検証結果を分析し、サマリーレポート、詳細レポート、トレンド分析レポート、パフォーマンスグラフ、エラーログ分析、品質指標の可視化機能を提供します。

## 主要機能

### 1. サマリーレポート生成
- 基本統計情報の要約
- 品質指標の概要
- カテゴリ別結果
- 主要エラーパターン

### 2. 詳細レポート生成
- HTML、Markdown、JSON形式での詳細レポート
- インタラクティブなチャートとグラフ
- 失敗したテストの詳細分析
- パフォーマンス指標の可視化

### 3. トレンド分析レポート
- 過去の検証結果との比較
- パフォーマンス推移の分析
- 品質指標のトレンド
- 時系列チャートの生成

### 4. パフォーマンスグラフ生成
- カテゴリ別成功率グラフ
- 実行時間分布グラフ
- メモリ使用量グラフ
- エラーパターン分布グラフ
- 品質指標レーダーチャート

### 5. エラーログ分析
- エラーパターンの分類と分析
- 失敗したテストの詳細
- エラー対策推奨事項
- エラー重要度の判定

### 6. 品質指標可視化
- 総合品質スコアの計算
- 安定性、パフォーマンス、効率性の評価
- ベンチマーク比較
- プログレスバーとレーダーチャート

## 使用方法

### 基本的な使用例

```python
from tests.validation_framework.validation_report_generator import (
    ValidationReportGenerator,
    ReportGenerationConfig,
    ValidationMetrics,
    PerformanceMetrics
)
from datetime import datetime

# レポート生成設定
config = ReportGenerationConfig(
    output_directory="./validation_reports",
    report_name="docmind_validation",
    include_charts=True,
    include_detailed_logs=True,
    include_trend_analysis=True,
    include_performance_graphs=True,
    include_error_analysis=True,
    chart_format="png",
    report_formats=["html", "markdown", "json"]
)

# レポート生成器の初期化
generator = ValidationReportGenerator(config)

# 検証結果の作成
validation_results = [
    ValidationMetrics(
        test_name="test_search_functionality",
        success=True,
        execution_time=2.5,
        memory_usage=512.0,
        cpu_usage=45.0,
        category="search",
        timestamp=datetime.now()
    ),
    ValidationMetrics(
        test_name="test_error_handling",
        success=False,
        execution_time=8.2,
        memory_usage=1024.0,
        cpu_usage=75.0,
        error_message="Timeout error occurred",
        category="error_handling",
        timestamp=datetime.now()
    )
]

# パフォーマンスメトリクス
performance_data = PerformanceMetrics(
    peak_cpu_percent=85.2,
    average_cpu_percent=62.8,
    peak_memory_mb=2048.5,
    average_memory_mb=1024.3,
    disk_read_mb=156.7,
    disk_write_mb=89.4,
    network_sent_mb=12.3,
    network_received_mb=45.6,
    monitoring_duration_seconds=300.0
)

# 包括的レポートの生成
generated_files = generator.generate_comprehensive_report(
    validation_results=validation_results,
    performance_data=performance_data,
    additional_data={
        "test_environment": "Windows 10",
        "python_version": "3.11.0"
    }
)

print(f"生成されたレポート: {generated_files}")
```

### 設定オプション

#### ReportGenerationConfig

| パラメータ | 型 | デフォルト | 説明 |
|-----------|----|-----------|----- |
| output_directory | str | 必須 | レポート出力ディレクトリ |
| report_name | str | "validation_report" | レポート名 |
| include_charts | bool | True | チャート生成の有無 |
| include_detailed_logs | bool | True | 詳細ログの有無 |
| include_trend_analysis | bool | True | トレンド分析の有無 |
| include_performance_graphs | bool | True | パフォーマンスグラフの有無 |
| include_error_analysis | bool | True | エラー分析の有無 |
| chart_format | str | "png" | チャート形式 (png, svg, pdf) |
| report_formats | List[str] | ["html"] | レポート形式 (html, markdown, json) |

#### ValidationMetrics

| パラメータ | 型 | 説明 |
|-----------|----|----- |
| test_name | str | テスト名 |
| success | bool | 成功/失敗 |
| execution_time | float | 実行時間（秒） |
| memory_usage | float | メモリ使用量（MB） |
| cpu_usage | float | CPU使用率（%） |
| error_message | Optional[str] | エラーメッセージ |
| timestamp | datetime | 実行時刻 |
| category | str | テストカテゴリ |

#### PerformanceMetrics

| パラメータ | 型 | 説明 |
|-----------|----|----- |
| peak_cpu_percent | float | 最大CPU使用率 |
| average_cpu_percent | float | 平均CPU使用率 |
| peak_memory_mb | float | 最大メモリ使用量 |
| average_memory_mb | float | 平均メモリ使用量 |
| disk_read_mb | float | ディスク読み込み量 |
| disk_write_mb | float | ディスク書き込み量 |
| network_sent_mb | float | ネットワーク送信量 |
| network_received_mb | float | ネットワーク受信量 |
| monitoring_duration_seconds | float | 監視時間 |

### 高度な使用例

#### カスタム品質指標の設定

```python
# 品質指標のカスタマイズ
config = ReportGenerationConfig(
    output_directory="./custom_reports",
    report_name="custom_validation",
    include_charts=True,
    chart_format="svg",  # SVG形式でチャート生成
    report_formats=["html", "json"]  # HTMLとJSONのみ生成
)

generator = ValidationReportGenerator(config)
```

#### 過去結果との比較

```python
# 過去の検証結果との比較レポート生成
comparison_report = generator.generate_comparison_with_historical_results({
    'summary': {
        'success_rate': 85.7,
        'average_execution_time': 5.2,
        'peak_memory_usage': 1536.0
    },
    'quality_indicators': {
        'overall_quality_score': 82.5
    },
    'metadata': {
        'generation_time': datetime.now().isoformat()
    }
})
```

#### エラー分析のカスタマイズ

```python
# エラー分析に特化したレポート生成
error_config = ReportGenerationConfig(
    output_directory="./error_reports",
    report_name="error_analysis",
    include_charts=False,
    include_trend_analysis=False,
    include_performance_graphs=False,
    include_error_analysis=True,  # エラー分析のみ有効
    report_formats=["html"]
)

error_generator = ValidationReportGenerator(error_config)
```

## 生成されるファイル

### 基本レポートファイル

1. **{report_name}_summary.txt** - テキスト形式のサマリーレポート
2. **{report_name}_detailed.html** - HTML形式の詳細レポート
3. **{report_name}_detailed.md** - Markdown形式の詳細レポート
4. **{report_name}_detailed.json** - JSON形式の詳細レポート

### 分析レポートファイル

5. **{report_name}_trend_analysis.html** - トレンド分析レポート
6. **{report_name}_error_analysis.html** - エラー分析レポート
7. **{report_name}_quality_indicators.html** - 品質指標可視化レポート
8. **{report_name}_historical_comparison.html** - 過去結果比較レポート

### グラフファイル（charts/ディレクトリ内）

9. **category_success_rate.png** - カテゴリ別成功率グラフ
10. **execution_time_distribution.png** - 実行時間分布グラフ
11. **memory_usage.png** - メモリ使用量グラフ
12. **error_patterns.png** - エラーパターン分布グラフ
13. **quality_radar.png** - 品質指標レーダーチャート
14. **performance_trend.png** - パフォーマンス推移グラフ

### 履歴データファイル

15. **validation_history.json** - 検証結果履歴データ

## 品質指標の計算方法

### 総合品質スコア
- 成功率: 40%
- 安定性スコア: 20%
- パフォーマンススコア: 20%
- 効率性（メモリ+CPU）: 20%

### 安定性スコア
実行時間の標準偏差から計算される一貫性の指標

### パフォーマンススコア
- 実行時間スコア: 50%
- メモリ効率性: 25%
- CPU効率性: 25%

### 効率性スコア
リソース使用量に基づく効率性の評価

## トラブルシューティング

### よくある問題

#### 1. チャート生成エラー
```
ModuleNotFoundError: No module named 'matplotlib'
```
**解決方法**: 必要なライブラリをインストール
```bash
pip install matplotlib seaborn pandas numpy
```

#### 2. 履歴データが見つからない
```
WARNING: トレンド分析に十分な履歴データがありません
```
**解決方法**: 複数回の検証実行後に再度実行

#### 3. 出力ディレクトリの権限エラー
```
PermissionError: [Errno 13] Permission denied
```
**解決方法**: 書き込み権限のあるディレクトリを指定

### デバッグ方法

```python
import logging

# ログレベルを設定してデバッグ情報を表示
logging.basicConfig(level=logging.DEBUG)

# レポート生成器の詳細ログを確認
generator = ValidationReportGenerator(config)
```

## パフォーマンス最適化

### 大量データの処理

```python
# 大量の検証結果を処理する場合の最適化
config = ReportGenerationConfig(
    output_directory="./large_reports",
    report_name="large_dataset",
    include_charts=False,  # チャート生成を無効化
    include_performance_graphs=False,  # パフォーマンスグラフを無効化
    report_formats=["json"]  # 軽量なJSON形式のみ
)
```

### メモリ使用量の削減

```python
# メモリ使用量を削減するための設定
config = ReportGenerationConfig(
    output_directory="./memory_optimized",
    report_name="optimized",
    include_detailed_logs=False,  # 詳細ログを無効化
    chart_format="png"  # 軽量なPNG形式を使用
)
```

## 拡張とカスタマイズ

### カスタムエラー分類器の追加

```python
class CustomValidationReportGenerator(ValidationReportGenerator):
    def _classify_error_type(self, error_message: str) -> str:
        """カスタムエラー分類ロジック"""
        if "custom_error" in error_message.lower():
            return "CustomError"
        return super()._classify_error_type(error_message)
```

### カスタム品質指標の追加

```python
def custom_quality_calculator(validation_results):
    """カスタム品質指標の計算"""
    # 独自の品質計算ロジックを実装
    pass
```

## ライセンス

このコードはMITライセンスの下で提供されています。

## サポート

問題や質問がある場合は、プロジェクトのIssueトラッカーまでお知らせください。