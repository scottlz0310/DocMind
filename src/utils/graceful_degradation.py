"""
優雅な劣化(Graceful Degradation)機能

コンポーネントが失敗した場合に、アプリケーション全体を停止させることなく、
機能を段階的に縮退させる仕組みを提供します。
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any

from .logging_config import get_logger


class ComponentStatus(Enum):
    """コンポーネントの状態"""

    HEALTHY = "healthy"  # 正常動作
    DEGRADED = "degraded"  # 機能制限あり
    FAILED = "failed"  # 完全に失敗
    DISABLED = "disabled"  # 無効化


@dataclass
class ComponentState:
    """コンポーネントの状態情報"""

    name: str
    status: ComponentStatus = ComponentStatus.HEALTHY
    error_message: str | None = None
    fallback_active: bool = False
    retry_count: int = 0
    max_retries: int = 3
    last_error_time: float | None = None
    capabilities: dict[str, bool] = field(default_factory=dict)


class GracefulDegradationManager:
    """
    優雅な劣化を管理するクラス

    各コンポーネントの状態を追跡し、失敗時のフォールバック処理を管理します。
    """

    def __init__(self):
        """劣化マネージャーを初期化"""
        self.logger = get_logger(__name__)
        self._components: dict[str, ComponentState] = {}
        self._fallback_handlers: dict[str, Callable] = {}
        self._health_checkers: dict[str, Callable] = {}

    def register_component(self, name: str, capabilities: dict[str, bool] = None, max_retries: int = 3) -> None:
        """
        コンポーネントを登録

        Args:
            name: コンポーネント名
            capabilities: コンポーネントの機能一覧
            max_retries: 最大リトライ回数
        """
        self._components[name] = ComponentState(name=name, capabilities=capabilities or {}, max_retries=max_retries)
        self.logger.debug(f"コンポーネントを登録: {name}")

    def register_fallback_handler(self, component_name: str, handler: Callable) -> None:
        """
        フォールバックハンドラーを登録

        Args:
            component_name: コンポーネント名
            handler: フォールバック処理を行う関数
        """
        self._fallback_handlers[component_name] = handler
        self.logger.debug(f"フォールバックハンドラーを登録: {component_name}")

    def register_health_checker(self, component_name: str, checker: Callable) -> None:
        """
        ヘルスチェッカーを登録

        Args:
            component_name: コンポーネント名
            checker: ヘルスチェックを行う関数
        """
        self._health_checkers[component_name] = checker
        self.logger.debug(f"ヘルスチェッカーを登録: {component_name}")

    def mark_component_failed(
        self,
        component_name: str,
        error: Exception,
        disable_capabilities: list[str] = None,
    ) -> bool:
        """
        コンポーネントを失敗状態にマーク

        Args:
            component_name: コンポーネント名
            error: 発生したエラー
            disable_capabilities: 無効化する機能のリスト

        Returns:
            フォールバック処理が成功した場合True
        """
        if component_name not in self._components:
            self.logger.warning(f"未登録のコンポーネント: {component_name}")
            return False

        component = self._components[component_name]
        component.status = ComponentStatus.FAILED
        component.error_message = str(error)
        component.retry_count += 1

        # 指定された機能を無効化
        if disable_capabilities:
            for capability in disable_capabilities:
                if capability in component.capabilities:
                    component.capabilities[capability] = False

        self.logger.warning(f"コンポーネント失敗: {component_name} - {error}")

        # フォールバック処理を試行
        return self._attempt_fallback(component_name, error)

    def mark_component_degraded(
        self,
        component_name: str,
        disable_capabilities: list[str] = None,
        error_message: str = None,
    ) -> None:
        """
        コンポーネントを劣化状態にマーク

        Args:
            component_name: コンポーネント名
            disable_capabilities: 無効化する機能のリスト
            error_message: エラーメッセージ
        """
        if component_name not in self._components:
            self.logger.warning(f"未登録のコンポーネント: {component_name}")
            return

        component = self._components[component_name]
        component.status = ComponentStatus.DEGRADED
        component.error_message = error_message

        # 指定された機能を無効化
        if disable_capabilities:
            for capability in disable_capabilities:
                if capability in component.capabilities:
                    component.capabilities[capability] = False

        self.logger.info(f"コンポーネント劣化: {component_name} - {error_message}")

    def mark_component_healthy(self, component_name: str) -> None:
        """
        コンポーネントを健全状態にマーク

        Args:
            component_name: コンポーネント名
        """
        if component_name not in self._components:
            # コンポーネントが未登録の場合は自動登録
            self.register_component(component_name)

        component = self._components[component_name]
        component.status = ComponentStatus.HEALTHY
        component.error_message = None
        component.fallback_active = False
        component.retry_count = 0

        # 全機能を有効化
        for capability in component.capabilities:
            component.capabilities[capability] = True

        self.logger.debug(f"コンポーネントを健全状態にマーク: {component_name}")

    def is_component_healthy(self, component_name: str) -> bool:
        """
        コンポーネントが正常かチェック

        Args:
            component_name: コンポーネント名

        Returns:
            正常な場合True
        """
        if component_name not in self._components:
            return False

        return self._components[component_name].status == ComponentStatus.HEALTHY

    def is_capability_available(self, component_name: str, capability: str) -> bool:
        """
        特定の機能が利用可能かチェック

        Args:
            component_name: コンポーネント名
            capability: 機能名

        Returns:
            利用可能な場合True
        """
        if component_name not in self._components:
            return False

        component = self._components[component_name]
        if component.status == ComponentStatus.DISABLED:
            return False

        return component.capabilities.get(capability, False)

    def get_component_status(self, component_name: str) -> ComponentState | None:
        """
        コンポーネントの状態を取得

        Args:
            component_name: コンポーネント名

        Returns:
            コンポーネントの状態
        """
        return self._components.get(component_name)

    def get_system_health(self) -> dict[str, Any]:
        """
        システム全体の健全性を取得

        Returns:
            システム健全性の情報
        """
        total_components = len(self._components)
        healthy_count = sum(1 for c in self._components.values() if c.status == ComponentStatus.HEALTHY)
        degraded_count = sum(1 for c in self._components.values() if c.status == ComponentStatus.DEGRADED)
        failed_count = sum(1 for c in self._components.values() if c.status == ComponentStatus.FAILED)

        return {
            "total_components": total_components,
            "healthy": healthy_count,
            "degraded": degraded_count,
            "failed": failed_count,
            "overall_health": (
                "healthy"
                if failed_count == 0 and degraded_count == 0
                else "degraded"
                if failed_count == 0
                else "critical"
            ),
            "components": {
                name: {
                    "status": state.status.value,
                    "error_message": state.error_message,
                    "fallback_active": state.fallback_active,
                    "capabilities": state.capabilities,
                }
                for name, state in self._components.items()
            },
        }

    def attempt_recovery(self, component_name: str) -> bool:
        """
        コンポーネントの回復を試行

        Args:
            component_name: コンポーネント名

        Returns:
            回復に成功した場合True
        """
        if component_name not in self._components:
            return False

        component = self._components[component_name]

        # リトライ回数をチェック
        if component.retry_count >= component.max_retries:
            self.logger.warning(f"最大リトライ回数に達しました: {component_name}")
            return False

        # ヘルスチェックを実行
        if component_name in self._health_checkers:
            try:
                checker = self._health_checkers[component_name]
                if checker():
                    component.status = ComponentStatus.HEALTHY
                    component.error_message = None
                    component.fallback_active = False
                    # 全機能を再有効化
                    for capability in component.capabilities:
                        component.capabilities[capability] = True

                    self.logger.info(f"コンポーネント回復: {component_name}")
                    return True
            except Exception as e:
                self.logger.error(f"ヘルスチェック失敗: {component_name} - {e}")

        return False

    def _attempt_fallback(self, component_name: str, error: Exception) -> bool:
        """
        フォールバック処理を試行

        Args:
            component_name: コンポーネント名
            error: 発生したエラー

        Returns:
            フォールバック処理が成功した場合True
        """
        if component_name not in self._fallback_handlers:
            return False

        try:
            handler = self._fallback_handlers[component_name]
            result = handler(error)

            if result:
                component = self._components[component_name]
                component.fallback_active = True
                component.status = ComponentStatus.DEGRADED
                self.logger.info(f"フォールバック処理成功: {component_name}")
                return True
        except Exception as fallback_error:
            self.logger.error(f"フォールバック処理失敗: {component_name} - {fallback_error}")

        return False


def with_graceful_degradation(component_name: str, disable_capabilities: list[str] = None, fallback_return=None):
    """
    優雅な劣化デコレータ

    Args:
        component_name: コンポーネント名
        disable_capabilities: エラー時に無効化する機能
        fallback_return: フォールバック時の戻り値
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            degradation_manager = get_global_degradation_manager()

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # コンポーネントを失敗状態にマーク
                fallback_success = degradation_manager.mark_component_failed(component_name, e, disable_capabilities)

                if fallback_success:
                    return fallback_return
                else:
                    raise

        return wrapper

    return decorator


