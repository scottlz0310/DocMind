`methods_map.md` は、巨大化した **main_window.py** を含む DocMind プロジェクトで、将来的に IDE 統合 AI(GPT-5、Claude Sonnet、Cursor など)に対して効率的にリファクタリング指示を出すための基礎資料になります。

以下は **methods_map.md** のテンプレート案です。
このテンプレートでは、**メソッドの概要・責務・依存関係・優先度**を整理し、AI に指示を出す際のベース情報として使えるようにしています。

---

# `methods_map.md`

## 目的

このドキュメントは、`src/gui/main_window.py` を中心とした **DocMind** の GUI 実装におけるメソッドの一覧・依存関係・責務を可視化するためのものです。
IDE統合AIやGPT-5などのモデルに対して、**リファクタリング方針を効率よく伝えるための基礎資料**として使用します。

---

## 1. メソッドマップ

| メソッド名                    | 概要                             | 所属クラス        | 依存モジュール                                    | 呼び出し元                | 呼び出し先                    | UI依存 | 優先度 |
| ------------------------ | ------------------------------ | ------------ | ------------------------------------------ | -------------------- | ------------------------ | ---- | --- |
| `__init__`               | メインウィンドウの初期化。メニュー、ツールバー、パネルを構築 | `MainWindow` | `PySide6`, `folder_tree`, `search_results` | `main.py`            | 全体                       | ✅    | 高   |
| `setup_ui`               | UI構造の初期設定                      | `MainWindow` | `PySide6`                                  | `__init__`           | -                        | ✅    | 高   |
| `on_folder_selected`     | サイドバーのフォルダツリーで選択されたフォルダをロード    | `MainWindow` | `folder_tree`, `document_processor`        | GUIイベント              | `load_documents`         | ✅    | 高   |
| `load_documents`         | ドキュメントをインデックスから取得しサムネイルに表示     | `MainWindow` | `index_manager`, `embedding_manager`       | `on_folder_selected` | `update_thumbnail_panel` | ✅    | 高   |
| `search_documents`       | クエリに基づき全文検索を実行                 | `MainWindow` | `search_manager`, `database`               | GUIイベント              | `update_search_results`  | ✅    | 高   |
| `update_thumbnail_panel` | サムネイルパネルを再描画                   | `MainWindow` | `thumbnail_panel`                          | `load_documents`     | -                        | ✅    | 中   |
| `update_preview_panel`   | プレビュー領域にドキュメント内容を表示            | `MainWindow` | `preview_widget`                           | GUIイベント              | -                        | ✅    | 中   |
| `export_index`           | 検索インデックスをエクスポート                | `MainWindow` | `index_manager`                            | メニューイベント             | `index_manager.export`   | ❌    | 低   |
| `show_about_dialog`      | バージョン情報などのポップアップを表示            | `MainWindow` | `PySide6`                                  | GUIイベント              | -                        | ✅    | 低   |

> **優先度の基準**

* **高**: 大規模リファクタリング候補。依存が複雑で、UI・検索・インデックス処理と直結。
* **中**: 補助的なUI更新ロジック。
* **低**: 単機能、分離しやすい。

---

## 2. メソッドの分類方針

### 2.1. GUIイベントハンドラ

* クリック、選択、ショートカット操作などで呼ばれる
* `on_` または `handle_` で始まることが多い
* 例: `on_folder_selected`, `on_search_triggered`

### 2.2. ビジネスロジック呼び出し

* コア処理 (`search_manager`, `index_manager` 等) を呼び出すラッパー
* 例: `load_documents`, `search_documents`

### 2.3. UI更新系

* パネル更新、レイアウト調整、ダイアログ表示
* 例: `update_thumbnail_panel`, `update_preview_panel`

### 2.4. ユーティリティ

* 設定ロード、ログ出力、エクスポート処理など
* 例: `export_index`, `show_about_dialog`

---

## 3. 作業手順

### 3.1. メソッド一覧抽出

```bash
grep -E "def " src/gui/main_window.py > methods_list.txt
```

### 3.2. 呼び出し関係を解析

```bash
grep -R "on_folder_selected" src/gui/ | grep -v "def"
```

→ イベントの発火元を特定し、マップに追記。

### 3.3. methods_map.md を更新

* 新規メソッドを追加
* 廃止メソッドを削除
* 優先度を定期的に見直す

---

## 4. AIへの指示例

```markdown
# AIへの依頼例

## タスク
- `src/gui/main_window.py` のメソッドのうち、**優先度: 高**のものを中心に `MainWindowController` クラスへ分離
- GUIイベントハンドラとビジネスロジックを明確に分離する

## 制約
- 既存の `search_manager` / `index_manager` / `folder_tree` との依存関係を維持
- メソッド名は原則として変更しない

## 対象メソッド
- `setup_ui`
- `on_folder_selected`
- `load_documents`
- `search_documents`
```

---

## 5. 今後の改善案

* **呼び出し関係図の自動生成**
  → `pydeps` などを使い、main_window.py だけでなく `src/gui/` 全体の依存関係を可視化
* **イベントマップの追加**
  → Qtシグナル・スロットを視覚化するとAIがリファクタリングしやすい
* **ドキュメント自動同期**
  → `methods_map.md` をCIで自動生成し、差分をPull Requestに添付

---

このテンプレートをベースに `methods_map.md` を作成しておけば、
将来 GPT-5 や Claude Sonnet に「main_window.py を分割して」と依頼する際に、**文脈を大量に貼り付けなくても済む**ようになります。

---
