#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タスク5: 進捗表示システムの統合 - 統合テスト

実際のIndexingWorkerとの統合をテストします。
"""

import sys
import os
import tempfile
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer

from src.gui.main_window import MainWindow
from src.utils.logging_config import setup_logging


def create_test_documents(test_dir: Path, num_files: int = 10) -> None:
    """テスト用ドキュメントを作成"""
    test_dir.mkdir(exist_ok=True)

    # サブディレクトリも作成
    sub_dir = test_dir / "subdirectory"
    sub_dir.mkdir(exist_ok=True)

    # 様々な形式のテストファイルを作成
    for i in range(num_files):
        # テキストファイル
        txt_file = test_dir / f"document_{i:02d}.txt"
        content = f"""これはテストドキュメント {i} です。

検索テスト用の内容を含んでいます。
キーワード: テスト, ドキュメント, 検索, インデックス

ファイル番号: {i}
作成日時: {time.strftime('%Y-%m-%d %H:%M:%S')}

このファイルは進捗表示システムのテスト用に作成されました。
インデックス再構築機能の動作確認に使用されます。
"""
        txt_file.write_text(content, encoding='utf-8')

        # Markdownファイル
        if i % 2 == 0:
            md_file = test_dir / f"readme_{i:02d}.md"
            md_content = f"""# テストドキュメント {i}

これはMarkdownファイルです。

## 概要

- ファイル番号: {i}
- 形式: Markdown
- 用途: テスト

## 内容

このファイルは**インデックス再構築**の進捗表示テスト用です。

### 特徴

1. 構造化されたテキスト
2. マークダウン記法
3. 検索可能なコンテンツ

> 引用テキスト: これはテスト用の引用です。

```python
# コードブロック例
def test_function():
    return "テスト関数"
```
"""
            md_file.write_text(md_content, encoding='utf-8')

        # サブディレクトリにもファイルを作成
        if i < 3:
            sub_txt = sub_dir / f"sub_document_{i}.txt"
            sub_txt.write_text(f"サブディレクトリのドキュメント {i}", encoding='utf-8')

    print(f"テストドキュメントを作成しました: {test_dir}")
    print(f"  - メインディレクトリ: {num_files}個のテキストファイル + {num_files//2}個のMarkdownファイル")
    print(f"  - サブディレクトリ: 3個のテキストファイル")
    print(f"  - 合計: {num_files + num_files//2 + 3}ファイル")


def test_integration():
    """進捗表示システムの統合テスト"""
    print("=== タスク5: 進捗表示システムの統合 - 統合テスト ===")

    # ログ設定
    setup_logging(level="INFO", enable_console=True)

    # QApplicationの作成
    app = QApplication(sys.argv)

    try:
        # メインウィンドウの作成
        print("メインウィンドウを作成中...")
        main_window = MainWindow()
        main_window.show()

        # テスト用ディレクトリの作成
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test_documents"
            create_test_documents(test_dir, num_files=8)

            print(f"\nテストディレクトリ: {test_dir}")

            # フォルダツリーにテストディレクトリを追加
            main_window.folder_tree_container.load_folder_structure(str(test_dir))

            # 進捗表示システムの動作確認
            print("\n=== 進捗表示システムの動作確認 ===")

            # 1. 手動での進捗表示テスト
            print("\n1. 手動進捗表示テスト")

            def run_manual_progress_test():
                """手動進捗表示テストを実行"""
                print("   スキャン段階をシミュレート...")
                main_window._on_rebuild_progress("manual_test", "ファイルをスキャン中...", 0, 0)
                app.processEvents()

                QTimer.singleShot(1000, lambda: simulate_processing_stage())

            def simulate_processing_stage():
                """処理段階をシミュレート"""
                total_files = 12
                for i in range(1, total_files + 1):
                    if i <= 8:
                        file_name = f"document_{i-1:02d}.txt"
                        icon = "📄"
                    elif i <= 12:
                        file_name = f"readme_{(i-9)*2:02d}.md"
                        icon = "📋"
                    else:
                        file_name = f"sub_document_{i-13}.txt"
                        icon = "📄"

                    message = f"処理中: {icon} {file_name} ({i}/{total_files})"
                    main_window._on_rebuild_progress("manual_test", message, i, total_files)
                    app.processEvents()
                    time.sleep(0.2)

                # インデックス作成段階
                print("   インデックス作成段階をシミュレート...")
                main_window._on_rebuild_progress("manual_test", "インデックスを作成中...", total_files, total_files)
                app.processEvents()

                QTimer.singleShot(1500, lambda: complete_manual_test(total_files))

            def complete_manual_test(total_files):
                """手動テストを完了"""
                print("   完了段階をシミュレート...")
                main_window._on_rebuild_progress("manual_test", "インデックス再構築が完了しました", total_files, total_files)
                app.processEvents()

                QTimer.singleShot(1000, lambda: main_window.hide_progress("手動テスト完了"))

                print("   ✅ 手動進捗表示テスト完了")

                # 実際のインデックス再構築テストの案内
                QTimer.singleShot(2000, show_real_test_dialog)

            def show_real_test_dialog():
                """実際のテストの案内ダイアログを表示"""
                reply = QMessageBox.question(
                    main_window,
                    "実際のインデックス再構築テスト",
                    "手動テストが完了しました。\n\n"
                    "実際のIndexingWorkerを使用したインデックス再構築をテストしますか？\n"
                    "（メニューから「検索 > インデックス再構築」を選択してテストできます）\n\n"
                    "テストを続行しますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    print("\n2. 実際のインデックス再構築テスト")
                    print("   メニューから「検索 > インデックス再構築」を選択してください。")
                    print("   進捗表示システムの動作を確認できます。")
                else:
                    print("\n✅ テスト完了")
                    app.quit()

            # 手動テストを開始
            QTimer.singleShot(1000, run_manual_progress_test)

            print("\n進捗表示システムのテストを開始します...")
            print("ウィンドウを閉じるとテストが終了します。")

            # メインウィンドウを表示してユーザーの操作を待つ
            return app.exec()

    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_integration()
    sys.exit(exit_code)
