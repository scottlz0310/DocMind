#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コンポーネント個別テスト

GUIを除く修正されたコンポーネントのテスト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

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


def test_mainwindow_import_only():
    """MainWindowのインポートテスト（初期化なし）"""
    try:
        print("MainWindowクラスのインポートをテスト中...")
        
        # LoggerMixinをインポート
        from src.utils.logging_config import LoggerMixin
        print("✓ LoggerMixinが正常にインポートされました")
        
        # MainWindowクラスをインポート（初期化はしない）
        from src.gui.main_window import MainWindow
        print("✓ MainWindowクラスが正常にインポートされました")
        
        # クラスがLoggerMixinを継承していることを確認
        assert issubclass(MainWindow, LoggerMixin), "MainWindowがLoggerMixinを継承していません"
        print("✓ MainWindowがLoggerMixinを継承しています")
        
        # loggerプロパティが定義されていることを確認（クラスレベル）
        assert hasattr(LoggerMixin, 'logger'), "LoggerMixinにloggerプロパティが定義されていません"
        print("✓ LoggerMixinにloggerプロパティが定義されています")
        
        print("✓ MainWindowインポートテストが完了しました")
        return True
        
    except Exception as e:
        print(f"✗ MainWindowインポートテストが失敗しました: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メインテスト関数"""
    print("=== 修正後のコンポーネントテスト ===\n")
    
    results = []
    
    # 1. MainWindowのインポートテスト（初期化なし）
    print("1. MainWindowのインポートテスト")
    results.append(test_mainwindow_import_only())
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