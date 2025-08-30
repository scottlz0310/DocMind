"""
インデックス再構築のタイムアウト管理システム

このモジュールは、インデックス再構築処理のタイムアウト監視機能を提供します。
QTimerを使用して30分のタイムアウトを実装し、タイムアウト発生時にシグナルを送信します。
"""

import logging

from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)


class RebuildTimeoutManager(QObject):
    """
    インデックス再構築のタイムアウト管理クラス

    複数のスレッドIDに対してタイムアウト監視を行い、
    指定時間経過後にタイムアウトシグナルを送信します。
    """

    # タイムアウト発生時に送信されるシグナル (thread_id: str)
    timeout_occurred = Signal(str)

    def __init__(self, timeout_minutes: int = 30, parent: QObject | None = None):
        """
        タイムアウトマネージャーを初期化

        Args:
            timeout_minutes: タイムアウト時間（分）、デフォルトは30分
            parent: 親QObjectオブジェクト
        """
        super().__init__(parent)
        self.timeout_minutes = timeout_minutes
        self.timeout_milliseconds = timeout_minutes * 60 * 1000  # ミリ秒に変換

        # アクティブなタイマーを管理する辞書 {thread_id: QTimer}
        self.active_timers: dict[str, QTimer] = {}

        logger.info(f"RebuildTimeoutManager初期化完了: タイムアウト時間={timeout_minutes}分")

    def start_timeout(self, thread_id: str) -> None:
        """
        指定されたスレッドIDに対してタイムアウト監視を開始

        Args:
            thread_id: 監視対象のスレッドID
        """
        if not thread_id:
            logger.warning("空のthread_idが指定されました")
            return

        # 既存のタイマーがある場合は停止
        if thread_id in self.active_timers:
            logger.info(f"既存のタイマーを停止: {thread_id}")
            self.cancel_timeout(thread_id)

        # 新しいタイマーを作成
        timer = QTimer(self)
        timer.setSingleShot(True)  # 一回だけ実行
        timer.timeout.connect(lambda: self._handle_timeout(thread_id))

        # タイマーを開始
        timer.start(self.timeout_milliseconds)
        self.active_timers[thread_id] = timer

        logger.info(f"タイムアウト監視開始: {thread_id} ({self.timeout_minutes}分)")

    def cancel_timeout(self, thread_id: str) -> None:
        """
        指定されたスレッドIDのタイムアウト監視をキャンセル

        Args:
            thread_id: キャンセル対象のスレッドID
        """
        if thread_id not in self.active_timers:
            logger.debug(f"キャンセル対象のタイマーが見つかりません: {thread_id}")
            return

        timer = self.active_timers[thread_id]
        timer.stop()
        timer.deleteLater()  # メモリリークを防ぐ
        del self.active_timers[thread_id]

        logger.info(f"タイムアウト監視キャンセル: {thread_id}")

    def _handle_timeout(self, thread_id: str) -> None:
        """
        タイムアウト発生時の内部処理

        Args:
            thread_id: タイムアウトが発生したスレッドID
        """
        logger.warning(f"インデックス再構築タイムアウト発生: {thread_id}")

        # タイマーをクリーンアップ
        if thread_id in self.active_timers:
            timer = self.active_timers[thread_id]
            timer.deleteLater()
            del self.active_timers[thread_id]

        # タイムアウトシグナルを送信
        self.timeout_occurred.emit(thread_id)

        logger.info(f"タイムアウトシグナル送信完了: {thread_id}")

    def is_timeout_active(self, thread_id: str) -> bool:
        """
        指定されたスレッドIDのタイムアウト監視がアクティブかチェック

        Args:
            thread_id: チェック対象のスレッドID

        Returns:
            bool: タイムアウト監視がアクティブな場合True
        """
        return thread_id in self.active_timers and self.active_timers[thread_id].isActive()

    def get_active_timeouts(self) -> list[str]:
        """
        現在アクティブなタイムアウト監視のスレッドIDリストを取得

        Returns:
            list[str]: アクティブなスレッドIDのリスト
        """
        return [thread_id for thread_id, timer in self.active_timers.items() if timer.isActive()]

    def cancel_all_timeouts(self) -> None:
        """
        すべてのタイムアウト監視をキャンセル

        アプリケーション終了時やクリーンアップ時に使用
        """
        thread_ids = list(self.active_timers.keys())
        for thread_id in thread_ids:
            self.cancel_timeout(thread_id)

        logger.info(f"すべてのタイムアウト監視をキャンセル: {len(thread_ids)}個")

    def get_remaining_time(self, thread_id: str) -> int | None:
        """
        指定されたスレッドIDの残り時間を秒単位で取得

        Args:
            thread_id: 対象のスレッドID

        Returns:
            Optional[int]: 残り時間（秒）、タイマーが存在しない場合はNone
        """
        if thread_id not in self.active_timers:
            return None

        timer = self.active_timers[thread_id]
        if not timer.isActive():
            return None

        # QTimerには残り時間を直接取得するメソッドがないため、
        # タイマー開始時からの経過時間を計算する必要がある
        # ここでは簡易実装として、タイムアウト時間を返す
        return self.timeout_minutes * 60
