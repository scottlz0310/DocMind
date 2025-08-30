#!/usr/bin/env python3
"""
非同期処理管理マネージャー

フォルダツリーの非同期処理を統合管理するマネージャークラスです。
スレッド管理、エラーハンドリング、リソース管理を担当します。
"""

import logging

from PySide6.QtCore import QObject, Qt, QThread, Signal

from .folder_load_worker import FolderLoadWorker


class AsyncOperationManager(QObject):
    """
    非同期処理管理マネージャー

    フォルダツリーの非同期処理を統合管理し、
    スレッドの安全な作成・実行・終了を保証します。
    """

    # シグナル定義
    folder_loaded = Signal(str, list)  # path, subdirectories
    load_error = Signal(str, str)      # path, error_message
    load_finished = Signal()

    def __init__(self, parent: QObject | None = None):
        """
        非同期処理管理マネージャーの初期化

        Args:
            parent: 親オブジェクト
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)

        # ワーカースレッド管理
        self.load_worker: QThread | None = None
        self.folder_worker: FolderLoadWorker | None = None

        self.logger.info("非同期処理管理マネージャーが初期化されました")

    def start_folder_loading(self, root_path: str, max_depth: int = 2):
        """
        フォルダ読み込みを開始します

        Args:
            root_path: 読み込み対象のルートパス
            max_depth: 最大読み込み深度
        """
        try:
            # 既存のワーカーを確実にクリーンアップ
            self.cleanup_workers()

            # 新しいワーカー作成
            self.load_worker = QThread()
            self.folder_worker = FolderLoadWorker(root_path, max_depth)

            # ワーカーをスレッドに移動
            self.folder_worker.moveToThread(self.load_worker)

            # シグナル接続（安全な接続方法）
            self._connect_worker_signals()

            # スレッド開始
            self.load_worker.start()

            self.logger.info(f"フォルダ読み込み開始: {root_path}")

        except Exception as e:
            self.logger.error(f"フォルダ読み込み開始エラー: {e}")
            self.cleanup_workers()
            self.load_error.emit(root_path, f"読み込み開始エラー: {str(e)}")

    def _connect_worker_signals(self):
        """ワーカーのシグナルを接続します"""
        if not self.load_worker or not self.folder_worker:
            return

        # スレッド管理シグナル
        self.load_worker.started.connect(
            self.folder_worker.do_work, Qt.QueuedConnection
        )
        self.folder_worker.finished.connect(
            self.load_worker.quit, Qt.QueuedConnection
        )
        self.folder_worker.finished.connect(
            self.folder_worker.deleteLater, Qt.QueuedConnection
        )
        self.load_worker.finished.connect(
            self.load_worker.deleteLater, Qt.QueuedConnection
        )

        # アプリケーションシグナル転送
        self.folder_worker.folder_loaded.connect(
            self.folder_loaded.emit, Qt.QueuedConnection
        )
        self.folder_worker.load_error.connect(
            self.load_error.emit, Qt.QueuedConnection
        )
        self.folder_worker.finished.connect(
            self._on_load_finished, Qt.QueuedConnection
        )

    def _on_load_finished(self):
        """読み込み完了時の処理"""
        self.logger.info("フォルダ読み込み完了")
        self.load_finished.emit()

    def stop_folder_loading(self):
        """フォルダ読み込みを停止します"""
        if self.folder_worker:
            self.folder_worker.stop()
            self.logger.info("フォルダ読み込み停止要求")

    def cleanup_workers(self):
        """ワーカーをクリーンアップします"""
        try:
            # フォルダワーカーの停止
            if self.folder_worker:
                self.folder_worker.stop()
                self._disconnect_worker_signals()
                self.folder_worker = None

            # ロードワーカーの停止
            if self.load_worker:
                if self.load_worker.isRunning():
                    # スレッドの安全な終了
                    self.load_worker.quit()

                    # スレッドが終了するまで待機（最大3秒）
                    if not self.load_worker.wait(3000):
                        self.logger.warning("ワーカースレッドの終了を強制終了します")
                        self.load_worker.terminate()
                        self.load_worker.wait(1000)

                    # スレッドの状態確認
                    if self.load_worker.isRunning():
                        self.logger.error("スレッドの終了に失敗しました")

                self.load_worker = None

            self.logger.debug("ワーカークリーンアップ完了")

        except Exception as e:
            self.logger.error(f"ワーカークリーンアップ中にエラーが発生しました: {e}")
        finally:
            # 確実にNoneに設定
            self.folder_worker = None
            self.load_worker = None

    def _disconnect_worker_signals(self):
        """ワーカーのシグナル接続を切断します"""
        if not self.folder_worker:
            return

        try:
            self.folder_worker.folder_loaded.disconnect()
            self.folder_worker.load_error.disconnect()
            self.folder_worker.finished.disconnect()
        except (TypeError, RuntimeError):
            # シグナルが接続されていない場合のエラーは無視
            pass

    def is_loading(self) -> bool:
        """
        現在読み込み中かどうかを確認します

        Returns:
            読み込み中の場合True
        """
        return (self.load_worker is not None and
                self.load_worker.isRunning() and
                self.folder_worker is not None)

    def __del__(self):
        """デストラクタ"""
        self.cleanup_workers()
