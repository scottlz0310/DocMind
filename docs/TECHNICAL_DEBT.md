# 技術的負債・改善項目

## 🚨 緊急度：高

### HTMLテンプレートのハードコーディング問題

**問題**：
- `tests/validation_framework/validation_report_generator.py` (3,000行以上)
- `tests/validation_framework/validation_reporter.py` (2,500行以上)
- HTMLテンプレート、CSS、JavaScriptが全てPythonコード内にハードコーディング
- 455個の行長制限違反(E501エラー)

**影響**：
- コードの可読性・保守性が極めて低い
- HTMLの修正時にPythonコードを変更する必要
- 行長制限違反によりコード品質チェックが通らない
- デザイナーがHTMLを修正できない

**解決策**：
```
tests/validation_framework/
├── templates/
│   ├── base.html
│   ├── comprehensive_report.html
│   ├── error_handling_report.html
│   ├── performance_report.html
│   └── compatibility_report.html
├── static/
│   ├── css/
│   │   └── report_styles.css
│   └── js/
│       └── report_charts.js
└── template_loader.py
```

**実装方針**：
1. **テンプレートエンジン導入**: Jinja2を使用
2. **静的ファイル分離**: CSS/JSを外部ファイル化
3. **テンプレート継承**: base.htmlで共通レイアウト
4. **設定外部化**: レポート設定をYAMLファイル化

## 🔧 緊急度：中

### 大型ファイルの分割

**残存する大型ファイル**：
- `src/gui/preview_widget.py` (747行)
- `src/gui/search_results.py` (756行)
- `src/gui/settings_dialog.py` (598行)

**対応**：Phase5リファクタリングで責務分離

### テストフレームワークの整理

**問題**：
- 78,195行のテストコード(本体コードより多い)
- 重複するテストロジック
- テスト実行時間の長期化

**対応**：
- 共通テストユーティリティの抽出
- パフォーマンステストの最適化
- テストデータ生成の効率化

## 📋 緊急度：低

### 設定管理の統一

**問題**：
- 設定ファイルが複数形式(JSON、YAML、Python)
- 設定の重複・不整合

**対応**：
- 設定形式をYAMLに統一
- 設定バリデーション機能追加

### ログ出力の最適化

**問題**：
- 大量のデバッグログ出力
- ログレベルの不統一

**対応**：
- ログレベルの見直し
- 構造化ログの導入

## 🎯 優先順位

1. **最優先**: HTMLテンプレート分離(コード品質・保守性)
2. **高優先**: 大型ファイル分割(Phase5リファクタリング)
3. **中優先**: テストフレームワーク整理
4. **低優先**: 設定管理統一、ログ最適化

## 📅 実装スケジュール

### Phase5A: HTMLテンプレート分離 (1-2週間)
- [ ] Jinja2導入
- [ ] テンプレートファイル分離
- [ ] CSS/JS外部化
- [ ] 行長制限違反解消

### Phase5B: 大型ファイル分割 (2-3週間)
- [ ] preview_widget.py分割
- [ ] search_results.py分割
- [ ] settings_dialog.py分割

### Phase6: テスト最適化 (1-2週間)
- [ ] 共通ユーティリティ抽出
- [ ] テスト実行時間短縮
- [ ] テストカバレッジ最適化

## 💡 備考

この技術的負債は、PoC(概念実証)から本格的なアプリケーションへの成長過程で蓄積されたものです。機能実装を優先した結果、コード品質の改善が後回しになりました。

**教訓**：
- 初期段階からテンプレート分離を考慮すべき
- HTMLハードコーディングは避けるべき
- 定期的なリファクタリングが重要