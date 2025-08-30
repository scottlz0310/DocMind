#!/usr/bin/env python3
"""
テスト実行システム
Phase4リファクタリング用の品質保証
"""

import subprocess
import sys
from pathlib import Path


class TestRunner:
    """テスト実行管理クラス"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)

    def run_import_tests(self) -> bool:
        """importテストの実行"""

        test_modules = [
            "src.gui.folder_tree",
            "src.gui.main_window",
            "src.gui.search_interface"
        ]

        all_passed = True
        for module in test_modules:
            try:
                result = subprocess.run([
                    sys.executable, "-c", f"import {module}; print('✅ {module}')"
                ], capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    pass
                else:
                    all_passed = False
            except Exception:
                all_passed = False

        return all_passed

    def run_syntax_check(self) -> bool:
        """構文チェックの実行"""

        python_files = [
            "src/gui/folder_tree.py",
            "src/gui/main_window.py",
            "src/gui/search_interface.py"
        ]

        all_passed = True
        for file_path in python_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                result = subprocess.run([
                    sys.executable, "-m", "py_compile", str(full_path)
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    pass
                else:
                    all_passed = False
            except Exception:
                all_passed = False

        return all_passed

    def run_all_tests(self) -> bool:
        """全テストの実行"""

        syntax_ok = self.run_syntax_check()
        import_ok = self.run_import_tests()

        if syntax_ok and import_ok:
            return True
        else:
            return False

def main():
    """テスト実行のメイン関数"""
    runner = TestRunner()
    success = runner.run_all_tests()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
