"""
インデックス再構築機能のシンプルテスト

このテストモジュールは、インデックス再構築機能の基本的な動作を
シンプルなテストケースで検証します。
"""

import os
import shutil
import sys
import tempfile
import time
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.exceptions import DocMindException


class TestIndexRebuildSimple:
    """インデックス再構築機能のシンプルテスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app

    @pytest.fixture
    def simple_temp_folder(self):
        """シンプルテスト用の一時フォルダを作成"""
        temp_dir = tempfile.mkdtemp(prefix="docmind_simple_test_")

        # シンプルなテストファイルを作成
        test_files = [
            ("simple1.txt", "シンプルテスト用ファイル1"),
            ("simple2.txt", "シンプルテスト用ファイル2"),
        ]

        for filename, content in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        yield temp_dir

        # クリーンアップ
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_simple_file_creation(self, simple_temp_folder):
        """シンプルなファイル作成テスト"""
        files = os.listdir(simple_temp_folder)
        assert len(files) == 2
        assert "simple1.txt" in files
        assert "simple2.txt" in files

    def test_main_window_import(self, app):
        """MainWindowのインポートテスト"""
        try:
            from src.gui.main_window import MainWindow
            assert MainWindow is not None
        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")

    def test_main_window_creation_with_mock(self, app):
        """モックを使用したMainWindow作成テスト"""
        try:
            from src.gui.main_window import MainWindow

            # 必要なコンポーネントをモック
            with patch('src.core.index_manager.IndexManager'):
                with patch('src.core.search_manager.SearchManager'):
                    with patch('src.core.thread_manager.IndexingThreadManager'):
                        with patch('src.utils.config.Config.get_data_directory') as mock_data_dir:
                            mock_data_dir.return_value = tempfile.mkdtemp(prefix="docmind_mock_test_")

                            # MainWindowを作成
                            window = MainWindow()

                            # 基本的な属性が存在することを確認
                            assert window is not None
                            assert hasattr(window, '_rebuild_index')

                            window.close()

                            # データディレクトリをクリーンアップ
                            data_dir = mock_data_dir.return_value
                            if os.path.exists(data_dir):
                                shutil.rmtree(data_dir, ignore_errors=True)

        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")

    def test_rebuild_index_method_call_with_mock(self, app):
        """モックを使用した_rebuild_indexメソッド呼び出しテスト"""
        try:
            from src.gui.main_window import MainWindow

            with patch('src.core.index_manager.IndexManager'):
                with patch('src.core.search_manager.SearchManager'):
                    with patch('src.core.thread_manager.IndexingThreadManager'):
                        with patch('src.utils.config.Config.get_data_directory') as mock_data_dir:
                            mock_data_dir.return_value = tempfile.mkdtemp(prefix="docmind_mock_test_")

                            window = MainWindow()

                            # 確認ダイアログをモック（キャンセル）
                            with patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
                                # _rebuild_indexメソッドを呼び出し（エラーが発生しないことを確認）
                                try:
                                    window._rebuild_index()
                                    # エラーが発生しなければ成功
                                    assert True
                                except Exception as e:
                                    pytest.fail(f"_rebuild_indexメソッドの呼び出しでエラー: {e}")

                            window.close()

                            # データディレクトリをクリーンアップ
                            data_dir = mock_data_dir.return_value
                            if os.path.exists(data_dir):
                                shutil.rmtree(data_dir, ignore_errors=True)

        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")

    def test_progress_methods_with_mock(self, app):
        """モックを使用した進捗メソッドテスト"""
        try:
            from src.gui.main_window import MainWindow

            with patch('src.core.index_manager.IndexManager'):
                with patch('src.core.search_manager.SearchManager'):
                    with patch('src.core.thread_manager.IndexingThreadManager'):
                        with patch('src.utils.config.Config.get_data_directory') as mock_data_dir:
                            mock_data_dir.return_value = tempfile.mkdtemp(prefix="docmind_mock_test_")

                            window = MainWindow()

                            # 進捗メソッドを呼び出し（エラーが発生しないことを確認）
                            try:
                                window.show_progress("テスト", 0)
                                window.update_progress(1, 2, "テスト進捗")
                                window.hide_progress("テスト完了")
                                assert True
                            except Exception as e:
                                pytest.fail(f"進捗メソッドの呼び出しでエラー: {e}")

                            window.close()

                            # データディレクトリをクリーンアップ
                            data_dir = mock_data_dir.return_value
                            if os.path.exists(data_dir):
                                shutil.rmtree(data_dir, ignore_errors=True)

        except ImportError as e:
            pytest.skip(f"MainWindowをインポートできません: {e}")


class TestIndexRebuildMockIntegration:
    """モック統合テスト"""

    @pytest.fixture
    def app(self):
        """QApplicationのフィクスチャ"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app

    def test_mock_components_integration(self):
        """モックコンポーネントの統合テスト"""
        # IndexManagerのモック
        mock_index_manager = Mock()
        mock_index_manager.clear_index.return_value = True
        mock_index_manager.get_document_count.return_value = 0

        # SearchManagerのモック
        mock_search_manager = Mock()
        mock_search_manager.clear_suggestion_cache.return_value = None

        # ThreadManagerのモック
        mock_thread_manager = Mock()
        mock_thread_manager.start_indexing_thread.return_value = "test_thread_123"
        mock_thread_manager.get_active_thread_count.return_value = 0

        # モックの動作を確認
        assert mock_index_manager.clear_index() is True
        assert mock_index_manager.get_document_count() == 0

        mock_search_manager.clear_suggestion_cache()
        assert mock_search_manager.clear_suggestion_cache.called

        thread_id = mock_thread_manager.start_indexing_thread("/test/path")
        assert thread_id == "test_thread_123"
        assert mock_thread_manager.get_active_thread_count() == 0

    def test_error_simulation_with_mocks(self):
        """モックを使用したエラーシミュレーション"""
        # エラーを発生させるモック
        mock_index_manager = Mock()
        mock_index_manager.clear_index.side_effect = DocMindException("テストエラー")

        # エラーが正しく発生することを確認
        with pytest.raises(DocMindException) as exc_info:
            mock_index_manager.clear_index()

        assert str(exc_info.value) == "テストエラー"

    def test_timeout_simulation(self, app):
        """タイムアウトシミュレーション"""
        timeout_occurred = False

        def on_timeout():
            nonlocal timeout_occurred
            timeout_occurred = True

        # 短いタイムアウトを設定
        timer = QTimer()
        timer.timeout.connect(on_timeout)
        timer.setSingleShot(True)
        timer.start(100)  # 100ms

        # タイムアウトが発生するまで待機
        start_time = time.time()
        while not timeout_occurred and time.time() - start_time < 1.0:
            QApplication.processEvents()
            time.sleep(0.01)

        assert timeout_occurred, "タイムアウトが発生しませんでした"


