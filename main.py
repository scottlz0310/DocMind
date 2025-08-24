#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind - ローカルAI搭載ドキュメント検索アプリケーション
メインエントリーポイント

このファイルはアプリケーションの起動点として機能し、
必要な初期化処理を行った後、GUIアプリケーションを開始します。
包括的エラーハンドリングと優雅な劣化機能を統合しています。
"""

import sys
import os
import logging
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QCoreApplication

from src.utils.config import Config
from src.utils.logging_config import setup_logging
from src.utils.error_handler import setup_global_exception_handler, get_global_error_handler
from src.utils.graceful_degradation import setup_component_monitoring, get_global_degradation_manager
from src.utils.cache_manager import initialize_cache_manager
from src.utils.background_processor import initialize_task_manager
from src.utils.memory_manager import initialize_memory_manager
from src.utils.updater import UpdateManager


def main():
    """
    メインアプリケーション関数
    
    アプリケーションの初期化、設定の読み込み、
    ログの設定を行い、GUIアプリケーションを起動します。
    包括的エラーハンドリングと優雅な劣化機能を含みます。
    """
    app = None
    logger = None
    
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
        setup_logging(
            level=config.get_log_level(),
            log_file=config.get_log_file_path()
        )
        logger = logging.getLogger(__name__)
        logger.info("DocMindアプリケーションを開始しています...")
        
        # グローバル例外ハンドラーの設定
        setup_global_exception_handler()
        logger.info("グローバル例外ハンドラーを設定しました")
        
        # コンポーネント監視の設定
        setup_component_monitoring()
        logger.info("コンポーネント監視を設定しました")
        
        # データディレクトリの作成
        data_dir = Path(config.get_data_directory())
        _ensure_directories_exist(data_dir, logger)
        
        # パフォーマンス最適化コンポーネントの初期化
        cache_manager = initialize_cache_manager(str(data_dir / "cache"))
        task_manager = initialize_task_manager()
        memory_manager = initialize_memory_manager()
        
        # バックグラウンド処理を開始
        task_manager.start_all()
        memory_manager.start()
        
        logger.info("パフォーマンス最適化コンポーネントを初期化しました")
        
        logger.info(f"データディレクトリ: {data_dir}")
        
        # エラーハンドラーの初期化
        error_handler = get_global_error_handler()
        _setup_application_recovery_handlers(error_handler, logger)
        
        # 更新マネージャーの初期化
        update_manager = UpdateManager(config)
        logger.info("更新マネージャーを初期化しました")
        
        # メインウィンドウの作成と表示
        try:
            from src.gui.main_window import MainWindow
            main_window = MainWindow()
            
            # 更新マネージャーは将来の機能として保持
            # main_window.set_update_manager(update_manager)
            
            main_window.show()
            logger.info("メインウィンドウを表示しました")
        except Exception as gui_error:
            logger.error(f"GUIの初期化に失敗しました: {gui_error}")
            _show_critical_error_dialog(
                "GUI初期化エラー",
                f"ユーザーインターフェースの初期化に失敗しました。\n\n詳細: {gui_error}",
                app
            )
            return 1
        
        # システム健全性の初期チェック
        _perform_initial_health_check(logger)
        
        # アプリケーションのメインループを開始
        logger.info("アプリケーションのメインループを開始します")
        result = app.exec()
        
        # クリーンアップ処理
        logger.info("DocMindアプリケーションを終了しています...")
        
        # メインウィンドウのクリーンアップ
        try:
            if 'main_window' in locals() and main_window:
                main_window.close()
            logger.info("メインウィンドウをクリーンアップしました")
        except Exception as cleanup_error:
            logger.error(f"メインウィンドウクリーンアップでエラー: {cleanup_error}")
        
        # パフォーマンス最適化コンポーネントの停止（順序重要）
        try:
            logger.info("バックグラウンドコンポーネントの停止を開始")
            memory_manager.stop()
            logger.info("メモリマネージャーを停止")
            task_manager.stop_all()
            logger.info("タスクマネージャーを停止")
            cache_manager.save_persistent_caches()
            logger.info("パフォーマンス最適化コンポーネントを停止しました")
        except Exception as cleanup_error:
            logger.error(f"クリーンアップ処理でエラー: {cleanup_error}")
        
        # 少し待機してからQt終了
        import time
        time.sleep(0.5)
        
        # Qtアプリケーションの終了処理
        try:
            if app:
                app.quit()
        except Exception as cleanup_error:
            logger.error(f"Qtアプリケーション終了処理でエラー: {cleanup_error}")
        
        return result
        
    except Exception as e:
        # 重大なエラーが発生した場合の処理
        error_msg = f"アプリケーションの初期化中に重大なエラーが発生しました: {str(e)}"
        print(error_msg, file=sys.stderr)
        
        # ログが設定されている場合はログにも記録
        if logger:
            logger.critical(error_msg, exc_info=True)
        
        # エラーハンドラーが利用可能な場合は詳細レポートを生成
        try:
            error_handler = get_global_error_handler()
            error_handler.handle_exception(
                e, 
                "アプリケーション初期化", 
                "アプリケーションの起動に失敗しました。システム管理者にお問い合わせください。",
                attempt_recovery=False
            )
        except:
            pass
        
        # ユーザーにエラーダイアログを表示
        _show_critical_error_dialog(
            "起動エラー",
            f"DocMindの起動に失敗しました。\n\n{error_msg}",
            app
        )
        
        return 1


def _ensure_directories_exist(data_dir: Path, logger: logging.Logger) -> None:
    """
    必要なディレクトリが存在することを確認
    
    Args:
        data_dir: データディレクトリのパス
        logger: ロガーインスタンス
    """
    directories = [
        data_dir,
        data_dir / "logs",
        data_dir / "models", 
        data_dir / "whoosh_index",
        data_dir / "error_reports",
        data_dir / "cache"
    ]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"ディレクトリを確認/作成: {directory}")
        except Exception as e:
            logger.error(f"ディレクトリの作成に失敗: {directory} - {e}")
            raise


def _setup_application_recovery_handlers(error_handler, logger: logging.Logger) -> None:
    """
    アプリケーション固有の回復ハンドラーを設定
    
    Args:
        error_handler: エラーハンドラーインスタンス
        logger: ロガーインスタンス
    """
    from src.utils.exceptions import ConfigurationError, FileSystemError
    
    def config_recovery_handler(exc: Exception, error_info: dict) -> bool:
        """設定エラーからの回復処理"""
        try:
            logger.info("設定エラーからの回復を試行中...")
            # デフォルト設定で再初期化を試行
            from src.utils.config import Config
            config = Config()
            config.reset_to_defaults()
            logger.info("設定をデフォルト値にリセットしました")
            return True
        except Exception as recovery_error:
            logger.error(f"設定回復に失敗: {recovery_error}")
            return False
    
    def filesystem_recovery_handler(exc: Exception, error_info: dict) -> bool:
        """ファイルシステムエラーからの回復処理"""
        try:
            logger.info("ファイルシステムエラーからの回復を試行中...")
            # 基本ディレクトリの再作成を試行
            from src.utils.config import Config
            config = Config()
            data_dir = Path(config.get_data_directory())
            _ensure_directories_exist(data_dir, logger)
            logger.info("ディレクトリ構造を復旧しました")
            return True
        except Exception as recovery_error:
            logger.error(f"ファイルシステム回復に失敗: {recovery_error}")
            return False
    
    error_handler.register_recovery_handler(ConfigurationError, config_recovery_handler)
    error_handler.register_recovery_handler(FileSystemError, filesystem_recovery_handler)
    
    logger.info("アプリケーション回復ハンドラーを設定しました")


def _perform_initial_health_check(logger: logging.Logger) -> None:
    """
    アプリケーション起動時の初期健全性チェック
    
    Args:
        logger: ロガーインスタンス
    """
    try:
        degradation_manager = get_global_degradation_manager()
        health = degradation_manager.get_system_health()
        
        logger.info(f"システム健全性チェック完了:")
        logger.info(f"  - 総コンポーネント数: {health['total_components']}")
        logger.info(f"  - 健全: {health['healthy']}")
        logger.info(f"  - 劣化: {health['degraded']}")
        logger.info(f"  - 失敗: {health['failed']}")
        logger.info(f"  - 全体的な健全性: {health['overall_health']}")
        
        if health['overall_health'] != 'healthy':
            logger.warning("一部のコンポーネントに問題があります。機能が制限される可能性があります。")
            
    except Exception as e:
        logger.error(f"健全性チェックに失敗: {e}")


def _show_critical_error_dialog(title: str, message: str, app: QApplication = None) -> None:
    """
    重大なエラーダイアログを表示
    
    Args:
        title: ダイアログのタイトル
        message: エラーメッセージ
        app: Qtアプリケーションインスタンス
    """
    try:
        if app is None:
            # アプリケーションが作成されていない場合は作成
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
        
    except Exception as dialog_error:
        # ダイアログの表示にも失敗した場合はコンソールに出力
        print(f"エラーダイアログの表示に失敗: {dialog_error}", file=sys.stderr)
        print(f"元のエラー - {title}: {message}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())