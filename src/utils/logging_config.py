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
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True
) -> None:
    """
    アプリケーションのログ設定を初期化
    
    Args:
        level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: ログファイルのパス（省略時はデフォルトパスを使用）
        max_bytes: ログファイルの最大サイズ（バイト）
        backup_count: 保持するバックアップファイル数
        enable_console: コンソール出力を有効にするか
        enable_file: ファイル出力を有効にするか
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
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # ファイルハンドラーの追加
    if enable_file:
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
    if enable_file and log_file:
        logger.info(f"ログファイル: {log_file}")


def setup_logging_from_config(config) -> None:
    """
    設定オブジェクトからログ設定を初期化
    
    Args:
        config: 設定管理オブジェクト
    """
    setup_logging(
        level=config.get_log_level(),
        log_file=config.get_log_file_path(),
        enable_console=config.is_console_logging_enabled(),
        enable_file=config.is_file_logging_enabled()
    )


def reconfigure_logging(
    level: Optional[str] = None,
    enable_console: Optional[bool] = None,
    enable_file: Optional[bool] = None
) -> None:
    """
    実行時にログ設定を再構成
    
    Args:
        level: 新しいログレベル
        enable_console: コンソール出力の有効/無効
        enable_file: ファイル出力の有効/無効
    """
    root_logger = logging.getLogger()
    
    # ログレベルの変更
    if level is not None:
        log_level = getattr(logging, level.upper(), logging.INFO)
        root_logger.setLevel(log_level)
        
        # 全ハンドラーのレベルも更新
        for handler in root_logger.handlers:
            handler.setLevel(log_level)
    
    # ハンドラーの有効/無効切り替え
    if enable_console is not None or enable_file is not None:
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.handlers.RotatingFileHandler):
                # コンソールハンドラー
                if enable_console is False:
                    root_logger.removeHandler(handler)
            elif isinstance(handler, logging.handlers.RotatingFileHandler):
                # ファイルハンドラー
                if enable_file is False:
                    root_logger.removeHandler(handler)
        
        # 必要に応じて新しいハンドラーを追加
        if enable_console is True and not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler) for h in root_logger.handlers):
            formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler = logging.StreamHandler()
            console_handler.setLevel(root_logger.level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)


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