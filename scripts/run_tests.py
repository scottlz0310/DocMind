#!/usr/bin/env python3
"""
テスト実行スクリプト - 段階的テスト実行とレポート生成
"""
import subprocess
import sys
import os
from pathlib import Path

def setup_environment():
    """テスト環境のセットアップ"""
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['QT_LOGGING_RULES'] = '*.debug=false'
    
    # DISPLAYが設定されていない場合は仮想ディスプレイを使用
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':99'

def run_unit_tests():
    """ユニットテスト実行"""
    print("🧪 ユニットテスト実行中...")
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/unit/',
        '-v', '--tb=short',
        '--cov=src',
        '--cov-report=term-missing',
        '--cov-report=xml',
        '-m', 'not slow'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("警告:", result.stderr)
    
    return result.returncode == 0

def run_integration_tests():
    """統合テスト実行"""
    print("🔗 統合テスト実行中...")
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/integration/',
        '-v', '--tb=short',
        '--maxfail=5'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("警告:", result.stderr)
    
    return result.returncode == 0

def run_performance_tests():
    """パフォーマンステスト実行"""
    print("⚡ パフォーマンステスト実行中...")
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/performance/',
        '-v', '--benchmark-only',
        '--benchmark-sort=mean',
        '--benchmark-columns=min,max,mean,stddev'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("警告:", result.stderr)
    
    return result.returncode == 0

def run_gui_tests():
    """GUIテスト実行"""
    print("🖥️ GUIテスト実行中...")
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/unit/gui/',
        '-v', '--tb=short',
        '--maxfail=3',
        '-m', 'gui'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("警告:", result.stderr)
    
    return result.returncode == 0

def main():
    """メイン実行関数"""
    print("📋 DocMind テストスイート実行")
    print("=" * 50)
    
    setup_environment()
    
    # 実行するテストの選択
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == 'unit':
            success = run_unit_tests()
        elif test_type == 'integration':
            success = run_integration_tests()
        elif test_type == 'performance':
            success = run_performance_tests()
        elif test_type == 'gui':
            success = run_gui_tests()
        else:
            print(f"❌ 不明なテストタイプ: {test_type}")
            print("使用可能: unit, integration, performance, gui")
            sys.exit(1)
    else:
        # 全テスト実行
        print("🚀 全テスト実行モード")
        results = []
        
        results.append(("ユニットテスト", run_unit_tests()))
        results.append(("統合テスト", run_integration_tests()))
        results.append(("パフォーマンステスト", run_performance_tests()))
        results.append(("GUIテスト", run_gui_tests()))
        
        # 結果サマリー
        print("\n📊 テスト結果サマリー")
        print("-" * 30)
        success = True
        for test_name, result in results:
            status = "✅ 成功" if result else "❌ 失敗"
            print(f"{test_name}: {status}")
            success = success and result
    
    if success:
        print("\n🎉 全テスト成功!")
        sys.exit(0)
    else:
        print("\n💥 テスト失敗")
        sys.exit(1)

if __name__ == "__main__":
    main()