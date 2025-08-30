"""
エラーハンドリング統合テスト

包括的エラーハンドリング、優雅な劣化、回復メカニズムの
統合動作をテストします。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

from src.gui.error_dialog import SystemStatusDialog, UserNotificationManager
from src.utils.error_handler import ErrorHandler
from src.utils.exceptions import DocumentProcessingError, IndexingError, SearchError
from src.utils.graceful_degradation import (
    GracefulDegradationManager,
)


class TestErrorHandlingIntegration:
    """エラーハンドリング統合テスト"""

    def setup_method(self):
        """テスト前の設定"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = ErrorHandler(data_dir=self.temp_dir)
        self.degradation_manager = GracefulDegradationManager()

        # テスト用コンポーネントを設定
        self.degradation_manager.register_component(
            "test_search", {"full_text": True, "semantic": True}
        )
        self.degradation_manager.register_component(
            "test_index", {"indexing": True, "search": True}
        )

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_error_with_degradation_flow(self):
        """エラー発生から劣化までの統合フロー"""
        # 回復ハンドラーを登録
        recovery_called = False

        def recovery_handler(exc, error_info):
            nonlocal recovery_called
            recovery_called = True
            return False  # 回復失敗をシミュレート

        self.error_handler.register_recovery_handler(SearchError, recovery_handler)

        # フォールバックハンドラーを登録
        fallback_called = False

        def fallback_handler(error):
            nonlocal fallback_called
            fallback_called = True
            return True  # フォールバック成功

        self.degradation_manager.register_fallback_handler(
            "test_search", fallback_handler
        )

        # エラーを発生させる
        test_error = SearchError("統合テストエラー")

        # エラーハンドラーでエラーを処理
        self.error_handler.handle_exception(
            test_error, context="統合テスト", attempt_recovery=True
        )

        # 劣化マネージャーでコンポーネントを失敗状態にマーク
        degradation_result = self.degradation_manager.mark_component_failed(
            "test_search", test_error, disable_capabilities=["full_text"]
        )

        # 結果を検証
        assert recovery_called is True
        assert fallback_called is True
        assert degradation_result is True  # フォールバック成功

        # コンポーネント状態を確認
        component = self.degradation_manager.get_component_status("test_search")
        assert component.status.value == "degraded"
        assert component.fallback_active is True
        assert component.capabilities["full_text"] is False
        assert component.capabilities["semantic"] is True

        # エラーレポートが生成されていることを確認
        report_files = list(Path(self.temp_dir).glob("error_reports/*.json"))
        assert len(report_files) > 0

    def test_cascading_failure_scenario(self):
        """カスケード障害シナリオのテスト"""
        # 依存関係のあるコンポーネントを設定
        self.degradation_manager.register_component("database", {"connection": True})
        self.degradation_manager.register_component("search_service", {"search": True})

        # データベース障害をシミュレート
        db_error = RuntimeError("データベース接続失敗")
        self.error_handler.handle_exception(db_error, "データベース接続")
        self.degradation_manager.mark_component_failed("database", db_error)

        # 検索サービスも影響を受ける
        SearchError("データベース障害により検索不可")
        self.degradation_manager.mark_component_degraded(
            "search_service",
            disable_capabilities=["search"],
            error_message="データベース障害の影響",
        )

        # システム健全性を確認
        health = self.degradation_manager.get_system_health()
        assert health["overall_health"] == "critical"
        assert health["failed"] >= 1
        assert health["degraded"] >= 1

    def test_recovery_after_failure(self):
        """障害後の回復テスト"""
        # ヘルスチェッカーを設定
        health_check_count = 0

        def health_checker():
            nonlocal health_check_count
            health_check_count += 1
            return health_check_count >= 2  # 2回目で回復

        self.degradation_manager.register_health_checker("test_search", health_checker)

        # 障害を発生させる
        test_error = SearchError("一時的な障害")
        self.degradation_manager.mark_component_failed("test_search", test_error)

        # 最初の回復試行（失敗）
        recovery1 = self.degradation_manager.attempt_recovery("test_search")
        assert recovery1 is False
        assert not self.degradation_manager.is_component_healthy("test_search")

        # 2回目の回復試行（成功）
        recovery2 = self.degradation_manager.attempt_recovery("test_search")
        assert recovery2 is True
        assert self.degradation_manager.is_component_healthy("test_search")

        # 全機能が復旧していることを確認
        assert self.degradation_manager.is_capability_available(
            "test_search", "full_text"
        )
        assert self.degradation_manager.is_capability_available(
            "test_search", "semantic"
        )

    def test_error_report_generation_with_system_state(self):
        """システム状態を含むエラーレポート生成テスト"""
        # システム状態を設定
        self.degradation_manager.mark_component_degraded("test_index", ["indexing"])

        # エラーを発生させる
        test_error = DocumentProcessingError(
            "ドキュメント処理失敗", file_path="/test/document.pdf", file_type="pdf"
        )

        self.error_handler.handle_exception(test_error, "ドキュメント処理テスト")

        # レポートファイルを確認
        report_files = list(Path(self.temp_dir).glob("error_reports/*.json"))
        assert len(report_files) == 1

        with open(report_files[0], encoding="utf-8") as f:
            report_data = json.load(f)

        # レポート内容を検証
        assert "system_info" in report_data
        assert "application_state" in report_data
        assert "docmind_details" in report_data
        assert (
            report_data["docmind_details"]["custom_attributes"]["file_path"]
            == "/test/document.pdf"
        )


