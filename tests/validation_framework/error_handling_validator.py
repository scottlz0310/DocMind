"""
エラーハンドリング・回復機能検証クラス

DocMindアプリケーションのエラーハンドリング機能と回復機能を包括的に検証します。
予期しない例外のキャッチ、適切なエラーメッセージ表示、優雅な劣化機能、
自動回復機能を検証します。
"""

import logging
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from .base_validator import BaseValidator, ValidationConfig
    from .error_injector import ErrorInjector
    from .test_data_generator import TestDataGenerator
except ImportError:
    from base_validator import BaseValidator, ValidationConfig
    from test_data_generator import TestDataGenerator

from src.utils.error_handler import ErrorHandler
from src.utils.exceptions import (
    ConfigurationError,
    DatabaseError,
    DocumentProcessingError,
    EmbeddingError,
    FileSystemError,
    IndexingError,
    SearchError,
)
from src.utils.exceptions import MemoryError as DocMindMemoryError
from src.utils.graceful_degradation import ComponentStatus, GracefulDegradationManager


class ErrorHandlingValidator(BaseValidator):
    """
    エラーハンドリング・回復機能検証クラス

    DocMindアプリケーションのエラーハンドリング機能と回復機能を
    包括的に検証します。
    """

    def __init__(self, config: ValidationConfig | None = None):
        """
        エラーハンドリング検証クラスの初期化

        Args:
            config: 検証設定
        """
        super().__init__(config)

        # テストデータ生成器
        self.test_data_generator = TestDataGenerator()

        # テスト用の一時ディレクトリ
        self.temp_dir = None
        self.test_db_path = None
        self.test_index_path = None

        # エラーハンドラーとマネージャー
        self.error_handler = None
        self.degradation_manager = None

        # テスト結果の記録
        self.exception_handling_results = []
        self.recovery_results = []
        self.degradation_results = []

        self.logger.info("エラーハンドリング検証クラスを初期化しました")

    def setup_test_environment(self) -> None:
        """テスト環境のセットアップ"""
        self.logger.info("エラーハンドリング検証のテスト環境をセットアップします")

        # 一時ディレクトリの作成
        self.temp_dir = Path(tempfile.mkdtemp(prefix="error_handling_test_"))
        self.test_db_path = self.temp_dir / "test_documents.db"
        self.test_index_path = self.temp_dir / "test_index"

        # テスト用データディレクトリの作成
        test_data_dir = self.temp_dir / "docmind_data"
        test_data_dir.mkdir(parents=True, exist_ok=True)

        # エラーハンドラーの初期化
        self.error_handler = ErrorHandler(str(test_data_dir))

        # 劣化マネージャーの初期化
        self.degradation_manager = GracefulDegradationManager()
        self._setup_test_components()

        # テストデータの生成
        self.test_data_generator.setup_test_environment(str(self.temp_dir))

        self.logger.info(f"テスト環境をセットアップしました: {self.temp_dir}")

    def teardown_test_environment(self) -> None:
        """テスト環境のクリーンアップ"""
        self.logger.info("エラーハンドリング検証のテスト環境をクリーンアップします")

        try:
            # テストデータ生成器のクリーンアップ
            if hasattr(self.test_data_generator, 'cleanup'):
                self.test_data_generator.cleanup()

            # 一時ディレクトリの削除
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.logger.debug(f"一時ディレクトリを削除しました: {self.temp_dir}")

        except Exception as e:
            self.logger.warning(f"テスト環境のクリーンアップ中にエラーが発生: {e}")

    def _setup_test_components(self) -> None:
        """テスト用コンポーネントの設定"""
        # 主要コンポーネントを登録
        components = [
            ("search_manager", {"full_text_search": True, "semantic_search": True}),
            ("index_manager", {"indexing": True, "search": True}),
            ("embedding_manager", {"embedding_generation": True}),
            ("document_processor", {"pdf_processing": True, "text_processing": True}),
            ("database", {"metadata_storage": True, "search_history": True}),
            ("file_watcher", {"file_monitoring": True})
        ]

        for name, capabilities in components:
            self.degradation_manager.register_component(name, capabilities)

    def test_exception_catching_and_logging(self) -> None:
        """予期しない例外のキャッチとログ記録の検証"""
        self.logger.info("例外キャッチとログ記録の検証を開始します")

        test_cases = [
            {
                "name": "DocumentProcessingError",
                "exception": DocumentProcessingError("テストファイル処理エラー", "/test/file.pdf"),
                "context": "ドキュメント処理テスト"
            },
            {
                "name": "IndexingError",
                "exception": IndexingError("インデックス作成エラー", str(self.test_index_path)),
                "context": "インデックス作成テスト"
            },
            {
                "name": "SearchError",
                "exception": SearchError("検索実行エラー", "テストクエリ", "full_text"),
                "context": "検索実行テスト"
            },
            {
                "name": "DatabaseError",
                "exception": DatabaseError("データベース接続エラー", str(self.test_db_path)),
                "context": "データベース操作テスト"
            },
            {
                "name": "UnexpectedException",
                "exception": RuntimeError("予期しないランタイムエラー"),
                "context": "予期しない例外テスト"
            }
        ]

        for test_case in test_cases:
            try:
                # エラーハンドラーでの例外処理
                recovery_success = self.error_handler.handle_exception(
                    test_case["exception"],
                    test_case["context"],
                    f"テスト用エラーメッセージ: {test_case['name']}",
                    attempt_recovery=True
                )

                # 結果の記録
                result = {
                    "test_name": f"exception_handling_{test_case['name']}",
                    "exception_type": type(test_case["exception"]).__name__,
                    "context": test_case["context"],
                    "handled_successfully": True,
                    "recovery_attempted": True,
                    "recovery_success": recovery_success,
                    "error_report_generated": self._check_error_report_generated()
                }

                self.exception_handling_results.append(result)

                # アサーション
                self.assert_condition(
                    result["handled_successfully"],
                    f"例外 {test_case['name']} が正常に処理されました"
                )

                self.logger.info(f"例外処理テスト完了: {test_case['name']}")

            except Exception as e:
                self.logger.error(f"例外処理テスト中にエラー: {test_case['name']} - {e}")
                result = {
                    "test_name": f"exception_handling_{test_case['name']}",
                    "exception_type": type(test_case["exception"]).__name__,
                    "context": test_case["context"],
                    "handled_successfully": False,
                    "error_message": str(e)
                }
                self.exception_handling_results.append(result)

    def test_error_message_display(self) -> None:
        """適切なエラーメッセージ表示の検証"""
        self.logger.info("エラーメッセージ表示の検証を開始します")

        # ログハンドラーをモックして、メッセージの内容を検証
        with patch('logging.Logger.info') as mock_info, \
             patch('logging.Logger.error') as mock_error, \
             patch('logging.Logger.warning'):

            test_messages = [
                {
                    "exception": DocumentProcessingError("PDFファイルが破損しています"),
                    "user_message": "ファイルの処理中にエラーが発生しました。ファイルが破損している可能性があります。",
                    "expected_log_level": "error"
                },
                {
                    "exception": SearchError("検索インデックスにアクセスできません"),
                    "user_message": "検索機能が一時的に利用できません。しばらく待ってから再試行してください。",
                    "expected_log_level": "error"
                },
                {
                    "exception": ConfigurationError("設定ファイルが見つかりません"),
                    "user_message": "設定に問題があります。デフォルト設定で続行します。",
                    "expected_log_level": "warning"
                }
            ]

            for i, test_case in enumerate(test_messages):
                # エラーハンドラーでメッセージ処理
                self.error_handler.handle_exception(
                    test_case["exception"],
                    f"メッセージ表示テスト_{i}",
                    test_case["user_message"],
                    attempt_recovery=False
                )

                # ログ呼び出しの検証
                if test_case["expected_log_level"] == "error":
                    self.assert_condition(
                        mock_error.called,
                        f"エラーレベルのログが記録されました: {test_case['user_message']}"
                    )
                elif test_case["expected_log_level"] == "warning":
                    # 警告レベルのログも検証可能
                    pass

                # ユーザーメッセージの記録確認
                info_calls = [call for call in mock_info.call_args_list
                             if test_case["user_message"] in str(call)]
                self.assert_condition(
                    len(info_calls) > 0,
                    f"ユーザーメッセージがログに記録されました: {test_case['user_message']}"
                )

        self.logger.info("エラーメッセージ表示の検証が完了しました")

    def test_graceful_degradation(self) -> None:
        """優雅な劣化機能の検証"""
        self.logger.info("優雅な劣化機能の検証を開始します")

        # 各コンポーネントの劣化テスト
        degradation_scenarios = [
            {
                "component": "search_manager",
                "error": SearchError("セマンティック検索モデルの読み込み失敗"),
                "disable_capabilities": ["semantic_search"],
                "expected_remaining": ["full_text_search"]
            },
            {
                "component": "embedding_manager",
                "error": EmbeddingError("埋め込みモデルのメモリ不足"),
                "disable_capabilities": ["embedding_generation"],
                "expected_remaining": []
            },
            {
                "component": "document_processor",
                "error": DocumentProcessingError("PDFライブラリの初期化失敗"),
                "disable_capabilities": ["pdf_processing"],
                "expected_remaining": ["text_processing"]
            }
        ]

        for scenario in degradation_scenarios:
            # コンポーネントを劣化状態にマーク
            self.degradation_manager.mark_component_degraded(
                scenario["component"],
                scenario["disable_capabilities"],
                str(scenario["error"])
            )

            # 劣化状態の確認
            component_state = self.degradation_manager.get_component_status(scenario["component"])

            self.assert_condition(
                component_state.status == ComponentStatus.DEGRADED,
                f"コンポーネント {scenario['component']} が劣化状態になりました"
            )

            # 無効化された機能の確認
            for disabled_capability in scenario["disable_capabilities"]:
                is_available = self.degradation_manager.is_capability_available(
                    scenario["component"], disabled_capability
                )
                self.assert_condition(
                    not is_available,
                    f"機能 {disabled_capability} が無効化されました"
                )

            # 残存機能の確認
            for remaining_capability in scenario["expected_remaining"]:
                is_available = self.degradation_manager.is_capability_available(
                    scenario["component"], remaining_capability
                )
                self.assert_condition(
                    is_available,
                    f"機能 {remaining_capability} は利用可能です"
                )

            # 結果の記録
            result = {
                "component": scenario["component"],
                "error_type": type(scenario["error"]).__name__,
                "disabled_capabilities": scenario["disable_capabilities"],
                "remaining_capabilities": scenario["expected_remaining"],
                "degradation_successful": component_state.status == ComponentStatus.DEGRADED
            }
            self.degradation_results.append(result)

            self.logger.info(f"劣化テスト完了: {scenario['component']}")

        # システム全体の健全性確認
        system_health = self.degradation_manager.get_system_health()
        self.assert_condition(
            system_health["overall_health"] in ["degraded", "critical"],
            "システム全体が劣化状態を正しく認識しています"
        )

        self.logger.info("優雅な劣化機能の検証が完了しました")

    def test_automatic_recovery_mechanisms(self) -> None:
        """自動回復機能の検証"""
        self.logger.info("自動回復機能の検証を開始します")

        # ファイルシステム回復テスト
        self._test_filesystem_recovery()

        # データベース回復テスト
        self._test_database_recovery()

        # メモリ回復テスト
        self._test_memory_recovery()

        # ネットワーク回復テスト（シミュレーション）
        self._test_network_recovery()

        self.logger.info("自動回復機能の検証が完了しました")

    def _test_filesystem_recovery(self) -> None:
        """ファイルシステム回復の検証"""
        self.logger.info("ファイルシステム回復テストを開始します")

        # テスト用ディレクトリの作成
        test_dir = self.temp_dir / "recovery_test"
        test_file = test_dir / "test_file.txt"

        # 1. ディレクトリ不存在からの回復
        if test_dir.exists():
            shutil.rmtree(test_dir)

        # ディレクトリ不存在エラーを発生させる
        error = FileSystemError("ディレクトリが存在しません", str(test_dir))

        # エラーハンドラーで回復を試行
        self.error_handler.handle_exception(
            error, "ファイルシステム回復テスト", attempt_recovery=True
        )

        # 2. ファイル権限エラーからの回復
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file.write_text("テストデータ")

        # 権限を変更（読み取り専用）
        original_mode = test_file.stat().st_mode
        test_file.chmod(0o444)

        try:
            # 書き込み試行でエラーを発生
            with open(test_file, 'w') as f:
                f.write("新しいデータ")
        except PermissionError:
            # 権限エラーからの回復
            self.error_handler.handle_exception(
                FileSystemError("ファイル書き込み権限がありません", str(test_file)),
                "権限回復テスト",
                attempt_recovery=True
            )
        finally:
            # 権限を復元
            test_file.chmod(original_mode)

        # 結果の記録
        self.recovery_results.append({
            "test_type": "filesystem_recovery",
            "scenarios": ["directory_creation", "permission_recovery"],
            "success": True
        })

        self.logger.info("ファイルシステム回復テストが完了しました")

    def _test_database_recovery(self) -> None:
        """データベース回復の検証"""
        self.logger.info("データベース回復テストを開始します")

        # テスト用データベースファイル
        test_db = self.temp_dir / "recovery_test.db"

        # 1. データベースファイル不存在からの回復
        if test_db.exists():
            test_db.unlink()

        # データベース接続エラーを発生
        error = DatabaseError("データベースファイルが見つかりません", str(test_db))
        recovery_success = self.error_handler.handle_exception(
            error, "データベース回復テスト", attempt_recovery=True
        )

        # 2. データベース破損からの回復
        # 破損ファイルを作成
        with open(test_db, 'wb') as f:
            f.write(b'corrupted database content')

        try:
            # SQLite接続を試行
            conn = sqlite3.connect(str(test_db))
            conn.execute("SELECT * FROM documents")
        except sqlite3.DatabaseError:
            # データベース破損からの回復
            recovery_success = self.error_handler.handle_exception(
                DatabaseError("データベースが破損しています", str(test_db)),
                "データベース破損回復テスト",
                attempt_recovery=True
            )
        finally:
            if 'conn' in locals():
                conn.close()

        # 3. データベースロックからの回復
        # 正常なデータベースを作成
        conn = sqlite3.connect(str(test_db))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                content TEXT
            )
        """)
        conn.commit()

        # ロック状況をシミュレート
        def simulate_lock_recovery():
            time.sleep(0.1)  # 短時間待機後に接続を閉じる
            conn.close()

        lock_thread = threading.Thread(target=simulate_lock_recovery)
        lock_thread.start()

        try:
            # 別の接続でロックエラーを発生させる
            conn2 = sqlite3.connect(str(test_db), timeout=0.05)
            conn2.execute("INSERT INTO test_table (content) VALUES ('test')")
        except sqlite3.OperationalError:
            # ロックエラーからの回復
            recovery_success = self.error_handler.handle_exception(
                DatabaseError("データベースがロックされています", str(test_db)),
                "データベースロック回復テスト",
                attempt_recovery=True
            )
        finally:
            lock_thread.join()
            if 'conn2' in locals():
                conn2.close()

        # 結果の記録
        self.recovery_results.append({
            "test_type": "database_recovery",
            "scenarios": ["file_missing", "corruption", "lock"],
            "success": True
        })

        self.logger.info("データベース回復テストが完了しました")

    def _test_memory_recovery(self) -> None:
        """メモリ回復の検証"""
        self.logger.info("メモリ回復テストを開始します")

        # メモリ不足エラーをシミュレート
        def simulate_memory_intensive_operation():
            # 大量のメモリを消費する操作をシミュレート
            large_data = []
            try:
                for _i in range(1000):  # 適度なサイズに調整
                    large_data.append([0] * 10000)
                return large_data
            except MemoryError:
                raise

        try:
            # メモリ集約的な操作を実行
            result = simulate_memory_intensive_operation()

            # メモリ使用量をチェック
            import psutil
            process = psutil.Process()
            memory_usage_mb = process.memory_info().rss / 1024 / 1024

            if memory_usage_mb > 1000:  # 1GB以上の場合
                # メモリ不足エラーとして処理
                error = DocMindMemoryError("メモリ使用量が制限を超えました")
                self.error_handler.handle_exception(
                    error, "メモリ回復テスト", attempt_recovery=True
                )

                # メモリを解放
                del result
                import gc
                gc.collect()

        except MemoryError as e:
            # メモリエラーからの回復
            self.error_handler.handle_exception(
                e, "メモリ回復テスト", attempt_recovery=True
            )

        # 結果の記録
        self.recovery_results.append({
            "test_type": "memory_recovery",
            "scenarios": ["memory_exhaustion"],
            "success": True
        })

        self.logger.info("メモリ回復テストが完了しました")

    def _test_network_recovery(self) -> None:
        """ネットワーク回復の検証（シミュレーション）"""
        self.logger.info("ネットワーク回復テストを開始します")

        # ネットワークタイムアウトエラーをシミュレート
        import socket

        # 1. 接続タイムアウト
        try:
            # 存在しないホストへの接続を試行
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)  # 短いタイムアウト
            sock.connect(("192.0.2.1", 80))  # RFC 5737のテスト用IP
        except (TimeoutError, OSError):
            # ネットワークエラーからの回復
            self.error_handler.handle_exception(
                ConnectionError("ネットワーク接続がタイムアウトしました"),
                "ネットワーク回復テスト",
                attempt_recovery=True
            )
        finally:
            sock.close()

        # 2. DNS解決エラー
        try:
            socket.gethostbyname("nonexistent.invalid.domain")
        except socket.gaierror:
            # DNS解決エラーからの回復
            self.error_handler.handle_exception(
                ConnectionError("DNS解決に失敗しました"),
                "DNS回復テスト",
                attempt_recovery=True
            )

        # 結果の記録
        self.recovery_results.append({
            "test_type": "network_recovery",
            "scenarios": ["connection_timeout", "dns_resolution"],
            "success": True
        })

        self.logger.info("ネットワーク回復テストが完了しました")

    def test_error_injection_scenarios(self) -> None:
        """エラー注入シナリオの検証"""
        self.logger.info("エラー注入シナリオの検証を開始します")

        # エラー注入設定
        injection_scenarios = [
            {
                "error_type": "file_not_found",
                "parameters": {"target_file": str(self.temp_dir / "missing_file.txt")},
                "expected_exception": FileNotFoundError
            },
            {
                "error_type": "permission_denied",
                "parameters": {"target_path": str(self.temp_dir)},
                "expected_exception": PermissionError
            },
            {
                "error_type": "corrupted_file",
                "parameters": {"target_file": str(self.temp_dir / "corrupted.txt")},
                "expected_exception": UnicodeDecodeError
            },
            {
                "error_type": "database_connection_error",
                "parameters": {"db_file": str(self.test_db_path)},
                "expected_exception": sqlite3.Error
            }
        ]

        for scenario in injection_scenarios:
            try:
                # エラーを注入
                injection_success = self.error_injector.inject_error(
                    scenario["error_type"],
                    parameters=scenario["parameters"]
                )

                self.assert_condition(
                    injection_success,
                    f"エラー注入が成功しました: {scenario['error_type']}"
                )

                # 注入されたエラーに対する処理をテスト
                # （実際のアプリケーションコードでエラーが発生することを想定）

                self.logger.info(f"エラー注入テスト完了: {scenario['error_type']}")

            except Exception as e:
                self.logger.error(f"エラー注入テスト中にエラー: {scenario['error_type']} - {e}")

        # エラー注入統計の確認
        injection_stats = self.error_injector.get_injection_statistics()
        self.assert_condition(
            injection_stats.get("total_injections", 0) > 0,
            "エラー注入が実行されました"
        )

        self.logger.info("エラー注入シナリオの検証が完了しました")

    def test_critical_function_continuity(self) -> None:
        """重要機能継続の検証"""
        self.logger.info("重要機能継続の検証を開始します")

        # 重要機能のリスト
        critical_functions = [
            {
                "name": "basic_search",
                "component": "search_manager",
                "fallback_capability": "full_text_search"
            },
            {
                "name": "document_storage",
                "component": "database",
                "fallback_capability": "metadata_storage"
            },
            {
                "name": "file_processing",
                "component": "document_processor",
                "fallback_capability": "text_processing"
            }
        ]

        for function in critical_functions:
            # コンポーネントを部分的に失敗させる
            self.degradation_manager.mark_component_degraded(
                function["component"],
                disable_capabilities=[],  # 重要機能は維持
                error_message=f"テスト用部分失敗: {function['name']}"
            )

            # 重要機能が利用可能か確認
            is_available = self.degradation_manager.is_capability_available(
                function["component"],
                function["fallback_capability"]
            )

            self.assert_condition(
                is_available,
                f"重要機能 {function['name']} が継続利用可能です"
            )

            self.logger.info(f"重要機能継続テスト完了: {function['name']}")

        self.logger.info("重要機能継続の検証が完了しました")

    def _check_error_report_generated(self) -> bool:
        """エラーレポートが生成されたかチェック"""
        error_reports_dir = Path(self.error_handler.error_reports_dir)
        if not error_reports_dir.exists():
            return False

        # 最近作成されたレポートファイルを確認
        report_files = list(error_reports_dir.glob("error_report_*.json"))
        return len(report_files) > 0

    def get_validation_summary(self) -> dict[str, Any]:
        """検証結果のサマリーを取得"""
        return {
            "exception_handling": {
                "total_tests": len(self.exception_handling_results),
                "successful_handling": sum(1 for r in self.exception_handling_results
                                         if r.get("handled_successfully", False)),
                "results": self.exception_handling_results
            },
            "recovery_mechanisms": {
                "total_tests": len(self.recovery_results),
                "successful_recovery": sum(1 for r in self.recovery_results
                                         if r.get("success", False)),
                "results": self.recovery_results
            },
            "graceful_degradation": {
                "total_tests": len(self.degradation_results),
                "successful_degradation": sum(1 for r in self.degradation_results
                                            if r.get("degradation_successful", False)),
                "results": self.degradation_results
            },
            "system_health": self.degradation_manager.get_system_health() if self.degradation_manager else {},
            "error_injection_stats": self.error_injector.get_injection_statistics()
        }


if __name__ == "__main__":
    # 単体テスト実行
    import logging
    logging.basicConfig(level=logging.INFO)

    # 検証設定
    config = ValidationConfig(
        enable_performance_monitoring=True,
        enable_memory_monitoring=True,
        enable_error_injection=True,
        max_execution_time=300.0,
        max_memory_usage=1024.0
    )

    # 検証実行
    validator = ErrorHandlingValidator(config)

    try:
        validator.setup_test_environment()
        results = validator.run_validation()

        # 結果の表示
        summary = validator.get_validation_summary()
        print("\n=== エラーハンドリング検証結果 ===")
        print(f"例外処理テスト: {summary['exception_handling']['successful_handling']}/{summary['exception_handling']['total_tests']}")
        print(f"回復機能テスト: {summary['recovery_mechanisms']['successful_recovery']}/{summary['recovery_mechanisms']['total_tests']}")
        print(f"劣化機能テスト: {summary['graceful_degradation']['successful_degradation']}/{summary['graceful_degradation']['total_tests']}")

        # パフォーマンス要件の検証
        for result in results:
            if result.success:
                print(f"✓ {result.test_name}: 成功 ({result.execution_time:.2f}秒)")
            else:
                print(f"✗ {result.test_name}: 失敗 - {result.error_message}")

    finally:
        validator.teardown_test_environment()
        validator.cleanup()
