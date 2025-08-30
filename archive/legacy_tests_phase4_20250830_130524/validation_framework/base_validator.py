"""
基盤検証クラス

包括的検証のベースとなるフレームワーククラスを提供します。
すべての検証クラスはこのクラスを継承して実装されます。
"""

import logging
import time
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

try:
    from .error_injector import ErrorInjector
    from .memory_monitor import MemoryMonitor
    from .performance_monitor import PerformanceMonitor
    from .statistics_collector import StatisticsCollector
except ImportError:
    # 相対インポートが失敗した場合の絶対インポート
    from error_injector import ErrorInjector
    from memory_monitor import MemoryMonitor
    from performance_monitor import PerformanceMonitor
    from statistics_collector import StatisticsCollector


@dataclass
class ValidationResult:
    """検証結果を格納するデータクラス"""

    test_name: str
    success: bool
    execution_time: float
    memory_usage: float
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationConfig:
    """検証設定を格納するデータクラス"""

    enable_performance_monitoring: bool = True
    enable_memory_monitoring: bool = True
    enable_error_injection: bool = False
    max_execution_time: float = 300.0  # 5分
    max_memory_usage: float = 2048.0  # 2GB (MB単位)
    log_level: str = "INFO"
    output_directory: str = "validation_results"


class BaseValidator(ABC):
    """
    包括的検証のベースクラス

    すべての検証クラスはこのクラスを継承し、
    共通の検証機能とインターフェースを提供します。
    """

    def __init__(self, config: ValidationConfig | None = None):
        """
        基盤検証クラスの初期化

        Args:
            config: 検証設定。Noneの場合はデフォルト設定を使用
        """
        self.config = config or ValidationConfig()
        self.logger = self._setup_logger()

        # 監視・測定コンポーネントの初期化
        self.performance_monitor = PerformanceMonitor()
        self.memory_monitor = MemoryMonitor()
        self.error_injector = ErrorInjector()
        self.statistics_collector = StatisticsCollector()

        # 検証結果の保存
        self.validation_results: list[ValidationResult] = []
        self.current_test_name: str | None = None

        self.logger.info(f"{self.__class__.__name__}を初期化しました")

    def _setup_logger(self) -> logging.Logger:
        """ロガーの設定"""
        logger = logging.getLogger(f"validation.{self.__class__.__name__}")
        logger.setLevel(getattr(logging, self.config.log_level))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def run_validation(
        self, test_methods: list[str] | None = None
    ) -> list[ValidationResult]:
        """
        検証の実行

        Args:
            test_methods: 実行するテストメソッド名のリスト。
                         Noneの場合は'test_'で始まるすべてのメソッドを実行

        Returns:
            検証結果のリスト
        """
        self.logger.info("検証を開始します")

        # 実行するテストメソッドの決定
        if test_methods is None:
            test_methods = [
                method
                for method in dir(self)
                if method.startswith("test_") and callable(getattr(self, method))
            ]

        # 各テストメソッドの実行
        for method_name in test_methods:
            self._run_single_test(method_name)

        self.logger.info(
            f"検証が完了しました。実行テスト数: {len(self.validation_results)}"
        )
        return self.validation_results

    def _run_single_test(self, method_name: str) -> ValidationResult:
        """
        単一テストの実行

        Args:
            method_name: 実行するテストメソッド名

        Returns:
            テスト結果
        """
        self.current_test_name = method_name
        self.logger.info(f"テスト '{method_name}' を開始します")

        # パフォーマンス・メモリ監視の開始
        if self.config.enable_performance_monitoring:
            self.performance_monitor.start_monitoring()

        if self.config.enable_memory_monitoring:
            self.memory_monitor.start_monitoring()

        start_time = time.time()
        result = None

        try:
            # テストメソッドの実行
            method = getattr(self, method_name)
            method()

            # 成功時の結果作成
            execution_time = time.time() - start_time
            memory_usage = (
                self.memory_monitor.get_peak_memory()
                if self.config.enable_memory_monitoring
                else 0.0
            )

            result = ValidationResult(
                test_name=method_name,
                success=True,
                execution_time=execution_time,
                memory_usage=memory_usage,
            )

            self.logger.info(
                f"テスト '{method_name}' が成功しました (実行時間: {execution_time:.2f}秒)"
            )

        except Exception as e:
            # 失敗時の結果作成
            execution_time = time.time() - start_time
            memory_usage = (
                self.memory_monitor.get_peak_memory()
                if self.config.enable_memory_monitoring
                else 0.0
            )

            result = ValidationResult(
                test_name=method_name,
                success=False,
                execution_time=execution_time,
                memory_usage=memory_usage,
                error_message=str(e),
                details={"traceback": traceback.format_exc()},
            )

            self.logger.error(f"テスト '{method_name}' が失敗しました: {str(e)}")

        finally:
            # 監視の停止
            if self.config.enable_performance_monitoring:
                self.performance_monitor.stop_monitoring()

            if self.config.enable_memory_monitoring:
                self.memory_monitor.stop_monitoring()

            # 統計情報の収集
            if result:
                self.statistics_collector.add_result(result)
                self.validation_results.append(result)

        return result

    def validate_performance_requirements(
        self, max_time: float, max_memory: float
    ) -> bool:
        """
        パフォーマンス要件の検証

        Args:
            max_time: 最大実行時間（秒）
            max_memory: 最大メモリ使用量（MB）

        Returns:
            要件を満たしている場合True
        """
        if not self.validation_results:
            return False

        latest_result = self.validation_results[-1]

        time_ok = latest_result.execution_time <= max_time
        memory_ok = latest_result.memory_usage <= max_memory

        if not time_ok:
            self.logger.warning(
                f"実行時間が要件を超過: {latest_result.execution_time:.2f}秒 > {max_time}秒"
            )

        if not memory_ok:
            self.logger.warning(
                f"メモリ使用量が要件を超過: {latest_result.memory_usage:.2f}MB > {max_memory}MB"
            )

        return time_ok and memory_ok

    def inject_error(self, error_type: str, **kwargs) -> None:
        """
        エラー注入の実行

        Args:
            error_type: 注入するエラーの種類
            **kwargs: エラー注入の追加パラメータ
        """
        if self.config.enable_error_injection:
            self.error_injector.inject_error(error_type, **kwargs)

    def get_statistics_summary(self) -> dict[str, Any]:
        """
        統計情報サマリーの取得

        Returns:
            統計情報の辞書
        """
        return self.statistics_collector.get_summary()

    def cleanup(self) -> None:
        """
        検証後のクリーンアップ処理

        リソースの解放や一時ファイルの削除などを行います。
        """
        self.logger.info("検証フレームワークのクリーンアップを実行します")

        # 監視コンポーネントのクリーンアップ
        self.performance_monitor.cleanup()
        self.memory_monitor.cleanup()
        self.error_injector.cleanup()

        self.logger.info("クリーンアップが完了しました")

    @abstractmethod
    def setup_test_environment(self) -> None:
        """
        テスト環境のセットアップ

        各検証クラスで実装する必要があります。
        """
        pass

    @abstractmethod
    def teardown_test_environment(self) -> None:
        """
        テスト環境のクリーンアップ

        各検証クラスで実装する必要があります。
        """
        pass

    def assert_condition(self, condition: bool, message: str) -> None:
        """
        条件のアサーション

        Args:
            condition: 検証する条件
            message: 失敗時のメッセージ

        Raises:
            AssertionError: 条件が偽の場合
        """
        if not condition:
            self.logger.error(f"アサーション失敗: {message}")
            raise AssertionError(message)

        self.logger.debug(f"アサーション成功: {message}")

    def measure_execution_time(
        self, func: Callable, *args, **kwargs
    ) -> tuple[Any, float]:
        """
        関数の実行時間を測定

        Args:
            func: 測定する関数
            *args: 関数の引数
            **kwargs: 関数のキーワード引数

        Returns:
            (関数の戻り値, 実行時間)のタプル
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time

        self.logger.debug(f"関数 {func.__name__} の実行時間: {execution_time:.4f}秒")

        return result, execution_time
