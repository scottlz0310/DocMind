#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI機能統合検証実行スクリプト - 再設計版

シンプルで効果的なGUI検証を実行します。
"""

import sys
import os
import logging
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.validation_framework.gui_functionality_validator import GUIFunctionalityValidator
from tests.validation_framework.base_validator import ValidationConfig


def setup_logging():
    """ログ設定のセットアップ"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """GUI機能検証のメイン実行関数"""
    print("DocMind GUI機能統合検証（再設計版）を開始します...")
    
    # ログ設定
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # 検証設定の作成（シンプル化）
        config = ValidationConfig(
            enable_performance_monitoring=False,  # 基本検証では無効化
            enable_memory_monitoring=False,       # 基本検証では無効化
            enable_error_injection=False,
            max_execution_time=30.0,  # 30秒
            max_memory_usage=512.0,   # 512MB
            log_level="INFO"
        )
        
        # GUI機能検証クラスの初期化
        validator = GUIFunctionalityValidator(config)
        
        # テスト環境のセットアップ
        logger.info("テスト環境をセットアップしています...")
        validator.setup_test_environment()
        
        # 検証の実行
        logger.info("GUI機能検証を実行しています...")
        results = validator.run_validation()
        
        # 結果の表示
        print(f"\n=== GUI機能検証結果 ===")
        print(f"実行テスト数: {len(results)}")
        
        success_count = sum(1 for r in results if r.success)
        failure_count = len(results) - success_count
        
        print(f"成功: {success_count}")
        print(f"失敗: {failure_count}")
        
        if len(results) > 0:
            print(f"成功率: {success_count/len(results)*100:.1f}%")
        
        # 詳細結果の表示
        print(f"\n=== 詳細結果 ===")
        for result in results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.test_name}")
            print(f"  実行時間: {result.execution_time:.3f}秒")
            
            if not result.success:
                print(f"  エラー: {result.error_message}")
            print()
        
        # 検証結果の判定
        if failure_count == 0:
            print("\n🎉 すべてのGUI機能検証が成功しました！")
            return 0
        else:
            print(f"\n❌ {failure_count}個のテストが失敗しました。")
            return 1
            
    except Exception as e:
        logger.error(f"GUI機能検証中にエラーが発生しました: {str(e)}")
        print(f"\nエラー: {str(e)}")
        return 1
        
    finally:
        # クリーンアップ
        try:
            validator.teardown_test_environment()
            validator.cleanup()
        except Exception as e:
            logger.warning(f"クリーンアップ中にエラーが発生しました: {str(e)}")


if __name__ == "__main__":
    sys.exit(main())