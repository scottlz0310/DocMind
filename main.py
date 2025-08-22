#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind - ローカルAI搭載ドキュメント検索アプリケーション
メインエントリーポイント

このファイルはアプリケーションの起動点として機能し、
必要な初期化処理を行った後、GUIアプリケーションを開始します。
"""

import sys
import os
import logging
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

from src.utils.config import Config
from src.utils.logging_config import setup_logging


def main():
    """
    メインアプリケーション関数
    
    アプリケーションの初期化、設定の読み込み、
    ログの設定を行い、GUIアプリケーションを起動します。
    """
    try:
        # アプリケーション情報の設定
        QCoreApplication.setApplicationName("DocMind")
        QCoreApplication.setApplicationVersion("1.0.0")
        QCoreApplication.setOrganizationName("DocMind")
        
        # Qtアプリケーションの作成
        app = QApplication(sys.argv)
        
        # 設定の初期化
        config = Config()
        
        # ログの設定
        setup_logging(config.get_log_level())
        logger = logging.getLogger(__name__)
        logger.info("DocMindアプリケーションを開始しています...")
        
        # データディレクトリの作成
        data_dir = Path(config.get_data_directory())
        data_dir.mkdir(exist_ok=True)
        (data_dir / "logs").mkdir(exist_ok=True)
        (data_dir / "models").mkdir(exist_ok=True)
        (data_dir / "whoosh_index").mkdir(exist_ok=True)
        
        logger.info(f"データディレクトリ: {data_dir}")
        
        # メインウィンドウの作成と表示
        from src.gui.main_window import MainWindow
        main_window = MainWindow()
        main_window.show()
        
        logger.info("メインウィンドウを表示しました")
        
        # アプリケーションのメインループを開始
        result = app.exec()
        
        logger.info("DocMindアプリケーションを終了しています...")
        return result
        
    except Exception as e:
        # 重大なエラーが発生した場合の処理
        error_msg = f"アプリケーションの初期化中にエラーが発生しました: {str(e)}"
        print(error_msg, file=sys.stderr)
        
        # ログが設定されている場合はログにも記録
        try:
            logger = logging.getLogger(__name__)
            logger.critical(error_msg, exc_info=True)
        except:
            pass
            
        return 1


if __name__ == "__main__":
    sys.exit(main())