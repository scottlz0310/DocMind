# DocMind 基盤検証フレームワーク

DocMindアプリケーションの包括的な動作検証を実施するための基盤フレームワークです。

## 概要

このフレームワークは以下の機能を提供します：

- **基盤検証クラス**: すべての検証の基盤となるベースクラス
- **パフォーマンス監視**: CPU、メモリ、ディスクI/O、ネットワークI/Oの監視
- **メモリ監視**: メモリ使用量の詳細監視とメモリリーク検出
- **エラー注入**: 意図的なエラー発生による堅牢性テスト
- **テストデータ生成**: 包括的なテストデータの自動生成
- **検証結果レポート**: HTML、Markdown、JSONでの詳細レポート生成
- **統計情報収集**: 検証結果の統計分析とトレンド分析

## 使用方法

### 基本的な使用例

```python
from validation_framework import BaseValidator, ValidationConfig

# カスタム検証クラスの作成
class MyValidator(BaseValidator):
    def setup_test_environment(self):
        # テスト環境のセットアップ
        pass
    
    def teardown_test_environment(self):
        # テスト環境のクリーンアップ
        pass
    
    def test_my_feature(self):
        # 実際の検証ロジック
        self.assert_condition(True, "機能が正常に動作しています")

# 検証の実行
config = ValidationConfig(
    enable_performance_monitoring=True,
    enable_memory_monitoring=True,
    max_execution_time=60.0,
    max_memory_usage=1024.0
)

validator = MyValidator(config)
results = validator.run_validation()

# 結果の確認
for result in results:
    print(f"テスト: {result.test_name}")
    print(f"結果: {'成功' if result.success else '失敗'}")
    print(f"実行時間: {result.execution_time:.2f}秒")
```

### パフォーマンス監視の使用例

```python
from validation_framework import PerformanceMonitor

monitor = PerformanceMonitor(sampling_interval=1.0)

# 監視開始
monitor.start_monitoring()

# 監視対象の処理を実行
# ... your code here ...

# 監視停止
monitor.stop_monitoring()

# 結果の取得
summary = monitor.get_performance_summary()
print(f"最大CPU使用率: {summary['cpu_usage']['peak_percent']:.1f}%")
print(f"最大メモリ使用量: {summary['memory_usage']['peak_mb']:.1f}MB")

# 閾値チェック
results = monitor.check_performance_thresholds(
    max_cpu_percent=80.0,
    max_memory_mb=2048.0
)
print(f"CPU閾値内: {results['cpu_within_threshold']}")
print(f"メモリ閾値内: {results['memory_within_threshold']}")
```

### エラー注入の使用例

```python
from validation_framework import ErrorInjector

injector = ErrorInjector()

# ファイル不存在エラーの注入
injector.inject_error(
    'file_not_found',
    parameters={'target_file': 'important_file.txt'},
    duration_seconds=10.0
)

# メモリ不足エラーの注入
injector.inject_error(
    'memory_error',
    parameters={'memory_mb': 500},
    probability=0.5  # 50%の確率で発生
)

# 注入統計の確認
stats = injector.get_injection_statistics()
print(f"総注入回数: {stats['total_injections']}")
print(f"成功率: {stats['success_rate']:.1%}")
```

### テストデータ生成の使用例

```python
from validation_framework import TestDataGenerator, TestDatasetConfig

generator = TestDataGenerator()

# 標準データセットの生成
config = TestDatasetConfig(
    dataset_name="standard_test",
    output_directory="./test_data",
    file_count=1000,
    file_types=['txt', 'pdf', 'docx', 'xlsx'],
    size_range_kb=(1, 100),
    include_corrupted=True,
    include_special_chars=True
)

result = generator.generate_dataset(config)
print(f"生成されたファイル数: {result['statistics']['total_files']}")
print(f"総サイズ: {result['statistics']['total_size_mb']:.2f}MB")

# 大規模データセットの生成
large_result = generator.generate_large_dataset(
    output_dir="./large_test_data",
    document_count=50000
)
```

