# folder_tree.py 完全分析レポート

## 📊 **基本統計情報**

### **ファイル規模**
- **総行数**: 1,408行
- **クラス数**: 5個
- **メソッド数**: 76個
- **インポート数**: 30個

### **リスク評価結果**
- **総合リスクレベル**: 🔴 **HIGH**
- **複雑度リスク**: 🟢 LOW (平均2.8, 最大26)
- **非同期処理リスク**: 🟡 MEDIUM (20コンポーネント)
- **Qt依存関係リスク**: 🔴 HIGH (108依存)
- **シグナル・スロットリスク**: 🔴 HIGH (61使用箇所)

## 🏗️ **クラス構造分析**

### **1. FolderLoadWorker (26-140行)**
**責務**: 非同期フォルダ読み込み処理
**継承**: QObject
**メソッド数**: 4個
**リスク**: 🔴 **極高** (非同期処理の中核)

**主要メソッド**:
- `do_work()` - メイン処理 (複雑度: 3)
- `_load_folder_recursive()` - 再帰読み込み (複雑度: 26) ⚠️ **最高複雑度**
- `stop()` - 処理停止
- シグナル: `folder_loaded`, `load_error`, `finished`

**分離戦略**: 最優先で独立モジュール化

### **2. FolderItemType (141-149行)**
**責務**: フォルダアイテム種類定義
**継承**: Enum
**メソッド数**: 0個
**リスク**: 🟢 **低** (単純な列挙型)

**分離戦略**: 共通定義として独立

### **3. FolderTreeItem (151-245行)**
**責務**: ツリーアイテムの拡張
**継承**: QTreeWidgetItem
**メソッド数**: 4個
**リスク**: 🟡 **中** (UI依存)

**主要メソッド**:
- `set_folder_data()` - データ設定 (複雑度: 2)
- `_update_icon()` - アイコン更新 (複雑度: 7)
- `update_statistics()` - 統計更新 (複雑度: 5)

**分離戦略**: UI管理系に統合

### **4. FolderTreeWidget (246-1206行) ⚠️ **最大クラス**
**責務**: メインツリーウィジェット
**継承**: QTreeWidget
**メソッド数**: 47個 (全体の62%)
**行数**: 960行 (全体の68%)
**リスク**: 🔴 **極高** (巨大・複雑・多責務)

**責務分析**:
1. **非同期処理管理** (8メソッド)
2. **UI設定・管理** (12メソッド)
3. **イベント処理** (15メソッド)
4. **状態管理** (12メソッド)

**分離戦略**: 4つの専門領域に分割

### **5. FolderTreeContainer (1208-1408行)**
**責務**: コンテナウィジェット
**継承**: QWidget
**メソッド数**: 20個
**リスク**: 🟡 **中** (比較的単純)

**分離戦略**: 最後に軽微な調整

## 🔄 **非同期処理分析**

### **非同期コンポーネント (20個)**
- **スレッド関連**: `QThread`, `Worker`, `moveToThread` (7箇所)
- **シグナル**: `started`, `finished` (10箇所)
- **制御メソッド**: `start()`, `quit()`, `terminate()` (3箇所)

### **非同期処理フロー**
```
1. load_folder_structure() 
   ↓
2. _load_subfolders_async()
   ↓
3. FolderLoadWorker作成・スレッド移動
   ↓
4. シグナル接続 (folder_loaded, load_error, finished)
   ↓
5. スレッド開始
   ↓
6. _load_folder_recursive() (バックグラウンド実行)
   ↓
7. 結果シグナル発行
   ↓
8. _on_folder_loaded() / _on_load_error()
   ↓
9. _cleanup_worker()
```

### **非同期処理リスク**
- **複雑なシグナル接続**: Qt.QueuedConnection使用
- **スレッドライフサイクル**: 適切なクリーンアップ必要
- **エラーハンドリング**: 多段階のエラー処理
- **メモリ管理**: deleteLater()による自動削除

## 📡 **シグナル・スロット分析**

### **シグナル定義 (11個)**
- `folder_loaded`, `load_error`, `finished` (Worker)
- `folder_selected`, `folder_indexed`, `folder_excluded`, `refresh_requested` (Widget)
- 重複定義あり (Container)

### **シグナル接続 (33箇所)**
- **UI イベント**: `itemSelectionChanged`, `itemExpanded` 等
- **アクション**: `triggered` (7箇所)
- **ショートカット**: `activated` (3箇所)
- **非同期**: `started`, `finished` 等
- **カスタム**: `folder_selected` 等

### **シグナル発行 (16箇所)**
- **エラー通知**: `load_error` (6箇所)
- **完了通知**: `finished`, `folder_loaded`
- **ユーザーアクション**: `folder_selected`, `folder_indexed` 等

## 🎨 **UI依存関係分析**

