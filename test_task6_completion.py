#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タスク6「完了処理とシステム状態更新の実装」のテスト

このテストは以下の要件を検証します:
- IndexingThreadManagerの完了シグナルを受信する_on_rebuild_completedメソッドを実装
- SearchManagerのclear_suggestion_cacheメソッドを呼び出してキャッシュクリア
- システム情報ラベルの更新処理を実装
- フォルダツリーの状態更新処理を実装
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from src.gui.main_window import MainWindow
from src.utils.config import Config


def test_on_rebuild_completed_implementation():
    """_on_rebuild_completedメソッドの実装をテスト"""
    print("=== タスク6: 完了処理とシステム状態更新の実装テスト ===")

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    try:
        # メインウィンドウを作成
        main_window = MainWindow()

        # 1. _on_rebuild_completedメソッドが存在することを確認
            print("1. _on_rebuild_completedメソッドの存在確認...")
            assert hasattr(main_window, '_on_rebuild_completed'), "_on_rebuild_completedメソッドが実装されていません"
            print("   ✅ _on_rebuild_completedメソッドが実装されています")

            # 2. SearchManagerのclear_suggestion_cacheメソッドが呼び出されることを確認
            print("2. SearchManagerのclear_suggestion_cacheメソッド呼び出し確認...")

            # SearchManagerをモック化
            mock_search_manager = Mock()
            main_window.search_manager = mock_search_manager

            # タイムアウトマネージャーをモック化
            mock_timeout_manager = Mock()
            main_window.timeout_manager = mock_timeout_manager

            # システム情報ラベルをモック化
            mock_system_info_label = Mock()
            main_window.system_info_label = mock_system_info_label

            # フォルダツリーコンテナをモック化
            mock_folder_tree = Mock()
            main_window.folder_tree_container = mock_folder_tree

            # スレッドマネージャーをモック化
            mock_thread_manager = Mock()
            mock_thread_info = Mock()
            mock_thread_info.folder_path = "/test/folder"
            mock_thread_manager.get_thread_info.return_value = mock_thread_info
            main_window.thread_manager = mock_thread_manager

            # インデックスマネージャーをモック化
            mock_index_manager = Mock()
            mock_index_manager.get_index_stats.return_value = {
                'document_count': 100,
                'index_size': 1024
            }
            main_window.index_manager = mock_index_manager

            # テスト用統計情報
            test_statistics = {
                'files_processed': 50,
                'documents_added': 45,
                'processing_time': 30.5,
                'files_failed': 5
            }

            # _on_rebuild_completedメソッドを呼び出し
            main_window._on_rebuild_completed("test_thread_id", test_statistics)

            # SearchManagerのclear_suggestion_cacheが呼び出されたことを確認
            mock_search_manager.clear_suggestion_cache.assert_called_once()
            print("   ✅ SearchManager.clear_suggestion_cache()が呼び出されました")

            # 3. タイムアウト監視がキャンセルされることを確認
            print("3. タイムアウト監視キャンセル確認...")
            mock_timeout_manager.cancel_timeout.assert_called_once_with("test_thread_id")
            print("   ✅ タイムアウト監視がキャンセルされました")

            # 4. システム情報ラベルが更新されることを確認
            print("4. システム情報ラベル更新確認...")
            # システム情報ラベルのsetTextが呼び出されたことを確認
            assert mock_system_info_label.setText.called, "システム情報ラベルが更新されていません"

            # 呼び出された引数を確認
            call_args = mock_system_info_label.setText.call_args[0][0]
            assert "100ドキュメント" in call_args, "ドキュメント数が含まれていません"
            assert "50ファイル" in call_args, "処理ファイル数が含まれていません"
            assert "45件" in call_args, "追加ドキュメント数が含まれていません"
            assert "30.1秒" in call_args, "処理時間が含まれていません"
            print("   ✅ システム情報ラベルが正しく更新されました")

            # 5. フォルダツリーの状態が更新されることを確認
            print("5. フォルダツリー状態更新確認...")
            mock_folder_tree.set_folder_indexed.assert_called_once_with(
                "/test/folder", 50, 45
            )
            print("   ✅ フォルダツリーの状態が更新されました")

            # 6. _update_system_info_after_rebuildメソッドの存在確認
            print("6. _update_system_info_after_rebuildメソッドの存在確認...")
            assert hasattr(main_window, '_update_system_info_after_rebuild'), "_update_system_info_after_rebuildメソッドが実装されていません"
            print("   ✅ _update_system_info_after_rebuildメソッドが実装されています")

            # 7. _update_folder_tree_after_rebuildメソッドの存在確認
            print("7. _update_folder_tree_after_rebuildメソッドの存在確認...")
            assert hasattr(main_window, '_update_folder_tree_after_rebuild'), "_update_folder_tree_after_rebuildメソッドが実装されていません"
            print("   ✅ _update_folder_tree_after_rebuildメソッドが実装されています")

            print("\n=== すべてのテストが成功しました！ ===")
            print("タスク6「完了処理とシステム状態更新の実装」が正常に完了しています。")
            print("\n実装された機能:")
            print("- ✅ IndexingThreadManagerの完了シグナル受信処理")
            print("- ✅ SearchManagerのキャッシュクリア処理")
            print("- ✅ システム情報ラベルの更新処理")
            print("- ✅ フォルダツリーの状態更新処理")
            print("- ✅ タイムアウト監視のキャンセル処理")
            print("- ✅ 詳細な統計情報の表示")

            return True

    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """エラーハンドリングのテスト"""
    print("\n=== エラーハンドリングテスト ===")

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    try:
        # メインウィンドウを作成
        main_window = MainWindow()

            # 必要なコンポーネントを削除してエラー状況をシミュレート
            delattr(main_window, 'search_manager')
            delattr(main_window, 'timeout_manager')

            # エラーが発生してもクラッシュしないことを確認
            try:
                main_window._on_rebuild_completed("test_thread_id", {})
                print("   ✅ エラー状況でもクラッシュしませんでした")
            except Exception as e:
                print(f"   ❌ エラーハンドリングが不十分です: {e}")
                return False

            return True

    except Exception as e:
        print(f"❌ エラーハンドリングテスト中にエラーが発生しました: {e}")
        return False


if __name__ == "__main__":
    success = True

    # メイン機能テスト
    if not test_on_rebuild_completed_implementation():
        success = False

    # エラーハンドリングテスト
    if not test_error_handling():
        success = False

    if success:
        print("\n🎉 すべてのテストが成功しました！")
        print("タスク6「完了処理とシステム状態更新の実装」は正常に完了しています。")
        sys.exit(0)
    else:
        print("\n❌ 一部のテストが失敗しました。")
        sys.exit(1)
