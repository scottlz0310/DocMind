#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タスク5: 進捗表示システムの統合 - テストスクリプト

インデックス再構築の進捗表示機能をテストします。
"""

import sys
import os
import tempfile
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from src.gui.main_window import MainWindow
from src.utils.logging_config import setup_logging


def create_test_documents(test_dir: Path, num_files: int = 5) -> None:
    """テスト用ドキュメントを作成"""
    test_dir.mkdir(exist_ok=True)

    # 様々な形式のテストファイルを作成
    for i in range(num_files):
        # テキストファイル
        txt_file = test_dir / f"document_{i}.txt"
        txt_file.write_text(f"これはテストドキュメント {i} です。\n検索テスト用の内容を含んでいます。", encoding='utf-8')

        # Markdownファイル
        md_file = test_dir / f"readme_{i}.md"
        md_file.write_text(f"# テストドキュメント {i}\n\nこれはMarkdownファイルです。", encoding='utf-8')

    print(f"テストドキュメントを作成しました: {test_dir} ({num_files * 2}ファイル)")


def test_progress_display():
    """進捗表示システムのテスト"""
    print("=== タスク5: 進捗表示システムの統合 テスト ===")

    # ログ設定
    setup_logging(level="DEBUG", enable_console=True)

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
            create_test_documents(test_dir, num_files=3)

            print(f"テストディレクトリ: {test_dir}")

            # フォルダツリーにテストディレクトリを追加
            main_window.folder_tree_container.load_folder_structure(str(test_dir))

            # 進捗表示メソッドの動作確認
            print("\n1. 基本的な進捗表示メソッドのテスト")

            # スキャン段階のテスト
            print("   - スキャン段階")
            main_window._on_rebuild_progress("test_thread_1", "ファイルをスキャン中...", 0, 0)
            app.processEvents()
            time.sleep(1)

            # 処理段階のテスト
            print("   - 処理段階")
            for i in range(1, 4):
                message = f"処理中: 📄 document_{i}.txt ({i}/3)"
                main_window._on_rebuild_progress("test_thread_1", message, i, 3)
                app.processEvents()
                time.sleep(0.5)

            # インデックス作成段階のテスト
            print("   - インデックス作成段階")
            main_window._on_rebuild_progress("test_thread_1", "インデックスを作成中...", 3, 3)
            app.processEvents()
            time.sleep(1)

            # 完了段階のテスト
            print("   - 完了段階")
            main_window._on_rebuild_progress("test_thread_1", "インデックス再構築が完了しました", 3, 3)
            app.processEvents()
            time.sleep(1)

            # 進捗バーを非表示
            main_window.hide_progress("テスト完了")

            print("\n2. 段階判定メソッドのテスト")

            # 段階判定のテスト
            test_cases = [
                ("ファイルをスキャン中...", 0, 0, "scanning"),
                ("処理中: document.txt", 1, 3, "processing"),
                ("インデックスを作成中...", 3, 3, "indexing"),
                ("完了", 3, 3, "completed"),
            ]

            for message, current, total, expected_stage in test_cases:
                actual_stage = main_window._determine_rebuild_stage(message, current, total)
                status = "✅" if actual_stage == expected_stage else "❌"
                print(f"   {status} '{message}' -> {actual_stage} (期待値: {expected_stage})")

            print("\n3. メッセージフォーマットのテスト")

            # メッセージフォーマットのテスト
            format_test_cases = [
                ("scanning", "ファイルをスキャン中...", "test_folder", 0, 5),
                ("processing", "処理中: 📄 document.txt", "test_folder", 2, 5),
                ("indexing", "インデックスを作成中...", "test_folder", 5, 5),
                ("completed", "完了", "test_folder", 5, 5),
            ]

            for stage, message, folder, current, total in format_test_cases:
                formatted = main_window._format_rebuild_progress_message(stage, message, folder, current, total)
                print(f"   {stage}: {formatted}")

            print("\n4. システム情報更新のテスト")

            # システム情報更新のテスト
            for stage in ["scanning", "processing", "indexing", "completed"]:
                main_window._update_rebuild_system_info("test_folder", stage, 3, 5)
                app.processEvents()
                time.sleep(0.3)

            print("\n✅ すべてのテストが完了しました")
            print("\nメインウィンドウが表示されています。")
            print("実際のインデックス再構築をテストするには、メニューから「検索 > インデックス再構築」を選択してください。")
            print("ウィンドウを閉じるとテストが終了します。")

            # メインウィンドウを表示してユーザーの操作を待つ
            return app.exec()

    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_progress_display()
    sys.exit(exit_code)