### **Qt Widget依存 (108箇所)**
- **ウィジェット**: `QTreeWidget`, `QWidget`, `QVBoxLayout` 等 (30箇所)
- **コア**: `QThread`, `QObject`, `QTimer` (7箇所)
- **シグナル**: `Signal`, `connect`, `emit` (71箇所)

### **UI操作分析**
- **ツリー操作**: `addTopLevelItem`, `currentItem` 等 (10箇所)
- **アイテム操作**: `setExpanded`, `setHidden` (5箇所)
- **スタイリング**: `setStyleSheet`, `setIcon`, `setToolTip` (11箇所)

## 📋 **Phase4分離戦略**

### **Week 1: 非同期処理分離**
**対象**: `FolderLoadWorker` + 関連メソッド
**新構造**:
```
src/gui/folder_tree/
├── loaders/
│   ├── __init__.py
│   ├── folder_load_worker.py      # FolderLoadWorker
│   ├── async_manager.py           # 非同期処理管理
│   └── thread_coordinator.py     # スレッド調整
```

**分離メソッド**:
- `_load_subfolders_async()`
- `_on_folder_loaded()`
- `_on_load_error()`
- `_cleanup_worker()`
- `_on_load_finished()`

### **Week 2: 状態管理分離**
**対象**: 状態管理関連メソッド
**新構造**:
```
src/gui/folder_tree/
├── state/
│   ├── __init__.py
│   ├── folder_state_manager.py    # 統一状態管理
│   ├── index_tracker.py           # インデックス状態
│   └── selection_coordinator.py   # 選択状態
```

**分離メソッド**:
- `set_folder_indexing()`
- `set_folder_indexed()`
- `set_folder_error()`
- `clear_folder_state()`
- `_update_item_types()`
- 状態セット管理 (`indexed_paths`, `excluded_paths` 等)

### **Week 3: UI管理分離**
**対象**: UI構築・管理メソッド
**新構造**:
```
src/gui/folder_tree/
├── ui/
│   ├── __init__.py
│   ├── tree_widget_manager.py     # ツリーウィジェット管理
│   ├── item_factory.py            # アイテム生成
│   └── display_coordinator.py     # 表示調整
```

**分離メソッド**:
- `_setup_tree_widget()`
- `_setup_context_menu()`
- `_setup_shortcuts()`
- `filter_folders()` + フィルタリング関連
- `_update_statistics()`

### **Week 4: イベント処理分離**
**対象**: イベント・インタラクション処理
**新構造**:
```
src/gui/folder_tree/
├── events/
│   ├── __init__.py
│   ├── tree_event_handler.py      # ツリーイベント
│   ├── context_menu_manager.py    # コンテキストメニュー
│   └── signal_coordinator.py      # シグナル調整
```

**分離メソッド**:
- `_on_selection_changed()` 等のイベントハンドラー
- `_show_context_menu()` + コンテキストメニュー関連
- `_add_folder()`, `_remove_folder()` 等のアクション

## ⚠️ **Phase4リスク要因と対策**

### **高リスク要因**
1. **非同期処理の複雑性**
   - **リスク**: スレッド間通信、シグナル接続の複雑さ
   - **対策**: 段階的分離、徹底的なテスト

2. **Qt UI依存関係**
   - **リスク**: 108箇所のQt依存、密結合
   - **対策**: 抽象化レイヤー導入、インターフェース分離

3. **シグナル・スロット接続**
   - **リスク**: 61箇所の複雑な接続関係
   - **対策**: 接続マップ作成、段階的移行

4. **状態管理の複雑性**
   - **リスク**: 複数状態セットの整合性
   - **対策**: 統一状態管理クラス導入

### **対策の優先順位**
1. **最優先**: 非同期処理の安全な分離
2. **高優先**: 状態管理の統一化
3. **中優先**: UI依存関係の抽象化
4. **低優先**: イベント処理の整理

## 📊 **期待成果**

### **分離後の構造**
```
folder_tree.py (1,408行) 
↓
├── folder_tree.py (200行) - 統合管理のみ
├── loaders/ (300行) - 非同期処理
├── state/ (250行) - 状態管理
├── ui/ (400行) - UI管理
└── events/ (258行) - イベント処理
```

### **削減目標**
- **行数削減**: 1,408行 → 200行 (85.8%削減)
- **メソッド削減**: 76個 → 15個以下 (80%削減)
- **責務分離**: 4つの専門領域に分離
- **保守性向上**: 各コンポーネント独立修正可能

### **品質向上**
- **テスト容易性**: 各コンポーネント単体テスト可能
- **可読性**: 責務が明確、理解しやすい
- **拡張性**: 新機能追加時の影響最小化
- **安定性**: エラー影響範囲の限定化

---
**作成日**: 2025-08-28
**分析対象**: src/gui/folder_tree.py (1,408行, 76メソッド)
**分析結果**: 総合リスクHIGH、Phase4実行推奨
**次のアクション**: Week 0 Day 2 テスト環境構築