"""
包括的エラーハンドリングユーティリティ

アプリケーション全体のエラーハンドリング、回復メカニズム、
診断情報収集を提供します。
"""

import json
import platform
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

import psutil

from .exceptions import DocMindException
from .logging_config import get_logger


class ErrorHandler:
    """
    包括的エラーハンドリングクラス

    エラーの捕捉、ログ記録、回復処理、診断情報収集を統合的に管理します。
    """

    def __init__(self, data_dir: str = "docmind_data"):
        """
        エラーハンドラーを初期化

        Args:
            data_dir: データディレクトリのパス
        """
        self.logger = get_logger(__name__)
        self.data_dir = Path(data_dir)
        self.error_reports_dir = self.data_dir / "error_reports"
        self.error_reports_dir.mkdir(parents=True, exist_ok=True)

        # エラー回復ハンドラーの登録
        self._recovery_handlers: dict[type[Exception], Callable] = {}

        # システム情報キャッシュ
        self._system_info: dict[str, Any] | None = None

    def register_recovery_handler(
        self, exception_type: type[Exception], handler: Callable
    ) -> None:
        """
        特定の例外タイプに対する回復ハンドラーを登録

        Args:
            exception_type: 例外の型
            handler: 回復処理を行う関数
        """
        self._recovery_handlers[exception_type] = handler
        self.logger.debug(f"回復ハンドラーを登録: {exception_type.__name__}")

    def handle_exception(
        self,
        exc: Exception,
        context: str = "",
        user_message: str = None,
        attempt_recovery: bool = True,
    ) -> bool:
        """
        例外を包括的に処理

        Args:
            exc: 発生した例外
            context: エラーが発生したコンテキスト
            user_message: ユーザー向けメッセージ
            attempt_recovery: 回復を試行するか

        Returns:
            回復に成功した場合True、失敗した場合False
        """
        # エラー情報の収集
        error_info = self._collect_error_info(exc, context)

        # ログに記録
        self._log_error(exc, error_info, context)

        # 診断レポートの生成
        self._generate_error_report(exc, error_info, context)

        # ユーザー向けメッセージの表示
        if user_message:
            self._show_user_message(user_message, exc)

        # 回復処理の試行
        recovery_success = False
        if attempt_recovery:
            recovery_success = self._attempt_recovery(exc, error_info)

        return recovery_success

    def _collect_error_info(self, exc: Exception, context: str) -> dict[str, Any]:
        """
        エラーに関する詳細情報を収集

        Args:
            exc: 発生した例外
            context: エラーコンテキスト

        Returns:
            エラー情報の辞書
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "context": context,
            "traceback": traceback.format_exc(),
            "system_info": self._get_system_info(),
            "application_state": self._get_application_state(),
        }

        # DocMind固有の例外情報を追加
        if isinstance(exc, DocMindException):
            error_info["docmind_details"] = {
                "details": exc.details,
                "custom_attributes": {
                    attr: getattr(exc, attr)
                    for attr in dir(exc)
                    if not attr.startswith("_")
                    and attr not in ["args", "message", "details"]
                },
            }

        return error_info

    def _get_system_info(self) -> dict[str, Any]:
        """
        システム情報を取得（キャッシュ付き）

        Returns:
            システム情報の辞書
        """
        if self._system_info is None:
            try:
                self._system_info = {
                    "platform": platform.platform(),
                    "python_version": sys.version,
                    "cpu_count": psutil.cpu_count(),
                    "memory_total": psutil.virtual_memory().total,
                    "disk_usage": {
                        "total": (
                            psutil.disk_usage("/").total
                            if platform.system() != "Windows"
                            else psutil.disk_usage("C:").total
                        ),
                        "free": (
                            psutil.disk_usage("/").free
                            if platform.system() != "Windows"
                            else psutil.disk_usage("C:").free
                        ),
                    },
                }
            except Exception as e:
                self.logger.warning(f"システム情報の取得に失敗: {e}")
                self._system_info = {"error": "システム情報取得失敗"}

        return self._system_info

    def _get_application_state(self) -> dict[str, Any]:
        """
        アプリケーションの現在の状態を取得

        Returns:
            アプリケーション状態の辞書
        """
        try:
            # メモリ使用量
            process = psutil.Process()
            memory_info = process.memory_info()

            # データディレクトリの状態
            data_dir_exists = self.data_dir.exists()
            data_dir_size = 0
            if data_dir_exists:
                try:
                    data_dir_size = sum(
                        f.stat().st_size
                        for f in self.data_dir.rglob("*")
                        if f.is_file()
                    )
                except Exception:
                    data_dir_size = -1

            return {
                "memory_usage": {"rss": memory_info.rss, "vms": memory_info.vms},
                "data_directory": {
                    "exists": data_dir_exists,
                    "size": data_dir_size,
                    "path": str(self.data_dir),
                },
                "thread_count": process.num_threads(),
            }
        except Exception as e:
            self.logger.warning(f"アプリケーション状態の取得に失敗: {e}")
            return {"error": "アプリケーション状態取得失敗"}

    def _log_error(
        self, exc: Exception, error_info: dict[str, Any], context: str
    ) -> None:
        """
        エラーをログに記録

        Args:
            exc: 発生した例外
            error_info: エラー情報
            context: エラーコンテキスト
        """
        log_message = f"エラーが発生しました - コンテキスト: {context}"

        if isinstance(exc, DocMindException):
            self.logger.error(
                log_message,
                exc_info=exc,
                extra={
                    "error_type": type(exc).__name__,
                    "context": context,
                    "details": exc.details,
                },
            )
        else:
            self.logger.error(
                log_message,
                exc_info=exc,
                extra={"error_type": type(exc).__name__, "context": context},
            )

    def _generate_error_report(
        self, exc: Exception, error_info: dict[str, Any], context: str
    ) -> Path:
        """
        詳細なエラーレポートを生成

        Args:
            exc: 発生した例外
            error_info: エラー情報
            context: エラーコンテキスト

        Returns:
            生成されたレポートファイルのパス
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"error_report_{timestamp}_{type(exc).__name__}.json"
        report_path = self.error_reports_dir / report_filename

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(error_info, f, ensure_ascii=False, indent=2, default=str)

            self.logger.info(f"エラーレポートを生成: {report_path}")
        except Exception as e:
            self.logger.error(f"エラーレポートの生成に失敗: {e}")

        return report_path

    def _show_user_message(self, message: str, exc: Exception) -> None:
        """
        ユーザーにエラーメッセージを表示

        Args:
            message: 表示するメッセージ
            exc: 発生した例外
        """
        # ここではログに記録するだけ（GUIでの表示は別途実装）
        self.logger.info(f"ユーザーメッセージ: {message}")

    def _attempt_recovery(self, exc: Exception, error_info: dict[str, Any]) -> bool:
        """
        エラーからの回復を試行

        Args:
            exc: 発生した例外
            error_info: エラー情報

        Returns:
            回復に成功した場合True
        """
        # 登録された回復ハンドラーを試行
        for exc_type, handler in self._recovery_handlers.items():
            if isinstance(exc, exc_type):
                try:
                    self.logger.info(f"回復処理を試行: {exc_type.__name__}")
                    result = handler(exc, error_info)
                    if result:
                        self.logger.info("回復処理が成功しました")
                        return True
                except Exception as recovery_exc:
                    self.logger.error(f"回復処理中にエラーが発生: {recovery_exc}")

        # デフォルトの回復処理
        return self._default_recovery(exc, error_info)

    def _default_recovery(self, exc: Exception, error_info: dict[str, Any]) -> bool:
        """
        デフォルトの回復処理

        Args:
            exc: 発生した例外
            error_info: エラー情報

        Returns:
            回復に成功した場合True
        """
        # 基本的な回復処理（ディレクトリの作成など）
        try:
            # データディレクトリが存在しない場合は作成
            if not self.data_dir.exists():
                self.data_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info("データディレクトリを作成しました")
                return True

            # ログディレクトリが存在しない場合は作成
            log_dir = self.data_dir / "logs"
            if not log_dir.exists():
                log_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info("ログディレクトリを作成しました")
                return True

        except Exception as recovery_exc:
            self.logger.error(f"デフォルト回復処理に失敗: {recovery_exc}")

        return False


