#!/usr/bin/env python3
"""
GUI機能統合検証クラスのテスト - 再設計版

GUIFunctionalityValidatorクラス自体の動作をテストします。
"""

import os
import sys
from pathlib import Path

import pytest

# GUI環境の設定
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.validation_framework.base_validator import ValidationConfig
from tests.validation_framework.gui_functionality_validator import (
    GUIFunctionalityValidator,
)


class TestGUIFunctionalityValidator:
    """GUIFunctionalityValidatorクラスのテストケース"""

    def setup_method(self):
        """各テストメソッドの前に実行されるセットアップ"""
        self.config = ValidationConfig(
            enable_performance_monitoring=False,
            enable_memory_monitoring=False,
            enable_error_injection=False,
            max_execution_time=10.0,
            max_memory_usage=256.0,
            log_level="INFO",
        )

        self.validator = GUIFunctionalityValidator(self.config)

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ"""
        if hasattr(self, "validator"):
            try:
                self.validator.teardown_test_environment()
                self.validator.cleanup()
            except Exception:
                pass  # クリーンアップエラーは無視

    def test_validator_initialization(self):
        """検証クラスの初期化テスト"""
        assert self.validator is not None
        assert self.validator.config == self.config

    def test_setup_test_environment(self):
        """テスト環境セットアップのテスト"""
        # セットアップの実行
        self.validator.setup_test_environment()

        # 基本的なセットアップが完了していることを確認
        # 具体的な検証は各テストメソッドで実行

    def test_gui_imports_validation(self):
        """GUIインポート検証のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()

        # テストの実行
        self.validator.test_gui_imports()

        # 検証結果があることを確認
        assert len(self.validator.validation_results) > 0

        # 最新の結果を確認
        latest_result = self.validator.validation_results[-1]
        assert latest_result.test_name == "test_gui_imports"

    def test_qt_widget_creation_validation(self):
        """Qtウィジェット作成検証のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()

        # テストの実行
        self.validator.test_qt_widget_creation()

        # 検証結果があることを確認
        assert len(self.validator.validation_results) > 0

        # 最新の結果を確認
        latest_result = self.validator.validation_results[-1]
        assert latest_result.test_name == "test_qt_widget_creation"

    def test_main_window_instantiation_validation(self):
        """メインウィンドウインスタンス化検証のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()

        # テストの実行
        self.validator.test_main_window_instantiation()

        # 検証結果があることを確認
        assert len(self.validator.validation_results) > 0

        # 最新の結果を確認
        latest_result = self.validator.validation_results[-1]
        assert latest_result.test_name == "test_main_window_instantiation"

    def test_gui_component_interfaces_validation(self):
        """GUIコンポーネントインターフェース検証のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()

        # テストの実行
        self.validator.test_gui_component_interfaces()

        # 検証結果があることを確認
        assert len(self.validator.validation_results) > 0

        # 最新の結果を確認
        latest_result = self.validator.validation_results[-1]
        assert latest_result.test_name == "test_gui_component_interfaces"

    def test_gui_error_handling_validation(self):
        """GUIエラーハンドリング検証のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()

        # テストの実行
        self.validator.test_gui_error_handling()

        # 検証結果があることを確認
        assert len(self.validator.validation_results) > 0

        # 最新の結果を確認
        latest_result = self.validator.validation_results[-1]
        assert latest_result.test_name == "test_gui_error_handling"

    def test_gui_performance_basics_validation(self):
        """GUI基本パフォーマンス検証のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()

        # テストの実行
        self.validator.test_gui_performance_basics()

        # 検証結果があることを確認
        assert len(self.validator.validation_results) > 0

        # 最新の結果を確認
        latest_result = self.validator.validation_results[-1]
        assert latest_result.test_name == "test_gui_performance_basics"

    def test_run_validation_integration(self):
        """統合検証実行のテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()

        # 特定のテストメソッドのみを実行
        test_methods = ["test_gui_imports", "test_qt_widget_creation"]

        results = self.validator.run_validation(test_methods)

        # 結果の確認
        assert len(results) == len(test_methods)

        for result in results:
            assert result.test_name in test_methods
            assert isinstance(result.execution_time, float)
            assert isinstance(result.success, bool)

    def test_error_handling_during_validation(self):
        """検証中のエラーハンドリングテスト"""
        # テスト環境のセットアップ
        self.validator.setup_test_environment()

        # 意図的にエラーを発生させるテストメソッドを追加
        def failing_test():
            raise Exception("テスト用エラー")

        # テストメソッドを動的に追加
        self.validator.test_failing_test = failing_test

        # 失敗するテストを実行
        results = self.validator.run_validation(["test_failing_test"])

        # 結果の確認
        assert len(results) == 1
        assert not results[0].success
        assert "テスト用エラー" in results[0].error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
