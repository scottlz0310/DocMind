# search_interface.py 詳細分析レポート

## 📊 現状分析

**ファイル**: `src/gui/search_interface.py`
- **行数**: 1,504行
- **メソッド数**: 79メソッド
- **クラス数**: 7クラス
- **複雑度**: 非常に高

## 🔍 クラス別分析

### 1. SearchInputWidget (検索入力ウィジェット)
- **行数**: 約180行
- **メソッド数**: 8メソッド
- **責務**: オートコンプリート付き検索入力
- **分離可能性**: ✅ 独立性高

### 2. SearchTypeSelector (検索タイプ選択)
- **行数**: 約120行
- **メソッド数**: 4メソッド
- **責務**: 全文/セマンティック/ハイブリッド検索選択
- **分離可能性**: ✅ 独立性高

### 3. AdvancedSearchOptions (高度な検索オプション)
- **行数**: 約350行
- **メソッド数**: 12メソッド
- **責務**: ファイルタイプ、日付範囲、重み設定
- **分離可能性**: ✅ 独立性高

### 4. SearchProgressWidget (検索進捗表示)
- **行数**: 約150行
- **メソッド数**: 8メソッド
- **責務**: 進捗バー、キャンセル機能、実行時間表示
- **分離可能性**: ✅ 独立性高

### 5. SearchHistoryWidget (検索履歴管理)
- **行数**: 約400行
- **メソッド数**: 15メソッド
- **責務**: 最近の検索、人気の検索、保存された検索
- **分離可能性**: ✅ 独立性高

### 6. SearchInterface (統合検索インターフェース)
- **行数**: 約280行
- **メソッド数**: 31メソッド
- **責務**: 全コンポーネントの統合管理
- **分離可能性**: 🔄 部分的分離可能

### 7. SearchWorkerThread (検索ワーカースレッド)
- **行数**: 約24行
- **メソッド数**: 3メソッド
- **責務**: 非同期検索処理
- **分離可能性**: ✅ 独立性高

## 🎯 リファクタリング戦略

### Phase 1: 独立コンポーネントの分離
**目標**: 各ウィジェットを独立ファイルに分離

```
src/gui/search/
├── __init__.py
├── input_widget.py          # SearchInputWidget
├── type_selector.py         # SearchTypeSelector  
├── advanced_options.py      # AdvancedSearchOptions
├── progress_widget.py       # SearchProgressWidget
├── history_widget.py        # SearchHistoryWidget
└── worker_thread.py         # SearchWorkerThread
```

### Phase 2: SearchInterface の分離
**目標**: 統合管理クラスを責務別に分離

```
src/gui/search/
├── managers/
│   ├── search_ui_manager.py     # UI構築・レイアウト管理
│   ├── search_state_manager.py  # 検索状態管理
│   └── search_event_manager.py  # イベント・シグナル管理
├── controllers/
│   ├── search_controller.py     # 検索ロジック制御
│   └── query_builder.py         # SearchQuery構築
└── search_interface.py          # 統合インターフェース (目標: 150行)
```

## 📈 期待効果

### 分離前 (現状)
- **search_interface.py**: 1,504行, 79メソッド
- **保守性**: 低 (巨大ファイル)
- **テスト容易性**: 低 (複雑な依存関係)
- **再利用性**: 低 (密結合)

### 分離後 (目標)
- **search_interface.py**: 150行, 10メソッド (90%削減)
- **個別コンポーネント**: 各100-200行, 5-15メソッド
- **保守性**: 高 (責務分離)
- **テスト容易性**: 高 (独立テスト可能)
- **再利用性**: 高 (疎結合)

## 🔧 実装計画

### Week 1: 独立コンポーネント分離
- **Day 1**: SearchInputWidget → input_widget.py
- **Day 2**: SearchTypeSelector → type_selector.py
- **Day 3**: AdvancedSearchOptions → advanced_options.py
- **Day 4**: SearchProgressWidget → progress_widget.py
- **Day 5**: SearchHistoryWidget → history_widget.py

### Week 2: SearchInterface リファクタリング
- **Day 1-2**: UI管理・状態管理分離
- **Day 3-4**: イベント管理・検索制御分離
- **Day 5**: 統合テスト・品質保証

## 🚨 リスク要因

### 高リスク
1. **複雑なシグナル接続**: 多数のQt シグナル・スロット接続
2. **状態管理**: 検索状態の複雑な管理ロジック
3. **UI依存関係**: ウィジェット間の密な結合

### 対策
- **段階的分離**: 1つずつ慎重に分離
- **シグナル管理**: 専用マネージャーで集中管理
- **インターフェース設計**: 明確なAPI定義

## 📋 品質基準

### 分離後の各ファイル
- **最大行数**: 200行
- **最大メソッド数**: 15メソッド
- **単一責任**: 1ファイル = 1責務
- **循環参照**: 禁止
- **型ヒント**: 必須

### テスト要件
- **単体テスト**: 各コンポーネント個別テスト
- **統合テスト**: 全体動作確認
- **UI テスト**: ユーザー操作シナリオ
- **パフォーマンステスト**: 応答性確認

## 🎯 成功指標

### 定量的指標
- **search_interface.py**: 1,504行 → 150行 (90%削減)
- **メソッド数**: 79個 → 10個 (87%削減)
- **ファイル数**: 1個 → 10個 (責務分散)
- **テスト実行時間**: 50%短縮

### 定性的指標
- **保守性**: 各コンポーネントの独立修正可能
- **拡張性**: 新機能追加の影響最小化
- **可読性**: 責務の明確化
- **再利用性**: 他プロジェクトでの利用可能

---
**作成日**: 2025-08-28
**分析対象**: search_interface.py (1,504行, 79メソッド)
**リファクタリング優先度**: 🔴 最高 (Phase 2の最重要ターゲット)