### レポート生成の使用例

```python
from validation_framework import ValidationReporter, ReportConfig

reporter = ValidationReporter()

config = ReportConfig(
    output_directory="./reports",
    report_name="comprehensive_validation",
    include_charts=True,
    include_detailed_logs=True,
    report_format="html"
)

# レポート生成
report_files = reporter.generate_comprehensive_report(
    validation_results=validation_results,
    performance_data=performance_data,
    memory_data=memory_data,
    error_injection_data=error_data,
    config=config
)

print(f"HTMLレポート: {report_files['html_report']}")
print(f"サマリーレポート: {report_files['summary_report']}")
```

## アーキテクチャ

### クラス構成

```
BaseValidator (基盤クラス)
├── ValidationResult (結果データ)
├── ValidationConfig (設定データ)
├── PerformanceMonitor (パフォーマンス監視)
├── MemoryMonitor (メモリ監視)
├── ErrorInjector (エラー注入)
├── TestDataGenerator (テストデータ生成)
├── ValidationReporter (レポート生成)
└── StatisticsCollector (統計収集)
```

### 検証フロー

1. **初期化**: 検証設定の読み込みと監視コンポーネントの初期化
2. **環境セットアップ**: テスト環境の準備
3. **監視開始**: パフォーマンス・メモリ監視の開始
4. **テスト実行**: 各検証メソッドの実行
5. **結果収集**: 実行結果と統計情報の収集
6. **監視停止**: 監視の停止と結果取得
7. **レポート生成**: 包括的なレポートの生成
8. **クリーンアップ**: リソースの解放

## 設定オプション

### ValidationConfig

```python
ValidationConfig(
    enable_performance_monitoring=True,  # パフォーマンス監視の有効化
    enable_memory_monitoring=True,       # メモリ監視の有効化
    enable_error_injection=False,        # エラー注入の有効化
    max_execution_time=300.0,           # 最大実行時間（秒）
    max_memory_usage=2048.0,            # 最大メモリ使用量（MB）
    log_level="INFO",                   # ログレベル
    output_directory="validation_results" # 出力ディレクトリ
)
```

### ReportConfig

```python
ReportConfig(
    output_directory="./reports",        # レポート出力ディレクトリ
    report_name="validation_report",     # レポート名
    include_charts=True,                # チャート生成の有効化
    include_detailed_logs=True,         # 詳細ログの有効化
    chart_format="png",                 # チャート形式
    report_format="html"                # レポート形式
)
```

## エラー注入の種類

フレームワークは以下のエラー注入をサポートしています：

- `file_not_found`: ファイル不存在エラー
- `permission_denied`: 権限拒否エラー
- `disk_full`: ディスク容量不足エラー
- `memory_error`: メモリ不足エラー
- `network_timeout`: ネットワークタイムアウトエラー
- `database_connection_error`: データベース接続エラー
- `corrupted_file`: ファイル破損エラー
- `process_killed`: プロセス強制終了エラー
- `system_overload`: システム過負荷エラー
- `encoding_error`: 文字エンコーディングエラー

## 統計分析機能

### 基本統計

- 成功率、失敗率
- 実行時間の統計（平均、中央値、標準偏差、パーセンタイル）
- メモリ使用量の統計
- カテゴリ別分析

### 高度な分析

- トレンド分析（線形回帰）
- 異常値検出（IQR法）
- 相関分析（ピアソン相関係数）
- 分布分析（正規性検定、歪度、尖度）

## ベストプラクティス

### 1. 検証クラスの設計