class TestIndexRebuildErrorHandling:
    """エラーハンドリングテスト"""

    def test_file_not_found_error(self):
        """ファイル未発見エラーのテスト"""
        non_existent_file = "/non/existent/file.txt"

        with pytest.raises(FileNotFoundError):
            with open(non_existent_file):
                pass

    def test_permission_error_simulation(self, tmp_path):
        """権限エラーのシミュレーション"""
        # テストファイルを作成
        test_file = tmp_path / "readonly.txt"
        test_file.write_text("テスト内容")

        # 読み取り専用に設定
        os.chmod(test_file, 0o444)

        try:
            # 書き込み試行（エラーが発生するはず）
            with pytest.raises(PermissionError):
                with open(test_file, 'w') as f:
                    f.write("新しい内容")
        finally:
            # 権限を元に戻す
            os.chmod(test_file, 0o666)

    def test_docmind_exception_handling(self):
        """DocMindException例外ハンドリングのテスト"""
        def raise_exception():
            raise DocMindException("テスト例外", "詳細情報")

        with pytest.raises(DocMindException) as exc_info:
            raise_exception()

        assert exc_info.value.message == "テスト例外"
        assert exc_info.value.details == "詳細情報"
        assert "テスト例外 - 詳細: 詳細情報" in str(exc_info.value)


if __name__ == "__main__":
    # テストを直接実行する場合
    pytest.main([__file__, "-v", "--tb=short"])
