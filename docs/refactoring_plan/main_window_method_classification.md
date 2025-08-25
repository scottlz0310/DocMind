# main_window.py メソッド分類（112メソッド）

## 📊 メソッド分類と移動先計画

### 🏗️ UI構築・レイアウト系 (15メソッド) → `managers/layout_manager.py`
```python
__init__                    # メインウィンドウ初期化
_setup_window              # ウィンドウ基本設定
_setup_ui                  # UIレイアウト構築
_create_folder_pane        # フォルダペイン作成
_create_search_pane        # 検索ペイン作成
_create_preview_pane       # プレビューペイン作成
_setup_menu_bar           # メニューバー構築
_setup_status_bar         # ステータスバー構築
_setup_shortcuts          # ショートカット設定
_setup_accessibility      # アクセシビリティ設定
_apply_styling            # スタイル適用
_center_window            # ウィンドウ中央配置
_apply_theme              # テーマ適用
_apply_font_settings      # フォント設定
_toggle_preview_pane      # プレビューペイン表示切替
```

### 🎛️ 進捗・ステータス管理系 (12メソッド) → `managers/progress_manager.py`
```python
show_status_message           # ステータスメッセージ表示
show_progress                # 進捗バー表示
_get_progress_icon_message   # 進捗アイコンメッセージ生成
_get_progress_color_info     # 進捗色情報取得
_create_progress_tooltip     # 進捗ツールチップ作成
hide_progress               # 進捗バー非表示
_actually_hide_progress     # 実際の進捗バー非表示
_get_completion_icon_message # 完了アイコンメッセージ
update_system_info          # システム情報更新
update_progress             # 進捗更新
set_progress_indeterminate  # 不定進捗設定
is_progress_visible         # 進捗バー表示状態確認
get_progress_value          # 進捗値取得
set_progress_style          # 進捗バースタイル設定
```

### 🔗 シグナル・イベント管理系 (20メソッド) → `managers/signal_manager.py`
```python
_connect_all_signals           # 全シグナル接続
_connect_folder_tree_signals   # フォルダツリーシグナル接続
_connect_search_results_signals # 検索結果シグナル接続
_connect_rebuild_signals       # 再構築シグナル接続
_connect_thread_manager_signals # スレッドマネージャーシグナル接続
_connect_timeout_manager_signals # タイムアウトマネージャーシグナル接続
_on_folder_selected           # フォルダ選択イベント
_on_folder_indexed            # フォルダインデックス完了イベント
_on_folder_excluded           # フォルダ除外イベント
_on_folder_refresh            # フォルダリフレッシュイベント
_on_search_requested          # 検索要求イベント
_on_search_cancelled          # 検索キャンセルイベント
_on_search_completed          # 検索完了イベント
_on_search_error              # 検索エラーイベント
_on_search_text_changed       # 検索テキスト変更イベント
_on_search_result_selected    # 検索結果選択イベント
_on_preview_requested         # プレビュー要求イベント
_on_page_changed              # ページ変更イベント
_on_sort_changed              # ソート変更イベント
_on_filter_changed            # フィルター変更イベント
_on_preview_zoom_changed      # プレビューズーム変更イベント
_on_preview_format_changed    # プレビューフォーマット変更イベント
```

### 🔄 インデックス・スレッド管理系 (25メソッド) → `controllers/index_controller.py`
```python
_initialize_search_components  # 検索コンポーネント初期化
_rebuild_index                # インデックス再構築
_clear_index                  # インデックスクリア
_start_indexing_process       # インデックス処理開始
_format_completion_message    # 完了メッセージフォーマット
_cleanup_indexing_thread      # インデックススレッドクリーンアップ
_on_thread_started            # スレッド開始イベント
_on_thread_finished           # スレッド完了イベント
_on_thread_error              # スレッドエラーイベント
_on_thread_progress           # スレッド進捗イベント
_on_manager_status_changed    # マネージャー状態変更イベント
_on_rebuild_progress          # 再構築進捗イベント
_on_rebuild_completed         # 再構築完了イベント
_handle_rebuild_timeout       # 再構築タイムアウト処理
_force_stop_rebuild           # 再構築強制停止
_reset_rebuild_state          # 再構築状態リセット
_on_rebuild_error             # 再構築エラー処理
_analyze_error_type           # エラータイプ分析
_handle_file_access_error     # ファイルアクセスエラー処理
_handle_permission_error      # 権限エラー処理
_handle_resource_error        # リソースエラー処理
_handle_disk_space_error      # ディスク容量エラー処理
_handle_corruption_error      # データ破損エラー処理
_handle_system_error          # システムエラー処理
_cleanup_partial_index        # 部分インデックスクリーンアップ
_perform_error_cleanup        # エラー後クリーンアップ
```