@pytest.mark.skipif(not pytest.importorskip("PySide6"), reason="PySide6 not available")
class TestGUIErrorHandling:
    """GUI エラーハンドリングのテスト"""

    @classmethod
    def setup_class(cls):
        """テストクラスの設定"""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_user_notification_manager(self):
        """ユーザー通知マネージャーのテスト"""
        notification_manager = UserNotificationManager()

        # エラー表示のテスト（実際のダイアログは表示しない）
        with patch("src.gui.error_dialog.ErrorDialog") as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog.return_value = mock_dialog_instance

            notification_manager.show_error(
                "テストエラー", "テストメッセージ", "詳細情報", ["提案1", "提案2"]
            )

            mock_dialog.assert_called_once()
            mock_dialog_instance.exec.assert_called_once()

    def test_system_status_dialog_creation(self):
        """システム状態ダイアログの作成テスト"""
        # モックの劣化マネージャーを設定
        mock_manager = Mock()
        mock_manager.get_system_health.return_value = {
            "overall_health": "healthy",
            "total_components": 3,
            "healthy": 3,
            "degraded": 0,
            "failed": 0,
            "components": {
                "test_component": {
                    "status": "healthy",
                    "error_message": None,
                    "fallback_active": False,
                    "capabilities": {"feature1": True},
                }
            },
        }

        with patch(
            "src.gui.error_dialog.get_global_degradation_manager",
            return_value=mock_manager,
        ):
            dialog = SystemStatusDialog()

            # ダイアログが正常に作成されることを確認
            assert dialog.windowTitle() == "システム状態"
            assert hasattr(dialog, "overall_health_label")
            assert hasattr(dialog, "health_progress")

            # タイマーを停止
            dialog.update_timer.stop()
            dialog.close()

    def test_system_degradation_warning(self):
        """システム劣化警告のテスト"""
        notification_manager = UserNotificationManager()

        # 劣化状態をシミュレート
        mock_manager = Mock()
        mock_manager.get_system_health.return_value = {
            "overall_health": "degraded",
            "total_components": 3,
            "healthy": 2,
            "degraded": 1,
            "failed": 0,
        }

        with patch(
            "src.gui.error_dialog.get_global_degradation_manager",
            return_value=mock_manager,
        ):
            with patch("src.gui.error_dialog.ErrorDialog") as mock_dialog:
                mock_dialog_instance = Mock()
                mock_dialog.return_value = mock_dialog_instance

                notification_manager.show_system_degradation_warning()

                # エラーダイアログが呼び出されることを確認
                mock_dialog.assert_called_once()
                args, kwargs = mock_dialog.call_args
                assert "システム劣化警告" in args[0]
                assert "一部機能に問題" in args[1]


