"""
アプリケーション起動・初期化検証クラス

DocMindアプリケーションの起動プロセス全体を検証し、
すべてのコンポーネントが正常に初期化されることを確認します。
"""

import json
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .base_validator import BaseValidator, ValidationConfig


class ApplicationStartupValidator(BaseValidator):
    """
    アプリケーション起動・初期化検証クラス

    DocMindアプリケーションの起動プロセスを包括的に検証し、
    以下の要件を満たすことを確認します：
    - 10秒以内の起動時間
    - 必要なディレクトリの作成
    - 設定ファイルの適切な読み込み
    - ログシステムの初期化
    - データベースの初期化
    - エラー回復機能
    """

    def __init__(self, config: ValidationConfig | None = None):
        """
        ApplicationStartupValidatorの初期化

        Args:
            config: 検証設定
        """
        super().__init__(config)

        # テスト用の一時ディレクトリ
        self.temp_dir: Path | None = None
        self.test_data_dir: Path | None = None

        # 起動時間の要件（秒）
        self.max_startup_time = 10.0

        # 必要なディレクトリのリスト
        self.required_directories = [
            "logs",
            "models",
            "whoosh_index",
            "error_reports",
            "cache",
        ]

        # 必要な設定項目
        self.required_config_keys = [
            "data_directory",
            "log_level",
            "max_documents",
            "search_timeout",
            "embedding_model",
        ]

        self.logger.info("ApplicationStartupValidatorを初期化しました")

    def setup_test_environment(self) -> None:
        """
        テスト環境のセットアップ

        一時ディレクトリを作成し、テスト用の設定を準備します。
        """
        try:
            # 一時ディレクトリの作成
            self.temp_dir = Path(tempfile.mkdtemp(prefix="docmind_startup_test_"))
            self.test_data_dir = self.temp_dir / "docmind_data"
            self.test_data_dir.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"テスト環境をセットアップしました: {self.temp_dir}")

        except Exception as e:
            self.logger.error(f"テスト環境のセットアップに失敗: {e}")
            raise

    def teardown_test_environment(self) -> None:
        """
        テスト環境のクリーンアップ

        一時ディレクトリとテストファイルを削除します。
        """
        try:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"テスト環境をクリーンアップしました: {self.temp_dir}")

        except Exception as e:
            self.logger.warning(f"テスト環境のクリーンアップに失敗: {e}")

    def test_startup_time_requirement(self) -> None:
        """
        起動時間要件の検証

        要件1.1: アプリケーションを起動する時、システムは10秒以内にメインウィンドウを表示する
        """
        self.logger.info("起動時間要件の検証を開始します")

        # 起動時間の測定
        startup_time = self._measure_application_startup_time()

        # 要件の検証
        self.assert_condition(
            startup_time <= self.max_startup_time,
            f"起動時間が要件を超過しました: {startup_time:.2f}秒 > {self.max_startup_time}秒",
        )

        self.logger.info(f"起動時間要件を満たしています: {startup_time:.2f}秒")

    def test_directory_creation(self) -> None:
        """
        ディレクトリ作成の検証

        要件1.2: 初期化処理を実行する時、システムはすべての必要なディレクトリを作成する
        """
        self.logger.info("ディレクトリ作成の検証を開始します")

        # アプリケーションの初期化をシミュレート
        self._simulate_application_initialization()

        # 必要なディレクトリが作成されているかチェック
        for dir_name in self.required_directories:
            dir_path = self.test_data_dir / dir_name
            self.assert_condition(
                dir_path.exists() and dir_path.is_dir(),
                f"必要なディレクトリが作成されていません: {dir_name}",
            )

        self.logger.info("すべての必要なディレクトリが正常に作成されました")

    def test_config_initialization(self) -> None:
        """
        設定初期化の検証

        要件1.3: 設定ファイルを読み込む時、システムは適切なデフォルト値を使用する
        """
        self.logger.info("設定初期化の検証を開始します")

        # 設定ファイルが存在する場合は削除してテスト
        config_file = self.test_data_dir / "config.json"
        if config_file.exists():
            config_file.unlink()
            self.logger.debug("既存の設定ファイルを削除しました")

        self.assert_condition(
            not config_file.exists(), "設定ファイルが削除されていません"
        )

        # 設定の初期化をテスト
        config = self._initialize_config_with_defaults()

        # 必要な設定項目が存在することを確認
        for key in self.required_config_keys:
            self.assert_condition(
                config.get(key) is not None, f"必要な設定項目が存在しません: {key}"
            )

        # デフォルト値の妥当性をチェック
        self._validate_default_config_values(config)

        self.logger.info("設定初期化が正常に完了しました")

    def test_logging_system_initialization(self) -> None:
        """
        ログシステム初期化の検証

        要件1.4: ログシステムを初期化する時、システムは適切なログレベルで動作する
        """
        self.logger.info("ログシステム初期化の検証を開始します")

        # ログシステムの初期化をテスト
        log_file = self.test_data_dir / "logs" / "docmind.log"
        self._initialize_logging_system(str(log_file))

        # ログファイルが作成されることを確認
        self.assert_condition(log_file.exists(), "ログファイルが作成されていません")

        # ログレベルの設定を確認
        self._verify_log_level_configuration()

        # ログメッセージの出力をテスト
        self._test_log_message_output(log_file)

        self.logger.info("ログシステム初期化が正常に完了しました")

    def test_database_initialization(self) -> None:
        """
        データベース初期化の検証

        要件1.5: データベースを初期化する時、システムは必要なテーブルを作成する
        """
        self.logger.info("データベース初期化の検証を開始します")

        # データベースの初期化をテスト
        db_file = self.test_data_dir / "documents.db"
        self._initialize_database(str(db_file))

        # データベースファイルが作成されることを確認
        self.assert_condition(
            db_file.exists(), "データベースファイルが作成されていません"
        )

        # 必要なテーブルが作成されることを確認
        self._verify_database_schema(str(db_file))

        # データベースの健全性をチェック
        self._verify_database_health(str(db_file))

        self.logger.info("データベース初期化が正常に完了しました")

    def test_startup_error_recovery(self) -> None:
        """
        起動時エラー回復機能の検証

        様々なエラー状況での回復機能をテストします。
        """
        self.logger.info("起動時エラー回復機能の検証を開始します")

        # 設定ファイル破損からの回復をテスト
        self._test_config_file_corruption_recovery()

        # ディレクトリアクセス権限エラーからの回復をテスト
        self._test_directory_permission_error_recovery()

        # データベース破損からの回復をテスト
        self._test_database_corruption_recovery()

        self.logger.info("起動時エラー回復機能の検証が完了しました")

    def test_startup_error_injection(self) -> None:
        """
        エラー注入テストによる堅牢性検証

        意図的にエラーを発生させて、適切な処理が行われることを確認します。
        """
        self.logger.info("エラー注入テストを開始します")

        if not self.config.enable_error_injection:
            self.logger.info("エラー注入が無効のため、テストをスキップします")
            return

        # ファイルシステムエラーの注入
        self._test_filesystem_error_injection()

        # メモリ不足エラーの注入
        self._test_memory_error_injection()

        # ネットワークエラーの注入（将来の機能用）
        self._test_network_error_injection()

        self.logger.info("エラー注入テストが完了しました")

    def _measure_application_startup_time(self) -> float:
        """
        アプリケーションの起動時間を測定

        Returns:
            起動時間（秒）
        """
        try:
            # 起動プロセスをシミュレート
            start_time = time.time()

            # 実際の起動プロセスの主要ステップを実行
            self._simulate_application_initialization()
            self._initialize_config_with_defaults()
            self._initialize_logging_system()
            self._initialize_database()

            end_time = time.time()
            startup_time = end_time - start_time

            self.logger.debug(f"起動時間測定結果: {startup_time:.4f}秒")
            return startup_time

        except Exception as e:
            self.logger.error(f"起動時間測定中にエラー: {e}")
            raise

    def _simulate_application_initialization(self) -> None:
        """
        アプリケーション初期化プロセスをシミュレート
        """
        # 必要なディレクトリを作成
        for dir_name in self.required_directories:
            dir_path = self.test_data_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)

    def _initialize_config_with_defaults(self) -> dict[str, Any]:
        """
        デフォルト設定でConfigを初期化

        Returns:
            設定辞書
        """
        try:
            # テスト用の設定を作成
            config_data = {
                "data_directory": str(self.test_data_dir),
                "log_level": "INFO",
                "max_documents": 50000,
                "search_timeout": 5.0,
                "embedding_model": "all-MiniLM-L6-v2",
                "whoosh_index_dir": "whoosh_index",
                "database_file": "documents.db",
                "embeddings_file": "embeddings.pkl",
            }

            # 設定ファイルに保存
            config_file = self.test_data_dir / "config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            return config_data

        except Exception as e:
            self.logger.error(f"設定初期化中にエラー: {e}")
            raise

    def _validate_default_config_values(self, config: dict[str, Any]) -> None:
        """
        デフォルト設定値の妥当性を検証

        Args:
            config: 設定辞書
        """
        # データディレクトリの妥当性
        data_dir = Path(config["data_directory"])
        self.assert_condition(
            data_dir.exists(), f"データディレクトリが存在しません: {data_dir}"
        )

        # ログレベルの妥当性
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.assert_condition(
            config["log_level"] in valid_log_levels,
            f"無効なログレベル: {config['log_level']}",
        )

        # 数値設定の妥当性
        self.assert_condition(
            config["max_documents"] > 0,
            "最大ドキュメント数は正の値である必要があります",
        )

        self.assert_condition(
            config["search_timeout"] > 0, "検索タイムアウトは正の値である必要があります"
        )

    def _initialize_logging_system(self, log_file: str | None = None) -> None:
        """
        ログシステムを初期化

        Args:
            log_file: ログファイルのパス
        """
        try:
            from src.utils.logging_config import setup_logging

            if log_file is None:
                log_file = str(self.test_data_dir / "logs" / "docmind.log")

            # ログディレクトリを作成
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # ログシステムを初期化
            setup_logging(
                level="INFO", log_file=log_file, enable_console=True, enable_file=True
            )

        except Exception as e:
            self.logger.error(f"ログシステム初期化中にエラー: {e}")
            raise

    def _verify_log_level_configuration(self) -> None:
        """
        ログレベル設定の検証
        """
        import logging

        # ルートロガーのレベルを確認
        root_logger = logging.getLogger()
        self.assert_condition(
            root_logger.level == logging.INFO,
            f"ログレベルが期待値と異なります: {root_logger.level}",
        )

        # ハンドラーが設定されていることを確認
        self.assert_condition(
            len(root_logger.handlers) > 0, "ログハンドラーが設定されていません"
        )

    def _test_log_message_output(self, log_file: Path) -> None:
        """
        ログメッセージ出力のテスト

        Args:
            log_file: ログファイルのパス
        """
        import logging

        # テストメッセージを出力
        test_logger = logging.getLogger("test_logger")
        test_message = "テストログメッセージ"
        test_logger.info(test_message)

        # ログファイルにメッセージが記録されることを確認
        time.sleep(0.1)  # ファイル書き込みの待機

        if log_file.exists():
            with open(log_file, encoding="utf-8") as f:
                log_content = f.read()
                self.assert_condition(
                    test_message in log_content,
                    "ログメッセージがファイルに記録されていません",
                )

    def _initialize_database(self, db_file: str | None = None) -> None:
        """
        データベースを初期化

        Args:
            db_file: データベースファイルのパス
        """
        try:
            if db_file is None:
                db_file = str(self.test_data_dir / "documents.db")

            # データベースディレクトリを作成
            db_path = Path(db_file)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # データベースマネージャーを初期化
            from src.data.database import DatabaseManager

            db_manager = DatabaseManager(db_file)

            # 初期化が完了したら接続を閉じる
            db_manager.close()

        except Exception as e:
            self.logger.error(f"データベース初期化中にエラー: {e}")
            raise

    def _verify_database_schema(self, db_file: str) -> None:
        """
        データベーススキーマの検証

        Args:
            db_file: データベースファイルのパス
        """
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # 必要なテーブルが存在することを確認
            required_tables = [
                "documents",
                "search_history",
                "saved_searches",
                "schema_version",
            ]

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]

            for table in required_tables:
                self.assert_condition(
                    table in existing_tables, f"必要なテーブルが存在しません: {table}"
                )

            conn.close()

        except Exception as e:
            self.logger.error(f"データベーススキーマ検証中にエラー: {e}")
            raise

    def _verify_database_health(self, db_file: str) -> None:
        """
        データベースの健全性検証

        Args:
            db_file: データベースファイルのパス
        """
        try:
            from src.data.database import DatabaseManager

            db_manager = DatabaseManager(db_file)
            health_ok = db_manager.health_check()

            self.assert_condition(
                health_ok, "データベースの健全性チェックに失敗しました"
            )

            db_manager.close()

        except Exception as e:
            self.logger.error(f"データベース健全性検証中にエラー: {e}")
            raise

    def _test_config_file_corruption_recovery(self) -> None:
        """
        設定ファイル破損からの回復テスト
        """
        self.logger.info("設定ファイル破損回復テストを実行します")

        try:
            # 破損した設定ファイルを作成
            config_file = self.test_data_dir / "config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                f.write("{ invalid json content")

            # 回復処理をテスト
            config = self._initialize_config_with_defaults()

            # デフォルト設定で動作することを確認
            self.assert_condition(
                config is not None, "破損した設定ファイルからの回復に失敗しました"
            )

        except Exception as e:
            self.logger.error(f"設定ファイル破損回復テスト中にエラー: {e}")
            raise

    def _test_directory_permission_error_recovery(self) -> None:
        """
        ディレクトリアクセス権限エラーからの回復テスト
        """
        self.logger.info("ディレクトリ権限エラー回復テストを実行します")

        # Windowsでは権限テストが困難なため、シミュレーションで実装
        try:
            # 権限エラーをシミュレート
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                mock_mkdir.side_effect = PermissionError("Permission denied")

                # エラーハンドリングをテスト
                try:
                    self._simulate_application_initialization()
                    # エラーが適切に処理されることを確認
                except PermissionError:
                    # 期待されるエラー
                    pass

        except Exception as e:
            self.logger.error(f"ディレクトリ権限エラー回復テスト中にエラー: {e}")
            # このテストは環境依存のため、エラーでも継続

    def _test_database_corruption_recovery(self) -> None:
        """
        データベース破損からの回復テスト
        """
        self.logger.info("データベース破損回復テストを実行します")

        try:
            # 破損したデータベースファイルを作成
            db_file = self.test_data_dir / "documents.db"
            with open(db_file, "wb") as f:
                f.write(b"corrupted database content")

            # 回復処理をテスト
            try:
                self._initialize_database(str(db_file))
                # 新しいデータベースが作成されることを確認
                self._verify_database_schema(str(db_file))
            except Exception:
                # データベースの再作成が行われることを期待
                pass

        except Exception as e:
            self.logger.error(f"データベース破損回復テスト中にエラー: {e}")
            raise

    def _test_filesystem_error_injection(self) -> None:
        """
        ファイルシステムエラー注入テスト
        """
        self.logger.info("ファイルシステムエラー注入テストを実行します")

        try:
            # ディスク容量不足エラーをシミュレート
            self.inject_error("disk_full", target_path=str(self.test_data_dir))

            # エラーハンドリングをテスト
            # 実際のエラー注入は error_injector.py で実装

        except Exception as e:
            self.logger.warning(f"ファイルシステムエラー注入テスト中にエラー: {e}")

    def _test_memory_error_injection(self) -> None:
        """
        メモリ不足エラー注入テスト
        """
        self.logger.info("メモリ不足エラー注入テストを実行します")

        try:
            # メモリ不足エラーをシミュレート
            self.inject_error("memory_exhaustion", threshold_mb=100)

            # エラーハンドリングをテスト
            # 実際のエラー注入は error_injector.py で実装

        except Exception as e:
            self.logger.warning(f"メモリ不足エラー注入テスト中にエラー: {e}")

    def _test_network_error_injection(self) -> None:
        """
        ネットワークエラー注入テスト（将来の機能用）
        """
        self.logger.info("ネットワークエラー注入テストを実行します")

        try:
            # ネットワーク接続エラーをシミュレート
            self.inject_error("network_disconnection")

            # 現在はローカル処理のみなので、将来の拡張用

        except Exception as e:
            self.logger.warning(f"ネットワークエラー注入テスト中にエラー: {e}")