# グローバル劣化マネージャーインスタンス
_global_degradation_manager: GracefulDegradationManager | None = None


def get_global_degradation_manager() -> GracefulDegradationManager:
    """
    グローバル劣化マネージャーを取得

    Returns:
        劣化マネージャーインスタンス
    """
    global _global_degradation_manager
    if _global_degradation_manager is None:
        _global_degradation_manager = GracefulDegradationManager()
        # 初回作成時にコンポーネント監視を設定
        setup_component_monitoring()
    return _global_degradation_manager


def setup_component_monitoring():
    """
    コンポーネント監視を設定
    """
    manager = get_global_degradation_manager()

    # 主要コンポーネントを登録(デフォルトで健全状態)
    manager.register_component(
        "search_manager",
        {"full_text_search": True, "semantic_search": True, "hybrid_search": True},
    )

    manager.register_component("index_manager", {"indexing": True, "incremental_update": True, "search": True})

    manager.register_component(
        "embedding_manager",
        {
            "embedding_generation": True,
            "similarity_search": True,
            "model_loading": True,
        },
    )

    manager.register_component(
        "document_processor",
        {
            "pdf_processing": True,
            "word_processing": True,
            "excel_processing": True,
            "markdown_processing": True,
            "text_processing": True,
        },
    )

    manager.register_component("file_watcher", {"file_monitoring": True, "incremental_indexing": True})

    manager.register_component(
        "database",
        {"metadata_storage": True, "search_history": True, "document_management": True},
    )

    # 全コンポーネントを健全状態に設定
    for component_name in [
        "search_manager",
        "index_manager",
        "embedding_manager",
        "document_processor",
        "file_watcher",
        "database",
    ]:
        manager.mark_component_healthy(component_name)
