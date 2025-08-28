# DocMind リファクタリング継続用コンテキストファイル一覧

## 🎯 必須コンテキストファイル（セッション継続時に必ず読み込み）

### 1. プロジェクト基本情報
- `README.md` - プロジェクト概要・基本仕様
- `docs/DocuMind.txt` - 元の要件定義・仕様書

### 2. リファクタリング計画・進捗管理
- `REFACTORING_STATUS.md` - **最重要** Phase1完了状況・全体進捗
- `REFACTORING_PLAN_PHASE2.md` - Phase2詳細計画・戦略
- `REFACTORING_ROADMAP_2025.md` - 2025-2026年全体ロードマップ

### 3. 分析レポート
- `SEARCH_INTERFACE_ANALYSIS.md` - search_interface.py詳細分析（Phase2最優先ターゲット）

### 4. 安全性・品質ルール
- `.amazonq/rules/refactoring.md` - リファクタリング基本ルール
- `.amazonq/rules/safety.md` - 安全性確保ルール
- `.amazonq/rules/japanese.md` - 日本語対応規則
- `.amazonq/rules/product.md` - プロダクト概要

## 🔧 作業対象ファイル（実際のリファクタリング時）

### Phase2 最優先ターゲット
- `src/gui/search_interface.py` - **1,504行, 79メソッド** 最重要分離対象
- `src/gui/main_window.py` - **1,974行, 73メソッド** 追加リファクタリング対象

### 参考用既存分離済みファイル
- `src/gui/managers/` - Phase1で作成済みマネージャー群
- `src/gui/controllers/` - Phase1で作成済みコントローラー群
- `src/gui/dialogs/` - Phase1で作成済みダイアログ群

## 📋 セッション開始時のチェックリスト

### 1. 基本状況確認
```
@README.md
@REFACTORING_STATUS.md
@REFACTORING_PLAN_PHASE2.md
```

### 2. 作業対象確認
```
@src/gui/search_interface.py
@SEARCH_INTERFACE_ANALYSIS.md
```

### 3. ルール・安全性確認
```
@.amazonq/rules/refactoring.md
@.amazonq/rules/safety.md
```

## 🚨 重要な注意事項

### 必ず確認すべき情報
1. **Phase1成果**: main_window.py 3,605行→1,974行 (45.2%削減完了)
2. **Phase2目標**: search_interface.py 1,504行→150行 (90%削減)
3. **現在日付**: 2025-08-28以降の正確な日付を使用
4. **安全性原則**: 段階的分離、即座の検証、ロールバック準備

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
├── REFACTORING_PLAN_PHASE2.md         # ✅ 必須
├── REFACTORING_ROADMAP_2025.md        # ✅ 必須
├── SEARCH_INTERFACE_ANALYSIS.md       # ✅ 必須
├── .amazonq/rules/                    # ✅ 必須
│   ├── refactoring.md
│   ├── safety.md
│   ├── japanese.md
│   └── product.md
├── docs/DocuMind.txt                  # ✅ 必須
└── src/gui/
    ├── search_interface.py            # 🎯 Phase2最優先ターゲット
    ├── main_window.py                 # 🎯 Phase2追加ターゲット
    ├── managers/                      # 📚 参考用
    ├── controllers/                   # 📚 参考用
    └── dialogs/                       # 📚 参考用
```

## 🔄 セッション継続コマンド例

```
# 基本コンテキスト読み込み
@README.md @REFACTORING_STATUS.md @REFACTORING_PLAN_PHASE2.md

# 作業対象読み込み  
@src/gui/search_interface.py @SEARCH_INTERFACE_ANALYSIS.md

# ルール読み込み
@.amazonq/rules/refactoring.md @.amazonq/rules/safety.md
```

---
**作成日**: 2025-08-28
**用途**: セッション継続・作業中断時の必須ファイル管理
**重要度**: 🔴 最高 - 作業継続に必須