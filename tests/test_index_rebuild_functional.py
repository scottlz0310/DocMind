"""
インデックス再構築機能の機能テスト

このテストモジュールは、実際のMainWindowクラスを使用して
インデックス再構築機能の動作を検証します。
"""

import os
import shutil
import sys
import tempfile
import time
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.exceptions import DocMindException


class TestIndexRebuildFunctional:
    """インデックス再構築機能の機能テスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app

    @pytest.fixture
    def temp_folder(self):
        """テスト用の一時フォルダを作成"""
        temp_dir = tempfile.mkdtemp(prefix="docmind_test_functional_")

        # 機能テスト用ファイルを作成
        test_files = [
            ("functional_test1.txt", "機能テスト用ドキュメント1\n検索キーワード: 重要"),
            ("functional_test2.txt", "機能テスト用ドキュメント2\n検索キーワード: 通常"),
            (
                "functional_test3.md",
                "# 機能テスト用マークダウン\n\n検索キーワード: マークダウン",
            ),
        ]

        for filename, content in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        yield temp_dir

        # クリーンアップ
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_rebuild_index_method_exists(self, app):
        """_rebuild_indexメソッドが存在することをテスト"""
        try:
            from src.gui.main_window import MainWindow

            # メインウィンドウを作成（一時的なデータディレクトリを使用）
            with patch("src.utils.config.Config.get_data_directory") as mock_data_dir:
                mock_data_dir.return_value = tempfile.mkdtemp(
                    prefix="docmind_data_test_"
                )

                window = MainWindow()

                # _rebuild_indexメソッドが存在することを確認
                assert hasattr(
                    window, "_rebuild_index"
                ), "_rebuild_indexメソッドが存在しません"
                assert callable(
                    window._rebuild_index
                ), "_rebuild_indexが呼び出し可能ではありません"

                window.close()

                # データディレクトリをクリーンアップ
                data_dir = mock_data_dir.return_value
                if os.path.exists(data_dir):
                    shutil.rmtree(data_dir, ignore_errors=True)

        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")

    def test_progress_methods_exist(self, app):
        """進捗表示メソッドが存在することをテスト"""
        try:
            from src.gui.main_window import MainWindow

            with patch("src.utils.config.Config.get_data_directory") as mock_data_dir:
                mock_data_dir.return_value = tempfile.mkdtemp(
                    prefix="docmind_data_test_"
                )

                window = MainWindow()

                # 進捗表示メソッドが存在することを確認
                assert hasattr(
                    window, "show_progress"
                ), "show_progressメソッドが存在しません"
                assert hasattr(
                    window, "update_progress"
                ), "update_progressメソッドが存在しません"
                assert hasattr(
                    window, "hide_progress"
                ), "hide_progressメソッドが存在しません"

                # メソッドが呼び出し可能であることを確認
                assert callable(
                    window.show_progress
                ), "show_progressが呼び出し可能ではありません"
                assert callable(
                    window.update_progress
                ), "update_progressが呼び出し可能ではありません"
                assert callable(
                    window.hide_progress
                ), "hide_progressが呼び出し可能ではありません"

                window.close()

                # データディレクトリをクリーンアップ
                data_dir = mock_data_dir.return_value
                if os.path.exists(data_dir):
                    shutil.rmtree(data_dir, ignore_errors=True)

        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")

    def test_core_components_exist(self, app):
        """コアコンポーネントが存在することをテスト"""
        try:
            from src.gui.main_window import MainWindow

            with patch("src.utils.config.Config.get_data_directory") as mock_data_dir:
                mock_data_dir.return_value = tempfile.mkdtemp(
                    prefix="docmind_data_test_"
                )

                window = MainWindow()

                # コアコンポーネントが存在することを確認
                assert hasattr(window, "index_manager"), "index_managerが存在しません"
                assert hasattr(window, "search_manager"), "search_managerが存在しません"
                assert hasattr(window, "thread_manager"), "thread_managerが存在しません"
                assert hasattr(
                    window, "folder_tree_container_container"
                ), "folder_tree_container_containerが存在しません"

                window.close()

                # データディレクトリをクリーンアップ
                data_dir = mock_data_dir.return_value
                if os.path.exists(data_dir):
                    shutil.rmtree(data_dir, ignore_errors=True)

        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")

    def test_rebuild_index_with_mocked_dialog(self, app, temp_folder):
        """モックダイアログを使用した再構築テスト"""
        try:
            from src.gui.main_window import MainWindow

            with patch("src.utils.config.Config.get_data_directory") as mock_data_dir:
                mock_data_dir.return_value = tempfile.mkdtemp(
                    prefix="docmind_data_test_"
                )

                window = MainWindow()
                window.show()

                # フォルダを設定
                if hasattr(window, "folder_tree_container") and hasattr(
                    window.folder_tree_container, "set_root_folder"
                ):
                    window.folder_tree_container_container.load_folder_structure(
                        temp_folder
                    )

                # 進捗追跡用の変数
                progress_calls = []

                # 進捗メソッドをモック
                original_show_progress = window.show_progress
                original_update_progress = window.update_progress
                original_hide_progress = window.hide_progress

                def mock_show_progress(message, value=0, current=0, total=0):
                    progress_calls.append(("show", message, value))
                    return original_show_progress(message, value, current, total)

                def mock_update_progress(current, total, message=""):
                    progress_calls.append(("update", current, total, message))
                    return original_update_progress(current, total, message)

                def mock_hide_progress(message=""):
                    progress_calls.append(("hide", message))
                    return original_hide_progress(message)

                window.show_progress = mock_show_progress
                window.update_progress = mock_update_progress
                window.hide_progress = mock_hide_progress

                # 確認ダイアログをモック（「はい」を選択）
                with patch.object(
                    QMessageBox, "question", return_value=QMessageBox.Yes
                ):
                    # インデックス再構築を実行
                    window._rebuild_index()

                    # 少し待機してイベントを処理
                    for _ in range(10):
                        QApplication.processEvents()
                        time.sleep(0.1)

                    # 進捗メソッドが呼ばれたことを確認
                    assert len(progress_calls) > 0, "進捗メソッドが呼ばれていません"

                    # show_progressが呼ばれたことを確認
                    show_calls = [call for call in progress_calls if call[0] == "show"]
                    assert len(show_calls) > 0, "show_progressが呼ばれていません"

                window.close()

                # データディレクトリをクリーンアップ
                data_dir = mock_data_dir.return_value
                if os.path.exists(data_dir):
                    shutil.rmtree(data_dir, ignore_errors=True)

        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")
        except Exception as e:
            pytest.fail(f"テスト実行中にエラーが発生しました: {e}")

    def test_rebuild_index_cancellation(self, app, temp_folder):
        """再構築キャンセルのテスト"""
        try:
            from src.gui.main_window import MainWindow

            with patch("src.utils.config.Config.get_data_directory") as mock_data_dir:
                mock_data_dir.return_value = tempfile.mkdtemp(
                    prefix="docmind_data_test_"
                )

                window = MainWindow()
                window.show()

                # フォルダを設定
                if hasattr(window, "folder_tree_container") and hasattr(
                    window.folder_tree_container, "set_root_folder"
                ):
                    window.folder_tree_container_container.load_folder_structure(
                        temp_folder
                    )

                # 確認ダイアログをモック（「いいえ」を選択）
                with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
                    # インデックス再構築を実行（キャンセル）
                    window._rebuild_index()

                    # 少し待機してイベントを処理
                    for _ in range(5):
                        QApplication.processEvents()
                        time.sleep(0.05)

                    # キャンセルされたため、再構築状態がアクティブでないことを確認
                    if hasattr(window, "_rebuild_state"):
                        assert (
                            not window._rebuild_state.is_active
                        ), "キャンセル後も再構築状態がアクティブです"

                window.close()

                # データディレクトリをクリーンアップ
                data_dir = mock_data_dir.return_value
                if os.path.exists(data_dir):
                    shutil.rmtree(data_dir, ignore_errors=True)

        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")
        except Exception as e:
            pytest.fail(f"テスト実行中にエラーが発生しました: {e}")

    def test_error_handling_simulation(self, app, temp_folder):
        """エラーハンドリングのシミュレーション"""
        try:
            from src.gui.main_window import MainWindow

            with patch("src.utils.config.Config.get_data_directory") as mock_data_dir:
                mock_data_dir.return_value = tempfile.mkdtemp(
                    prefix="docmind_data_test_"
                )

                window = MainWindow()
                window.show()

                # IndexManagerのclear_indexメソッドでエラーを発生させる
                if hasattr(window, "index_manager"):

                    def mock_clear_index():
                        raise DocMindException("テスト用エラー")

                    window.index_manager.clear_index = mock_clear_index

                # エラーダイアログをモック
                with patch.object(
                    QMessageBox, "question", return_value=QMessageBox.Yes
                ):
                    with patch.object(QMessageBox, "critical") as mock_error_dialog:
                        # インデックス再構築を実行
                        window._rebuild_index()

                        # 少し待機してイベントを処理
                        for _ in range(10):
                            QApplication.processEvents()
                            time.sleep(0.1)

                        # エラーダイアログが表示されたことを確認
                        assert (
                            mock_error_dialog.called
                        ), "エラーダイアログが表示されていません"

                window.close()

                # データディレクトリをクリーンアップ
                data_dir = mock_data_dir.return_value
                if os.path.exists(data_dir):
                    shutil.rmtree(data_dir, ignore_errors=True)

        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")
        except Exception as e:
            pytest.fail(f"テスト実行中にエラーが発生しました: {e}")


class TestIndexRebuildPerformance:
    """インデックス再構築のパフォーマンステスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app

    @pytest.fixture
    def performance_temp_folder(self):
        """パフォーマンステスト用の一時フォルダを作成"""
        temp_dir = tempfile.mkdtemp(prefix="docmind_test_performance_")

        # パフォーマンステスト用ファイルを作成（20ファイル）
        for i in range(20):
            filename = f"performance_test_{i:02d}.txt"
            content = f"""
            パフォーマンステスト用ドキュメント {i}

            このファイルはパフォーマンステスト用に作成されました。
            ファイル番号: {i}

            検索テスト用キーワード:
            - keyword_{i % 5}
            - performance_test
            - document_{i}

            追加のテキスト内容:
            {'テストテキスト ' * (i + 1)}
            """

            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        yield temp_dir

        # クリーンアップ
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_performance_measurement(self, app, performance_temp_folder):
        """パフォーマンス測定テスト"""
        try:
            from src.gui.main_window import MainWindow

            with patch("src.utils.config.Config.get_data_directory") as mock_data_dir:
                mock_data_dir.return_value = tempfile.mkdtemp(
                    prefix="docmind_data_perf_test_"
                )

                window = MainWindow()
                window.show()

                # フォルダを設定
                if hasattr(window, "folder_tree_container") and hasattr(
                    window.folder_tree_container, "set_root_folder"
                ):
                    window.folder_tree_container_container.load_folder_structure(
                        performance_temp_folder
                    )

                # パフォーマンス測定
                start_time = time.time()

                # 確認ダイアログをモック
                with patch.object(
                    QMessageBox, "question", return_value=QMessageBox.Yes
                ):
                    # インデックス再構築を実行
                    window._rebuild_index()

                    # 処理完了まで待機（最大30秒）
                    timeout = 30
                    while time.time() - start_time < timeout:
                        QApplication.processEvents()
                        if (
                            not hasattr(window, "_rebuild_state")
                            or not window._rebuild_state.is_active
                        ):
                            break
                        time.sleep(0.1)

                    end_time = time.time()
                    duration = end_time - start_time

                    # パフォーマンス検証
                    assert duration < 30, f"処理時間が長すぎます: {duration:.2f}秒"

                    # ファイル数あたりの処理時間を計算
                    files_per_second = 20 / duration if duration > 0 else 0

                    print("パフォーマンステスト結果:")
                    print(f"  - 処理時間: {duration:.2f}秒")
                    print(f"  - 処理速度: {files_per_second:.2f} files/sec")

                    # 最低限の処理速度を確認
                    assert (
                        files_per_second > 0.5
                    ), f"処理速度が遅すぎます: {files_per_second:.2f} files/sec"

                window.close()

                # データディレクトリをクリーンアップ
                data_dir = mock_data_dir.return_value
                if os.path.exists(data_dir):
                    shutil.rmtree(data_dir, ignore_errors=True)

        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")
        except Exception as e:
            pytest.fail(f"テスト実行中にエラーが発生しました: {e}")


if __name__ == "__main__":
    # テストを直接実行する場合
    pytest.main([__file__, "-v", "--tb=short"])
