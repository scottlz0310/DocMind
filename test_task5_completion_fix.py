#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タスク5: 進捗表示システムの統合 - 完了処理修正テスト

インデックス再構築の完了処理が正しく動作することをテストします。
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


def create_test_documents(test_dir: Path, num_files: int = 5) -> None:
    """テスト用ドキュメントを作成"""
    test_dir.mkdir(exist_ok=True)

    # 様々な形式のテストファイルを作成
    for i in range(num_files):
        # テキストファイル
        txt_file = test_dir / f"document_{i:02d}.txt"
        content = f"""これはテストドキュメント {i} です。

検索テスト用の内容を含んでいます。
キーワード: テスト, ドキュメント, 検索, インデックス

ファイル番号: {i}
作成日時: {time.strftime('%Y-%m-%d %H:%M:%S')}

このファイルは進捗表示システムの完了処理テスト用に作成されました。
"""
        txt_file.write_text(content, encoding='utf-8')

        # Markdownファイル
        if i % 2 == 0:
            md_file = test_dir / f"readme_{i:02d}.md"
            md_content = f"""# テストドキュメント {i}

これはMarkdownファイルです。

## 完了処理テスト

- ファイル番号: {i}
- 形式: Markdown
- 用途: 完了処理テスト

### 内容

このファイルは**インデックス再構築**の完了処理テスト用です。
"""
            md_file.write_text(md_content, encoding='utf-8')

    print(f"テストドキュメントを作成しました: {test_dir} ({num_files + num_files//2}ファイル)")


def test_completion_handling():
    """完了処理のテスト"""
    print("=== タスク5: 進捗表示システムの統合 - 完了処理テスト ===")

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
            create_test_documents(test_dir, num_files=5)

            print(f"\nテストディレクトリ: {test_dir}")

            # フォルダツリーにテストディレクトリを追加
            main_window.folder_tree_container.load_folder_structure(str(test_dir))

            print("\n=== 完了処理シミュレーションテスト ===")

            def run_completion_test():
                """完了処理テストを実行"""
                print("\n1. 進捗シミュレーション開始")

                # スキャン段階
                main_window._on_rebuild_progress("completion_test", "ファイルをスキャン中...", 0, 0)
                app.processEvents()

                QTimer.singleShot(1000, simulate_processing)

            def simulate_processing():
                """処理段階をシミュレート"""
                print("2. ファイル処理段階")
                total_files = 7  # 5個のtxtファイル + 3個のmdファイル

                for i in range(1, total_files + 1):
                    if i <= 5:
                        file_name = f"document_{i-1:02d}.txt"
                        icon = "📄"
                    else:
                        file_name = f"readme_{(i-6)*2:02d}.md"
                        icon = "📋"

                    message = f"処理中: {icon} {file_name} ({i}/{total_files})"
                    main_window._on_rebuild_progress("completion_test", message, i, total_files)
                    app.processEvents()
                    time.sleep(0.3)

                # 処理完了時の特別な処理をテスト
                print("3. 処理完了 - インデックス作成段階へ移行")
                QTimer.singleShot(500, simulate_indexing)

            def simulate_indexing():
                """インデックス作成段階をシミュレート"""
                print("4. インデックス作成段階")
                main_window._on_rebuild_progress("completion_test", "インデックスを作成中...", 7, 7)
                app.processEvents()

                QTimer.singleShot(1500, simulate_completion)

            def simulate_completion():
                """完了段階をシミュレート"""
                print("5. 完了段階")

                # 完了進捗を送信
                main_window._on_rebuild_progress("completion_test", "インデックス再構築が完了しました", 7, 7)
                app.processEvents()

                # 少し待ってから完了処理を実行
                QTimer.singleShot(1000, simulate_thread_finished)

            def simulate_thread_finished():
                """スレッド完了処理をシミュレート"""
                print("6. スレッド完了処理")

                # 統計情報を作成
                statistics = {
                    'folder_path': str(test_dir),
                    'total_files_found': 7,
                    'files_processed': 7,
                    'files_failed': 0,
                    'documents_added': 7,
                    'processing_time': 3.5,
                    'errors': []
                }

                # スレッド完了処理を実行
                main_window._on_thread_finished("completion_test", statistics)
                app.processEvents()

                print("7. 完了処理テスト終了")

                QTimer.singleShot(2000, show_test_results)

            def show_test_results():
                """テスト結果を表示"""
                print("\n=== テスト結果 ===")
                print("✅ 進捗表示システムの完了処理テストが完了しました")
                print("\n確認項目:")
                print("- スキャン段階の表示")
                print("- ファイル処理段階の進捗表示")
                print("- 処理完了時のインデックス作成段階への移行")
                print("- インデックス作成段階の表示")
                print("- 完了段階の表示")
                print("- スレッド完了処理")
                print("- 進捗バーの非表示")
                print("- システム情報の更新")

                # 実際のテストの案内
                reply = QMessageBox.question(
                    main_window,
                    "実際のインデックス再構築テスト",
                    "シミュレーションテストが完了しました。\n\n"
                    "実際のIndexingWorkerを使用したインデックス再構築をテストしますか？\n"
                    "（メニューから「検索 > インデックス再構築」を選択してテストできます）\n\n"
                    "テストを続行しますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    print("\n実際のインデックス再構築テスト:")
                    print("メニューから「検索 > インデックス再構築」を選択してください。")
                    print("完了処理が正しく動作することを確認できます。")
                else:
                    print("\nテスト完了")
                    app.quit()

            # テストを開始
            QTimer.singleShot(1000, run_completion_test)

            print("\n完了処理テストを開始します...")
            print("ウィンドウを閉じるとテストが終了します。")

            # メインウィンドウを表示してユーザーの操作を待つ
            return app.exec()

    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_completion_handling()
    sys.exit(exit_code)
