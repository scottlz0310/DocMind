#!/usr/bin/env python3
"""
検索ワーカースレッド

検索処理を別スレッドで実行するワーカークラスを提供します。
"""

import logging
from datetime import datetime

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QWidget

from ....data.models import SearchQuery


class SearchWorkerThread(QThread):
    """
    検索処理を別スレッドで実行するワーカークラス

    UIをブロックすることなく検索処理を実行し、
    進捗更新とキャンセル機能を提供します。
    """

    # シグナル定義
    progress_updated = Signal(str, int)      # 進捗更新 (メッセージ, 進捗%)
    search_completed = Signal(list, float)   # 検索完了 (結果, 実行時間)
    search_error = Signal(str)               # 検索エラー (エラーメッセージ)

    def __init__(self, search_manager, query: SearchQuery, parent: QWidget | None = None):
        """
        検索ワーカーを初期化

        Args:
            search_manager: 検索マネージャー
            query: 検索クエリ
            parent: 親ウィジェット
        """
        super().__init__(parent)

        self.search_manager = search_manager
        self.query = query
        self.is_cancelled = False
        self.logger = logging.getLogger(__name__)

    def run(self) -> None:
        """検索処理を実行"""
        try:
            start_time = datetime.now()

            # 検索実行
            self.progress_updated.emit("検索を実行中...", 10)

            if self.is_cancelled:
                return

            results = self.search_manager.search(self.query)

            if self.is_cancelled:
                return

            self.progress_updated.emit("結果を処理中...", 90)

            # 実行時間を計算
            execution_time = (datetime.now() - start_time).total_seconds()

            self.progress_updated.emit("完了", 100)
            self.search_completed.emit(results, execution_time)

        except Exception as e:
            if not self.is_cancelled:
                self.logger.error(f"検索スレッドエラー: {e}")
                self.search_error.emit(str(e))

    def cancel(self) -> None:
        """検索をキャンセル"""
        self.is_cancelled = True
        self.logger.debug("検索スレッドのキャンセルが要求されました")
