# テストタイムアウト設定ガイド

## 概要

DocMindプロジェクトでは、テストの実行時間を制御し、無限ループやハングアップを防ぐためにタイムアウト設定を導入しています。

## 設定内容

### 1. pytest設定(pytest.ini)

```ini
addopts = 
    --timeout=60
    --timeout-method=thread
```

- **デフォルトタイムアウト**: 60秒
- **タイムアウト方式**: スレッドベース

### 2. CI/CD設定(.github/workflows/ci.yml)

```yaml
- name: Run tests
  run: |
    pytest tests/ -v --cov=src --cov-report=xml --maxfail=5 -n auto --timeout=300 --tb=short
  timeout-minutes: 10
```

- **pytest タイムアウト**: 300秒(5分)
- **GitHub Actions タイムアウト**: 10分

### 3. 依存関係(pyproject.toml)

```toml
"pytest-timeout>=2.1.0",
```

## タイムアウト設定の階層

1. **個別テスト**: `@pytest.mark.timeout(秒数)` デコレータ
2. **pytest設定**: `pytest.ini` のデフォルト設定(60秒)
3. **CI実行**: GitHub Actions の `timeout-minutes`(10分)
4. **システム**: `timeout` コマンドによる強制終了

## 使用例

### 基本的なテスト
```python
def test_basic_operation():
    # デフォルト60秒タイムアウト
    assert True
```

### カスタムタイムアウト
```python
@pytest.mark.timeout(30)
def test_quick_operation():
    # 30秒タイムアウト
    assert True
```

### タイムアウト無効化
```python
@pytest.mark.timeout(0)
def test_no_timeout():
    # タイムアウトなし(非推奨)
    assert True
```

## 推奨タイムアウト時間

| テストタイプ | 推奨時間 | 理由 |
|-------------|---------|------|
| ユニットテスト | 5-10秒 | 高速実行が期待される |
| 統合テスト | 30-60秒 | 複数コンポーネントの連携 |
| パフォーマンステスト | 120-300秒 | 大量データ処理 |
| エンドツーエンドテスト | 300-600秒 | 全体フロー確認 |

## トラブルシューティング

### テストがタイムアウトする場合

1. **原因調査**
   - 無限ループの確認
   - 外部依存関係の問題
   - リソース不足

2. **対処方法**
   - タイムアウト時間の調整
   - モック化による高速化
   - テストの分割

### CI/CDでのタイムアウト

```bash
# ローカルでのタイムアウトテスト
timeout 60 pytest tests/specific_test.py -v

# 詳細ログ付き実行
pytest tests/ -v --timeout=60 --timeout-method=thread --tb=long
```

## 設定変更手順

1. **個別テスト**: デコレータを追加
2. **プロジェクト全体**: `pytest.ini` を編集
3. **CI/CD**: `.github/workflows/ci.yml` を編集
4. **依存関係**: `pyproject.toml` を更新

## 注意事項

- タイムアウト時間は適切に設定する(短すぎると正常なテストが失敗)
- CI環境とローカル環境の性能差を考慮する
- 重要なテストは複数回実行して安定性を確認する
- タイムアウトが頻発する場合はテスト設計を見直す

## 関連ファイル

- `pytest.ini`: pytest設定
- `.github/workflows/ci.yml`: CI/CD設定
- `pyproject.toml`: 依存関係設定
- `tests/test_timeout_verification.py`: タイムアウト動作確認テスト