# DocMind 包括的検証システム

DocMindアプリケーションの品質保証を目的とした包括的検証システムです。アプリケーションの全機能について体系的な検証を実施し、CI/CD環境での自動化された品質管理を提供します。

## 概要

### 主要機能

1. **包括的検証スイート** - 全機能の統合検証
2. **CI/CDパイプライン** - 継続的インテグレーション対応
3. **品質ゲート管理** - 品質基準の自動チェック
4. **検証スケジューラー** - 自動実行とスケジュール管理
5. **自動対応システム** - 問題発生時の自動対応

### 検証レベル

- **COMMIT** - コミット時の基本検証（5-10分）
- **DAILY** - 日次の包括検証（30-60分）
- **WEEKLY** - 週次の詳細検証（1-2時間）
- **RELEASE** - リリース前の完全検証（2-4時間）

## アーキテクチャ

```
包括的検証システム
├── 検証スイート層
│   ├── アプリケーション起動検証
│   ├── ドキュメント処理検証
│   ├── 検索機能検証
│   ├── GUI機能検証
│   ├── データ永続化検証
│   ├── エラーハンドリング検証
│   ├── パフォーマンス検証
│   ├── セキュリティ検証
│   ├── 統合ワークフロー検証
│   └── 互換性検証
├── CI/CDパイプライン層
│   ├── ビルドステージ
│   ├── テストステージ
│   ├── セキュリティスキャン
│   ├── パフォーマンステスト
│   └── デプロイステージ
├── 品質ゲート層
│   ├── テストカバレッジゲート
│   ├── セキュリティ問題ゲート
│   ├── パフォーマンス回帰ゲート
│   └── コード品質ゲート
└── 自動化・スケジューリング層
    ├── 検証スケジューラー
    ├── 自動対応システム
    └── 通知システム
```

## セットアップ

### 1. 依存関係のインストール

```bash
# 基本依存関係
pip install -r requirements.txt

# 検証フレームワーク用追加パッケージ
pip install pytest pytest-cov pytest-xvfb pytest-qt
pip install bandit safety semgrep
pip install memory-profiler psutil
pip install schedule requests
```

### 2. 設定ファイルの準備

```bash
# 設定ファイルのコピー
cp tests/validation_framework/config/validation_config.json.example \
   tests/validation_framework/config/validation_config.json

# 設定の編集
vim tests/validation_framework/config/validation_config.json
```

### 3. 環境変数の設定

```bash
# 通知設定（オプション）
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
export EMAIL_USERNAME="your-email@example.com"
export EMAIL_PASSWORD="your-app-password"

# GitHub設定（オプション）
export GITHUB_TOKEN="your-github-token"
```

## 使用方法

### 基本的な使用方法

#### 1. 単発実行

```bash
# コミット時検証の実行
python tests/validation_framework/run_comprehensive_validation.py --level commit

# 日次検証の実行
python tests/validation_framework/run_comprehensive_validation.py --level daily

# 週次検証の実行
python tests/validation_framework/run_comprehensive_validation.py --level weekly

# リリース前検証の実行
python tests/validation_framework/run_comprehensive_validation.py --level release
```

#### 2. スケジューラーモード

```bash
# デーモンモードでスケジューラーを開始
python tests/validation_framework/run_comprehensive_validation.py --scheduler

# 特定のスケジュールを即座に実行
python tests/validation_framework/run_comprehensive_validation.py --execute daily
```

#### 3. 個別コンポーネントの実行

```bash
# 包括的検証スイートのみ
python tests/validation_framework/comprehensive_validation_suite.py --level daily

# CI/CDパイプラインのみ
python tests/validation_framework/ci_cd_pipeline.py

# 品質ゲートのみ
python tests/validation_framework/quality_gate_manager.py \
  --coverage-file coverage.xml \
  --security-report security_report.json
```

### 高度な使用方法

#### 1. カスタム設定での実行

```bash
# タイムアウト時間の変更
python tests/validation_framework/run_comprehensive_validation.py \
  --level daily --timeout 180

# 特定コンポーネントの無効化
python tests/validation_framework/run_comprehensive_validation.py \
  --level daily --no-pipeline --no-quality-gates

# 詳細ログの有効化
python tests/validation_framework/run_comprehensive_validation.py \
  --level daily --verbose
```

#### 2. CI/CD環境での実行

```bash
# GitHub Actions での実行例
name: 包括的検証
on: [push, pull_request, schedule]
jobs:
  validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: 包括的検証の実行
        run: |
          python tests/validation_framework/run_comprehensive_validation.py \
            --level daily --output-dir ${{ github.workspace }}/results
```

## 設定

### 検証設定 (validation_config.json)

```json
{
  "validation_suite": {
    "default_level": "daily",
    "timeout_seconds": 3600,
    "parallel_execution": true,
    "components": {
      "startup": {"enabled": true, "timeout": 300},
      "document_processing": {"enabled": true, "timeout": 600},
      "search": {"enabled": true, "timeout": 900},
      "gui": {"enabled": false, "timeout": 1200},
      "performance": {"enabled": true, "timeout": 1800}
    }
  },
  "quality_gates": {
    "test_coverage": {
      "enabled": true,
      "thresholds": {"line_coverage": {"min_value": 80.0}}
    },
    "security_issues": {
      "enabled": true,
      "thresholds": {"critical_issues": {"max_value": 0}}
    }
  }
}
```

### スケジュール設定

```json
{
  "scheduler": {
    "schedules": {
      "commit": {
        "enabled": true,
        "validation_level": "commit",
        "watch_branches": ["main", "develop"]
      },
      "daily": {
        "enabled": true,
        "daily_time": "02:00"
      },
      "weekly": {
        "enabled": true,
        "weekly_day": "sunday",
        "weekly_time": "01:00"
      }
    }
  }
}
```

