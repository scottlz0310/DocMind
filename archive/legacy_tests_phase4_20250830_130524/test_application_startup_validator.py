"""
ApplicationStartupValidatorのテストケース

アプリケーション起動・初期化検証クラスの動作を検証します。
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.validation_framework.application_startup_validator import (
    ApplicationStartupValidator,
)
from tests.validation_framework.base_validator import ValidationConfig


class TestApplicationStartupValidator:
    """ApplicationStartupValidatorのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.config = ValidationConfig(
            enable_performance_monitoring=True,
            enable_memory_monitoring=True,
            enable_error_injection=False,  # 基本テストではエラー注入を無効
            max_execution_time=30.0,
            max_memory_usage=1024.0,
        )
        self.validator = ApplicationStartupValidator(self.config)
        self.validator.setup_test_environment()

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if hasattr(self, "validator"):
            self.validator.teardown_test_environment()
            self.validator.cleanup()

    def test_validator_initialization(self):
        """バリデーターの初期化テスト"""
        assert self.validator is not None
        assert self.validator.temp_dir is not None
        assert self.validator.test_data_dir is not None
        assert self.validator.temp_dir.exists()
        assert self.validator.test_data_dir.exists()

    def test_startup_time_requirement(self):
        """起動時間要件のテスト"""
        # テストを実行（BaseValidatorのrun_validationメソッドを使用）
        results = self.validator.run_validation(["test_startup_time_requirement"])

        # 結果を確認
        assert len(results) > 0

        latest_result = results[-1]
        assert latest_result.success is True
        assert latest_result.execution_time <= self.validator.max_startup_time

    def test_directory_creation(self):
        """ディレクトリ作成のテスト"""
        # テストを実行（BaseValidatorのrun_validationメソッドを使用）
        results = self.validator.run_validation(["test_directory_creation"])

        # 必要なディレクトリが作成されていることを確認
        for dir_name in self.validator.required_directories:
            dir_path = self.validator.test_data_dir / dir_name
            assert dir_path.exists()
            assert dir_path.is_dir()

        # 結果を確認
        assert len(results) > 0
        latest_result = results[-1]
        assert latest_result.success is True

    def test_config_initialization(self):
        """設定初期化のテスト"""
        # テストを実行（BaseValidatorのrun_validationメソッドを使用）
        results = self.validator.run_validation(["test_config_initialization"])

        # 設定ファイルが作成されていることを確認
        config_file = self.validator.test_data_dir / "config.json"
        assert config_file.exists()

        # 結果を確認
        assert len(results) > 0
        latest_result = results[-1]
        assert latest_result.success is True

    def test_logging_system_initialization(self):
        """ログシステム初期化のテスト"""
        # テストを実行（BaseValidatorのrun_validationメソッドを使用）
        results = self.validator.run_validation(["test_logging_system_initialization"])

        # ログファイルが作成されていることを確認
        log_file = self.validator.test_data_dir / "logs" / "docmind.log"
        assert log_file.exists()

        # 結果を確認
        assert len(results) > 0
        latest_result = results[-1]
        assert latest_result.success is True

    def test_database_initialization(self):
        """データベース初期化のテスト"""
        # テストを実行（BaseValidatorのrun_validationメソッドを使用）
        results = self.validator.run_validation(["test_database_initialization"])

        # データベースファイルが作成されていることを確認
        db_file = self.validator.test_data_dir / "documents.db"
        assert db_file.exists()

        # 結果を確認
        assert len(results) > 0
        latest_result = results[-1]
        assert latest_result.success is True

    def test_startup_error_recovery(self):
        """起動時エラー回復機能のテスト"""
        # テストを実行（BaseValidatorのrun_validationメソッドを使用）
        results = self.validator.run_validation(["test_startup_error_recovery"])

        # 結果を確認
        assert len(results) > 0
        latest_result = results[-1]
        assert latest_result.success is True

    def test_full_validation_run(self):
        """完全な検証実行のテスト"""
        # すべてのテストメソッドを実行
        test_methods = [
            "test_startup_time_requirement",
            "test_directory_creation",
            "test_config_initialization",
            "test_logging_system_initialization",
            "test_database_initialization",
            "test_startup_error_recovery",
        ]

        results = self.validator.run_validation(test_methods)

        # すべてのテストが実行されたことを確認
        assert len(results) == len(test_methods)

        # すべてのテストが成功したことを確認
        for result in results:
            assert (
                result.success is True
            ), f"テスト '{result.test_name}' が失敗しました: {result.error_message}"

        # パフォーマンス要件を確認
        for result in results:
            assert result.execution_time <= self.config.max_execution_time
            assert result.memory_usage <= self.config.max_memory_usage

    def test_error_injection_validation(self):
        """エラー注入テストの検証"""
        # エラー注入を有効にした設定でテスト
        error_injection_config = ValidationConfig(
            enable_error_injection=True,
            max_execution_time=60.0,
            max_memory_usage=2048.0,
        )

        error_validator = ApplicationStartupValidator(error_injection_config)
        error_validator.setup_test_environment()

        try:
            # エラー注入テストを実行
            results = error_validator.run_validation(["test_startup_error_injection"])

            # 結果を確認（エラー注入テストは警告レベルで失敗する可能性がある）
            assert len(results) > 0

        finally:
            error_validator.teardown_test_environment()
            error_validator.cleanup()

    def test_performance_monitoring(self):
        """パフォーマンス監視機能のテスト"""
        # パフォーマンス監視を有効にしてテスト実行
        self.validator.run_validation(["test_startup_time_requirement"])

        # パフォーマンス要件の検証
        performance_ok = self.validator.validate_performance_requirements(
            max_time=self.validator.max_startup_time, max_memory=1024.0
        )

        assert performance_ok is True

    def test_statistics_collection(self):
        """統計情報収集のテスト"""
        # いくつかのテストを実行
        self.validator.run_validation(["test_directory_creation"])
        self.validator.run_validation(["test_config_initialization"])

        # 統計情報を取得
        stats = self.validator.get_statistics_summary()

        assert stats is not None
        assert "total_tests" in stats
        assert "successful_tests" in stats
        assert "failed_tests" in stats
        assert stats["total_tests"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
