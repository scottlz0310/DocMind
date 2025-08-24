#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MainWindow初期化テスト

修正されたMainWindowクラスが正常に初期化できることを確認する簡単なテスト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_mainwindow_initialization():
    """MainWindowの初期化テスト"""
    try:
        # QApplicationを作成（ヘッドレスモード）
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        
        from PySide6.QtWidgets import QApplication
        from src.gui.main_window import MainWindow
        
        # アプリケーションインスタンスを作成
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        print("QApplicationが作成されました")
        
        # MainWindowを初期化
        print("MainWindowを初期化中...")
        main_window = MainWindow()
        print("✓ MainWindowが正常に初期化されました")
        
        # 基本的な属性の確認
        assert hasattr(main_window, 'logger'), "loggerプロパティが存在しません"
        assert hasattr(main_window, 'config'), "configプロパティが存在しません"
        
        # LoggerMixinのloggerプロパティが使用されていることを確認
        logger = main_window.logger
        assert logger is not None, "loggerがNoneです"
        print("✓ LoggerMixinのloggerプロパティが正常に動作しています")
        
        # ウィンドウタイトルの確認
        title = main_window.windowTitle()
        assert title == "DocMind - ローカルドキュメント検索", f"ウィンドウタイトルが正しくありません: {title}"
        print("✓ ウィンドウタイトルが正しく設定されています")
        
        # 基本的なウィジェットの存在確認
        assert hasattr(main_window, 'folder_tree_container'), "folder_tree_containerが存在しません"
        assert hasattr(main_window, 'search_results_widget'), "search_results_widgetが存在しません"
        assert hasattr(main_window, 'preview_widget'), "preview_widgetが存在しません"
        assert hasattr(main_window, 'search_interface'), "search_interfaceが存在しません"
        print("✓ 基本的なウィジェットが正常に作成されています")
        
        # メニューバーの確認
        menu_bar = main_window.menuBar()
        assert menu_bar is not None, "メニューバーが存在しません"
        print("✓ メニューバーが正常に作成されています")
        
        # ステータスバーの確認
        status_bar = main_window.statusBar()
        assert status_bar is not None, "ステータスバーが存在しません"
        print("✓ ステータスバーが正常に作成されています")
        
        # クリーンアップ
        main_window.close()
        main_window.deleteLater()
        
        print("✓ MainWindow初期化テストが完了しました")
        return True
        
    except Exception as e:
        print(f"✗ MainWindow初期化テストが失敗しました: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_manager_initialization():
    """DatabaseManagerの初期化テスト"""
    try:
        import tempfile
        from src.data.database import DatabaseManager
        
        print("DatabaseManagerを初期化中...")
        
        # 一時ディレクトリでテスト
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            
            # DatabaseManagerを初期化
            db_manager = DatabaseManager(str(db_path))
            print("✓ DatabaseManagerが正常に初期化されました")
            
            # initialize()メソッドの存在確認
            assert hasattr(db_manager, 'initialize'), "initialize()メソッドが存在しません"
            print("✓ initialize()メソッドが存在します")
            
            # 冪等性のテスト（複数回呼び出し）
            db_manager.initialize()
            db_manager.initialize()
            print("✓ initialize()メソッドの冪等性が確認されました")
            
            # 初期化フラグの確認
            assert hasattr(db_manager, '_initialized'), "_initializedフラグが存在しません"
            assert db_manager._initialized is True, "初期化フラグがTrueになっていません"
            print("✓ 初期化フラグが正しく設定されています")
            
            # 健全性チェック
            health_status = db_manager.health_check()
            assert health_status is True, "データベースの健全性チェックが失敗しました"
            print("✓ データベースの健全性チェックが成功しました")
            
            # クリーンアップ
            db_manager.close()
        
        print("✓ DatabaseManager初期化テストが完了しました")
        return True
        
    except Exception as e:
        print(f"✗ DatabaseManager初期化テストが失敗しました: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_data_dir_property():
    """Configクラスのdata_dirプロパティテスト"""
    try:
        from src.utils.config import Config
        from pathlib import Path
        
        print("Configクラスをテスト中...")
        
        # Configインスタンスを作成
        config = Config()
        print("✓ Configが正常に初期化されました")
        
        # data_dirプロパティの存在確認
        assert hasattr(config, 'data_dir'), "data_dirプロパティが存在しません"
        print("✓ data_dirプロパティが存在します")
        
        # data_dirプロパティの型確認
        data_dir = config.data_dir
        assert isinstance(data_dir, Path), f"data_dirプロパティがPathオブジェクトではありません: {type(data_dir)}"
        print("✓ data_dirプロパティがPathオブジェクトを返します")
        
        # exists()メソッドが呼び出せることを確認
        try:
            exists_result = data_dir.exists()
            print(f"✓ data_dir.exists()が正常に動作します: {exists_result}")
        except AttributeError as e:
            raise AssertionError(f"data_dir.exists()が呼び出せません: {e}")
        
        # 既存のget_data_directory()メソッドとの互換性確認
        assert hasattr(config, 'get_data_directory'), "get_data_directory()メソッドが存在しません"
        data_dir_str = config.get_data_directory()
        assert isinstance(data_dir_str, str), "get_data_directory()が文字列を返しません"
        assert str(data_dir) == data_dir_str, "data_dirプロパティとget_data_directory()の結果が一致しません"
        print("✓ 既存のget_data_directory()メソッドとの互換性が確認されました")
        
        print("✓ Config data_dirプロパティテストが完了しました")
        return True
        
    except Exception as e:
        print(f"✗ Config data_dirプロパティテストが失敗しました: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メインテスト関数"""
    print("=== 修正後の統合テスト実行と検証 ===\n")
    
    results = []
    
    # 1. MainWindowの初期化テスト
    print("1. MainWindowの初期化テスト")
    results.append(test_mainwindow_initialization())
    print()
    
    # 2. DatabaseManagerのinitialize()メソッドテスト
    print("2. DatabaseManagerのinitialize()メソッドテスト")
    results.append(test_database_manager_initialization())
    print()
    
    # 3. Configのdata_dirプロパティテスト
    print("3. Configのdata_dirプロパティテスト")
    results.append(test_config_data_dir_property())
    print()
    
    # 結果の集計
    passed = sum(results)
    total = len(results)
    
    print("=== テスト結果 ===")
    print(f"実行: {total}件")
    print(f"成功: {passed}件")
    print(f"失敗: {total - passed}件")
    
    if passed == total:
        print("\n✓ すべてのテストが成功しました！")
        print("修正されたコンポーネントが正常に動作しています。")
        return 0
    else:
        print(f"\n✗ {total - passed}件のテストが失敗しました。")
        return 1


if __name__ == "__main__":
    sys.exit(main())