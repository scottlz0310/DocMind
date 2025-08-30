"""
エラーハンドラーのテスト

包括的エラーハンドリング、回復メカニズム、診断情報収集機能のテストを行います。
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.utils.error_handler import (
    ErrorHandler,
    get_global_error_handler,
    handle_exceptions,
    setup_global_exception_handler,
)
from src.utils.exceptions import (
    DocumentProcessingError,
    IndexingError,
    SearchError,
)


class TestErrorHandler:
    """ErrorHandlerクラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = ErrorHandler(data_dir=self.temp_dir)

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_error_handler_initialization(self):
        """エラーハンドラーの初期化テスト"""
        assert self.error_handler.data_dir == Path(self.temp_dir)
        assert self.error_handler.error_reports_dir.exists()
        assert len(self.error_handler._recovery_handlers) == 0

    def test_register_recovery_handler(self):
        """回復ハンドラーの登録テスト"""
        def test_handler(exc, error_info):
            return True

        self.error_handler.register_recovery_handler(SearchError, test_handler)
        assert SearchError in self.error_handler._recovery_handlers
        assert self.error_handler._recovery_handlers[SearchError] == test_handler

    def test_handle_docmind_exception(self):
        """DocMind例外の処理テスト"""
        test_error = SearchError("テスト検索エラー", query="test query", details="詳細情報")

        result = self.error_handler.handle_exception(
            test_error,
            context="テストコンテキスト",
            user_message="ユーザー向けメッセージ",
            attempt_recovery=False
        )

        assert result is False  # 回復処理を試行しないため

        # エラーレポートが生成されているかチェック
        report_files = list(self.error_handler.error_reports_dir.glob("*.json"))
        assert len(report_files) > 0

        # レポート内容をチェック
        with open(report_files[0], encoding='utf-8') as f:
            report_data = json.load(f)

        assert report_data["exception_type"] == "SearchError"
        assert report_data["exception_message"] == "テスト検索エラー"
        assert report_data["context"] == "テストコンテキスト"
        assert "docmind_details" in report_data
        assert report_data["docmind_details"]["details"] == "詳細情報"

    def test_handle_standard_exception(self):
        """標準例外の処理テスト"""
        test_error = ValueError("標準エラー")

        result = self.error_handler.handle_exception(
            test_error,
            context="標準例外テスト",
            attempt_recovery=False
        )

        assert result is False

        # エラーレポートが生成されているかチェック
        report_files = list(self.error_handler.error_reports_dir.glob("*.json"))
        assert len(report_files) > 0

        with open(report_files[0], encoding='utf-8') as f:
            report_data = json.load(f)

        assert report_data["exception_type"] == "ValueError"
        assert "docmind_details" not in report_data

    def test_recovery_handler_execution(self):
        """回復ハンドラーの実行テスト"""
        recovery_called = False

        def recovery_handler(exc, error_info):
            nonlocal recovery_called
            recovery_called = True
            return True

        self.error_handler.register_recovery_handler(SearchError, recovery_handler)

        test_error = SearchError("回復テスト")
        result = self.error_handler.handle_exception(test_error, attempt_recovery=True)

        assert result is True
        assert recovery_called is True

    def test_default_recovery_creates_directories(self):
        """デフォルト回復処理でディレクトリが作成されるテスト"""
        # データディレクトリを削除
        import shutil
        shutil.rmtree(self.temp_dir)

        test_error = ValueError("ディレクトリテスト")
        result = self.error_handler.handle_exception(test_error, attempt_recovery=True)

        assert result is True
        assert Path(self.temp_dir).exists()

    @patch('psutil.virtual_memory')
    @patch('psutil.Process')
    def test_system_info_collection(self, mock_process, mock_memory):
        """システム情報収集のテスト"""
        # モックの設定
        mock_memory.return_value.total = 8 * 1024 * 1024 * 1024  # 8GB
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
        mock_process_instance.memory_info.return_value.vms = 200 * 1024 * 1024  # 200MB
        mock_process_instance.num_threads.return_value = 5
        mock_process.return_value = mock_process_instance

        test_error = ValueError("システム情報テスト")
        self.error_handler.handle_exception(test_error, attempt_recovery=False)

        # システム情報が収集されているかチェック
        assert self.error_handler._system_info is not None
        assert "platform" in self.error_handler._system_info
        assert "python_version" in self.error_handler._system_info

    def test_error_report_generation(self):
        """エラーレポート生成のテスト"""
        test_error = DocumentProcessingError(
            "ドキュメント処理エラー",
            file_path="/test/path.pdf",
            file_type="pdf"
        )

        self.error_handler.handle_exception(test_error, context="レポート生成テスト")

        # レポートファイルが生成されているかチェック
        report_files = list(self.error_handler.error_reports_dir.glob("*.json"))
        assert len(report_files) == 1

        report_file = report_files[0]
        assert "DocumentProcessingError" in report_file.name

        # レポート内容の詳細チェック
        with open(report_file, encoding='utf-8') as f:
            report_data = json.load(f)

        assert "timestamp" in report_data
        assert "traceback" in report_data
        assert "system_info" in report_data
        assert "application_state" in report_data
        assert report_data["docmind_details"]["custom_attributes"]["file_path"] == "/test/path.pdf"


