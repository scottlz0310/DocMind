# DocMind リファクタリング継続用コンテキストファイル一覧

## 🎯 必須コンテキストファイル（セッション継続時に必ず読み込み）

### 1. プロジェクト基本情報
- `README.md` - プロジェクト概要・基本仕様
- `docs/DocuMind.txt` - 元の要件定義・仕様書

### 2. リファクタリング計画・進捗管理
- `REFACTORING_STATUS.md` - **最重要** 全Phase進捗状況
- `PHASE4_PROGRESS_TRACKER.md` - **Phase4進捗追跡（中断・再開対応）**
- `PHASE4_SAFETY_PLAN.md` - Phase4安全実行計画
- `PHASE4_PREPARATION_CHECKLIST.md` - Phase4準備チェックリスト
- `REFACTORING_ROADMAP_2025.md` - 2025-2026年全体ロードマップ

### 3. 分析レポート
- `LARGE_FILES_ANALYSIS.md` - **Phase4以降対象ファイル分析（最新）**
- `folder_tree_dependencies.json` - **folder_tree.py依存関係分析結果**
- `FOLDER_TREE_ANALYSIS.md` - **folder_tree.py詳細分析（Phase4用）**
- `SEARCH_INTERFACE_ANALYSIS.md` - search_interface.py詳細分析（Phase2完了）
- `MAIN_WINDOW_PHASE3_ANALYSIS.md` - main_window.py詳細分析（Phase3完了）

### 4. 安全性・品質ルール
- `.amazonq/rules/refactoring.md` - リファクタリング基本ルール
- `.amazonq/rules/safety.md` - 安全性確保ルール
- `.amazonq/rules/japanese.md` - 日本語対応規則
- `.amazonq/rules/product.md` - プロダクト概要

## 🔧 作業対象ファイル（実際のリファクタリング時）

### Phase4 最優先ターゲット
- `src/gui/folder_tree.py` - **1,408行, 76メソッド** 最大規模ファイル

### Phase1-3 完了済み
- `src/gui/main_window.py` - **395行** (89.0%削減完了) ✅
- `src/gui/search_interface.py` - **215行** (85.7%削減完了) ✅

### 参考用既存分離済みファイル
- `src/gui/managers/` - Phase1で作成済みマネージャー群
- `src/gui/controllers/` - Phase1で作成済みコントローラー群
- `src/gui/dialogs/` - Phase1で作成済みダイアログ群

## 📋 セッション開始時のチェックリスト

### 1. Phase4基本状況確認
```
@README.md
@REFACTORING_STATUS.md
@PHASE4_PROGRESS_TRACKER.md
```

### 2. Phase4作業対象確認
```
@src/gui/folder_tree.py
@PHASE4_SAFETY_PLAN.md
@LARGE_FILES_ANALYSIS.md
```

### 3. Phase4安全性・準備確認
```
@PHASE4_PREPARATION_CHECKLIST.md
@.amazonq/rules/refactoring.md
@.amazonq/rules/safety.md
```

## 🚨 重要な注意事項

### 必ず確認すべき情報
1. **Phase1-3成果**: main_window.py 3,605行→395行 (89.0%削減完了) ✅
2. **Phase1-3成果**: search_interface.py 1,504行→215行 (85.7%削減完了) ✅
3. **Phase4候補**: folder_tree.py 1,408行→200行 (85%削減目標)
4. **現在日付**: 2025-08-28以降の正確な日付を使用
5. **安全性原則**: 段階的分離、即座の検証、ロールバック準備

### 作業継続時の確認事項
- 仮想環境アクティベート状況
- 現在のブランチ状況
- 前回作業の完了状況
- テスト実行結果

## 📁 ディレクトリ構造参考

```
DocMind/
├── README.md                           # ✅ 必須
├── REFACTORING_STATUS.md              # ✅ 必須
├── PHASE4_PROGRESS_TRACKER.md         # ✅ 必須（Phase4進捗追跡）
├── PHASE4_SAFETY_PLAN.md              # ✅ 必須（Phase4安全計画）
├── PHASE4_PREPARATION_CHECKLIST.md    # ✅ 必須（Phase4準備）
├── LARGE_FILES_ANALYSIS.md            # ✅ 必須（Phase4以降計画）
├── FOLDER_TREE_ANALYSIS.md            # ✅ 必須（Phase4詳細分析）
├── folder_tree_dependencies.json      # ✅ 必須（依存関係分析結果）
├── REFACTORING_ROADMAP_2025.md        # ✅ 必須
├── SEARCH_INTERFACE_ANALYSIS.md       # ✅ 必須（完了）
├── .amazonq/rules/                    # ✅ 必須
│   ├── refactoring.md
│   ├── safety.md
│   ├── japanese.md
│   └── product.md
├── docs/DocuMind.txt                  # ✅ 必須
└── src/gui/
    ├── search_interface.py            # ✅ Phase1-3完了 (215行)
    ├── main_window.py                 # ✅ Phase1-3完了 (395行)
    ├── folder_tree.py                 # 🎯 Phase4最優先ターゲット (1,408行)
    ├── managers/                      # 📚 参考用
    ├── controllers/                   # 📚 参考用
    └── dialogs/                       # 📚 参考用
```

## 🔄 セッション継続コマンド例

```
# Phase4セッション継続（必須）
@README.md @REFACTORING_STATUS.md @PHASE4_PROGRESS_TRACKER.md

# Phase4作業継続（作業時）
@src/gui/folder_tree.py @PHASE4_SAFETY_PLAN.md @FOLDER_TREE_ANALYSIS.md

# Phase4安全性確認（毎回）
@PHASE4_PREPARATION_CHECKLIST.md @.amazonq/rules/refactoring.md @.amazonq/rules/safety.md
```

---
**作成日**: 2025-08-28
**更新日**: 2025-08-28 (Phase3準備完了)
**用途**: セッション継続・作業中断時の必須ファイル管理
**重要度**: 🔴 最高 - 作業継続に必須
**現在フェーズ**: Phase4準備 (folder_tree.py リファクタリング - 中断・再開対応)