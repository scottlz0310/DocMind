# DocMind リファクタリング候補分析(行数ベース)

## 📊 行数ランキング(上位20ファイル)

| 順位 | ファイル | 行数 | 分類 | 優先度 | 問題点 |
|------|----------|------|------|--------|--------|
| 1 | `src/gui/main_window.py` | 3,605行 | GUI | 🚨 **最優先** | 責務混在、巨大クラス |
| 2 | `src/gui/search_interface.py` | 1,504行 | GUI | 🔥 **高** | 検索UI複雑化 |
| 3 | `src/gui/folder_tree.py` | 1,409行 | GUI | 🔥 **高** | フォルダ管理複雑化 |
| 4 | `src/gui/search_results.py` | 758行 | GUI | ⚠️ **中** | 結果表示ロジック集中 |
| 5 | `src/gui/preview_widget.py` | 751行 | GUI | ⚠️ **中** | プレビュー機能複雑化 |
| 6 | `src/core/thread_manager.py` | 713行 | Core | ⚠️ **中** | スレッド管理複雑化 |
| 7 | `src/core/index_manager.py` | 701行 | Core | ✅ **低** | 適切な構造 |
| 8 | `src/core/search_manager.py` | 667行 | Core | ✅ **低** | 適切な構造 |
| 9 | `src/core/file_watcher.py` | 633行 | Core | ⚠️ **中** | ファイル監視複雑化 |
| 10 | `src/data/models.py` | 605行 | Data | ✅ **低** | データモデル定義 |
| 11 | `src/gui/settings_dialog.py` | 600行 | GUI | ⚠️ **中** | 設定画面複雑化 |
| 12 | `src/data/search_history_repository.py` | 576行 | Data | ⚠️ **中** | 履歴管理複雑化 |
| 13 | `src/core/document_processor.py` | 567行 | Core | ✅ **低** | 適切な構造 |
| 14 | `src/utils/background_processor.py` | 559行 | Utils | ⚠️ **中** | バックグラウンド処理 |
| 15 | `src/utils/cache_manager.py` | 516行 | Utils | ⚠️ **中** | キャッシュ管理 |
| 16 | `src/data/database.py` | 506行 | Data | ✅ **低** | 適切な構造 |
| 17 | `src/data/document_repository.py` | 458行 | Data | ✅ **低** | 適切な構造 |
| 18 | `src/utils/config.py` | 446行 | Utils | ⚠️ **中** | 設定管理 |
| 19 | `src/gui/error_dialog.py` | 435行 | GUI | ⚠️ **中** | エラー処理UI |

## 🎯 リファクタリング戦略

### 最優先(S級)- 即座に対処が必要
- **`main_window.py`** (3,605行) - 責務分離が急務

### 高優先度(A級)- 早急な対処が必要
- **`search_interface.py`** (1,504行) - 検索UI分割
- **`folder_tree.py`** (1,409行) - フォルダ管理分割

### 中優先度(B級)- 計画的な改善が必要
- `search_results.py` (758行)
- `preview_widget.py` (751行)
- `thread_manager.py` (713行)
- `file_watcher.py` (633行)
- `settings_dialog.py` (600行)

### 低優先度(C級)- 現状維持
- Core層の適切に設計されたファイル
- Data層のリポジトリパターン実装

## 📈 問題の深刻度分析

### GUI層の問題(最重要)
```
総行数: 8,662行(全体の43%)
平均: 1,083行/ファイル
問題: UI・ロジック・データアクセスの混在
```

### Core層の状況(良好)
```
総行数: 3,281行
平均: 547行/ファイル
状況: 比較的適切な責務分離
```

### Data層の状況(良好)
```
総行数: 2,145行
平均: 536行/ファイル
状況: リポジトリパターンで適切に分離
```

## 🚀 推奨アクション

### Phase 1: 緊急対応(1-2週間)
1. `main_window.py` の責務分離
   - メニュー管理 → `menu_manager.py`
   - ダイアログ管理 → `dialog_manager.py`
   - 進捗管理 → `progress_manager.py`

### Phase 2: 構造改善(2-4週間)
2. `search_interface.py` の機能分割
3. `folder_tree.py` の責務整理

### Phase 3: 最適化(4-8週間)
4. 中優先度ファイルの段階的改善
5. テストカバレッジの向上

## 📋 成功指標

- `main_window.py`: 3,605行 → 500行以下
- GUI層平均: 1,083行 → 400行以下
- 新規機能追加時の影響範囲を50%削減
- テスト実行時間を30%短縮

## 🔧 実装方針

1. **段階的分割**: 一度に全てを変更せず、機能単位で分割
2. **既存機能保持**: リファクタリング中も全機能が動作することを保証
3. **テスト駆動**: 分割前後でテストが通ることを確認
4. **依存関係管理**: import文と呼び出し関係を慎重に管理