class TestErrorHandlingScenarios:
    """実際のエラーシナリオのテスト"""

    def setup_method(self):
        """テスト前の設定"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_system_error_scenario(self):
        """ファイルシステムエラーシナリオ"""
        error_handler = ErrorHandler(data_dir=self.temp_dir)

        # ファイルシステムエラーをシミュレート
        from src.utils.exceptions import FileSystemError

        fs_error = FileSystemError(
            "ディスク容量不足", path="/test/path", operation="write"
        )

        error_handler.handle_exception(
            fs_error,
            context="ファイル書き込み",
            user_message="ディスク容量が不足しています。",
            attempt_recovery=True,
        )

        # エラーレポートが生成されることを確認
        report_files = list(Path(self.temp_dir).glob("error_reports/*.json"))
        assert len(report_files) > 0

        # レポート内容を確認
        with open(report_files[0], encoding="utf-8") as f:
            report_data = json.load(f)

        assert report_data["exception_type"] == "FileSystemError"
        assert "ディスク容量不足" in report_data["exception_message"]

    def test_multiple_component_failure_scenario(self):
        """複数コンポーネント障害シナリオ"""
        degradation_manager = GracefulDegradationManager()

        # 複数のコンポーネントを登録
        components = ["search", "index", "embedding", "database"]
        for comp in components:
            degradation_manager.register_component(comp, {"main_feature": True})

        # 段階的に障害を発生させる
        errors = [
            ("database", RuntimeError("DB接続失敗")),
            ("index", IndexingError("インデックス破損")),
            ("search", SearchError("検索サービス停止")),
        ]

        for comp_name, error in errors:
            degradation_manager.mark_component_failed(comp_name, error)

        # システム健全性を確認
        health = degradation_manager.get_system_health()
        assert health["total_components"] == 4
        assert health["failed"] == 3
        assert health["healthy"] == 1
        assert health["overall_health"] == "critical"

        # 残りの健全なコンポーネントは動作していることを確認
        assert degradation_manager.is_component_healthy("embedding")
        assert degradation_manager.is_capability_available("embedding", "main_feature")

    def test_error_recovery_with_partial_success(self):
        """部分的成功を伴うエラー回復テスト"""
        ErrorHandler(data_dir=self.temp_dir)
        degradation_manager = GracefulDegradationManager()

        # コンポーネントを設定
        degradation_manager.register_component(
            "partial_recovery", {"feature1": True, "feature2": True, "feature3": True}
        )

        # 部分的回復ハンドラーを設定
        def partial_recovery_handler(error):
            # feature1のみ回復
            component = degradation_manager.get_component_status("partial_recovery")
            component.capabilities["feature1"] = True
            component.capabilities["feature2"] = False  # 回復失敗
            component.capabilities["feature3"] = False  # 回復失敗
            return True

        degradation_manager.register_fallback_handler(
            "partial_recovery", partial_recovery_handler
        )

        # 障害を発生させる
        test_error = RuntimeError("部分的障害")
        result = degradation_manager.mark_component_failed(
            "partial_recovery",
            test_error,
            disable_capabilities=["feature1", "feature2", "feature3"],
        )

        assert result is True  # フォールバック成功

        # 部分的回復を確認
        assert degradation_manager.is_capability_available(
            "partial_recovery", "feature1"
        )
        assert not degradation_manager.is_capability_available(
            "partial_recovery", "feature2"
        )
        assert not degradation_manager.is_capability_available(
            "partial_recovery", "feature3"
        )

        component = degradation_manager.get_component_status("partial_recovery")
        assert component.status.value == "degraded"
        assert component.fallback_active is True


if __name__ == "__main__":
    pytest.main([__file__])
