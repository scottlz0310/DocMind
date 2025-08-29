# -*- coding: utf-8 -*-
"""
テスト用モックタイマー

QApplicationが存在しない環境でもタイマー機能をテストできるように、
モックタイマーを提供します。
"""

import threading
from typing import Callable, Optional


class MockTimer:
    """QTimerのモック実装

    QApplicationが存在しない環境でも、タイマー機能をテストできるように
    threading.Timerを使用したモック実装を提供します。
    """

    def __init__(self):
        """MockTimerを初期化"""
        self._timer: Optional[threading.Timer] = None
        self._callback: Optional[Callable] = None
        self._interval: float = 0
        self._single_shot: bool = False
        self._running: bool = False

    def timeout(self):
        """タイムアウトシグナルのモック

        実際のQTimerのtimeoutシグナルの代わりに使用します。
        """
        return MockSignal()

    def setSingleShot(self, single_shot: bool) -> None:
        """シングルショットモードを設定

        Args:
            single_shot (bool): シングルショットモードかどうか
        """
        self._single_shot = single_shot

    def start(self, interval: int) -> None:
        """タイマーを開始

        Args:
            interval (int): インターバル（ミリ秒）
        """
        self.stop()  # 既存のタイマーを停止

        self._interval = interval / 1000.0  # ミリ秒を秒に変換
        self._running = True

        if self._callback:
            self._start_timer()

    def stop(self) -> None:
        """タイマーを停止"""
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self._running = False

    def isActive(self) -> bool:
        """タイマーがアクティブかどうかを判定

        Returns:
            bool: アクティブな場合はTrue
        """
        return self._running

    def _start_timer(self) -> None:
        """内部タイマーを開始"""
        if not self._running:
            return

        def timer_callback():
            if self._running and self._callback:
                try:
                    self._callback()
                except Exception as e:
                    print(f"MockTimer callback error: {e}")

                # 繰り返しタイマーの場合は再開
                if not self._single_shot and self._running:
                    self._start_timer()
                else:
                    self._running = False

        self._timer = threading.Timer(self._interval, timer_callback)
        self._timer.start()

    def connect_timeout(self, callback: Callable) -> None:
        """タイムアウトコールバックを接続

        Args:
            callback (Callable): タイムアウト時に呼び出すコールバック
        """
        self._callback = callback


class MockSignal:
    """QSignalのモック実装"""

    def __init__(self):
        """MockSignalを初期化"""
        self._callbacks = []

    def connect(self, callback: Callable) -> None:
        """コールバックを接続

        Args:
            callback (Callable): 接続するコールバック
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def disconnect(self, callback: Callable = None) -> None:
        """コールバックを切断

        Args:
            callback (Callable, optional): 切断するコールバック（Noneの場合は全て切断）
        """
        if callback is None:
            self._callbacks.clear()
        elif callback in self._callbacks:
            self._callbacks.remove(callback)

    def emit(self, *args, **kwargs) -> None:
        """シグナルを発行

        Args:
            *args: 引数
            **kwargs: キーワード引数
        """
        for callback in self._callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"MockSignal callback error: {e}")


def create_mock_timer() -> MockTimer:
    """モックタイマーを作成

    Returns:
        MockTimer: モックタイマーインスタンス
    """
    timer = MockTimer()
    return timer
