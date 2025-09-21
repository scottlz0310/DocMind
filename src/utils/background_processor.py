"""
バックグラウンド処理モジュール

このモジュールは、ノンブロッキング操作のためのバックグラウンド処理機能を提供します。
進捗追跡、タスクキューイング、並行処理をサポートします。
"""

import queue
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..utils.exceptions import BackgroundProcessingError
from ..utils.logging_config import LoggerMixin


class TaskStatus(Enum):
    """タスクステータス列挙型"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """タスク優先度列挙型"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ProgressInfo:
    """進捗情報を表すデータクラス"""

    current: int = 0
    total: int = 0
    message: str = ""
    percentage: float = 0.0

    def update(self, current: int, total: int, message: str = "") -> None:
        """進捗情報を更新"""
        self.current = current
        self.total = total
        self.message = message
        self.percentage = (current / total * 100) if total > 0 else 0.0


@dataclass
class BackgroundTask:
    """バックグラウンドタスクを表すデータクラス"""

    task_id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    progress: ProgressInfo = field(default_factory=ProgressInfo)
    result: Any = None
    error: Exception | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    progress_callback: Callable[[ProgressInfo], None] | None = None
    completion_callback: Callable[["BackgroundTask"], None] | None = None

    def __lt__(self, other: "BackgroundTask") -> bool:
        """優先度による比較（優先度キューで使用）"""
        return self.priority.value > other.priority.value


class ProgressTracker(LoggerMixin):
    """
    進捗追跡クラス

    長時間実行される操作の進捗を追跡し、コールバック通知を提供します。
    """

    def __init__(
        self,
        task_id: str,
        total_steps: int,
        progress_callback: Callable[[ProgressInfo], None] | None = None,
    ):
        """
        進捗追跡を初期化

        Args:
            task_id: タスクID
            total_steps: 総ステップ数
            progress_callback: 進捗更新時のコールバック
        """
        self.task_id = task_id
        self.progress = ProgressInfo(total=total_steps)
        self.progress_callback = progress_callback
        self._lock = threading.Lock()

    def update(self, current_step: int, message: str = "") -> None:
        """
        進捗を更新

        Args:
            current_step: 現在のステップ
            message: 進捗メッセージ
        """
        with self._lock:
            self.progress.update(current_step, self.progress.total, message)

            if self.progress_callback:
                try:
                    self.progress_callback(self.progress)
                except Exception as e:
                    self.logger.warning(f"進捗コールバックでエラー: {e}")

    def increment(self, message: str = "") -> None:
        """進捗を1つ進める"""
        with self._lock:
            self.update(self.progress.current + 1, message)

    def complete(self, message: str = "完了") -> None:
        """進捗を完了状態にする"""
        with self._lock:
            self.update(self.progress.total, message)


