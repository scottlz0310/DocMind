# リファクタリングルール

## 基本方針

### 1. 段階的リファクタリング
- **一度に全てを変更しない**: 機能単位で段階的に分離
- **既存機能保持**: リファクタリング中も全機能が動作することを保証
- **テスト駆動**: 各段階でテストスイートが通ることを確認
- **ロールバック可能**: 問題発生時は即座に前の状態に戻せる

### 2. 責務分離の原則
- **単一責任原則**: 1つのクラスは1つの責務のみ
- **依存関係の最小化**: コンポーネント間の結合度を下げる
- **インターフェース分離**: 必要な機能のみを公開
- **依存性注入**: 具象クラスではなくインターフェースに依存

### 3. コード品質基準
- **メソッド数制限**: 1クラス最大20メソッド
- **行数制限**: 1ファイル最大500行
- **循環参照禁止**: import文の循環参照を避ける
- **命名規則**: 責務が明確になる名前を使用

## Phase1-4完了: 主要GUIコンポーネントリファクタリング成果

### ✅ Phase1-4で完了した分離コンポーネント

#### main_window.py 分離コンポーネント
1. **UI構築系** → `managers/layout_manager.py` (348行)
2. **進捗管理系** → `managers/progress_manager.py` (253行)
3. **シグナル管理系** → `managers/signal_manager.py` (286行)
4. **インデックス制御系** → `controllers/index_controller.py` (760行)
5. **ダイアログ系** → `dialogs/dialog_manager.py` (584行)
6. **クリーンアップ系** → `managers/cleanup_manager.py` (256行)
7. **メニュー管理系** → `managers/menu_manager.py` (188行)
8. **ツールバー管理系** → `managers/toolbar_manager.py` (178行)
9. **ステータス管理系** → `managers/status_manager.py` (265行)
10. **ウィンドウ状態管理系** → `managers/window_state_manager.py` (255行)
11. **スレッド管理系** → `managers/thread_handler_manager.py` (321行)
12. **エラー・リビルド管理系** → `managers/error_rebuild_manager.py` (557行)
13. **設定管理系** → `managers/settings_handler_manager.py` (214行)
14. **検索ハンドラー系** → `managers/search_handler_manager.py` (210行)
15. **進捗システム管理系** → `managers/progress_system_manager.py` (444行)

#### search_interface.py 分離コンポーネント
1. **検索UI管理系** → `search/managers/search_ui_manager.py` (121行)
2. **検索実行系** → `search/controllers/search_controller.py` (142行)
3. **検索レイアウト系** → `search/managers/search_layout_manager.py` (102行)
4. **検索オプション系** → `search/managers/search_options_manager.py` (81行)
5. **検索イベント系** → `search/managers/search_event_manager.py` (96行)
6. **検索API系** → `search/managers/search_api_manager.py` (81行)
7. **ショートカット系** → `search/managers/shortcut_manager.py` (61行)
8. **検索ウィジェット系** → `search/widgets/` (複数ファイル)

#### folder_tree.py 分離コンポーネント
1. **フォルダツリーウィジェット** → `folder_tree/folder_tree_widget.py` (656行)
2. **イベント処理系** → `folder_tree/event_handling/` (複数ファイル)
3. **状態管理系** → `folder_tree/state_management/` (複数ファイル)
4. **UI管理系** → `folder_tree/ui_management/` (複数ファイル)
5. **非同期操作系** → `folder_tree_components/` (複数ファイル)

### 📊 Phase1-4総合成果指標
- **main_window.py**: 3,605行 → 395行 (89.0%削減)
- **search_interface.py**: 1,504行 → 215行 (85.7%削減)
- **folder_tree.py**: 2,000行以上 → 656行 (67%以上削減)
- **メソッド数**: 大幅削減（main_window.py: 112個 → 45個）
- **品質保証**: 全コンポーネント正常動作確認済み
- **アーキテクチャ**: 完全な責務分離・保守性・拡張性確保

## Phase5以降の計画: 残存大型ファイルの最適化

