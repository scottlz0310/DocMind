以下は **DocMind専用 `methods_map.md` テンプレート（初期分類済み）** です。

---

# `methods_map.md` (DocMind専用)

## 目的

このドキュメントは、`src/gui/main_window.py` のメソッド群を整理し、**リファクタリング方針をAIに効率的に伝えるための基礎資料**です。
まずはメソッドをカテゴリ別に分類し、依存関係・責務・優先度を可視化します。

---

## 1. メソッドカテゴリマップ

### 1.1 **初期化・UI構築系**（優先度: 高）

| メソッド名                  | 役割                | 主な依存             | 呼び出し元                  | 呼び出し先            |
| ---------------------- | ----------------- | ---------------- | ---------------------- | ---------------- |
| `__init__`             | メインウィンドウの初期化      | PySide6          | `main.py`              | ほぼ全体             |
| `_setup_window`        | ウィンドウ全体のレイアウト設定   | PySide6          | `__init__`             | -                |
| `_setup_ui`            | UI要素（パネル・ボタン等）の配置 | PySide6          | `__init__`             | `_create_*`      |
| `_create_folder_pane`  | フォルダペイン生成         | `folder_tree`    | `_setup_ui`            | -                |
| `_create_search_pane`  | 検索ペイン生成           | `search_results` | `_setup_ui`            | -                |
| `_create_preview_pane` | プレビューペイン生成        | `preview_widget` | `_setup_ui`            | -                |
| `_setup_menu_bar`      | メニューバー構築          | PySide6          | `_setup_ui`            | -                |
| `_setup_status_bar`    | ステータスバー構築         | PySide6          | `_setup_ui`            | -                |
| `_setup_shortcuts`     | キーボードショートカット設定    | PySide6          | `_setup_ui`            | -                |
| `_apply_styling`       | UIテーマ・CSS適用       | PySide6          | `_setup_ui`            | -                |
| `_apply_theme`         | ダーク/ライトテーマ切替      | Config           | `_on_settings_changed` | `_apply_styling` |

---

### 1.2 **イベントハンドラ系**（優先度: 高）

| メソッド名                        | イベント種別     | 主な依存                           | 呼び出し先                       | 備考    |
| ---------------------------- | ---------- | ------------------------------ | --------------------------- | ----- |
| `_on_folder_selected`        | フォルダ選択     | `folder_tree`, `index_manager` | `_start_indexing_process`   | GUI依存 |
| `_on_folder_indexed`         | インデックス作成完了 | `index_manager`                | `_refresh_view`             | -     |
| `_on_search_requested`       | 検索ボタン押下    | `search_manager`               | `_on_search_completed`      | -     |
| `_on_search_completed`       | 検索完了       | `search_results`               | `_update_preview_panel`     | -     |
| `_on_search_error`           | 検索失敗       | `logging`, `QMessageBox`       | `_show_system_error_dialog` | -     |
| `_on_search_result_selected` | 検索結果選択     | `search_results`               | `_on_preview_requested`     | GUI依存 |
| `_on_preview_requested`      | プレビュー要求    | `preview_widget`               | `_update_preview_panel`     | -     |
| `_on_page_changed`           | ページ切替      | `preview_widget`               | -                           | -     |
| `_on_sort_changed`           | ソート変更      | `search_results`               | `_refresh_view`             | -     |
| `_on_filter_changed`         | フィルタ変更     | `search_results`               | `_refresh_view`             | -     |

---

### 1.3 **検索・インデックス管理系**（優先度: 高）

| メソッド名                     | 役割             | 主な依存             | 呼び出し元                               | 呼び出し先                     |
| ------------------------- | -------------- | ---------------- | ----------------------------------- | ------------------------- |
| `_rebuild_index`          | インデックス再構築      | `index_manager`  | メニュー                                | `_start_indexing_process` |
| `_clear_index`            | インデックス削除       | `index_manager`  | メニュー                                | `_refresh_view`           |
| `_start_indexing_process` | インデックス作成スレッド開始 | `thread_manager` | `_on_folder_selected`               | `_on_thread_progress`     |
| `_on_thread_progress`     | スレッド進捗更新       | `thread_manager` | `_update_system_info_with_progress` | GUI依存                     |
| `_on_thread_finished`     | スレッド完了時処理      | `thread_manager` | `_cleanup_indexing_thread`          | GUI依存                     |
| `_on_thread_error`        | インデックス作成失敗     | `thread_manager` | `_show_system_error_dialog`         | GUI依存                     |

---

### 1.4 **プレビュー・検索結果UI更新系**（優先度: 中）

| メソッド名                   | 役割           | 主な依存             | 呼び出し元                   |
| ----------------------- | ------------ | ---------------- | ----------------------- |
| `_update_preview_panel` | プレビュー更新      | `preview_widget` | `_on_preview_requested` |
| `_toggle_preview_pane`  | プレビューペイン表示切替 | `preview_widget` | GUIイベント                 |
| `_clear_preview`        | プレビュー領域初期化   | `preview_widget` | `_refresh_view`         |
| `_refresh_view`         | 検索結果パネル更新    | `search_results` | 多数                      |

---

### 1.5 **エラーハンドリング系**（優先度: 高）

| メソッド名                       | 種別         | 呼び出し元            | 備考          |
| --------------------------- | ---------- | ---------------- | ----------- |
| `_handle_file_access_error` | ファイルアクセス不可 | `thread_manager` | ディスク容量不足など  |
| `_handle_permission_error`  | 権限不足       | `thread_manager` | -           |
| `_handle_disk_space_error`  | 空き容量不足     | `thread_manager` | -           |
| `_handle_corruption_error`  | データ破損      | `thread_manager` | -           |
| `_show_system_error_dialog` | 汎用システムエラー  | GUIイベント          | QMessageBox |

---

### 1.6 **ダイアログ・UI補助系**（優先度: 低）

| メソッド名                                   | 役割         | 呼び出し元          |
| --------------------------------------- | ---------- | -------------- |
| `_show_about_dialog`                    | アプリ情報ダイアログ | メニュー           |
| `_show_search_dialog`                   | 検索ダイアログ    | メニュー           |
| `_show_settings_dialog`                 | 設定画面表示     | メニュー           |
| `_show_clear_index_confirmation_dialog` | インデックス削除確認 | `_clear_index` |
| `_show_operation_failed_dialog`         | 操作失敗通知     | 多数             |

---

## 2. 優先度別リファクタリング方針

* **優先度: 高**

  * 初期化・UI構築・検索・インデックス・イベントハンドラ
  * → **Controllerクラス**に分離
* **優先度: 中**

  * プレビューや検索結果更新処理
  * → **PreviewController**や**SearchResultController**などに切り出し
* **優先度: 低**

  * ダイアログ表示系
  * → **DialogsHelper**モジュール化

---

## 次のステップ案

1. **メソッド呼び出し関係を自動抽出**

   ```bash
   grep -R "_on_folder_selected" src/gui/ | grep -v "def"
   ```

   → イベント発火元を特定してマップに追記

2. **methods_map.md を更新**

   * 優先度と依存関係を精緻化
   * Thread・Search・Previewを中心に整理

3. **AIにリファクタリング指示を出す**

   * 例: 「優先度: 高 のメソッドを `MainWindowController` に移動し、UIロジックと分離して」

---
