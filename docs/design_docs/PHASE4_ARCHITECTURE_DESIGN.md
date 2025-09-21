# Phase4 アーキテクチャ設計書

**作成日**: 2025-08-29T12:43:14.260355
**対象**: src/gui/folder_tree.py

## 現在の構造分析

- **総行数**: 1409行
- **クラス数**: 5個
- **メソッド数**: 76個
- **インポート数**: 11個
- **シグナル数**: 11個

## 分離領域設計

### 非同期処理領域

**説明**: フォルダ読み込みワーカーと非同期処理管理
**ディレクトリ**: `src/gui/folder_tree/async/`
**リスクレベル**: HIGH
**移行優先度**: 1

**コンポーネント**:
- **FolderLoadWorker** (`folder_load_worker.py`)
  - 責務: フォルダ構造の非同期読み込み
  - 推定行数: 150行

- **AsyncManager** (`async_manager.py`)
  - 責務: 非同期処理の統合管理
  - 推定行数: 120行

- **ThreadCoordinator** (`thread_coordinator.py`)
  - 責務: スレッド調整とライフサイクル管理
  - 推定行数: 80行

### 状態管理領域

**説明**: フォルダ状態とパス管理
**ディレクトリ**: `src/gui/folder_tree/state/`
**リスクレベル**: MEDIUM
**移行優先度**: 2

**コンポーネント**:
- **FolderStateManager** (`folder_state_manager.py`)
  - 責務: フォルダ状態の統一管理
  - 推定行数: 100行

- **PathTracker** (`path_tracker.py`)
  - 責務: パス集合の管理
  - 推定行数: 80行

- **ItemMapper** (`item_mapper.py`)
  - 責務: パス→アイテムマッピング管理
  - 推定行数: 70行

### UI管理領域

**説明**: ツリーウィジェットとUI表示管理
**ディレクトリ**: `src/gui/folder_tree/ui/`
**リスクレベル**: MEDIUM
**移行優先度**: 3

**コンポーネント**:
- **TreeWidgetManager** (`tree_widget_manager.py`)
  - 責務: QTreeWidgetの基本管理
  - 推定行数: 120行

- **ItemFactory** (`item_factory.py`)
  - 責務: FolderTreeItemの生成・管理
  - 推定行数: 90行

- **DisplayCoordinator** (`display_coordinator.py`)
  - 責務: 表示状態の調整
  - 推定行数: 80行

### イベント処理領域

**説明**: ユーザーイベントとシグナル管理
**ディレクトリ**: `src/gui/folder_tree/events/`
**リスクレベル**: LOW
**移行優先度**: 4

**コンポーネント**:
- **TreeEventHandler** (`tree_event_handler.py`)
  - 責務: ツリーイベントの処理
  - 推定行数: 100行

- **ContextMenuManager** (`context_menu_manager.py`)
  - 責務: コンテキストメニュー管理
  - 推定行数: 150行

- **ShortcutManager** (`shortcut_manager.py`)
  - 責務: キーボードショートカット管理
  - 推定行数: 60行

- **SignalCoordinator** (`signal_coordinator.py`)
  - 責務: シグナル接続の統合管理
  - 推定行数: 80行

## インターフェース設計

### FolderTreeCoreInterface

**ファイル**: `src/gui/folder_tree/interfaces/core_interface.py`
**説明**: フォルダツリーの核となるインターフェース

**メソッド**:
- `load_folder_structure(path: str) -> None`
- `get_selected_folder() -> Optional[str]`
- `set_folder_state(path: str, state: FolderState) -> None`
- `refresh_folder(path: str) -> None`

### AsyncProcessingInterface

**ファイル**: `src/gui/folder_tree/interfaces/async_interface.py`
**説明**: 非同期処理のインターフェース

**メソッド**:
- `start_async_load(path: str) -> None`
- `stop_async_load() -> None`
- `is_loading() -> bool`
- `get_load_progress() -> float`

### StateManagementInterface

**ファイル**: `src/gui/folder_tree/interfaces/state_interface.py`
**説明**: 状態管理のインターフェース

**メソッド**:
- `get_indexed_folders() -> List[str]`
- `get_excluded_folders() -> List[str]`
- `update_folder_status(path: str, status: str) -> None`
- `clear_all_states() -> None`

### UIManagementInterface

**ファイル**: `src/gui/folder_tree/interfaces/ui_interface.py`
**説明**: UI管理のインターフェース

**メソッド**:
- `update_display() -> None`
- `filter_items(filter_text: str) -> None`
- `expand_to_path(path: str) -> None`
- `refresh_ui() -> None`

### EventHandlingInterface

**ファイル**: `src/gui/folder_tree/interfaces/event_interface.py`
**説明**: イベント処理のインターフェース

**メソッド**:
- `handle_selection_change(path: str) -> None`
- `handle_context_menu(position: QPoint) -> None`
- `emit_folder_signal(signal_type: str, path: str) -> None`