def handle_exceptions(
    context: str = "",
    user_message: str = None,
    attempt_recovery: bool = True,
    reraise: bool = False,
):
    """
    例外処理デコレータ

    Args:
        context: エラーコンテキスト
        user_message: ユーザー向けメッセージ
        attempt_recovery: 回復を試行するか
        reraise: 例外を再発生させるか
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # グローバルエラーハンドラーを使用
                error_handler = get_global_error_handler()
                recovery_success = error_handler.handle_exception(
                    e,
                    context or f"{func.__module__}.{func.__name__}",
                    user_message,
                    attempt_recovery,
                )

                if reraise or not recovery_success:
                    raise

                return None

        return wrapper

    return decorator


# グローバルエラーハンドラーインスタンス
_global_error_handler: ErrorHandler | None = None


def get_global_error_handler() -> ErrorHandler:
    """
    グローバルエラーハンドラーを取得

    Returns:
        エラーハンドラーインスタンス
    """
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def setup_global_exception_handler():
    """
    グローバル例外ハンドラーを設定
    """

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Ctrl+Cは通常通り処理
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error_handler = get_global_error_handler()
        error_handler.handle_exception(
            exc_value,
            "未処理例外",
            "予期しないエラーが発生しました。アプリケーションを再起動してください。",
            attempt_recovery=True,
        )

    sys.excepthook = handle_exception
