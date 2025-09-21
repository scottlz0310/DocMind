"""
ログ設定モジュール

アプリケーション全体のログ設定を管理し、
統一されたログフォーマットとレベル制御を提供します。
"""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """
    アプリケーションのログ設定を初期化

    Args:
        level: ログレベル(DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: ログファイルのパス(省略時はデフォルトパスを使用)
        max_bytes: ログファイルの最大サイズ(バイト)
        backup_count: 保持するバックアップファイル数
        enable_console: コンソール出力を有効にするか
        enable_file: ファイル出力を有効にするか
    """

    # ログレベルの設定
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 改善されたログフォーマットの定義(インデックス再構築機能対応)
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソール用の簡潔なフォーマット
    console_formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 既存のハンドラーをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # コンソールハンドラーの追加
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # ファイルハンドラーの追加
    if enable_file:
        if log_file is None:
            # デフォルトのログファイルパス
            log_file = os.path.join("docmind_data", "logs", "docmind.log")

        # ログディレクトリの作成
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # ローテーティングファイルハンドラーの追加
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # インデックス再構築専用のログファイル
        rebuild_log_file = log_path.parent / "index_rebuild.log"
        rebuild_handler = logging.handlers.RotatingFileHandler(
            filename=str(rebuild_log_file),
            maxBytes=max_bytes // 2,  # 5MB
            backupCount=3,
            encoding="utf-8",
        )
        rebuild_handler.setLevel(logging.DEBUG)
        rebuild_handler.setFormatter(detailed_formatter)

        # インデックス再構築関連のロガーにのみ追加
        rebuild_logger = logging.getLogger("src.gui.main_window")
        rebuild_logger.addHandler(rebuild_handler)

        thread_manager_logger = logging.getLogger("src.core.thread_manager")
        thread_manager_logger.addHandler(rebuild_handler)

        timeout_manager_logger = logging.getLogger("src.core.rebuild_timeout_manager")
        timeout_manager_logger.addHandler(rebuild_handler)

    # 初期ログメッセージ
    logger = logging.getLogger(__name__)
    logger.info(f"ログシステムを初期化しました - レベル: {level}")
    if enable_file and log_file:
        logger.info(f"メインログファイル: {log_file}")
        if "rebuild_log_file" in locals():
            logger.info(f"インデックス再構築ログファイル: {rebuild_log_file}")


def setup_logging_from_config(config) -> None:
    """
    設定オブジェクトからログ設定を初期化

    Args:
        config: 設定管理オブジェクト
    """
    setup_logging(
        level=config.get_log_level(),
        log_file=config.get_log_file_path(),
        enable_console=config.is_console_logging_enabled(),
        enable_file=config.is_file_logging_enabled(),
    )


def reconfigure_logging(
    level: str | None = None,
    enable_console: bool | None = None,
    enable_file: bool | None = None,
) -> None:
    """
    実行時にログ設定を再構成

    Args:
        level: 新しいログレベル
        enable_console: コンソール出力の有効/無効
        enable_file: ファイル出力の有効/無効
    """
    root_logger = logging.getLogger()

    # ログレベルの変更
    if level is not None:
        log_level = getattr(logging, level.upper(), logging.INFO)
        root_logger.setLevel(log_level)

        # 全ハンドラーのレベルも更新
        for handler in root_logger.handlers:
            handler.setLevel(log_level)

    # ハンドラーの有効/無効切り替え
    if enable_console is not None or enable_file is not None:
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.handlers.RotatingFileHandler
            ):
                # コンソールハンドラー
                if enable_console is False:
                    root_logger.removeHandler(handler)
            elif isinstance(handler, logging.handlers.RotatingFileHandler):
                # ファイルハンドラー
                if enable_file is False:
                    root_logger.removeHandler(handler)

        # 必要に応じて新しいハンドラーを追加
        if enable_console is True and not any(
            isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler)
            for h in root_logger.handlers
        ):
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            console_handler = logging.StreamHandler()
            console_handler.setLevel(root_logger.level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得

    Args:
        name: ロガー名(通常は__name__を使用)

    Returns:
        ロガーインスタンス
    """
    return logging.getLogger(name)


class LoggerMixin:
    """
    ログ機能を提供するミックスインクラス

    このクラスを継承することで、簡単にログ機能を追加できます。
    """

    @property
    def logger(self) -> logging.Logger:
        """
        クラス専用のロガーを取得

        Returns:
            ロガーインスタンス
        """
        if not hasattr(self, "_logger"):
            self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        return self._logger

    def log_rebuild_operation(self, operation: str, thread_id: str = "", **kwargs) -> None:
        """
        インデックス再構築操作の詳細ログを記録

        Args:
            operation: 操作名
            thread_id: スレッドID
            **kwargs: 追加情報
        """
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"🔧 REBUILD [{operation}]"

        if thread_id:
            message += f" | Thread: {thread_id}"

        if extra_info:
            message += f" | {extra_info}"

        self.logger.info(message)

    def log_rebuild_progress(self, thread_id: str, current: int, total: int, message: str = "") -> None:
        """
        インデックス再構築の進捗ログを記録

        Args:
            thread_id: スレッドID
            current: 現在の処理数
            total: 総処理数
            message: 追加メッセージ
        """
        percentage = (current / total * 100) if total > 0 else 0
        progress_message = f"📊 PROGRESS [{thread_id}] {current:,}/{total:,} ({percentage:.1f}%)"

        if message:
            progress_message += f" | {message}"

        self.logger.debug(progress_message)

    def log_rebuild_error(self, thread_id: str, error_type: str, error_message: str, **context) -> None:
        """
        インデックス再構築エラーの詳細ログを記録

        Args:
            thread_id: スレッドID
            error_type: エラータイプ
            error_message: エラーメッセージ
            **context: エラーコンテキスト
        """
        context_info = " | ".join([f"{k}={v}" for k, v in context.items()])
        error_log = f"❌ ERROR [{thread_id}] Type: {error_type} | Message: {error_message}"

        if context_info:
            error_log += f" | Context: {context_info}"

        self.logger.error(error_log)

    def log_rebuild_timeout(self, thread_id: str, timeout_minutes: int, **details) -> None:
        """
        インデックス再構築タイムアウトの詳細ログを記録

        Args:
            thread_id: スレッドID
            timeout_minutes: タイムアウト時間(分)
            **details: 詳細情報
        """
        detail_info = " | ".join([f"{k}={v}" for k, v in details.items()])
        timeout_log = f"⏰ TIMEOUT [{thread_id}] Duration: {timeout_minutes}分"

        if detail_info:
            timeout_log += f" | {detail_info}"

        self.logger.warning(timeout_log)