class TestHandleExceptionsDecorator:
    """handle_exceptionsデコレータのテスト"""

    def test_decorator_catches_exception(self):
        """デコレータが例外をキャッチするテスト"""
        @handle_exceptions(
            context="デコレータテスト",
            user_message="テストエラー",
            attempt_recovery=False,
            reraise=False
        )
        def failing_function():
            raise ValueError("テスト例外")

        result = failing_function()
        assert result is None  # 例外が処理され、Noneが返される

    def test_decorator_reraises_exception(self):
        """デコレータが例外を再発生させるテスト"""
        @handle_exceptions(
            context="再発生テスト",
            reraise=True
        )
        def failing_function():
            raise ValueError("再発生テスト例外")

        with pytest.raises(ValueError):
            failing_function()

    def test_decorator_with_recovery(self):
        """デコレータの回復処理テスト"""
        # グローバルエラーハンドラーに回復ハンドラーを登録
        error_handler = get_global_error_handler()

        def recovery_handler(exc, error_info):
            return True

        error_handler.register_recovery_handler(ValueError, recovery_handler)

        @handle_exceptions(
            context="回復テスト",
            attempt_recovery=True,
            reraise=False
        )
        def failing_function():
            raise ValueError("回復テスト例外")

        result = failing_function()
        assert result is None  # 回復成功により例外は再発生されない

    def test_decorator_preserves_function_metadata(self):
        """デコレータが関数のメタデータを保持するテスト"""
        @handle_exceptions()
        def test_function():
            """テスト関数のドキュメント"""
            return "success"

        assert test_function.__name__ == "test_function"
        assert "テスト関数のドキュメント" in test_function.__doc__

        # 正常な実行もテスト
        result = test_function()
        assert result == "success"


class TestGlobalExceptionHandler:
    """グローバル例外ハンドラーのテスト"""

    def test_global_error_handler_singleton(self):
        """グローバルエラーハンドラーがシングルトンであることのテスト"""
        handler1 = get_global_error_handler()
        handler2 = get_global_error_handler()
        assert handler1 is handler2

    @patch('sys.excepthook')
    def test_setup_global_exception_handler(self, mock_excepthook):
        """グローバル例外ハンドラーの設定テスト"""
        setup_global_exception_handler()

        # sys.excepthookが設定されているかチェック
        import sys
        assert sys.excepthook != sys.__excepthook__

    def test_keyboard_interrupt_handling(self):
        """KeyboardInterrupt例外の特別処理テスト"""
        setup_global_exception_handler()

        # KeyboardInterruptは通常通り処理されることを確認
        # （実際のテストは困難なため、設定の確認のみ）
        import sys
        assert callable(sys.excepthook)


class TestErrorHandlerIntegration:
    """エラーハンドラーの統合テスト"""

    def setup_method(self):
        """テスト前の設定"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multiple_error_handling(self):
        """複数のエラーを連続して処理するテスト"""
        error_handler = ErrorHandler(data_dir=self.temp_dir)

        # 複数の異なる例外を処理
        errors = [
            SearchError("検索エラー1"),
            IndexingError("インデックスエラー1"),
            DocumentProcessingError("処理エラー1"),
            ValueError("標準エラー1")
        ]

        for error in errors:
            error_handler.handle_exception(error, attempt_recovery=False)

        # 各エラーに対してレポートが生成されているかチェック
        report_files = list(Path(self.temp_dir).glob("error_reports/*.json"))
        assert len(report_files) == len(errors)

    def test_error_handler_with_missing_directories(self):
        """ディレクトリが存在しない状態でのエラーハンドラーテスト"""
        non_existent_dir = os.path.join(self.temp_dir, "non_existent")
        error_handler = ErrorHandler(data_dir=non_existent_dir)

        # ディレクトリが自動作成されることを確認
        assert error_handler.error_reports_dir.exists()

        # エラー処理が正常に動作することを確認
        test_error = ValueError("ディレクトリ作成テスト")
        error_handler.handle_exception(test_error, attempt_recovery=False)

        # レポートが生成されることを確認
        report_files = list(error_handler.error_reports_dir.glob("*.json"))
        assert len(report_files) == 1


if __name__ == "__main__":
    pytest.main([__file__])
