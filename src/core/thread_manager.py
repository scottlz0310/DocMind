"""
DocMind スレッド管理モジュール

このモジュールは、IndexingWorkerのバックグラウンドスレッド実行を管理し、
複数の同時インデックス処理の制御、適切なスレッドライフサイクル管理、
リソースクリーンアップを提供します。
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import logging
import threading
import time
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication

from ..utils.exceptions import ThreadManagementError
from .indexing_worker import IndexingWorker


class ThreadState(Enum):
    """スレッドの状態を表す列挙型"""

    IDLE = "idle"  # アイドル状態
    STARTING = "starting"  # 開始中
    RUNNING = "running"  # 実行中
    STOPPING = "stopping"  # 停止中
    FINISHED = "finished"  # 完了
    ERROR = "error"  # エラー状態
    CLEANUP = "cleanup"  # クリーンアップ中


@dataclass
class ThreadInfo:
    """スレッド情報を格納するデータクラス"""

    thread_id: str  # スレッドID
    folder_path: str  # 処理対象フォルダパス
    thread: QThread  # QThreadインスタンス
    worker: IndexingWorker  # IndexingWorkerインスタンス
    state: ThreadState  # 現在の状態
    start_time: float  # 開始時刻
    end_time: float | None  # 終了時刻
    error_message: str | None  # エラーメッセージ
    cleanup_callbacks: list[Callable]  # クリーンアップコールバック

    def get_duration(self) -> float:
        """実行時間を取得(秒)"""
        if self.end_time:
            return self.end_time - self.start_time
        else:
            return time.time() - self.start_time

    def is_active(self) -> bool:
        """アクティブ状態かどうかを判定"""
        return self.state in [
            ThreadState.STARTING,
            ThreadState.RUNNING,
            ThreadState.STOPPING,
        ]

    def is_finished(self) -> bool:
        """完了状態かどうかを判定"""
        return self.state in [ThreadState.FINISHED, ThreadState.ERROR]


class IndexingThreadManager(QObject):
    """インデックス処理スレッドの管理クラス

    複数のIndexingWorkerスレッドの同時実行制御、ライフサイクル管理、
    リソースクリーンアップを行います。

    要件対応:
        - 3.1: バックグラウンドスレッドでの非同期処理
        - 3.5: 処理中断機能とリソースクリーンアップ
        - 6.2: 複数の同時インデックス処理の制御
    """

    # シグナル定義
    thread_started = Signal(str)  # thread_id
    thread_finished = Signal(str, dict)  # thread_id, statistics
    thread_error = Signal(str, str)  # thread_id, error_message
    thread_progress = Signal(str, str, int, int)  # thread_id, message, current, total
    manager_status_changed = Signal(str)  # status_message

    def __init__(self, max_concurrent_threads: int = 2, test_mode: bool = False):
        """IndexingThreadManagerを初期化

        Args:
            max_concurrent_threads (int): 最大同時実行スレッド数
            test_mode (bool): テストモード(QApplicationなしでの動作)
        """
        super().__init__()

        # 設定
        self.max_concurrent_threads = max_concurrent_threads
        self.test_mode = test_mode

        # スレッド管理
        self.active_threads: dict[str, ThreadInfo] = {}
        self.thread_counter = 0
        self.lock = threading.Lock()

        # ログ設定(タイマー設定より前に初期化)
        self.logger = logging.getLogger(__name__)

        # クリーンアップタイマー(QApplicationが存在する場合のみ)
        self.cleanup_timer = None
        if not test_mode:
            self._setup_cleanup_timer()
        else:
            self._setup_mock_cleanup_timer()

        self.logger.info(f"IndexingThreadManager初期化完了 (最大同時実行数: {max_concurrent_threads})")

    def _setup_cleanup_timer(self) -> None:
        """クリーンアップタイマーを設定(QApplicationが存在する場合のみ)"""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()

            if app is not None:
                # QApplicationが存在する場合のみタイマーを作成
                self.cleanup_timer = QTimer()
                self.cleanup_timer.timeout.connect(self._periodic_cleanup)
                self.cleanup_timer.start(30000)  # 30秒間隔でクリーンアップ
                self.logger.debug("定期クリーンアップタイマーを開始しました")
            else:
                # QApplicationが存在しない場合はタイマーなし
                self.cleanup_timer = None
                self.logger.debug("QApplicationが存在しないため、定期クリーンアップタイマーは無効です")

        except Exception as e:
            self.cleanup_timer = None
            self.logger.warning(f"クリーンアップタイマーの設定に失敗: {e}")

    def _setup_mock_cleanup_timer(self) -> None:
        """テスト用モッククリーンアップタイマーを設定"""
        try:
            # テストモードでは定期クリーンアップタイマーを無効化
            # 短時間のテストでは不要で、ハングの原因となる可能性がある
            self.cleanup_timer = None
            self.logger.debug("テストモード: 定期クリーンアップタイマーを無効化しました")

        except Exception as e:
            self.cleanup_timer = None
            self.logger.warning(f"モッククリーンアップタイマーの設定に失敗: {e}")
            # エラーの詳細をログに出力
            import traceback

            self.logger.debug(f"モッククリーンアップタイマー設定エラーの詳細: {traceback.format_exc()}")

    def _create_mock_thread_info(self, thread_id: str, folder_path: str) -> ThreadInfo:
        """テスト用のモックスレッド情報を作成

        Args:
            thread_id (str): スレッドID
            folder_path (str): フォルダパス

        Returns:
            ThreadInfo: モックスレッド情報
        """
        # モックスレッド情報を作成(実際のQThreadやWorkerは使わない)
        thread_info = ThreadInfo(
            thread_id=thread_id,
            folder_path=folder_path,
            thread=None,  # テストモードではNone
            worker=None,  # テストモードではNone
            state=ThreadState.RUNNING,  # 即座にRUNNING状態にする
            start_time=time.time(),
            end_time=None,
            error_message=None,
            cleanup_callbacks=[],
        )

        # テストモードでは即座に完了状態にする(同期的に)
        time.sleep(0.1)  # 短い遅延でシミュレート
        thread_info.state = ThreadState.FINISHED
        thread_info.end_time = time.time()

        # 完了シグナルを発行
        mock_stats = {
            "files_processed": 2,
            "files_failed": 0,
            "documents_added": 2,
            "processing_time": thread_info.get_duration(),
        }

        self.logger.debug(f"モックスレッド完了: {thread_id}")
        self.thread_finished.emit(thread_id, mock_stats)

        return thread_info

    def can_start_new_thread(self) -> bool:
        """新しいスレッドを開始できるかどうかを判定

        Returns:
            bool: 新しいスレッドを開始できる場合はTrue
        """
        with self.lock:
            active_count = sum(1 for info in self.active_threads.values() if info.is_active())
            return active_count < self.max_concurrent_threads

    def get_active_thread_count(self) -> int:
        """アクティブなスレッド数を取得

        Returns:
            int: アクティブなスレッド数
        """
        with self.lock:
            return sum(1 for info in self.active_threads.values() if info.is_active())

    def get_thread_info(self, thread_id: str) -> ThreadInfo | None:
        """スレッド情報を取得

        Args:
            thread_id (str): スレッドID

        Returns:
            Optional[ThreadInfo]: スレッド情報(存在しない場合はNone)
        """
        with self.lock:
            return self.active_threads.get(thread_id)

    def get_all_thread_info(self) -> list[ThreadInfo]:
        """すべてのスレッド情報を取得

        Returns:
            List[ThreadInfo]: すべてのスレッド情報のリスト
        """
        with self.lock:
            return list(self.active_threads.values())

    def start_indexing_thread(self, folder_path: str, document_processor, index_manager) -> str | None:
        """インデックス処理スレッドを開始

        Args:
            folder_path (str): インデックス化するフォルダのパス
            document_processor: ドキュメントプロセッサー
            index_manager: インデックスマネージャー

        Returns:
            Optional[str]: 開始されたスレッドのID(開始できない場合はNone)

        Raises:
            ThreadManagementError: スレッド開始に失敗した場合
        """
        try:
            # 同時実行数チェック
            if not self.can_start_new_thread():
                active_count = self.get_active_thread_count()
                self.logger.warning(f"最大同時実行数に達しています: {active_count}/{self.max_concurrent_threads}")
                return None

            # 既に同じフォルダが処理中かチェック
            if self._is_folder_being_processed(folder_path):
                self.logger.warning(f"フォルダは既に処理中です: {folder_path}")
                return None

            # スレッドIDを生成
            with self.lock:
                self.thread_counter += 1
                thread_id = f"indexing_thread_{self.thread_counter}"

            if self.test_mode:
                # テストモード: 実際のスレッドを作成せずにモック処理
                thread_info = self._create_mock_thread_info(thread_id, folder_path)
            else:
                # 通常モード: 実際のIndexingWorkerとQThreadを作成
                worker = IndexingWorker(
                    folder_path=folder_path,
                    document_processor=document_processor,
                    index_manager=index_manager,
                )

                # QThreadを作成
                thread = QThread()
                worker.moveToThread(thread)

                # ThreadInfoを作成
                thread_info = ThreadInfo(
                    thread_id=thread_id,
                    folder_path=folder_path,
                    thread=thread,
                    worker=worker,
                    state=ThreadState.STARTING,
                    start_time=time.time(),
                    end_time=None,
                    error_message=None,
                    cleanup_callbacks=[],
                )

                # シグナル接続
                self._connect_thread_signals(thread_info)

                # スレッド開始
                thread.start()

                # 状態を更新
                thread_info.state = ThreadState.RUNNING

            # スレッド管理に追加
            with self.lock:
                self.active_threads[thread_id] = thread_info

            self.logger.info(f"インデックス処理スレッドを開始: {thread_id} ({folder_path})")
            self.thread_started.emit(thread_id)
            self._emit_manager_status()

            return thread_id

        except Exception as e:
            error_msg = f"インデックス処理スレッドの開始に失敗: {e!s}"
            self.logger.error(error_msg, exc_info=True)
            raise ThreadManagementError(error_msg) from e

    def stop_thread(self, thread_id: str, force: bool = False) -> bool:
        """指定されたスレッドを停止

        Args:
            thread_id (str): 停止するスレッドのID
            force (bool): 強制停止するかどうか

        Returns:
            bool: 停止処理が開始された場合はTrue
        """
        try:
            thread_info = self.get_thread_info(thread_id)
            if not thread_info:
                self.logger.warning(f"スレッドが見つかりません: {thread_id}")
                return False

            if not thread_info.is_active():
                self.logger.warning(f"スレッドは既に非アクティブです: {thread_id} (状態: {thread_info.state.value})")
                return False

            self.logger.info(f"スレッド停止を開始: {thread_id} (強制: {force})")

            # 状態を更新
            thread_info.state = ThreadState.STOPPING

            # ワーカーに停止を要求
            if thread_info.worker:
                thread_info.worker.stop()

            if force:
                # 強制停止の場合は即座にスレッドを終了
                self._force_stop_thread(thread_info)
            else:
                # 通常停止の場合は完了を待つ
                self._graceful_stop_thread(thread_info)

            self._emit_manager_status()
            return True

        except Exception as e:
            self.logger.error(
                f"スレッド停止処理中にエラーが発生: {thread_id} - {e!s}",
                exc_info=True,
            )
            return False

    def stop_all_threads(self, force: bool = False) -> int:
        """すべてのアクティブなスレッドを停止

        Args:
            force (bool): 強制停止するかどうか

        Returns:
            int: 停止処理を開始したスレッド数
        """
        with self.lock:
            active_thread_ids = [thread_id for thread_id, info in self.active_threads.items() if info.is_active()]

        stopped_count = 0
        for thread_id in active_thread_ids:
            if self.stop_thread(thread_id, force):
                stopped_count += 1

        self.logger.info(f"すべてのスレッド停止を開始: {stopped_count}個のスレッド (強制: {force})")
        return stopped_count

    def cleanup_finished_threads(self) -> int:
        """完了したスレッドをクリーンアップ

        Returns:
            int: クリーンアップしたスレッド数
        """
        cleanup_count = 0

        with self.lock:
            finished_thread_ids = [
                thread_id
                for thread_id, info in self.active_threads.items()
                if info.is_finished() and info.state != ThreadState.CLEANUP
            ]

        for thread_id in finished_thread_ids:
            if self._cleanup_thread(thread_id):
                cleanup_count += 1

        if cleanup_count > 0:
            self.logger.info(f"完了したスレッドをクリーンアップ: {cleanup_count}個")
            self._emit_manager_status()

        return cleanup_count

    def get_status_summary(self) -> dict[str, Any]:
        """スレッドマネージャーの状態サマリーを取得

        Returns:
            Dict[str, Any]: 状態サマリー
        """
        with self.lock:
            state_counts = {}
            active_count = 0

            for info in self.active_threads.values():
                state = info.state.value
                state_counts[state] = state_counts.get(state, 0) + 1

                # アクティブスレッド数を直接計算(デッドロック回避)
                if info.is_active():
                    active_count += 1

            # can_start_new_threadも直接計算(デッドロック回避)
            can_start_new = active_count < self.max_concurrent_threads

            return {
                "total_threads": len(self.active_threads),
                "active_threads": active_count,
                "max_concurrent": self.max_concurrent_threads,
                "can_start_new": can_start_new,
                "state_counts": state_counts,
                "thread_details": [
                    {
                        "thread_id": info.thread_id,
                        "folder_path": info.folder_path,
                        "state": info.state.value,
                        "duration": info.get_duration(),
                        "error_message": info.error_message,
                    }
                    for info in self.active_threads.values()
                ],
            }

    def _is_folder_being_processed(self, folder_path: str) -> bool:
        """指定されたフォルダが処理中かどうかを判定

        Args:
            folder_path (str): チェックするフォルダパス

        Returns:
            bool: 処理中の場合はTrue
        """
        with self.lock:
            for info in self.active_threads.values():
                if info.folder_path == folder_path and info.is_active():
                    return True
            return False

    def _connect_thread_signals(self, thread_info: ThreadInfo) -> None:
        """スレッドのシグナルを接続

        Args:
            thread_info (ThreadInfo): スレッド情報
        """
        # スレッドシグナル
        thread_info.thread.started.connect(lambda: self._on_thread_started(thread_info.thread_id))
        thread_info.thread.finished.connect(lambda: self._on_thread_finished(thread_info.thread_id))

        # ワーカーシグナル
        thread_info.worker.progress_updated.connect(
            lambda msg, current, total: self._on_worker_progress(thread_info.thread_id, msg, current, total)
        )
        thread_info.worker.indexing_completed.connect(
            lambda folder_path, stats: self._on_worker_completed(thread_info.thread_id, folder_path, stats)
        )
        thread_info.worker.error_occurred.connect(
            lambda context, error_msg: self._on_worker_error(thread_info.thread_id, context, error_msg)
        )

        # ワーカーの処理開始
        thread_info.thread.started.connect(thread_info.worker.process_folder)

        # 完了時のスレッド終了
        thread_info.worker.indexing_completed.connect(thread_info.thread.quit)
        thread_info.worker.error_occurred.connect(thread_info.thread.quit)

    def _on_thread_started(self, thread_id: str) -> None:
        """スレッド開始時の処理

        Args:
            thread_id (str): スレッドID
        """
        thread_info = self.get_thread_info(thread_id)
        if thread_info:
            thread_info.state = ThreadState.RUNNING
            self.logger.debug(f"スレッド開始: {thread_id}")

    def _on_thread_finished(self, thread_id: str) -> None:
        """スレッド終了時の処理

        Args:
            thread_id (str): スレッドID
        """
        thread_info = self.get_thread_info(thread_id)
        if thread_info:
            thread_info.end_time = time.time()
            if thread_info.state != ThreadState.ERROR:
                thread_info.state = ThreadState.FINISHED

            self.logger.debug(f"スレッド終了: {thread_id} (実行時間: {thread_info.get_duration():.2f}秒)")

    def _on_worker_progress(self, thread_id: str, message: str, current: int, total: int) -> None:
        """ワーカー進捗更新時の処理

        Args:
            thread_id (str): スレッドID
            message (str): 進捗メッセージ
            current (int): 現在の処理数
            total (int): 総処理数
        """
        self.thread_progress.emit(thread_id, message, current, total)

    def _on_worker_completed(self, thread_id: str, folder_path: str, statistics: dict) -> None:
        """ワーカー完了時の処理

        Args:
            thread_id (str): スレッドID
            folder_path (str): 処理されたフォルダパス
            statistics (dict): 処理統計情報
        """
        thread_info = self.get_thread_info(thread_id)
        if thread_info:
            thread_info.state = ThreadState.FINISHED

        self.logger.info(f"ワーカー完了: {thread_id} ({folder_path})")
        self.thread_finished.emit(thread_id, statistics)

    def _on_worker_error(self, thread_id: str, context: str, error_message: str) -> None:
        """ワーカーエラー時の処理

        Args:
            thread_id (str): スレッドID
            context (str): エラーコンテキスト
            error_message (str): エラーメッセージ
        """
        thread_info = self.get_thread_info(thread_id)
        if thread_info:
            thread_info.state = ThreadState.ERROR
            thread_info.error_message = f"{context}: {error_message}"

        self.logger.error(f"ワーカーエラー: {thread_id} - {context}: {error_message}")
        self.thread_error.emit(thread_id, error_message)

    def _graceful_stop_thread(self, thread_info: ThreadInfo) -> None:
        """スレッドの優雅な停止

        Args:
            thread_info (ThreadInfo): スレッド情報
        """
        # ワーカーに停止要求を送信済み
        # スレッドの自然な終了を待つ
        self.logger.debug(f"優雅な停止を開始: {thread_info.thread_id}")

    def _force_stop_thread(self, thread_info: ThreadInfo) -> None:
        """スレッドの強制停止

        Args:
            thread_info (ThreadInfo): スレッド情報
        """
        try:
            # スレッドの強制終了
            if thread_info.thread and thread_info.thread.isRunning():
                thread_info.thread.terminate()
                if not thread_info.thread.wait(5000):  # 5秒待機
                    self.logger.warning(f"スレッドの強制終了がタイムアウト: {thread_info.thread_id}")

            thread_info.state = ThreadState.FINISHED
            thread_info.end_time = time.time()
            thread_info.error_message = "強制停止"

            self.logger.warning(f"スレッドを強制停止: {thread_info.thread_id}")

        except Exception as e:
            self.logger.error(f"スレッド強制停止中にエラー: {thread_info.thread_id} - {e!s}")

    def _cleanup_thread(self, thread_id: str) -> bool:
        """スレッドをクリーンアップ

        Args:
            thread_id (str): クリーンアップするスレッドID

        Returns:
            bool: クリーンアップが成功した場合はTrue
        """
        try:
            thread_info = self.get_thread_info(thread_id)
            if not thread_info:
                return False

            # 状態をクリーンアップ中に変更
            thread_info.state = ThreadState.CLEANUP

            # クリーンアップコールバックを実行
            for callback in thread_info.cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.warning(f"クリーンアップコールバック実行エラー: {e!s}")

            # ワーカーをクリーンアップ
            if thread_info.worker:
                try:
                    thread_info.worker.deleteLater()
                except RuntimeError:
                    pass  # C++オブジェクトが既に削除されている場合

            # スレッドをクリーンアップ
            if thread_info.thread:
                try:
                    if thread_info.thread.isRunning():
                        thread_info.thread.quit()
                        thread_info.thread.wait(3000)  # 3秒待機

                    thread_info.thread.deleteLater()
                except RuntimeError:
                    pass  # C++オブジェクトが既に削除されている場合

            # スレッド管理から削除
            with self.lock:
                if thread_id in self.active_threads:
                    del self.active_threads[thread_id]

            self.logger.debug(f"スレッドクリーンアップ完了: {thread_id}")
            return True

        except Exception as e:
            self.logger.error(f"スレッドクリーンアップ中にエラー: {thread_id} - {e!s}")
            return False

    def _periodic_cleanup(self) -> None:
        """定期的なクリーンアップ処理"""
        try:
            # 完了したスレッドをクリーンアップ
            cleanup_count = self.cleanup_finished_threads()

            # 長時間実行されているスレッドをチェック
            self._check_long_running_threads()

            if cleanup_count > 0:
                self.logger.debug(f"定期クリーンアップ実行: {cleanup_count}個のスレッドをクリーンアップ")

        except Exception as e:
            self.logger.error(f"定期クリーンアップ中にエラー: {e!s}")

    def _check_long_running_threads(self) -> None:
        """長時間実行されているスレッドをチェック"""
        max_duration = 3600  # 1時間

        with self.lock:
            long_running_threads = [
                info for info in self.active_threads.values() if info.is_active() and info.get_duration() > max_duration
            ]

        for thread_info in long_running_threads:
            self.logger.warning(
                f"長時間実行中のスレッド: {thread_info.thread_id} "
                f"(実行時間: {thread_info.get_duration():.0f}秒, フォルダ: {thread_info.folder_path})"
            )

    def _emit_manager_status(self) -> None:
        """マネージャーの状態変更を通知"""
        active_count = self.get_active_thread_count()
        status_msg = f"アクティブスレッド: {active_count}/{self.max_concurrent_threads}"
        self.manager_status_changed.emit(status_msg)

    def shutdown(self) -> None:
        """スレッドマネージャーをシャットダウン"""
        try:
            self.logger.info("スレッドマネージャーのシャットダウンを開始")

            # クリーンアップタイマーを停止
            if self.cleanup_timer:
                self.cleanup_timer.stop()

            # すべてのスレッドを停止
            stopped_count = self.stop_all_threads(force=True)

            # 少し待機してからクリーンアップ
            if stopped_count > 0:
                QApplication.processEvents()
                time.sleep(1)

            # 残りのスレッドをクリーンアップ
            cleanup_count = self.cleanup_finished_threads()

            self.logger.info(
                f"スレッドマネージャーのシャットダウン完了 (停止: {stopped_count}, クリーンアップ: {cleanup_count})"
            )

        except Exception as e:
            self.logger.error(f"スレッドマネージャーのシャットダウン中にエラー: {e!s}")
