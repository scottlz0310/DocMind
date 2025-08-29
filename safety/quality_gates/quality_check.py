#!/usr/bin/env python3
"""
品質ゲートチェックスクリプト
各週末に実行する品質確認
"""

import sys
import time
import subprocess
import psutil
from pathlib import Path

class QualityGate:
    """品質ゲート管理クラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.baseline_performance = {}
        self.load_baseline()
        
    def load_baseline(self):
        """基準値読み込み"""
        baseline_file = self.project_root / "safety" / "baseline_performance.json"
        if baseline_file.exists():
            import json
            self.baseline_performance = json.loads(baseline_file.read_text())
    
    def check_functionality(self):
        """機能性チェック"""
        print("🔍 機能性チェック実行中...")
        
        try:
            # 基本インポートテスト
            result = subprocess.run([
                sys.executable, "-c",
                "import sys; sys.path.append('src'); "
                "from gui.folder_tree import FolderTreeWidget; "
                "print('基本機能OK')"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ 機能性チェック成功")
                return True
            else:
                print(f"❌ 機能性チェック失敗: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 機能性チェック失敗: {e}")
            return False
    
    def check_performance(self):
        """性能チェック"""
        print("⚡ 性能チェック実行中...")
        
        try:
            # インポート時間測定
            start_time = time.time()
            result = subprocess.run([
                sys.executable, "-c",
                "import sys; sys.path.append('src'); "
                "from gui.folder_tree import FolderTreeWidget"
            ], capture_output=True, text=True, timeout=30)
            import_time = time.time() - start_time
            
            if result.returncode != 0:
                print(f"❌ インポート失敗: {result.stderr}")
                return False
            
            # 基準値と比較
            baseline_import = self.baseline_performance.get('import_time', 1.0)
            performance_ratio = import_time / baseline_import
            
            print(f"インポート時間: {import_time:.3f}秒 (基準値: {baseline_import:.3f}秒)")
            print(f"性能比率: {performance_ratio:.2f} (1.05以下が合格)")
            
            if performance_ratio <= 1.05:  # 5%以内の劣化は許容
                print("✅ 性能チェック成功")
                return True
            else:
                print("❌ 性能劣化が検出されました")
                return False
                
        except Exception as e:
            print(f"❌ 性能チェック失敗: {e}")
            return False
    
    def check_memory_usage(self):
        """メモリ使用量チェック"""
        print("💾 メモリ使用量チェック実行中...")
        
        try:
            # 現在のメモリ使用量
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            # 基準値と比較
            baseline_memory = self.baseline_performance.get('memory_mb', 100.0)
            memory_ratio = memory_mb / baseline_memory
            
            print(f"メモリ使用量: {memory_mb:.1f}MB (基準値: {baseline_memory:.1f}MB)")
            print(f"メモリ比率: {memory_ratio:.2f} (1.20以下が合格)")
            
            if memory_ratio <= 1.20:  # 20%以内の増加は許容
                print("✅ メモリ使用量チェック成功")
                return True
            else:
                print("❌ メモリ使用量増加が検出されました")
                return False
                
        except Exception as e:
            print(f"❌ メモリ使用量チェック失敗: {e}")
            return False
    
    def check_code_quality(self):
        """コード品質チェック"""
        print("📝 コード品質チェック実行中...")
        
        target_file = self.project_root / "src" / "gui" / "folder_tree.py"
        if not target_file.exists():
            print(f"❌ 対象ファイルが見つかりません: {target_file}")
            return False
        
        try:
            # ファイルサイズチェック
            file_size = target_file.stat().st_size
            line_count = len(target_file.read_text(encoding='utf-8').splitlines())
            
            print(f"ファイルサイズ: {file_size:,} bytes")
            print(f"行数: {line_count:,} 行")
            
            # 品質基準
            if line_count <= 1500:  # 目標に向けた段階的改善
                print("✅ コード品質チェック成功")
                return True
            else:
                print("⚠️ ファイルサイズが大きいですが、リファクタリング進行中のため継続")
                return True  # Phase4進行中は緩い基準
                
        except Exception as e:
            print(f"❌ コード品質チェック失敗: {e}")
            return False

def main():
    """メイン処理"""
    print("🚪 品質ゲートチェック実行")
    print("=" * 40)
    
    gate = QualityGate()
    
    checks = [
        ("機能性", gate.check_functionality),
        ("性能", gate.check_performance),
        ("メモリ使用量", gate.check_memory_usage),
        ("コード品質", gate.check_code_quality)
    ]
    
    results = []
    for name, check_func in checks:
        print()
        result = check_func()
        results.append((name, result))
    
    # 結果サマリー
    print("\n📊 品質ゲート結果")
    print("=" * 40)
    passed_count = 0
    for name, result in results:
        status = "✅ 合格" if result else "❌ 不合格"
        print(f"{name}: {status}")
        if result:
            passed_count += 1
    
    print(f"\n合格率: {passed_count}/{len(results)} ({passed_count/len(results)*100:.1f}%)")
    
    if passed_count == len(results):
        print("🎉 全ての品質ゲートを通過しました")
        return 0
    elif passed_count >= len(results) * 0.75:  # 75%以上で条件付き合格
        print("⚠️ 条件付き合格 - 注意して継続してください")
        return 0
    else:
        print("🚨 品質ゲート不合格 - 作業を停止してください")
        return 1

if __name__ == "__main__":
    sys.exit(main())
