"""
優雅な劣化機能のテスト

コンポーネントの状態管理、フォールバック処理、ヘルスチェック機能のテストを行います。
"""


import pytest

from src.utils.exceptions import SearchError
from src.utils.graceful_degradation import (
    ComponentState,
    ComponentStatus,
    GracefulDegradationManager,
    get_global_degradation_manager,
    setup_component_monitoring,
    with_graceful_degradation,
)


class TestComponentState:
    """ComponentStateクラスのテスト"""

    def test_component_state_initialization(self):
        """コンポーネント状態の初期化テスト"""
        state = ComponentState(
            name="test_component",
            capabilities={"feature1": True, "feature2": False}
        )

        assert state.name == "test_component"
        assert state.status == ComponentStatus.HEALTHY
        assert state.error_message is None
        assert state.fallback_active is False
        assert state.retry_count == 0
        assert state.max_retries == 3
        assert state.capabilities["feature1"] is True
        assert state.capabilities["feature2"] is False

    def test_component_state_defaults(self):
        """コンポーネント状態のデフォルト値テスト"""
        state = ComponentState(name="minimal_component")

        assert state.capabilities == {}
        assert state.max_retries == 3
        assert state.status == ComponentStatus.HEALTHY


class TestGracefulDegradationManager:
    """GracefulDegradationManagerクラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.manager = GracefulDegradationManager()

    def test_manager_initialization(self):
        """マネージャーの初期化テスト"""
        assert len(self.manager._components) == 0
        assert len(self.manager._fallback_handlers) == 0
        assert len(self.manager._health_checkers) == 0

    def test_register_component(self):
        """コンポーネント登録テスト"""
        capabilities = {"search": True, "index": True}
        self.manager.register_component("search_manager", capabilities, max_retries=5)

        assert "search_manager" in self.manager._components
        component = self.manager._components["search_manager"]
        assert component.name == "search_manager"
        assert component.capabilities == capabilities
        assert component.max_retries == 5
        assert component.status == ComponentStatus.HEALTHY

    def test_register_fallback_handler(self):
        """フォールバックハンドラー登録テスト"""
        def test_handler(error):
            return True

        self.manager.register_fallback_handler("test_component", test_handler)
        assert "test_component" in self.manager._fallback_handlers
        assert self.manager._fallback_handlers["test_component"] == test_handler

    def test_register_health_checker(self):
        """ヘルスチェッカー登録テスト"""
        def test_checker():
            return True

        self.manager.register_health_checker("test_component", test_checker)
        assert "test_component" in self.manager._health_checkers
        assert self.manager._health_checkers["test_component"] == test_checker

    def test_mark_component_failed(self):
        """コンポーネント失敗マークテスト"""
        self.manager.register_component("test_component", {"feature1": True, "feature2": True})

        test_error = SearchError("テストエラー")
        result = self.manager.mark_component_failed(
            "test_component",
            test_error,
            disable_capabilities=["feature1"]
        )

        component = self.manager._components["test_component"]
        assert component.status == ComponentStatus.FAILED
        assert component.error_message == "テストエラー"
        assert component.retry_count == 1
        assert component.capabilities["feature1"] is False
        assert component.capabilities["feature2"] is True
        assert result is False  # フォールバックハンドラーが登録されていないため

    def test_mark_component_failed_with_fallback(self):
        """フォールバック付きコンポーネント失敗マークテスト"""
        self.manager.register_component("test_component", {"feature1": True})

        def fallback_handler(error):
            return True

        self.manager.register_fallback_handler("test_component", fallback_handler)

        test_error = SearchError("フォールバックテスト")
        result = self.manager.mark_component_failed("test_component", test_error)

        component = self.manager._components["test_component"]
        assert component.status == ComponentStatus.DEGRADED  # フォールバック成功により劣化状態
        assert component.fallback_active is True
        assert result is True

    def test_mark_component_degraded(self):
        """コンポーネント劣化マークテスト"""
        self.manager.register_component("test_component", {"feature1": True, "feature2": True})

        self.manager.mark_component_degraded(
            "test_component",
            disable_capabilities=["feature1"],
            error_message="部分的な機能停止"
        )

        component = self.manager._components["test_component"]
        assert component.status == ComponentStatus.DEGRADED
        assert component.error_message == "部分的な機能停止"
        assert component.capabilities["feature1"] is False
        assert component.capabilities["feature2"] is True

    def test_is_component_healthy(self):
        """コンポーネント健全性チェックテスト"""
        self.manager.register_component("healthy_component")
        self.manager.register_component("failed_component")

        # 失敗状態にマーク
        self.manager.mark_component_failed("failed_component", ValueError("テスト"))

        assert self.manager.is_component_healthy("healthy_component") is True
        assert self.manager.is_component_healthy("failed_component") is False
        assert self.manager.is_component_healthy("non_existent") is False

    def test_is_capability_available(self):
        """機能可用性チェックテスト"""
        self.manager.register_component("test_component", {
            "feature1": True,
            "feature2": True,
            "feature3": True
        })

        # 一部機能を無効化
        self.manager.mark_component_degraded(
            "test_component",
            disable_capabilities=["feature2"]
        )

        assert self.manager.is_capability_available("test_component", "feature1") is True
        assert self.manager.is_capability_available("test_component", "feature2") is False
        assert self.manager.is_capability_available("test_component", "feature3") is True
        assert self.manager.is_capability_available("test_component", "non_existent") is False
        assert self.manager.is_capability_available("non_existent", "feature1") is False

    def test_get_component_status(self):
        """コンポーネント状態取得テスト"""
        self.manager.register_component("test_component", {"feature1": True})

        status = self.manager.get_component_status("test_component")
        assert status is not None
        assert status.name == "test_component"
        assert status.status == ComponentStatus.HEALTHY

        # 存在しないコンポーネント
        status = self.manager.get_component_status("non_existent")
        assert status is None

    def test_get_system_health(self):
        """システム健全性取得テスト"""
        # 複数のコンポーネントを登録
        self.manager.register_component("healthy1")
        self.manager.register_component("healthy2")
        self.manager.register_component("degraded1")
        self.manager.register_component("failed1")

        # 状態を設定
        self.manager.mark_component_degraded("degraded1")
        self.manager.mark_component_failed("failed1", ValueError("テスト"))

        health = self.manager.get_system_health()

        assert health["total_components"] == 4
        assert health["healthy"] == 2
        assert health["degraded"] == 1
        assert health["failed"] == 1
        assert health["overall_health"] == "critical"  # 失敗コンポーネントがあるため
        assert "components" in health
        assert len(health["components"]) == 4

    def test_attempt_recovery_with_health_checker(self):
        """ヘルスチェッカー付き回復試行テスト"""
        self.manager.register_component("test_component", {"feature1": True})

        # ヘルスチェッカーを登録
        health_check_called = False
        def health_checker():
            nonlocal health_check_called
            health_check_called = True
            return True

        self.manager.register_health_checker("test_component", health_checker)

        # コンポーネントを失敗状態にする
        self.manager.mark_component_failed("test_component", ValueError("テスト"))

        # 回復を試行
        result = self.manager.attempt_recovery("test_component")

        assert result is True
        assert health_check_called is True

        component = self.manager._components["test_component"]
        assert component.status == ComponentStatus.HEALTHY
        assert component.error_message is None
        assert component.fallback_active is False
        assert component.capabilities["feature1"] is True

    def test_attempt_recovery_max_retries(self):
        """最大リトライ回数での回復試行テスト"""
        self.manager.register_component("test_component", max_retries=2)

        # 最大リトライ回数を超える
        component = self.manager._components["test_component"]
        component.retry_count = 3

        result = self.manager.attempt_recovery("test_component")
        assert result is False

    def test_fallback_handler_failure(self):
        """フォールバックハンドラー失敗テスト"""
        self.manager.register_component("test_component")

        def failing_fallback_handler(error):
            raise RuntimeError("フォールバック失敗")

        self.manager.register_fallback_handler("test_component", failing_fallback_handler)

        test_error = SearchError("テストエラー")
        result = self.manager.mark_component_failed("test_component", test_error)

        assert result is False
        component = self.manager._components["test_component"]
        assert component.status == ComponentStatus.FAILED
        assert component.fallback_active is False


class TestGracefulDegradationDecorator:
    """with_graceful_degradationデコレータのテスト"""

    def setup_method(self):
        """テスト前の設定"""
        self.manager = get_global_degradation_manager()
        # テスト用コンポーネントを登録
        self.manager.register_component("test_component", {
            "feature1": True,
            "feature2": True
        })

    def test_decorator_normal_execution(self):
        """デコレータの正常実行テスト"""
        @with_graceful_degradation("test_component")
        def normal_function():
            return "success"

        result = normal_function()
        assert result == "success"

        # コンポーネントは健全な状態を維持
        assert self.manager.is_component_healthy("test_component")

    def test_decorator_with_exception(self):
        """デコレータの例外処理テスト"""
        @with_graceful_degradation(
            "test_component",
            disable_capabilities=["feature1"],
            fallback_return="fallback_result"
        )
        def failing_function():
            raise SearchError("テスト例外")

        failing_function()

        # フォールバックハンドラーが登録されていないため、例外が再発生される
        # ただし、コンポーネントは失敗状態になる
        component = self.manager.get_component_status("test_component")
        assert component.status == ComponentStatus.FAILED
        assert component.capabilities["feature1"] is False
        assert component.capabilities["feature2"] is True

    def test_decorator_with_successful_fallback(self):
        """デコレータの成功フォールバックテスト"""
        # フォールバックハンドラーを登録
        def fallback_handler(error):
            return True

        self.manager.register_fallback_handler("test_component", fallback_handler)

        @with_graceful_degradation(
            "test_component",
            disable_capabilities=["feature1"],
            fallback_return="fallback_success"
        )
        def failing_function():
            raise SearchError("フォールバックテスト")

        result = failing_function()
        assert result == "fallback_success"

        component = self.manager.get_component_status("test_component")
        assert component.status == ComponentStatus.DEGRADED
        assert component.fallback_active is True


class TestComponentMonitoring:
    """コンポーネント監視のテスト"""

    def test_setup_component_monitoring(self):
        """コンポーネント監視設定テスト"""
        manager = GracefulDegradationManager()

        # 元のグローバルマネージャーを一時的に置き換え
        import src.utils.graceful_degradation
        original_manager = src.utils.graceful_degradation._global_degradation_manager
        src.utils.graceful_degradation._global_degradation_manager = manager

        try:
            setup_component_monitoring()

            # 主要コンポーネントが登録されているかチェック
            expected_components = [
                "search_manager",
                "index_manager",
                "embedding_manager",
                "document_processor",
                "file_watcher",
                "database"
            ]

            for component_name in expected_components:
                assert component_name in manager._components
                component = manager._components[component_name]
                assert component.status == ComponentStatus.HEALTHY
                assert len(component.capabilities) > 0

        finally:
            # 元のマネージャーを復元
            src.utils.graceful_degradation._global_degradation_manager = original_manager

    def test_global_degradation_manager_singleton(self):
        """グローバル劣化マネージャーのシングルトンテスト"""
        manager1 = get_global_degradation_manager()
        manager2 = get_global_degradation_manager()
        assert manager1 is manager2


class TestIntegrationScenarios:
    """統合シナリオのテスト"""

    def setup_method(self):
        """テスト前の設定"""
        self.manager = GracefulDegradationManager()

    def test_cascading_failure_scenario(self):
        """カスケード障害シナリオのテスト"""
        # 依存関係のあるコンポーネントを設定
        self.manager.register_component("database", {"storage": True, "query": True})
        self.manager.register_component("index_manager", {"indexing": True, "search": True})
        self.manager.register_component("search_manager", {"full_text": True, "semantic": True})

        # データベース障害をシミュレート
        self.manager.mark_component_failed("database", RuntimeError("DB接続失敗"))

        # インデックスマネージャーが影響を受ける
        self.manager.mark_component_degraded(
            "index_manager",
            disable_capabilities=["indexing"],
            error_message="データベース障害によりインデックス機能が制限されています"
        )

        # 検索マネージャーも影響を受ける
        self.manager.mark_component_degraded(
            "search_manager",
            disable_capabilities=["full_text"],
            error_message="インデックス障害により全文検索が無効化されました"
        )

        # システム健全性をチェック
        health = self.manager.get_system_health()
        assert health["overall_health"] == "critical"
        assert health["failed"] == 1
        assert health["degraded"] == 2

        # 一部機能は依然として利用可能
        assert self.manager.is_capability_available("search_manager", "semantic") is True
        assert self.manager.is_capability_available("search_manager", "full_text") is False

    def test_recovery_scenario(self):
        """回復シナリオのテスト"""
        self.manager.register_component("test_service", {"feature1": True, "feature2": True})

        # ヘルスチェッカーを登録
        recovery_attempts = 0
        def health_checker():
            nonlocal recovery_attempts
            recovery_attempts += 1
            return recovery_attempts >= 2  # 2回目で成功

        self.manager.register_health_checker("test_service", health_checker)

        # サービス障害
        self.manager.mark_component_failed("test_service", RuntimeError("サービス障害"))
        assert not self.manager.is_component_healthy("test_service")

        # 1回目の回復試行（失敗）
        result1 = self.manager.attempt_recovery("test_service")
        assert result1 is False
        assert not self.manager.is_component_healthy("test_service")

        # 2回目の回復試行（成功）
        result2 = self.manager.attempt_recovery("test_service")
        assert result2 is True
        assert self.manager.is_component_healthy("test_service")

        # 全機能が復旧
        assert self.manager.is_capability_available("test_service", "feature1") is True
        assert self.manager.is_capability_available("test_service", "feature2") is True


if __name__ == "__main__":
    pytest.main([__file__])
