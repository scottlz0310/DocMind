#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タスク8: 実際の進捗表示機能のテスト

このスクリプトは、改善された進捗表示機能をテストします。
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.core.document_processor import DocumentProcessor
from src.core.index_manager import IndexManager
from src.core.thread_manager import IndexingThreadManager
from src.gui.main_window import MainWindow
from src.utils.config import Config


def create_test_files(test_dir: Path) -> None:
    """テスト用ファイルを作成"""
    print(f"テストファイルを作成中: {test_dir}")

    # テキストファイル
    (test_dir / "document1.txt").write_text("これは最初のテストドキュメントです。", encoding='utf-8')
    (test_dir / "document2.txt").write_text("これは2番目のテストドキュメントです。", encoding='utf-8')
    (test_dir / "document3.txt").write_text("これは3番目のテストドキュメントです。", encoding='utf-8')

    # Markdownファイル
    (test_dir / "readme.md").write_text("""# テストドキュメント

これはMarkdownのテストファイルです。

## セクション1
内容1

## セクション2
内容2
""", encoding='utf-8')

    # サブディレクトリ
    sub_dir = test_dir / "subdirectory"
    sub_dir.mkdir()
    (sub_dir / "sub_document1.txt").write_text("サブディレクトリのドキュメント1", encoding='utf-8')
    (sub_dir / "sub_document2.txt").write_text("サブディレクトリのドキュメント2", encoding='utf-8')

    print(f"テストファイル作成完了: {len(list(test_dir.rglob('*.txt'))) + len(list(test_dir.rglob('*.md')))}個")


def test_progress_display():
    """進捗表示機能のテスト"""
    print("=== タスク8: 実際の進捗表示機能のテスト ===")

    # QApplicationを作成
    app = QApplication(sys.argv)

    try:
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test_documents"
            test_dir.mkdir()

            # テストファイルを作成
            create_test_files(test_dir)

            # MainWindowを作成
            print("MainWindowを初期化中...")
            main_window = MainWindow()
            main_window.show()

            # 少し待機してUIが表示されるのを待つ
            QTimer.singleShot(1000, lambda: start_indexing_test(main_window, str(test_dir)))

            # 10秒後にアプリケーションを終了
            QTimer.singleShot(10000, app.quit)

            print("アプリケーションを開始...")
            print("進捗表示をテスト中...")
            print("- 現在処理中のファイル名の表示")
            print("- 処理済み/総ファイル数の進捗率表示")
            print("- 処理段階（スキャン中、処理中、インデックス作成中）の表示")

            # アプリケーションを実行
            app.exec()

    except Exception as e:
        print(f"テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("進捗表示機能のテスト完了")
    return True


def start_indexing_test(main_window: MainWindow, test_dir: str):
    """インデックス処理テストを開始"""
    try:
        print(f"インデックス処理を開始: {test_dir}")

        # フォルダツリーにテストディレクトリを追加
        main_window.folder_tree_container.load_folder_structure(test_dir)

        # 少し待機してからインデックス処理を開始
        QTimer.singleShot(500, lambda: trigger_indexing(main_window, test_dir))

    except Exception as e:
        print(f"インデックステスト開始中にエラー: {e}")


def trigger_indexing(main_window: MainWindow, test_dir: str):
    """インデックス処理をトリガー"""
    try:
        print("インデックス処理をトリガー中...")

        # _on_folder_indexedメソッドを直接呼び出してインデックス処理を開始
        main_window._on_folder_indexed(test_dir)

        print("インデックス処理が開始されました")
        print("進捗表示を確認してください:")
        print("1. ステータスバーに現在処理中のファイル名が表示されているか")
        print("2. 進捗バーに正確な進捗率が表示されているか")
        print("3. 処理段階（スキャン→処理→インデックス作成）が明確に表示されているか")

    except Exception as e:
        print(f"インデックス処理トリガー中にエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    success = test_progress_display()
    sys.exit(0 if success else 1)
