この計画書では、

* **現状分析**(問題点を定量的に示す)
* **理想構造**(あるべきコードのモジュール分割)
* **AIへの指示方法**(どんな粒度・形式で情報を与えるべきか)
* **作業手順**(AIが迷わないためのステップ化)
* **資料作りの方法論**(grep結果・依存関係・クラスダイアグラムなど)

をまとめることで、IDE統合AIが最小限のヒントで安全にリファクタリングできる状態を作ります。

以下に「DocMindリファクタリング計画書(案)」を示します。

---

## DocMind リファクタリング計画書(案)

### 1. 現状分析

#### 1.1 main_window.pyの問題点

* **行数**：約3500行 → PySide6 GUI・イベントハンドラ・ロジックがすべて集中
* **凝集度の低さ**：UI・データアクセス・検索機能が混在
* **依存関係の複雑化**：`core/`や`data/`への直接アクセス多数
* **テスト困難性**：機能単位での単体テストが困難

#### 1.2 症状

* 修正時の影響範囲が把握しにくい
* 機能追加ごとに複雑性が急増
* レビューコストが高い

---

### 2. 理想構造(再設計方針)

#### 2.1 GUIレイヤー分割

`src/gui`を次のように分割：

```
src/gui/
├── main_window.py        # MainWindowクラスのみ
├── panels/
│   ├── folder_panel.py   # フォルダツリー
│   ├── search_panel.py   # 検索結果表示
│   ├── preview_panel.py  # プレビュー
│   ├── status_panel.py   # ステータスバー
│   └── toolbar_panel.py  # ツールバー
└── dialogs/
    ├── settings_dialog.py
    ├── about_dialog.py
    └── progress_dialog.py
```

#### 2.2 ビジネスロジック整理

* **検索機能** → `src/core/search_manager.py`
* **埋め込み生成** → `src/core/embedding_manager.py`
* **インデックス管理** → `src/core/index_manager.py`
* **文書処理** → `src/core/document_processor.py`
* GUI側からは**マネージャ層のみ参照**させる

#### 2.3 データアクセス統一

* DBアクセス・ファイルIOは`src/data/`配下で一元管理
* GUIから直接SQLiteやストレージに触らない

---

### 3. AIへの指示方法

#### 3.1 指示の原則

* **コンテキストは最小限にする**

  * main_window.py全文ではなく、**grep結果で概要を与える**
  * 例：

    ```bash
    grep -E '^class |^def ' src/gui/main_window.py > methods.txt
    ```
* **依存関係を可視化して渡す**

  * import文だけ抽出

    ```bash
    grep '^import\|^from' src/gui/main_window.py > imports.txt
    ```
* **目的を明確にする**

  * NG: 「main_window.pyを分割してください」
  * OK: 「main_window.pyから検索パネル関連のメソッドを抽出し、search_panel.pyに移動してください。UIイベントハンドラは保持、ビジネスロジックはcore/search_managerを呼び出す形にしてください」

#### 3.2 情報提供の優先度

1. **クラス・メソッド名リスト**(最優先)
2. **import依存関係**
3. **呼び出し元・呼び出し先のマッピング**
4. **実際のコード(必要部分のみ)**

---

### 4. 作業手順(AIにやらせる順番)

| ステップ | 作業内容       | 出力物                    | AIへの指示例                                    |
| ---- | ---------- | ---------------------- | ------------------------------------------ |
| 1    | 機能分類       | methods_map.md        | 「main_window.pyのクラス・メソッド一覧を機能別に分類してください」 |
| 2    | GUIパネル切り出し | `src/gui/panels/*.py`  | 「プレビュー関連のメソッドをpreview_panel.pyへ移動」        |
| 3    | ダイアログ切り出し  | `src/gui/dialogs/*.py` | 「ダイアログ系メソッドを別ファイルへ」                        |
| 4    | ビジネスロジック分離 | `src/core/`            | 「検索・インデックス関連はcore層へ移動」                     |
| 5    | テスト更新      | `tests/`               | 「切り出したメソッドの単体テストを生成」                       |

---

### 5. 資料作りの方法論

AIに渡す資料は、**軽量で要点だけ**にします。
以下のスクリプトで準備できます。

#### 5.1 メソッド一覧抽出

```bash
grep -nE '^class |^    def ' src/gui/main_window.py > docs/main_window_methods.txt
```

#### 5.2 依存関係抽出

```bash
grep -nE '^import |^from ' src/gui/main_window.py > docs/main_window_imports.txt
```

#### 5.3 呼び出し関係マップ(オプション)

```bash
ctags -x --c-kinds=fp src/gui/main_window.py > docs/main_window_ctags.txt
```

#### 5.4 機能別サマリ

* ExcelやMarkdownで、「メソッド名」「役割」「呼び出し元」「移動先ファイル」をまとめると理想的
* 最終的にIDE統合AIに渡すとき、この資料を入力するだけで、全体像を把握してリファクタリングが可能

---

### 6. 次のステップ

1. `main_window.py`のメソッド一覧をgrepで抽出
2. methods.txtを基に機能ごとに分類
3. 上記分類表をAIに渡して、「第1弾」としてGUIパネル切り出しから始める

---

ここまでやれば、将来的にGPT-5やClaude SonnetなどをIDE統合AIとして使ったとき、**一括自動リファクタリング**が非常にやりやすくなります。

---

次のステップとして
**DocMind専用の「methods_map.md」テンプレート**を作り、そこにメソッド名と役割を分類できる表を提案します。
これがあると、grep結果をそのまま貼るだけで、自動的に整理しやすくなります。

やりますか？
この表を先に作っておくと、後でAIへの指示がかなり効率化されます。
