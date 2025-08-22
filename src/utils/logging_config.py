# -*- coding: utf-8 -*-
"""
ログ設定モジュール

アプリケーション全体のログ設定を管理し、
統一されたログフォーマットとレベル制御を提供します。
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    アプリケーションのログ設定を初期化
    
    Args:
        level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: ログファイルのパス（省略時はデフォルトパスを使用）
        max_bytes: ログファイルの最大サイズ（バイト）
        backup_count: 保持するバックアップファイル数
    """
    
    # ログレベルの設定
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # ログフォーマットの定義
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 既存のハンドラーをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # コンソールハンドラーの追加
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラーの追加
    if log_file is None:
        # デフォルトのログファイルパス
        log_file = os.path.join("docmind_data", "logs", "docmind.log")
    
    # ログディレクトリの作成
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # ローテーティングファイルハンドラーの追加
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 初期ログメッセージ
    logger = logging.getLogger(__name__)
    logger.info(f"ログシステムを初期化しました - レベル: {level}")
    logger.info(f"ログファイル: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得
    
    Args:
        name: ロガー名（通常は__name__を使用）
        
    Returns:
        ロガーインスタンス
    """
    return logging.getLogger(name)


class LoggerMixin:
    """
    ログ機能を提供するミックスインクラス
    
    このクラスを継承することで、簡単にログ機能を追加できます。
    """
    
    @property
    def logger(self) -> logging.Logger:
        """
        クラス専用のロガーを取得
        
        Returns:
            ロガーインスタンス
        """
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            )
        return self._logger