### 🎯 次期優先ターゲット
1. **preview_widget.py** (747行) - プレビュー機能の分離
2. **search_results.py** (756行) - 検索結果表示の分離
3. **settings_dialog.py** (598行) - 設定ダイアログの分離
4. **error_dialog.py** (434行) - エラーダイアログの分離

### Phase5での検証項目
- [ ] プレビュー機能が正常に動作する
- [ ] 検索結果表示が正常動作する
- [ ] 設定機能が正常動作する
- [ ] エラーハンドリングが正常動作する
- [ ] パフォーマンスが劣化していない

## 実装ガイドライン

### 基底クラスの設計
```python
from abc import ABC, abstractmethod
from typing import Protocol

class ManagerProtocol(Protocol):
    """マネージャークラスの共通インターフェース"""
    def initialize(self) -> None: ...
    def cleanup(self) -> None: ...
```

### 依存性注入パターン
```python
class MainWindow(QMainWindow):
    def __init__(self):
        # 各マネージャーを注入
        self.layout_manager = LayoutManager(self)
        self.progress_manager = ProgressManager(self)
        # ...
```

### エラーハンドリング
- 各コンポーネントで適切な例外処理
- ログ出力による問題の追跡可能性
- ユーザーへの分かりやすいエラーメッセージ

## 禁止事項

### やってはいけないこと
- **一括置換**: 大量のコードを一度に移動しない
- **テスト無視**: テストを実行せずに次の段階に進まない
- **機能削除**: リファクタリングで既存機能を削除しない
- **命名変更**: 外部インターフェースの名前を勝手に変更しない

### 危険な操作
- **import文の大幅変更**: 一度に多くのimport文を変更しない
- **シグナル接続の変更**: Qt シグナル・スロットの接続を不用意に変更しない
- **スレッド処理の変更**: マルチスレッド処理の変更は特に慎重に

## 品質チェック

### コードレビューポイント
- [ ] 責務が明確に分離されているか
- [ ] 循環参照が発生していないか
- [ ] 適切な型ヒントが付与されているか
- [ ] ドキュメント文字列が記述されているか
- [ ] エラーハンドリングが適切か

### パフォーマンスチェック
- [ ] 起動時間が劣化していないか
- [ ] メモリ使用量が増加していないか
- [ ] UI応答性が維持されているか
- [ ] 検索性能が劣化していないか

## 緊急時対応

### Phase2用ロールバック手順
```bash
# Phase2問題発生時の緊急ロールバック
git checkout main
git branch -D refactor/search-interface-phase2

# 新しいブランチで再開
git checkout -b refactor/search-interface-phase2-v2
```

### Phase1成果の保護
```bash
# Phase1成果は保護済み（mainブランチにマージ済み）
# Phase2作業はPhase1成果を基盤として実施
git checkout -b refactor/search-interface-phase2
```

### 部分的ロールバック
- 特定のコミットのみを取り消す場合は `git revert` を使用
- 機能単位でのロールバックを可能にするため、コミットは細かく分ける

## 成功指標

### Phase1-4達成済み指標
- ✅ main_window.py: 3,605行 → 395行（89.0%削減）
- ✅ search_interface.py: 1,504行 → 215行（85.7%削減）
- ✅ folder_tree関連: 大幅な責務分離完了
- ✅ メソッド数: 大幅削減（main_window.py: 112個 → 45個）
- ✅ 全機能正常動作確認
- ✅ 品質保証完了（メモリ効率・起動時間・依存関係）
- ✅ 完全な責務分離アーキテクチャ確立

### Phase5目標指標
- preview_widget.py: 747行 → 300行以下（60%削減）
- search_results.py: 756行 → 300行以下（60%削減）
- settings_dialog.py: 598行 → 250行以下（58%削減）
- error_dialog.py: 434行 → 200行以下（54%削減）

### 全体目標（2025-2026年）
- 巨大ファイル完全解消（500行以下）
- テスト実行時間: 30%短縮
- 新機能追加時間: 50%短縮
- コードの可読性・保守性・テスト容易性向上