```python
class MyFeatureValidator(BaseValidator):
    def setup_test_environment(self):
        """テスト環境の準備"""
        # データベースの初期化
        # テストデータの準備
        # 設定ファイルの作成
        pass
    
    def teardown_test_environment(self):
        """テスト環境のクリーンアップ"""
        # 一時ファイルの削除
        # データベースのクリーンアップ
        # リソースの解放
        pass
    
    def test_basic_functionality(self):
        """基本機能のテスト"""
        # 要件1.1の検証
        result = self.target_function()
        self.assert_condition(result is not None, "結果が返されること")
        
    def test_performance_requirements(self):
        """パフォーマンス要件のテスト"""
        # 要件7.1の検証（5秒以内の検索）
        start_time = time.time()
        result = self.search_function("test query")
        execution_time = time.time() - start_time
        
        self.assert_condition(execution_time <= 5.0, "検索が5秒以内に完了すること")
        self.assert_condition(len(result) > 0, "検索結果が返されること")
```

### 2. エラー処理

```python
def test_error_handling(self):
    """エラーハンドリングのテスト"""
    # エラー注入
    self.inject_error('file_not_found', parameters={'target_file': 'config.json'})
    
    try:
        # エラーが発生する可能性のある処理
        result = self.load_config()
        
        # エラーハンドリングが適切に動作することを確認
        self.assert_condition(result is not None, "デフォルト設定が使用されること")
        
    except Exception as e:
        # 予期しない例外は失敗とする
        self.assert_condition(False, f"予期しない例外が発生しました: {e}")
```

### 3. パフォーマンス監視

```python
def test_with_performance_monitoring(self):
    """パフォーマンス監視付きテスト"""
    # 監視開始
    self.performance_monitor.start_monitoring()
    
    try:
        # 監視対象の処理
        self.heavy_processing_function()
        
        # パフォーマンス要件の検証
        self.validate_performance_requirements(
            max_time=30.0,
            max_memory=1024.0
        )
        
    finally:
        # 監視停止
        self.performance_monitor.stop_monitoring()
```

## トラブルシューティング

### よくある問題と解決方法

1. **メモリ監視でtracemalloc関連のエラー**
   ```python
   # tracemalloc無効化での初期化
   monitor = MemoryMonitor(enable_tracemalloc=False)
   ```

2. **パフォーマンス監視でpsutil関連のエラー**
   ```bash
   pip install psutil
   ```

3. **レポート生成でmatplotlib関連のエラー**
   ```bash
   pip install matplotlib seaborn pandas
   ```

4. **ドキュメント生成ライブラリのエラー**
   ```bash
   pip install python-docx openpyxl PyMuPDF
   ```

### ログレベルの調整

```python
import logging

# デバッグレベルでの詳細ログ
config = ValidationConfig(log_level="DEBUG")

# 特定のロガーのレベル調整
logging.getLogger("validation.PerformanceMonitor").setLevel(logging.WARNING)
```

## 拡張方法

### カスタムエラー注入の追加

```python
class CustomErrorInjector(ErrorInjector):
    def __init__(self):
        super().__init__()
        # カスタムエラー注入メソッドの追加
        self.injection_methods['custom_error'] = self._inject_custom_error
    
    def _inject_custom_error(self, config):
        # カスタムエラー注入の実装
        pass
```

### カスタム統計分析の追加

```python
class CustomStatisticsCollector(StatisticsCollector):
    def get_custom_analysis(self):
        # カスタム分析の実装
        return {"custom_metric": self._calculate_custom_metric()}
    
    def _calculate_custom_metric(self):
        # カスタム指標の計算
        pass
```

## 参考資料

- [DocMind要件定義書](../comprehensive-validation/requirements.md)
- [DocMind設計書](../comprehensive-validation/design.md)
- [DocMind実装計画](../comprehensive-validation/tasks.md)
- [Python unittest ドキュメント](https://docs.python.org/3/library/unittest.html)
- [psutil ドキュメント](https://psutil.readthedocs.io/)
- [matplotlib ドキュメント](https://matplotlib.org/stable/contents.html)