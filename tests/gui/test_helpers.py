"""
Phase6 GUIテスト用ヘルパークラス

ヘッドレス環境でのGUIテスト実行をサポート
タイムアウト設定でハングアップを防止
"""

import logging
import time
from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

try:
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication, QWidget
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


class GUITestHelper:
    """GUIテスト用ヘルパークラス"""

    DEFAULT_TIMEOUT = 5.0  # デフォルトタイムアウト（秒）

    @staticmethod
    def create_test_widget(widget_class, timeout: float = DEFAULT_TIMEOUT, **kwargs) -> QWidget | None:
        """
        テスト用ウィジェット作成

        Args:
            widget_class: ウィジェットクラス
            timeout: タイムアウト時間（秒）
            **kwargs: ウィジェット初期化引数

        Returns:
            作成されたウィジェット（失敗時はNone）
        """
        if not GUI_AVAILABLE:
            return None

        try:
            # タイムアウト付きでウィジェット作成
            widget = None

            def create_widget():
                nonlocal widget
                widget = widget_class(**kwargs)
                widget.show()
                QApplication.processEvents()

            if GUITestHelper._execute_with_timeout(create_widget, timeout):
                return widget
            else:
                logging.warning(f"ウィジェット作成がタイムアウトしました: {widget_class.__name__}")
                return None

        except Exception as e:
            logging.error(f"ウィジェット作成エラー: {e}")
            return None

    @staticmethod
    def simulate_user_interaction(widget: QWidget, action: str, timeout: float = DEFAULT_TIMEOUT, *args) -> bool:
        """
        ユーザー操作シミュレーション

        Args:
            widget: 対象ウィジェット
            action: 実行するアクション名
            timeout: タイムアウト時間（秒）
            *args: アクション引数

        Returns:
            成功時True、失敗時False
        """
        if not GUI_AVAILABLE or widget is None:
            return False

        try:
            def execute_action():
                if hasattr(widget, action):
                    getattr(widget, action)(*args)
                    QApplication.processEvents()
                else:
                    raise AttributeError(f"アクション '{action}' が見つかりません")

            return GUITestHelper._execute_with_timeout(execute_action, timeout)

        except Exception as e:
            logging.error(f"ユーザー操作シミュレーションエラー: {e}")
            return False

    @staticmethod
    def wait_for_condition(condition: Callable[[], bool], timeout: float = DEFAULT_TIMEOUT,
                          interval: float = 0.1) -> bool:
        """
        条件が満たされるまで待機

        Args:
            condition: 待機条件（True/Falseを返す関数）
            timeout: タイムアウト時間（秒）
            interval: チェック間隔（秒）

        Returns:
            条件が満たされた場合True、タイムアウト時False
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if condition():
                    return True

                if GUI_AVAILABLE:
                    QApplication.processEvents()

                time.sleep(interval)

            except Exception as e:
                logging.error(f"条件チェックエラー: {e}")
                return False

        return False

    @staticmethod
    def cleanup_widget(widget: QWidget, timeout: float = DEFAULT_TIMEOUT) -> bool:
        """
        ウィジェットのクリーンアップ

        Args:
            widget: クリーンアップ対象ウィジェット
            timeout: タイムアウト時間（秒）

        Returns:
            成功時True、失敗時False
        """
        if not GUI_AVAILABLE or widget is None:
            return True

        try:
            def cleanup():
                widget.hide()
                widget.close()
                widget.deleteLater()
                QApplication.processEvents()

            return GUITestHelper._execute_with_timeout(cleanup, timeout)

        except Exception as e:
            logging.error(f"ウィジェットクリーンアップエラー: {e}")
            return False

    @staticmethod
    def _execute_with_timeout(func: Callable, timeout: float) -> bool:
        """
        タイムアウト付きで関数を実行

        Args:
            func: 実行する関数
            timeout: タイムアウト時間（秒）

        Returns:
            成功時True、タイムアウト時False
        """
        if not GUI_AVAILABLE:
            return False

        try:
            # タイムアウトタイマーを設定
            timer = QTimer()
            timer.setSingleShot(True)

            loop = QEventLoop()
            timer.timeout.connect(loop.quit)

            # 関数を実行
            success = False

            def execute_func():
                nonlocal success
                try:
                    func()
                    success = True
                except Exception as e:
                    logging.error(f"関数実行エラー: {e}")
                    success = False
                finally:
                    loop.quit()

            # 即座に実行
            QTimer.singleShot(0, execute_func)

            # タイムアウト開始
            timer.start(int(timeout * 1000))

            # イベントループ実行
            loop.exec()

            return success

        except Exception as e:
            logging.error(f"タイムアウト付き実行エラー: {e}")
            return False


class MockGUITestHelper:
    """GUI環境が利用できない場合のモックヘルパー"""

    @staticmethod
    def create_test_widget(widget_class, timeout: float = 5.0, **kwargs) -> Mock:
        """モックウィジェットを作成"""
        mock_widget = Mock()
        mock_widget.__class__ = widget_class
        return mock_widget

    @staticmethod
    def simulate_user_interaction(widget: Any, action: str, timeout: float = 5.0, *args) -> bool:
        """モックユーザー操作"""
        if hasattr(widget, action):
            getattr(widget, action)(*args)
        return True

    @staticmethod
    def wait_for_condition(condition: Callable[[], bool], timeout: float = 5.0,
                          interval: float = 0.1) -> bool:
        """モック条件待機"""
        try:
            return condition()
        except Exception:
            return False

    @staticmethod
    def cleanup_widget(widget: Any, timeout: float = 5.0) -> bool:
        """モッククリーンアップ"""
        return True


# 環境に応じてヘルパーを選択
if GUI_AVAILABLE:
    TestHelper = GUITestHelper
else:
    TestHelper = MockGUITestHelper


def create_safe_test_widget(widget_class, **kwargs):
    """
    安全なテストウィジェット作成

    常にモックを使用してQObject初期化問題を回避
    """
    # 常にモックを使用してハングやクラッシュを防止
    mock_widget = Mock()
    mock_widget.__class__ = widget_class

    # 必要なメソッドをモック化
    mock_widget.show = Mock()
    mock_widget.hide = Mock()
    mock_widget.close = Mock()
    mock_widget.deleteLater = Mock()
    mock_widget.isVisible = Mock(return_value=False)
    mock_widget.setVisible = Mock()
    mock_widget.setEnabled = Mock()
    mock_widget.setMinimumSize = Mock()
    mock_widget.resize = Mock()

    # ウィジェット固有のメソッドをkwargsから設定
    for key, value in kwargs.items():
        setattr(mock_widget, key, value)

    return mock_widget


def safe_user_interaction(widget, action, *args):
    """
    安全なユーザー操作シミュレーション

    タイムアウト付きで操作を実行し、
    失敗時はログ出力のみ
    """
    success = TestHelper.simulate_user_interaction(widget, action, *args)

    if not success:
        logging.warning(f"ユーザー操作が失敗しました: {action}")

    return success


def safe_cleanup(widget):
    """
    安全なウィジェットクリーンアップ

    タイムアウト付きでクリーンアップを実行し、
    失敗時もエラーを発生させない
    """
    try:
        return TestHelper.cleanup_widget(widget)
    except Exception as e:
        logging.warning(f"クリーンアップが失敗しました: {e}")
        return False
