#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase4準備: 現在動作記録スクリプト

folder_tree.pyリファクタリング前の現在動作を完全記録し、
Phase4実行時の安全な基準値として保存します。
"""

import os
import sys
import json
import time
import logging
import traceback
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

class BehaviorRecorder:
    """現在動作記録システム"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "phase": "Phase4準備 - Week 0 Day 2",
            "target_file": "src/gui/folder_tree.py",
            "tests": {},
            "performance": {},
            "errors": [],
            "warnings": []
        }
        
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger("BehaviorRecorder")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def record_all_behaviors(self) -> Dict[str, Any]:
        """全動作を記録"""
        self.logger.info("=== Phase4準備: 現在動作記録開始 ===")
        
        try:
            # 1. 基本環境チェック
            self._record_environment()
            
            # 2. インポートテスト
            self._record_import_tests()
            
            # 3. クラス初期化テスト
            self._record_initialization_tests()
            
            # 4. 基本機能テスト
            self._record_functionality_tests()
            
            # 5. パフォーマンステスト
            self._record_performance_tests()
            
            # 6. メモリ使用量テスト
            self._record_memory_tests()
            
            # 7. 結果保存
            self._save_results()
            
            self.logger.info("=== 現在動作記録完了 ===")
            return self.results
            
        except Exception as e:
            self.logger.error(f"動作記録中にエラー: {e}")
            self.results["errors"].append({
                "type": "RecordingError",
                "message": str(e),
                "traceback": traceback.format_exc()
            })
            return self.results
    
    def _record_environment(self):
        """環境情報を記録"""
        self.logger.info("環境情報を記録中...")
        
        try:
            env_info = {
                "python_version": sys.version,
                "platform": sys.platform,
                "working_directory": os.getcwd(),
                "project_root": str(project_root),
                "sys_path": sys.path[:5],  # 最初の5つのパスのみ
            }
            
            # 仮想環境チェック
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                env_info["virtual_env"] = True
                env_info["virtual_env_path"] = sys.prefix
            else:
                env_info["virtual_env"] = False
            
            # 必要なパッケージの存在確認
            required_packages = ["PySide6", "logging"]
            package_status = {}
            
            for package in required_packages:
                try:
                    __import__(package)
                    package_status[package] = "OK"
                except ImportError as e:
                    package_status[package] = f"ERROR: {e}"
            
            env_info["packages"] = package_status
            
            self.results["environment"] = env_info
            self.logger.info("環境情報記録完了")
            
        except Exception as e:
            self.results["errors"].append({
                "test": "environment",
                "error": str(e)
            })
    
    def _record_import_tests(self):
        """インポートテストを記録"""
        self.logger.info("インポートテストを実行中...")
        
        import_tests = {}
        
        # 1. folder_tree.py直接インポート
        try:
            start_time = time.time()
            from gui.folder_tree import FolderTreeWidget, FolderTreeContainer, FolderLoadWorker
            import_time = time.time() - start_time
            
            import_tests["folder_tree_direct"] = {
                "status": "SUCCESS",
                "import_time": import_time,
                "classes": ["FolderTreeWidget", "FolderTreeContainer", "FolderLoadWorker"]
            }
            self.logger.info(f"folder_tree.py直接インポート成功 ({import_time:.3f}秒)")
            
        except Exception as e:
            import_tests["folder_tree_direct"] = {
                "status": "ERROR",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            self.logger.error(f"folder_tree.py直接インポートエラー: {e}")
        
        # 2. 依存関係インポート
        dependencies = [
            "PySide6.QtWidgets",
            "PySide6.QtCore", 
            "PySide6.QtGui",
            "logging",
            "os",
            "pathlib"
        ]
        
        for dep in dependencies:
            try:
                start_time = time.time()
                __import__(dep)
                import_time = time.time() - start_time
                
                import_tests[f"dependency_{dep}"] = {
                    "status": "SUCCESS",
                    "import_time": import_time
                }
                
            except Exception as e:
                import_tests[f"dependency_{dep}"] = {
                    "status": "ERROR",
                    "error": str(e)
                }
        
        self.results["tests"]["imports"] = import_tests
        self.logger.info("インポートテスト完了")
    
    def _record_initialization_tests(self):
        """初期化テストを記録"""
        self.logger.info("初期化テストを実行中...")
        
        init_tests = {}
        
        try:
            # QApplicationが必要
            from PySide6.QtWidgets import QApplication
            
            # QApplicationインスタンスの確認/作成
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
                app_created = True
            else:
                app_created = False
            
            # 1. FolderLoadWorker初期化
            try:
                start_time = time.time()
                from gui.folder_tree import FolderLoadWorker
                
                worker = FolderLoadWorker("/tmp", max_depth=2)
                init_time = time.time() - start_time
                
                init_tests["FolderLoadWorker"] = {
                    "status": "SUCCESS",
                    "init_time": init_time,
                    "attributes": {
                        "root_path": worker.root_path,
                        "max_depth": worker.max_depth,
                        "should_stop": worker.should_stop
                    }
                }
                
                # クリーンアップ
                worker.deleteLater()
                
            except Exception as e:
                init_tests["FolderLoadWorker"] = {
                    "status": "ERROR",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
            
            # 2. FolderTreeWidget初期化
            try:
                start_time = time.time()
                from gui.folder_tree import FolderTreeWidget
                
                widget = FolderTreeWidget()
                init_time = time.time() - start_time
                
                init_tests["FolderTreeWidget"] = {
                    "status": "SUCCESS",
                    "init_time": init_time,
                    "attributes": {
                        "root_paths_count": len(widget.root_paths),
                        "item_map_count": len(widget.item_map),
                        "header_label": widget.headerItem().text(0) if widget.headerItem() else None
                    }
                }
                
                # クリーンアップ
                widget.deleteLater()
                
            except Exception as e:
                init_tests["FolderTreeWidget"] = {
                    "status": "ERROR",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
            
            # 3. FolderTreeContainer初期化
            try:
                start_time = time.time()
                from gui.folder_tree import FolderTreeContainer
                
                container = FolderTreeContainer()
                init_time = time.time() - start_time
                
                init_tests["FolderTreeContainer"] = {
                    "status": "SUCCESS",
                    "init_time": init_time,
                    "has_tree_widget": hasattr(container, 'tree_widget'),
                    "has_filter_input": hasattr(container, 'filter_input')
                }
                
                # クリーンアップ
                container.deleteLater()
                
            except Exception as e:
                init_tests["FolderTreeContainer"] = {
                    "status": "ERROR",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
            
            # QApplicationクリーンアップ
            if app_created:
                app.quit()
                
        except Exception as e:
            init_tests["general_error"] = {
                "status": "ERROR",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        
        self.results["tests"]["initialization"] = init_tests
        self.logger.info("初期化テスト完了")
    
    def _record_functionality_tests(self):
        """基本機能テストを記録"""
        self.logger.info("基本機能テストを実行中...")
        
        func_tests = {}
        
        try:
            from PySide6.QtWidgets import QApplication
            from gui.folder_tree import FolderTreeWidget, FolderTreeContainer
            
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
                app_created = True
            else:
                app_created = False
            
            # テスト用一時ディレクトリ作成
            test_dir = Path("/tmp/docmind_test")
            test_dir.mkdir(exist_ok=True)
            (test_dir / "subdir1").mkdir(exist_ok=True)
            (test_dir / "subdir2").mkdir(exist_ok=True)
            
            # 1. フォルダ構造読み込みテスト
            try:
                widget = FolderTreeWidget()
                
                start_time = time.time()
                widget.load_folder_structure(str(test_dir))
                load_time = time.time() - start_time
                
                func_tests["load_folder_structure"] = {
                    "status": "SUCCESS",
                    "load_time": load_time,
                    "root_paths_count": len(widget.root_paths),
                    "item_map_count": len(widget.item_map)
                }
                
                widget.deleteLater()
                
            except Exception as e:
                func_tests["load_folder_structure"] = {
                    "status": "ERROR",
                    "error": str(e)
                }
            
            # 2. 状態管理テスト
            try:
                widget = FolderTreeWidget()
                
                # インデックス状態設定
                test_path = str(test_dir)
                widget.set_folder_indexing(test_path)
                widget.set_folder_indexed(test_path, 10, 8)
                
                func_tests["state_management"] = {
                    "status": "SUCCESS",
                    "indexed_folders": len(widget.get_indexed_folders()),
                    "indexing_folders": len(widget.get_indexing_folders())
                }
                
                widget.deleteLater()
                
            except Exception as e:
                func_tests["state_management"] = {
                    "status": "ERROR",
                    "error": str(e)
                }
            
            # 3. フィルタリングテスト
            try:
                widget = FolderTreeWidget()
                widget.load_folder_structure(str(test_dir))
                
                start_time = time.time()
                widget.filter_folders("subdir")
                filter_time = time.time() - start_time
                
                func_tests["filtering"] = {
                    "status": "SUCCESS",
                    "filter_time": filter_time
                }
                
                widget.deleteLater()
                
            except Exception as e:
                func_tests["filtering"] = {
                    "status": "ERROR",
                    "error": str(e)
                }
            
            # テストディレクトリクリーンアップ
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
            
            if app_created:
                app.quit()
                
        except Exception as e:
            func_tests["general_error"] = {
                "status": "ERROR",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        
        self.results["tests"]["functionality"] = func_tests
        self.logger.info("基本機能テスト完了")
    
    def _record_performance_tests(self):
        """パフォーマンステストを記録"""
        self.logger.info("パフォーマンステストを実行中...")
        
        perf_tests = {}
        
        try:
            # 1. インポート時間測定
            start_time = time.time()
            from gui.folder_tree import FolderTreeWidget, FolderTreeContainer, FolderLoadWorker
            import_time = time.time() - start_time
            
            perf_tests["import_time"] = {
                "total_time": import_time,
                "status": "SUCCESS"
            }
            
            # 2. 初期化時間測定
            from PySide6.QtWidgets import QApplication
            
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
                app_created = True
            else:
                app_created = False
            
            start_time = time.time()
            widget = FolderTreeWidget()
            init_time = time.time() - start_time
            
            perf_tests["initialization_time"] = {
                "widget_init_time": init_time,
                "status": "SUCCESS"
            }
            
            # 3. 大量フォルダ処理時間（シミュレーション）
            test_dir = Path("/tmp/docmind_perf_test")
            test_dir.mkdir(exist_ok=True)
            
            # 複数のサブディレクトリを作成
            for i in range(10):
                (test_dir / f"folder_{i:03d}").mkdir(exist_ok=True)
            
            start_time = time.time()
            widget.load_folder_structure(str(test_dir))
            load_time = time.time() - start_time
            
            perf_tests["bulk_load_time"] = {
                "folders_count": 10,
                "load_time": load_time,
                "status": "SUCCESS"
            }
            
            # クリーンアップ
            widget.deleteLater()
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
            
            if app_created:
                app.quit()
                
        except Exception as e:
            perf_tests["error"] = {
                "status": "ERROR",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        
        self.results["performance"] = perf_tests
        self.logger.info("パフォーマンステスト完了")
    
    def _record_memory_tests(self):
        """メモリ使用量テストを記録"""
        self.logger.info("メモリ使用量テストを実行中...")
        
        memory_tests = {}
        
        try:
            import psutil
            process = psutil.Process()
            
            # 1. 初期メモリ使用量
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 2. インポート後メモリ使用量
            from gui.folder_tree import FolderTreeWidget, FolderTreeContainer
            import_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 3. 初期化後メモリ使用量
            from PySide6.QtWidgets import QApplication
            
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
                app_created = True
            else:
                app_created = False
            
            widget = FolderTreeWidget()
            init_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            memory_tests = {
                "initial_memory_mb": initial_memory,
                "import_memory_mb": import_memory,
                "init_memory_mb": init_memory,
                "import_overhead_mb": import_memory - initial_memory,
                "init_overhead_mb": init_memory - import_memory,
                "status": "SUCCESS"
            }
            
            # クリーンアップ
            widget.deleteLater()
            if app_created:
                app.quit()
                
        except ImportError:
            memory_tests = {
                "status": "SKIPPED",
                "reason": "psutil not available"
            }
        except Exception as e:
            memory_tests = {
                "status": "ERROR",
                "error": str(e)
            }
        
        self.results["tests"]["memory"] = memory_tests
        self.logger.info("メモリ使用量テスト完了")
    
    def _save_results(self):
        """結果を保存"""
        self.logger.info("結果を保存中...")
        
        # 結果ファイルパス
        results_dir = project_root / "test_results"
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"phase4_baseline_{timestamp}.json"
        
        # 結果保存
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # 最新結果として別名保存
        latest_file = results_dir / "phase4_baseline_latest.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"結果保存完了: {results_file}")
        
        # サマリー表示
        self._print_summary()
    
    def _print_summary(self):
        """結果サマリーを表示"""
        print("\n" + "="*60)
        print("Phase4準備: 現在動作記録 - サマリー")
        print("="*60)
        
        # 環境情報
        if "environment" in self.results:
            env = self.results["environment"]
            print(f"Python: {env.get('python_version', 'Unknown')[:20]}...")
            print(f"仮想環境: {'有効' if env.get('virtual_env') else '無効'}")
        
        # テスト結果
        if "tests" in self.results:
            tests = self.results["tests"]
            
            # インポートテスト
            if "imports" in tests:
                imports = tests["imports"]
                success_count = sum(1 for t in imports.values() if t.get("status") == "SUCCESS")
                total_count = len(imports)
                print(f"インポートテスト: {success_count}/{total_count} 成功")
            
            # 初期化テスト
            if "initialization" in tests:
                init = tests["initialization"]
                success_count = sum(1 for t in init.values() if t.get("status") == "SUCCESS")
                total_count = len(init)
                print(f"初期化テスト: {success_count}/{total_count} 成功")
            
            # 機能テスト
            if "functionality" in tests:
                func = tests["functionality"]
                success_count = sum(1 for t in func.values() if t.get("status") == "SUCCESS")
                total_count = len(func)
                print(f"機能テスト: {success_count}/{total_count} 成功")
        
        # パフォーマンス
        if "performance" in self.results:
            perf = self.results["performance"]
            if "import_time" in perf:
                print(f"インポート時間: {perf['import_time'].get('total_time', 0):.3f}秒")
            if "initialization_time" in perf:
                print(f"初期化時間: {perf['initialization_time'].get('widget_init_time', 0):.3f}秒")
        
        # エラー・警告
        error_count = len(self.results.get("errors", []))
        warning_count = len(self.results.get("warnings", []))
        
        if error_count > 0:
            print(f"⚠️  エラー: {error_count}件")
        if warning_count > 0:
            print(f"⚠️  警告: {warning_count}件")
        
        if error_count == 0 and warning_count == 0:
            print("✅ エラー・警告なし")
        
        print("="*60)
        print("記録完了: Phase4実行時の基準値として使用されます")
        print("="*60)


def main():
    """メイン実行関数"""
    print("Phase4準備: 現在動作記録スクリプト")
    print("folder_tree.py リファクタリング前の基準値を記録します")
    print()
    
    # 仮想環境チェック
    if not (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
        print("⚠️  警告: 仮想環境が有効化されていない可能性があります")
        print("   推奨: source venv/bin/activate")
        print()
    
    # 記録実行
    recorder = BehaviorRecorder()
    results = recorder.record_all_behaviors()
    
    # 結果確認
    if results.get("errors"):
        print("\n❌ エラーが発生しました:")
        for error in results["errors"]:
            print(f"  - {error.get('type', 'Error')}: {error.get('message', 'Unknown')}")
        return 1
    
    print("\n✅ 現在動作記録が正常に完了しました")
    print("Phase4実行時にこの基準値と比較して安全性を確保します")
    return 0


if __name__ == "__main__":
    sys.exit(main())