## 品質ゲート

### 標準品質ゲート

1. **テストカバレッジ**
   - ラインカバレッジ: 80%以上
   - ブランチカバレッジ: 75%以上

2. **セキュリティ問題**
   - 重要な問題: 0件
   - 高レベル問題: 2件以下

3. **パフォーマンス回帰**
   - 回帰率: 10%以下
   - メモリ使用量: 15%以下の増加

4. **コード品質**
   - 複雑度スコア: 10以下
   - 重複率: 5%以下

### カスタム品質ゲートの追加

```python
from tests.validation_framework.quality_gate_manager import (
    QualityGateChecker, QualityGateConfig, QualityGateType
)

class CustomQualityGate(QualityGateChecker):
    async def check(self, data):
        # カスタムチェックロジック
        return self._create_result(QualityGateResult.PASSED)

# 品質ゲートの追加
config = QualityGateConfig(gate_type=QualityGateType.CODE_QUALITY)
custom_gate = CustomQualityGate(config)
manager.add_gate(custom_gate)
```

## 自動対応アクション

### 標準アクション

1. **通知** - Slack/メール通知
2. **デプロイメントブロック** - 自動デプロイの停止
3. **ロールバック** - 自動的な変更の取り消し
4. **課題作成** - GitHub Issues の自動作成

### カスタムアクションの追加

```python
from tests.validation_framework.quality_gate_manager import AutoActionExecutor

class CustomAction(AutoActionExecutor):
    async def execute(self, gate_result, context):
        # カスタムアクションロジック
        return True

# アクションの追加
action_config = AutoActionConfig(action_type=ActionType.CUSTOM_SCRIPT)
custom_action = CustomAction(action_config)
manager.add_action(custom_action)
```

## レポート

### 生成されるレポート

1. **HTMLレポート** - 視覚的な結果表示
2. **JSONレポート** - 機械可読な詳細結果
3. **XMLレポート** - CI/CD統合用
4. **トレンドレポート** - 時系列での品質推移

### レポートの確認

```bash
# レポート生成
python tests/validation_framework/validation_report_generator.py \
  --input-dir validation_results \
  --output-file report.html \
  --format html

# ブラウザでレポートを開く
open report.html
```

## トラブルシューティング

### よくある問題

#### 1. GUI テストの失敗

```bash
# 仮想ディスプレイの設定
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 &

# オフスクリーンモードの使用
export QT_QPA_PLATFORM=offscreen
```

#### 2. メモリ不足エラー

```bash
# メモリ制限の調整
export PYTEST_CURRENT_TEST_MEMORY_LIMIT=4GB

# 並列実行の無効化
python run_comprehensive_validation.py --level daily --no-parallel
```

#### 3. タイムアウトエラー

```bash
# タイムアウト時間の延長
python run_comprehensive_validation.py --level daily --timeout 180
```

### ログの確認

```bash
# 詳細ログの確認
tail -f validation_results/comprehensive_validation_*.log

# エラーログの抽出
grep ERROR validation_results/*.log
```

### デバッグモード

```bash
# デバッグモードでの実行
python -m pdb tests/validation_framework/run_comprehensive_validation.py --level daily

# 詳細ログの有効化
python run_comprehensive_validation.py --level daily --verbose
```

## パフォーマンス最適化

### 実行時間の短縮

1. **並列実行の有効化**
   ```json
   {"validation_suite": {"parallel_execution": true}}
   ```

2. **不要なコンポーネントの無効化**
   ```json
   {"components": {"gui": {"enabled": false}}}
   ```

3. **テストデータサイズの調整**
   ```json
   {"document_processing": {"test_data_size": "small"}}
   ```

### リソース使用量の最適化

1. **メモリ制限の設定**
   ```json
   {"performance": {"memory_limit_gb": 2.0}}
   ```

2. **CPU使用率の制限**
   ```json
   {"performance": {"cpu_threshold_percent": 80.0}}
   ```

## 拡張

### 新しい検証コンポーネントの追加

```python
from tests.validation_framework.base_validator import BaseValidator

class NewValidator(BaseValidator):
    async def run_validation(self):
        # 検証ロジックの実装
        return {"success": True, "details": {}}

# 検証スイートへの追加
suite.validators['new_component'] = NewValidator()
```

### 新しい品質ゲートの追加

```python
class NewQualityGate(QualityGateChecker):
    async def check(self, data):
        # チェックロジックの実装
        return self._create_result(QualityGateResult.PASSED)
```

### 新しい通知チャンネルの追加

```python
class NewNotificationChannel:
    async def send(self, message):
        # 通知送信ロジックの実装
        pass
```

## ベストプラクティス

### 1. 検証レベルの選択

- **開発中**: COMMIT レベルで高速フィードバック
- **統合時**: DAILY レベルで包括的チェック
- **リリース前**: WEEKLY または RELEASE レベルで完全検証

### 2. 品質ゲートの設定

- 段階的な基準設定（警告 → エラー）
- プロジェクトの成熟度に応じた調整
- 継続的な基準の見直し

### 3. 自動対応の設定

- 重要度に応じたアクションの選択
- 誤検知を考慮した慎重な設定
- 手動介入の余地を残す

### 4. 監視とメンテナンス

- 定期的な実行時間の監視
- 失敗パターンの分析と改善
- テストデータの定期更新

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

プロジェクトへの貢献を歓迎します。以下の手順に従ってください：

1. フォークを作成
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## サポート

問題や質問がある場合は、以下の方法でサポートを受けることができます：

- GitHub Issues での報告
- プロジェクトドキュメントの確認
- コミュニティフォーラムでの質問

---

**注意**: このシステムは継続的に改善されています。最新の情報については、プロジェクトのドキュメントを確認してください。