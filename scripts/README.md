# DocMind 開発ツール

このディレクトリには、DocMindプロジェクトの開発・保守に使用するツールが含まれています。

## 📁 ディレクトリ構成

```
scripts/
├── tools/          # 有用な開発ツール
├── archive/        # 旧開発ファイル（参考用）
└── README.md       # このファイル
```

## 🛠️ 開発ツール (tools/)

### run_tests.py
**用途**: 段階的テスト実行とレポート生成

```bash
# 全テスト実行
python scripts/tools/run_tests.py

# 特定のテストタイプのみ実行
python scripts/tools/run_tests.py unit        # ユニットテスト
python scripts/tools/run_tests.py integration # 統合テスト
python scripts/tools/run_tests.py performance # パフォーマンステスト
python scripts/tools/run_tests.py gui         # GUIテスト
```

**機能**:
- 環境セットアップ（オフスクリーンモード）
- テストタイプ別実行
- 結果サマリー表示
- カバレッジレポート生成

### measure_test_coverage.py
**用途**: テストカバレッジ測定と分析

```bash
python scripts/tools/measure_test_coverage.py
```

**機能**:
- ソースファイル分析
- テストファイル検索・作成
- カバレッジ測定実行
- 詳細レポート生成（TEST_COVERAGE_REPORT.md）
- 改善提案



## 📋 使用例

### 開発ワークフロー

1. **コード変更後のテスト実行**
   ```bash
   python scripts/tools/run_tests.py unit
   ```

2. **カバレッジ確認**
   ```bash
   python scripts/tools/measure_test_coverage.py
   ```

### CI/CD統合

これらのツールはMakefileから呼び出すことも可能：

```bash
make test          # run_tests.py相当
make test-cov      # カバレッジ付きテスト
```

## 📦 archive/

旧開発ファイルが保存されています。これらは：

- **Phase4開発時のスクリプト**: 開発プロセスの記録として保持
- **分析・最適化ツール**: 特定の開発段階で使用されたツール
- **進捗管理スクリプト**: プロジェクト管理用のスクリプト

**注意**: archiveディレクトリのファイルは現在のプロジェクト構成では動作しない可能性があります。

## 🔧 ツール開発ガイドライン

新しいツールを追加する場合：

1. **tools/ディレクトリに配置**
2. **適切なdocstringを記述**
3. **このREADMEを更新**
4. **エラーハンドリングを実装**
5. **ログ出力を統一**

### コーディング規約

- Python 3.11以上対応
- 型ヒント使用
- ruff準拠のコードスタイル
- 適切な例外処理
- ユーザーフレンドリーな出力

## 📝 ログ出力形式

ツールの出力は以下の形式に統一：

```
🔍 [ツール名] 処理開始
=== セクション名 ===
✅ 成功メッセージ
⚠️ 警告メッセージ
❌ エラーメッセージ
📊 結果サマリー
```

## 🤝 貢献

ツールの改善や新機能追加は歓迎します：

1. 既存ツールの機能拡張
2. 新しい分析ツールの追加
3. パフォーマンス改善
4. ドキュメント改善

---

**最終更新**: 2024-12-19
**メンテナー**: DocMind開発チーム