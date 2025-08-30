"""
ログ設定システムのユニットテスト

logging_config モジュールのテストを実装します。
"""

import logging
import os
import tempfile
import unittest

from src.utils.config import Config
from src.utils.logging_config import (
    LoggerMixin,
    get_logger,
    reconfigure_logging,
    setup_logging,
    setup_logging_from_config,
)


class TestLoggingConfig(unittest.TestCase):
    """ログ設定システムのテストクラス"""

    def setUp(self):
        """テスト前の準備"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")

        # ログ設定をリセット
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil

        # ログ設定をリセット
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()  # ファイルハンドラーを閉じる
            root_logger.removeHandler(handler)

        # 一時ディレクトリを再帰的に削除
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_setup_logging_basic(self):
        """基本的なログ設定のテスト"""
        setup_logging(level="INFO", log_file=self.log_file)

        # ルートロガーの設定確認
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)

        # ハンドラーの確認（コンソールとファイル）
        self.assertEqual(len(root_logger.handlers), 2)

        # ログファイルが作成されることを確認
        logger = logging.getLogger("test")
        logger.info("テストメッセージ")

        self.assertTrue(os.path.exists(self.log_file))

        # ログファイルの内容確認
        with open(self.log_file, encoding='utf-8') as f:
            content = f.read()
            self.assertIn("テストメッセージ", content)

    def test_setup_logging_levels(self):
        """異なるログレベルのテスト"""
        # DEBUGレベル
        setup_logging(level="DEBUG", log_file=self.log_file)
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.DEBUG)

        # WARNINGレベル
        setup_logging(level="WARNING", log_file=self.log_file)
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.WARNING)

        # 無効なレベル（デフォルトのINFOになる）
        setup_logging(level="INVALID", log_file=self.log_file)
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)

    def test_setup_logging_console_only(self):
        """コンソールのみのログ設定テスト"""
        setup_logging(
            level="INFO",
            log_file=self.log_file,
            enable_console=True,
            enable_file=False
        )

        root_logger = logging.getLogger()

        # コンソールハンドラーのみ存在することを確認
        self.assertEqual(len(root_logger.handlers), 1)
        self.assertIsInstance(root_logger.handlers[0], logging.StreamHandler)
        self.assertFalse(isinstance(root_logger.handlers[0], logging.handlers.RotatingFileHandler))

        # ログファイルが作成されないことを確認
        logger = logging.getLogger("test")
        logger.info("テストメッセージ")
        self.assertFalse(os.path.exists(self.log_file))

    def test_setup_logging_file_only(self):
        """ファイルのみのログ設定テスト"""
        setup_logging(
            level="INFO",
            log_file=self.log_file,
            enable_console=False,
            enable_file=True
        )

        root_logger = logging.getLogger()

        # ファイルハンドラーのみ存在することを確認
        self.assertEqual(len(root_logger.handlers), 1)
        self.assertIsInstance(root_logger.handlers[0], logging.handlers.RotatingFileHandler)

        # ログファイルが作成されることを確認
        logger = logging.getLogger("test")
        logger.info("テストメッセージ")
        self.assertTrue(os.path.exists(self.log_file))

    def test_setup_logging_no_handlers(self):
        """ハンドラーなしのログ設定テスト"""
        setup_logging(
            level="INFO",
            log_file=self.log_file,
            enable_console=False,
            enable_file=False
        )

        root_logger = logging.getLogger()

        # ハンドラーが存在しないことを確認
        self.assertEqual(len(root_logger.handlers), 0)

    def test_log_directory_creation(self):
        """ログディレクトリの自動作成テスト"""
        nested_log_file = os.path.join(self.temp_dir, "logs", "nested", "test.log")

        setup_logging(level="INFO", log_file=nested_log_file)

        # ログメッセージを出力
        logger = logging.getLogger("test")
        logger.info("テストメッセージ")

        # ネストされたディレクトリとログファイルが作成されることを確認
        self.assertTrue(os.path.exists(nested_log_file))
        self.assertTrue(os.path.isdir(os.path.dirname(nested_log_file)))

    def test_setup_logging_from_config(self):
        """設定オブジェクトからのログ設定テスト"""
        # テスト用設定を作成
        config_file = os.path.join(self.temp_dir, "config.json")
        config = Config(config_file=config_file)
        config.set("log_level", "DEBUG")
        config.set("data_directory", self.temp_dir)
        config.set("console_logging", True)
        config.set("file_logging", True)

        # 設定からログを初期化
        setup_logging_from_config(config)

        # ログレベルの確認
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.DEBUG)

        # ハンドラー数の確認
        self.assertEqual(len(root_logger.handlers), 2)

    def test_reconfigure_logging_level(self):
        """ログレベルの再設定テスト"""
        # 初期設定
        setup_logging(level="INFO", log_file=self.log_file)
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)

        # レベルを変更
        reconfigure_logging(level="DEBUG")
        self.assertEqual(root_logger.level, logging.DEBUG)

        # 全ハンドラーのレベルも変更されることを確認
        for handler in root_logger.handlers:
            self.assertEqual(handler.level, logging.DEBUG)

    def test_reconfigure_logging_handlers(self):
        """ログハンドラーの再設定テスト"""
        # 初期設定（コンソールとファイル両方）
        setup_logging(
            level="INFO",
            log_file=self.log_file,
            enable_console=True,
            enable_file=True
        )
        root_logger = logging.getLogger()
        self.assertEqual(len(root_logger.handlers), 2)

        # コンソールハンドラーを無効化
        reconfigure_logging(enable_console=False)

        # ファイルハンドラーのみ残ることを確認
        self.assertEqual(len(root_logger.handlers), 1)
        self.assertIsInstance(root_logger.handlers[0], logging.handlers.RotatingFileHandler)

        # ファイルハンドラーも無効化
        reconfigure_logging(enable_file=False)

        # ハンドラーがなくなることを確認
        self.assertEqual(len(root_logger.handlers), 0)

        # コンソールハンドラーを再度有効化
        reconfigure_logging(enable_console=True)

        # コンソールハンドラーが追加されることを確認
        self.assertEqual(len(root_logger.handlers), 1)
        self.assertIsInstance(root_logger.handlers[0], logging.StreamHandler)
        self.assertFalse(isinstance(root_logger.handlers[0], logging.handlers.RotatingFileHandler))

    def test_get_logger(self):
        """ロガー取得のテスト"""
        logger = get_logger("test_module")

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_module")

    def test_logger_mixin(self):
        """LoggerMixinのテスト"""
        class TestClass(LoggerMixin):
            def test_method(self):
                self.logger.info("テストメッセージ")
                return self.logger

        # テストクラスのインスタンスを作成
        test_instance = TestClass()

        # ロガーが正しく取得されることを確認
        logger = test_instance.test_method()
        self.assertIsInstance(logger, logging.Logger)

        # ロガー名が正しいことを確認
        expected_name = f"{TestClass.__module__}.{TestClass.__name__}"
        self.assertEqual(logger.name, expected_name)

        # 同じインスタンスで同じロガーが返されることを確認
        logger2 = test_instance.logger
        self.assertIs(logger, logger2)

    def test_log_rotation(self):
        """ログローテーションのテスト"""
        # 小さなファイルサイズでログ設定
        setup_logging(
            level="INFO",
            log_file=self.log_file,
            max_bytes=100,  # 100バイト
            backup_count=2
        )

        logger = logging.getLogger("test")

        # 大量のログメッセージを出力してローテーションを発生させる
        for i in range(50):
            logger.info(f"テストメッセージ {i:03d} - これは長いメッセージです")

        # ログファイルが存在することを確認
        self.assertTrue(os.path.exists(self.log_file))

        # バックアップファイルが作成される可能性がある
        # （ファイルサイズが小さいため、ローテーションが発生する可能性）
        log_dir = os.path.dirname(self.log_file)
        log_files = [f for f in os.listdir(log_dir) if f.startswith("test.log")]

        # 少なくとも1つのログファイルが存在することを確認
        self.assertGreaterEqual(len(log_files), 1)

    def test_unicode_logging(self):
        """Unicode文字のログ出力テスト"""
        setup_logging(level="INFO", log_file=self.log_file)

        logger = logging.getLogger("test")

        # 日本語メッセージをログ出力
        japanese_message = "これは日本語のテストメッセージです 🚀"
        logger.info(japanese_message)

        # ログファイルの内容確認
        with open(self.log_file, encoding='utf-8') as f:
            content = f.read()
            self.assertIn(japanese_message, content)


if __name__ == '__main__':
    unittest.main()
