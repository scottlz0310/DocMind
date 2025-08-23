#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI検証のデバッグテスト

問題の原因を特定するための最小限のテストです。
"""

import os
import sys
import time
import logging
from pathlib import Path

# GUI環境の設定
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def test_basic_imports():
    """基本的なインポートテスト"""
    logger.info("=== 基本的なインポートテストを開始 ===")
    
    try:
        logger.info("1. 標準ライブラリのインポート")
        import sys
        import os
        import time
        logger.info("✓ 標準ライブラリのインポート成功")
        
        logger.info("2. PySide6のインポート")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        logger.info("✓ PySide6のインポート成功")
        
        logger.info("3. プロジェクトモジュールのインポート")
        from src.utils.exceptions import DocMindException
        logger.info("✓ プロジェクトモジュールのインポート成功")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ インポートテスト失敗: {str(e)}")
        return False


def test_qt_application():
    """QApplicationの基本テスト"""
    logger.info("=== QApplicationの基本テストを開始 ===")
    
    try:
        from PySide6.QtWidgets import QApplication
        
        logger.info("1. QApplication.instance()の確認")
        existing_app = QApplication.instance()
        logger.info(f"既存のQApplication: {existing_app}")
        
        if not existing_app:
            logger.info("2. 新しいQApplicationの作成")
            app = QApplication([])
            logger.info(f"新しいQApplication作成: {app}")
            
            logger.info("3. processEventsの実行")
            app.processEvents()
            logger.info("✓ processEvents完了")
        else:
            logger.info("2. 既存のQApplicationを使用")
            app = existing_app
        
        logger.info("4. QApplicationの基本プロパティ確認")
        logger.info(f"アプリケーション名: {app.applicationName()}")
        logger.info(f"組織名: {app.organizationName()}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ QApplicationテスト失敗: {str(e)}")
        return False


def test_basic_widgets():
    """基本ウィジェットの作成テスト"""
    logger.info("=== 基本ウィジェットの作成テストを開始 ===")
    
    try:
        from PySide6.QtWidgets import QApplication, QWidget, QLabel
        
        # QApplicationの確保
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        
        logger.info("1. QWidgetの作成")
        widget = QWidget()
        logger.info(f"QWidget作成: {widget}")
        
        logger.info("2. QLabelの作成")
        label = QLabel("テストラベル")
        logger.info(f"QLabel作成: {label}")
        
        logger.info("3. ウィジェットのクリーンアップ")
        widget.deleteLater()
        label.deleteLater()
        
        logger.info("4. processEventsの実行")
        app.processEvents()
        
        logger.info("✓ 基本ウィジェットテスト成功")
        return True
        
    except Exception as e:
        logger.error(f"✗ 基本ウィジェットテスト失敗: {str(e)}")
        return False


def test_gui_module_imports():
    """GUIモジュールのインポートテスト"""
    logger.info("=== GUIモジュールのインポートテストを開始 ===")
    
    gui_modules = [
        'src.gui.main_window',
        'src.gui.folder_tree',
        'src.gui.search_interface',
        'src.gui.search_results',
        'src.gui.preview_widget'
    ]
    
    success_count = 0
    
    for module_name in gui_modules:
        try:
            logger.info(f"インポート試行: {module_name}")
            module = __import__(module_name)
            logger.info(f"✓ {module_name} インポート成功")
            success_count += 1
        except Exception as e:
            logger.error(f"✗ {module_name} インポート失敗: {str(e)}")
    
    logger.info(f"GUIモジュールインポート結果: {success_count}/{len(gui_modules)} 成功")
    return success_count == len(gui_modules)


def main():
    """メイン実行関数"""
    logger.info("GUI検証デバッグテストを開始します")
    
    start_time = time.time()
    
    tests = [
        ("基本インポート", test_basic_imports),
        ("QApplication", test_qt_application),
        ("基本ウィジェット", test_basic_widgets),
        ("GUIモジュールインポート", test_gui_module_imports)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"テスト開始: {test_name}")
        logger.info(f"{'='*50}")
        
        test_start = time.time()
        
        try:
            result = test_func()
            test_time = time.time() - test_start
            
            if result:
                logger.info(f"✓ {test_name} 成功 ({test_time:.3f}秒)")
            else:
                logger.error(f"✗ {test_name} 失敗 ({test_time:.3f}秒)")
            
            results.append((test_name, result, test_time))
            
        except Exception as e:
            test_time = time.time() - test_start
            logger.error(f"✗ {test_name} 例外発生 ({test_time:.3f}秒): {str(e)}")
            results.append((test_name, False, test_time))
    
    # 結果サマリー
    total_time = time.time() - start_time
    success_count = sum(1 for _, success, _ in results if success)
    
    logger.info(f"\n{'='*50}")
    logger.info("テスト結果サマリー")
    logger.info(f"{'='*50}")
    
    for test_name, success, test_time in results:
        status = "✓" if success else "✗"
        logger.info(f"{status} {test_name}: {test_time:.3f}秒")
    
    logger.info(f"\n成功: {success_count}/{len(tests)}")
    logger.info(f"総実行時間: {total_time:.3f}秒")
    
    if success_count == len(tests):
        logger.info("🎉 すべてのテストが成功しました！")
        return 0
    else:
        logger.error(f"❌ {len(tests) - success_count}個のテストが失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())