### 💬 ダイアログ・UI操作系 (25メソッド) → `dialogs/dialog_manager.py`
```python
_open_folder_dialog                    # フォルダ選択ダイアログ
_show_search_dialog                    # 検索ダイアログ表示
_show_settings_dialog                  # 設定ダイアログ表示
_show_about_dialog                     # バージョン情報ダイアログ
_show_rebuild_confirmation_dialog      # 再構築確認ダイアログ
_show_folder_not_selected_dialog       # フォルダ未選択ダイアログ
_show_thread_start_error_dialog        # スレッド開始エラーダイアログ
_show_system_error_dialog              # システムエラーダイアログ
_show_improved_timeout_dialog          # 改善タイムアウトダイアログ
_show_clear_index_confirmation_dialog  # インデックスクリア確認ダイアログ
_show_component_unavailable_dialog     # コンポーネント利用不可ダイアログ
_show_operation_failed_dialog          # 操作失敗ダイアログ
_show_partial_failure_dialog           # 部分失敗ダイアログ
_show_timeout_dialog                   # タイムアウトダイアログ
_show_fallback_error_dialog            # フォールバックエラーダイアログ
_get_thread_start_time                 # スレッド開始時刻取得
_update_system_info_after_rebuild      # 再構築後システム情報更新
_update_folder_tree_after_rebuild      # 再構築後フォルダツリー更新
_determine_rebuild_stage               # 再構築段階判定
_format_rebuild_progress_message       # 再構築進捗メッセージフォーマット
_update_rebuild_system_info            # 再構築システム情報更新
_format_detailed_completion_message    # 詳細完了メッセージフォーマット
_update_system_info_with_progress      # 進捗付きシステム情報更新
_format_progress_message               # 進捗メッセージフォーマット
```

### 🧹 クリーンアップ・終了処理系 (15メソッド) → `managers/cleanup_manager.py`
```python
closeEvent                      # ウィンドウクローズイベント
_cleanup_all_components         # 全コンポーネントクリーンアップ
_cleanup_rebuild_components     # 再構築コンポーネントクリーンアップ
_cleanup_ui_components          # UIコンポーネントクリーンアップ
_cleanup_search_components      # 検索コンポーネントクリーンアップ
_disconnect_all_signals         # 全シグナル切断
_disconnect_rebuild_signals     # 再構築シグナル切断
_disconnect_ui_signals          # UIシグナル切断
_on_settings_changed            # 設定変更処理
_clear_preview                  # プレビュークリア
_refresh_view                   # ビューリフレッシュ
```

## 🎯 リファクタリング実行計画

### Phase 1: 基盤整備（1週間）
1. 新しいディレクトリ構造作成
2. 基底クラス・インターフェース定義
3. 既存テストの実行確認

### Phase 2: 段階的分離（2-3週間）
1. **ダイアログ系** → 最も独立性が高い
2. **進捗管理系** → UI更新ロジック
3. **クリーンアップ系** → 終了処理
4. **シグナル管理系** → イベント処理
5. **インデックス制御系** → ビジネスロジック
6. **UI構築系** → レイアウト管理

### Phase 3: 統合・テスト（1週間）
1. 分離されたコンポーネントの統合
2. 全機能テスト
3. パフォーマンステスト
4. ドキュメント更新

## 📈 期待される効果

### 分離後の main_window.py
```python
class MainWindow(QMainWindow):
    """メインウィンドウ - 各マネージャーの統合のみ担当"""
    
    def __init__(self):
        # 各マネージャーの初期化のみ
        self.layout_manager = LayoutManager(self)
        self.progress_manager = ProgressManager(self)
        self.signal_manager = SignalManager(self)
        self.index_controller = IndexController(self)
        self.dialog_manager = DialogManager(self)
        self.cleanup_manager = CleanupManager(self)
    
    # 残るメソッドは10個以下の予定
```

### 改善指標
- **行数**: 3,605行 → 300行以下（90%削減）
- **メソッド数**: 112個 → 10個以下（91%削減）
- **責務**: 6つの明確な責務に分離
- **テスト容易性**: 各コンポーネント単体でテスト可能