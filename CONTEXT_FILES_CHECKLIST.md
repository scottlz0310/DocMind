# DocMind リファクタリング継続用コンテキストファイル一覧

## 🎯 必須コンテキストファイル（セッション継続時に必ず読み込み）

### 1. プロジェクト基本情報
- `README.md` - プロジェクト概要・基本仕様
- `docs/DocuMind.txt` - 元の要件定義・仕様書

### 2. リファクタリング計画・進捗管理
- `REFACTORING_STATUS.md` - **最重要** 全Phase進捗状況
- `REFACTORING_PLAN_PHASE2.md` - Phase2詳細計画・戦略（完了）
- `REFACTORING_PLAN_PHASE3.md` - **Phase3詳細計画・戦略（現在）**
- `REFACTORING_ROADMAP_2025.md` - 2025-2026年全体ロードマップ

### 3. 分析レポート
- `SEARCH_INTERFACE_ANALYSIS.md` - search_interface.py詳細分析（Phase2完了）
- `MAIN_WINDOW_ANALYSIS.md` - main_window.py詳細分析（Phase3必要時作成）

### 4. 安全性・品質ルール
- `.amazonq/rules/refactoring.md` - リファクタリング基本ルール
- `.amazonq/rules/safety.md` - 安全性確保ルール
- `.amazonq/rules/japanese.md` - 日本語対応規則
- `.amazonq/rules/product.md` - プロダクト概要

## 🔧 作業対象ファイル（実際のリファクタリング時）

### Phase3 最優先ターゲット
- `src/gui/main_window.py` - **1,975行, 73メソッド** 追加リファクタリング対象

### Phase2 完了済み
- `src/gui/search_interface.py` - **215行** (85.7%削減完了) ✅

### 参考用既存分離済みファイル
- `src/gui/managers/` - Phase1で作成済みマネージャー群
- `src/gui/controllers/` - Phase1で作成済みコントローラー群
- `src/gui/dialogs/` - Phase1で作成済みダイアログ群

## 📋 セッション開始時のチェックリスト

### 1. 基本状況確認
```
@README.md
@REFACTORING_STATUS.md
@REFACTORING_PLAN_PHASE3.md
```

### 2. 作業対象確認
```
@src/gui/main_window.py
@REFACTORING_PLAN_PHASE3.md
```

### 3. ルール・安全性確認
```
@.amazonq/rules/refactoring.md
@.amazonq/rules/safety.md
```

## 🚨 重要な注意事項

### 必ず確認すべき情報
1. **Phase1成果**: main_window.py 3,605行→1,975行 (45.2%削減完了)
2. **Phase2成果**: search_interface.py 1,504行→215行 (85.7%削減完了)
3. **Phase3目標**: main_window.py 1,975行→800行 (60%削減)
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
├── REFACTORING_PLAN_PHASE2.md         # ✅ 必須（完了）
├── REFACTORING_PLAN_PHASE3.md         # ✅ 必須（現在）
├── REFACTORING_ROADMAP_2025.md        # ✅ 必須
├── SEARCH_INTERFACE_ANALYSIS.md       # ✅ 必須（完了）
├── .amazonq/rules/                    # ✅ 必須
│   ├── refactoring.md
│   ├── safety.md
│   ├── japanese.md
│   └── product.md
├── docs/DocuMind.txt                  # ✅ 必須
└── src/gui/
    ├── search_interface.py            # ✅ Phase2完了 (215行)
    ├── main_window.py                 # 🎯 Phase3最優先ターゲット (1,975行)
    ├── managers/                      # 📚 参考用
    ├── controllers/                   # 📚 参考用
    └── dialogs/                       # 📚 参考用
```

## 🔄 セッション継続コマンド例

```
# Phase3基本コンテキスト読み込み
@README.md @REFACTORING_STATUS.md @REFACTORING_PLAN_PHASE3.md

# Phase3作業対象読み込み  
@src/gui/main_window.py @REFACTORING_PLAN_PHASE3.md

# ルール読み込み
@.amazonq/rules/refactoring.md @.amazonq/rules/safety.md
```

---
**作成日**: 2025-08-28
**更新日**: 2025-08-28 (Phase3準備完了)
**用途**: セッション継続・作業中断時の必須ファイル管理
**重要度**: 🔴 最高 - 作業継続に必須
**現在フェーズ**: Phase3 (main_window.py追加リファクタリング)