class BackgroundProcessor(LoggerMixin):
    """
    バックグラウンド処理管理クラス

    タスクキューイング、並行処理、進捗追跡機能を提供します。
    """

    """
    バックグラウンド処理管理クラス

    タスクキューイング、並行処理、進捗追跡機能を提供します。
    """

    def __init__(self, max_workers: int = 4, queue_size: int = 100):
        """
        バックグラウンドプロセッサーを初期化

        Args:
            max_workers: 最大ワーカー数
            queue_size: キューの最大サイズ
        """
        self.max_workers = max_workers
        self.queue_size = queue_size

        # タスクキューと管理
        self._task_queue = queue.PriorityQueue(maxsize=queue_size)
        self._tasks: dict[str, BackgroundTask] = {}
        self._futures: dict[str, Future] = {}

        # スレッドプールエグゼキューター
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        # 制御フラグ
        self._running = False
        self._shutdown = False

        # ロック
        self._lock = threading.RLock()

        # ワーカースレッド
        self._worker_thread: threading.Thread | None = None

        self.logger.info(
            f"バックグラウンドプロセッサーを初期化: ワーカー数={max_workers}"
        )

    def __del__(self):
        """デストラクタでリソースをクリーンアップ"""
        try:
            self.stop(timeout=1.0)
        except Exception:
            pass

    def start(self) -> None:
        """バックグラウンド処理を開始"""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._shutdown = False

            # ワーカースレッドを開始
            self._worker_thread = threading.Thread(
                target=self._worker_loop, daemon=True
            )
            self._worker_thread.start()

            self.logger.info("バックグラウンド処理を開始しました")

    def stop(self, timeout: float = 30.0) -> None:
        """
        バックグラウンド処理を停止

        Args:
            timeout: 停止タイムアウト（秒）
        """
        with self._lock:
            if not self._running:
                return

            self._shutdown = True
            self._running = False

        # 実行中のタスクをキャンセル
        for task_id, future in list(self._futures.items()):
            if not future.done():
                future.cancel()
                task = self._tasks.get(task_id)
                if task:
                    task.status = TaskStatus.CANCELLED

        # ワーカースレッドの終了を待機
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=min(timeout, 5.0))

        # エグゼキューターをシャットダウン
        try:
            self._executor.shutdown(wait=False)
        except Exception as e:
            self.logger.warning(f"エグゼキューターシャットダウンでエラー: {e}")

        self.logger.info("バックグラウンド処理を停止しました")

    def submit_task(self, task: BackgroundTask) -> str:
        """
        タスクをキューに追加

        Args:
            task: 実行するタスク

        Returns:
            タスクID

        Raises:
            BackgroundProcessingError: キューが満杯の場合
        """
        if self._shutdown:
            raise BackgroundProcessingError("プロセッサーはシャットダウン中です")

        try:
            with self._lock:
                self._tasks[task.task_id] = task
                self._task_queue.put_nowait(task)

            self.logger.debug(f"タスクをキューに追加: {task.name} (ID: {task.task_id})")
            return task.task_id

        except queue.Full:
            raise BackgroundProcessingError("タスクキューが満杯です") from None

    def create_and_submit_task(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        progress_callback: Callable[[ProgressInfo], None] | None = None,
        completion_callback: Callable[[BackgroundTask], None] | None = None,
    ) -> str:
        """
        タスクを作成してキューに追加

        Args:
            name: タスク名
            func: 実行する関数
            args: 関数の引数
            kwargs: 関数のキーワード引数
            priority: タスク優先度
            progress_callback: 進捗コールバック
            completion_callback: 完了コールバック

        Returns:
            タスクID
        """
        import uuid

        task_id = str(uuid.uuid4())
        task = BackgroundTask(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
        )

        return self.submit_task(task)

    def get_task_status(self, task_id: str) -> BackgroundTask | None:
        """
        タスクの状態を取得

        Args:
            task_id: タスクID

        Returns:
            タスク情報、または None
        """
        with self._lock:
            return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """
        タスクをキャンセル

        Args:
            task_id: タスクID

        Returns:
            キャンセルに成功した場合True
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                return False

            # 実行中の場合はFutureをキャンセル
            future = self._futures.get(task_id)
            if future and not future.done():
                cancelled = future.cancel()
                if cancelled:
                    task.status = TaskStatus.CANCELLED
                    self.logger.debug(f"タスクをキャンセル: {task.name}")
                return cancelled

            # まだ実行されていない場合
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True

            return False

    def get_queue_stats(self) -> dict[str, Any]:
        """キューの統計情報を取得"""
        with self._lock:
            pending_count = sum(
                1 for task in self._tasks.values() if task.status == TaskStatus.PENDING
            )
            running_count = sum(
                1 for task in self._tasks.values() if task.status == TaskStatus.RUNNING
            )
            completed_count = sum(
                1
                for task in self._tasks.values()
                if task.status == TaskStatus.COMPLETED
            )
            failed_count = sum(
                1 for task in self._tasks.values() if task.status == TaskStatus.FAILED
            )

            return {
                "queue_size": self._task_queue.qsize(),
                "max_queue_size": self.queue_size,
                "total_tasks": len(self._tasks),
                "pending": pending_count,
                "running": running_count,
                "completed": completed_count,
                "failed": failed_count,
                "max_workers": self.max_workers,
                "is_running": self._running,
            }

    def _worker_loop(self) -> None:
        """ワーカーループ（別スレッドで実行）"""
        self.logger.debug("ワーカーループを開始")

        while not self._shutdown:
            try:
                # タスクを取得（タイムアウト付き）
                try:
                    task = self._task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if self._shutdown:
                    break

                # タスクを実行
                self._execute_task(task)

            except Exception as e:
                self.logger.error(f"ワーカーループでエラー: {e}")

        self.logger.debug("ワーカーループを終了")

    def _execute_task(self, task: BackgroundTask) -> None:
        """
        タスクを実行

        Args:
            task: 実行するタスク
        """
        try:
            # タスクステータスを更新
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

            self.logger.debug(f"タスク実行開始: {task.name}")

            # 進捗トラッカーを作成
            progress_tracker = ProgressTracker(
                task.task_id,
                100,
                task.progress_callback,  # デフォルトの総ステップ数
            )

            # タスクの引数に進捗トラッカーを追加（関数がサポートしている場合のみ）
            enhanced_kwargs = task.kwargs.copy()

            # 関数のシグネチャをチェックして進捗トラッカーをサポートしているか確認
            import inspect

            sig = inspect.signature(task.func)
            if "progress_tracker" in sig.parameters:
                enhanced_kwargs["progress_tracker"] = progress_tracker

            # Futureを作成して実行
            future = self._executor.submit(task.func, *task.args, **enhanced_kwargs)

            with self._lock:
                self._futures[task.task_id] = future

            # 結果を待機
            try:
                result = future.result()
                task.result = result
                task.status = TaskStatus.COMPLETED
                self.logger.debug(f"タスク実行完了: {task.name}")

            except Exception as e:
                task.error = e
                task.status = TaskStatus.FAILED
                self.logger.error(f"タスク実行失敗: {task.name} - {e}")

            # 完了時刻を記録
            task.completed_at = time.time()

            # 完了コールバックを呼び出し
            if task.completion_callback:
                try:
                    task.completion_callback(task)
                except Exception as e:
                    self.logger.warning(f"完了コールバックでエラー: {e}")

        except Exception as e:
            task.error = e
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            self.logger.error(f"タスク実行でエラー: {task.name} - {e}")

        finally:
            # Futureを削除
            with self._lock:
                self._futures.pop(task.task_id, None)


class TaskManager(LoggerMixin):
    """
    タスク管理クラス

    複数のバックグラウンドプロセッサーを管理し、
    アプリケーション全体のタスク実行を調整します。
    """

    def __init__(self):
        """タスクマネージャーを初期化"""
        # 異なる種類のタスク用のプロセッサー
        self.indexing_processor = BackgroundProcessor(max_workers=2, queue_size=50)
        self.search_processor = BackgroundProcessor(max_workers=3, queue_size=100)
        self.file_processor = BackgroundProcessor(max_workers=2, queue_size=50)

        self._processors = {
            "indexing": self.indexing_processor,
            "search": self.search_processor,
            "file": self.file_processor,
        }

        self.logger.info("タスクマネージャーを初期化しました")

    def start_all(self) -> None:
        """すべてのプロセッサーを開始"""
        for name, processor in self._processors.items():
            processor.start()
            self.logger.info(f"{name}プロセッサーを開始")

    def stop_all(self, timeout: float = 30.0) -> None:
        """すべてのプロセッサーを停止"""
        for name, processor in self._processors.items():
            processor.stop(timeout=timeout)
            self.logger.info(f"{name}プロセッサーを停止")

    def submit_indexing_task(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        progress_callback: Callable[[ProgressInfo], None] | None = None,
        completion_callback: Callable[[BackgroundTask], None] | None = None,
    ) -> str:
        """インデックス化タスクを送信"""
        return self.indexing_processor.create_and_submit_task(
            name, func, args, kwargs, priority, progress_callback, completion_callback
        )

    def submit_search_task(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.HIGH,
        progress_callback: Callable[[ProgressInfo], None] | None = None,
        completion_callback: Callable[[BackgroundTask], None] | None = None,
    ) -> str:
        """検索タスクを送信"""
        return self.search_processor.create_and_submit_task(
            name, func, args, kwargs, priority, progress_callback, completion_callback
        )

    def submit_file_task(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        progress_callback: Callable[[ProgressInfo], None] | None = None,
        completion_callback: Callable[[BackgroundTask], None] | None = None,
    ) -> str:
        """ファイル処理タスクを送信"""
        return self.file_processor.create_and_submit_task(
            name, func, args, kwargs, priority, progress_callback, completion_callback
        )

    def get_task_status(self, task_id: str) -> BackgroundTask | None:
        """タスクの状態を取得"""
        for processor in self._processors.values():
            task = processor.get_task_status(task_id)
            if task:
                return task
        return None

    def cancel_task(self, task_id: str) -> bool:
        """タスクをキャンセル"""
        for processor in self._processors.values():
            if processor.cancel_task(task_id):
                return True
        return False

    def get_all_stats(self) -> dict[str, Any]:
        """すべてのプロセッサーの統計情報を取得"""
        return {
            name: processor.get_queue_stats()
            for name, processor in self._processors.items()
        }


# グローバルタスクマネージャーインスタンス
_global_task_manager: TaskManager | None = None


def get_global_task_manager() -> TaskManager:
    """グローバルタスクマネージャーを取得"""
    global _global_task_manager
    if _global_task_manager is None:
        _global_task_manager = TaskManager()
    return _global_task_manager


def initialize_task_manager() -> TaskManager:
    """タスクマネージャーを初期化"""
    global _global_task_manager
    _global_task_manager = TaskManager()
    return _global_task_manager
