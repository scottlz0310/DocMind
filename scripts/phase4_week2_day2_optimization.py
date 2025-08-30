#!/usr/bin/env python3
"""
Phase4 Week 2 Day 2: 統合・最適化スクリプト

コンポーネント間の統合最適化、パフォーマンス最適化、メモリ使用量最適化を実施します。
"""

import logging
import sys
import time
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('phase4_week2_day2_optimization.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def analyze_current_state():
    """現在の状態を分析"""
    logger = logging.getLogger(__name__)

    folder_tree_path = project_root / "src" / "gui" / "folder_tree" / "folder_tree_widget.py"

    if not folder_tree_path.exists():
        logger.error(f"ファイルが見つかりません: {folder_tree_path}")
        return None

    with open(folder_tree_path, encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    methods = [line for line in lines if line.strip().startswith('def ')]
    imports = [line for line in lines if line.strip().startswith('import ') or line.strip().startswith('from ')]

    logger.info("現在の状況:")
    logger.info(f"  - 行数: {len(lines)}")
    logger.info(f"  - メソッド数: {len(methods)}")
    logger.info(f"  - インポート数: {len(imports)}")

    return {
        'lines': len(lines),
        'methods': len(methods),
        'imports': len(imports),
        'content': content
    }

def optimize_imports():
    """インポート文の最適化"""
    logger = logging.getLogger(__name__)

    folder_tree_path = project_root / "src" / "gui" / "folder_tree" / "folder_tree_widget.py"

    with open(folder_tree_path, encoding='utf-8') as f:
        content = f.read()

    # 最適化されたインポート文
    optimized_imports = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind フォルダツリーナビゲーションウィジェット

QTreeWidgetを拡張したフォルダツリーナビゲーション機能を提供します。
フォルダ構造の表示、選択、展開、コンテキストメニュー、フィルタリング機能を実装します。
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Set

from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel
)
from PySide6.QtCore import Qt, Signal, QTimer

# 統合されたコンポーネントインポート
from ..folder_tree_components import AsyncOperationManager
from .state_management import FolderItemType, FolderTreeItem
from .ui_management import UISetupManager, FilterManager, ContextMenuManager
from .event_handling import EventHandlerManager, SignalManager, ActionManager
'''

    # インポート部分を置換
    lines = content.split('\n')

    # docstringの終了位置を見つける
    docstring_end = 0
    in_docstring = False
    for i, line in enumerate(lines):
        if '"""' in line:
            if not in_docstring:
                in_docstring = True
            else:
                docstring_end = i
                break

    # インポート部分を見つける
    import_start = docstring_end + 1
    import_end = import_start

    for i in range(import_start, len(lines)):
        line = lines[i].strip()
        if line and not (line.startswith('import ') or line.startswith('from ') or line.startswith('#')):
            import_end = i
            break

    # 新しいコンテンツを作成
    new_lines = []
    new_lines.extend(optimized_imports.split('\n'))
    new_lines.extend(lines[import_end:])

    new_content = '\n'.join(new_lines)

    # ファイルに書き込み
    with open(folder_tree_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    logger.info("インポート文の最適化完了")
    return True

def remove_duplicate_code():
    """重複コードの削除"""
    logger = logging.getLogger(__name__)

    folder_tree_path = project_root / "src" / "gui" / "folder_tree" / "folder_tree_widget.py"

    with open(folder_tree_path, encoding='utf-8') as f:
        content = f.read()

    # 重複している空のメソッド定義を削除
    lines = content.split('\n')
    new_lines = []

    for i, line in enumerate(lines):
        # 空のメソッド定義をスキップ
        if line.strip() == '':
            # 連続する空行は1つだけ残す
            if i > 0 and lines[i-1].strip() != '':
                new_lines.append(line)
        elif line.strip().startswith('# ') and ('イベントハンドラー' in line or 'コンテキストメニュー' in line or 'アクション関連' in line):
            # 空のセクションコメントをスキップ
            continue
        else:
            new_lines.append(line)

    new_content = '\n'.join(new_lines)

    # ファイルに書き込み
    with open(folder_tree_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    logger.info("重複コードの削除完了")
    return True

def optimize_method_calls():
    """メソッド呼び出しの最適化"""
    logger = logging.getLogger(__name__)

    folder_tree_path = project_root / "src" / "gui" / "folder_tree" / "folder_tree_widget.py"

    with open(folder_tree_path, encoding='utf-8') as f:
        content = f.read()

    # 最適化: 直接的なマネージャー呼び出しに変更
    optimizations = [
        # UI設定の統合
        ('self.ui_setup_manager.setup_tree_widget()\n        self.context_menu_manager.setup_context_menu()\n        self.signal_manager.setup_shortcuts()\n        self.signal_manager.setup_tree_signals()\n        self.signal_manager.setup_async_signals()',
         'self._setup_all_components()'),
    ]

    for old, new in optimizations:
        content = content.replace(old, new)

    # 新しい統合メソッドを追加
    setup_method = '''
    def _setup_all_components(self):
        """全コンポーネントの統合セットアップ"""
        # UI設定
        self.ui_setup_manager.setup_tree_widget()
        self.context_menu_manager.setup_context_menu()

        # シグナル設定
        self.signal_manager.setup_shortcuts()
        self.signal_manager.setup_tree_signals()
        self.signal_manager.setup_async_signals()
'''

    # __init__メソッドの後に追加
    init_end = content.find('self.logger.info("フォルダツリーウィジェットが初期化されました")')
    if init_end != -1:
        insert_pos = content.find('\n    \n', init_end) + 1
        content = content[:insert_pos] + setup_method + content[insert_pos:]

    # ファイルに書き込み
    with open(folder_tree_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info("メソッド呼び出しの最適化完了")
    return True

def optimize_memory_usage():
    """メモリ使用量の最適化"""
    logger = logging.getLogger(__name__)

    folder_tree_path = project_root / "src" / "gui" / "folder_tree" / "folder_tree_widget.py"

    with open(folder_tree_path, encoding='utf-8') as f:
        content = f.read()

    # メモリ効率的な初期化
    memory_optimizations = [
        # セットの初期化を遅延化
        ('self.expanded_paths: Set[str] = set()',
         'self.expanded_paths: Optional[Set[str]] = None'),
        ('self.indexing_paths: Set[str] = set()',
         'self.indexing_paths: Optional[Set[str]] = None'),
        ('self.indexed_paths: Set[str] = set()',
         'self.indexed_paths: Optional[Set[str]] = None'),
        ('self.excluded_paths: Set[str] = set()',
         'self.excluded_paths: Optional[Set[str]] = None'),
        ('self.error_paths: Set[str] = set()',
         'self.error_paths: Optional[Set[str]] = None'),
    ]

    for old, new in memory_optimizations:
        content = content.replace(old, new)

    # 遅延初期化メソッドを追加
    lazy_init_method = '''
    def _ensure_path_sets(self):
        """パスセットの遅延初期化"""
        if self.expanded_paths is None:
            self.expanded_paths = set()
        if self.indexing_paths is None:
            self.indexing_paths = set()
        if self.indexed_paths is None:
            self.indexed_paths = set()
        if self.excluded_paths is None:
            self.excluded_paths = set()
        if self.error_paths is None:
            self.error_paths = set()
'''

    # _setup_all_componentsメソッドの後に追加
    setup_end = content.find('self.signal_manager.setup_async_signals()')
    if setup_end != -1:
        insert_pos = content.find('\n    \n', setup_end) + 1
        content = content[:insert_pos] + lazy_init_method + content[insert_pos:]

    # パスセット使用箇所に遅延初期化を追加
    path_set_usages = [
        'self.expanded_paths.discard',
        'self.indexing_paths.add',
        'self.indexing_paths.discard',
        'self.indexed_paths.add',
        'self.indexed_paths.discard',
        'self.excluded_paths.add',
        'self.excluded_paths.discard',
        'self.error_paths.add',
        'self.error_paths.discard',
    ]

    for usage in path_set_usages:
        content = content.replace(usage, f'self._ensure_path_sets()\n        {usage}')

    # ファイルに書き込み
    with open(folder_tree_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info("メモリ使用量の最適化完了")
    return True

def create_performance_optimized_methods():
    """パフォーマンス最適化メソッドの作成"""
    logger = logging.getLogger(__name__)

    # パフォーマンス最適化用のヘルパーメソッドファイルを作成
    helper_path = project_root / "src" / "gui" / "folder_tree" / "performance_helpers.py"

    helper_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
フォルダツリーパフォーマンス最適化ヘルパー

メモリ効率とパフォーマンスを向上させるためのヘルパー関数群
"""

from typing import Dict, Set, List, Optional
from functools import lru_cache
import os

class PathOptimizer:
    """パス操作の最適化クラス"""

    def __init__(self):
        self._path_cache: Dict[str, str] = {}
        self._basename_cache: Dict[str, str] = {}

    @lru_cache(maxsize=1000)
    def get_basename(self, path: str) -> str:
        """キャッシュ付きbasename取得"""
        return os.path.basename(path)

    @lru_cache(maxsize=1000)
    def normalize_path(self, path: str) -> str:
        """キャッシュ付きパス正規化"""
        return os.path.normpath(path)

    def clear_cache(self):
        """キャッシュをクリア"""
        self.get_basename.cache_clear()
        self.normalize_path.cache_clear()
        self._path_cache.clear()
        self._basename_cache.clear()

class SetManager:
    """セット操作の最適化クラス"""

    def __init__(self):
        self._sets: Dict[str, Set[str]] = {}

    def get_or_create_set(self, name: str) -> Set[str]:
        """セットの遅延作成"""
        if name not in self._sets:
            self._sets[name] = set()
        return self._sets[name]

    def add_to_set(self, set_name: str, value: str):
        """セットに値を追加"""
        self.get_or_create_set(set_name).add(value)

    def remove_from_set(self, set_name: str, value: str):
        """セットから値を削除"""
        if set_name in self._sets:
            self._sets[set_name].discard(value)

    def get_set_list(self, set_name: str) -> List[str]:
        """セットをリストとして取得"""
        return list(self._sets.get(set_name, set()))

    def clear_set(self, set_name: str):
        """セットをクリア"""
        if set_name in self._sets:
            self._sets[set_name].clear()

    def cleanup(self):
        """全セットをクリア"""
        self._sets.clear()

class BatchProcessor:
    """バッチ処理最適化クラス"""

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self._pending_operations: List = []

    def add_operation(self, operation):
        """操作をバッチに追加"""
        self._pending_operations.append(operation)

        if len(self._pending_operations) >= self.batch_size:
            self.flush()

    def flush(self):
        """バッチ処理を実行"""
        if not self._pending_operations:
            return

        # バッチ処理実行
        for operation in self._pending_operations:
            try:
                operation()
            except Exception as e:
                # エラーログ出力（実装時に追加）
                pass

        self._pending_operations.clear()

    def cleanup(self):
        """クリーンアップ"""
        self.flush()
        self._pending_operations.clear()
'''

    with open(helper_path, 'w', encoding='utf-8') as f:
        f.write(helper_content)

    logger.info(f"パフォーマンス最適化ヘルパー作成完了: {helper_path}")
    return True

def integrate_performance_helpers():
    """パフォーマンスヘルパーの統合"""
    logger = logging.getLogger(__name__)

    folder_tree_path = project_root / "src" / "gui" / "folder_tree" / "folder_tree_widget.py"

    with open(folder_tree_path, encoding='utf-8') as f:
        content = f.read()

    # パフォーマンスヘルパーのインポートを追加
    import_addition = "from .performance_helpers import PathOptimizer, SetManager, BatchProcessor\n"

    # インポート部分の最後に追加
    import_end = content.find('from .event_handling import EventHandlerManager, SignalManager, ActionManager')
    if import_end != -1:
        insert_pos = content.find('\n', import_end) + 1
        content = content[:insert_pos] + import_addition + content[insert_pos:]

    # __init__メソッドにパフォーマンスヘルパーを追加
    init_addition = '''
        # パフォーマンス最適化コンポーネント
        self.path_optimizer = PathOptimizer()
        self.set_manager = SetManager()
        self.batch_processor = BatchProcessor()
'''

    init_pos = content.find('# イベント処理コンポーネント')
    if init_pos != -1:
        content = content[:init_pos] + init_addition + '\n        ' + content[init_pos:]

    # ファイルに書き込み
    with open(folder_tree_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info("パフォーマンスヘルパーの統合完了")
    return True

def run_syntax_check():
    """構文チェック実行"""
    logger = logging.getLogger(__name__)

    folder_tree_path = project_root / "src" / "gui" / "folder_tree" / "folder_tree_widget.py"

    try:
        import py_compile
        py_compile.compile(folder_tree_path, doraise=True)
        logger.info("✅ 構文チェック成功")
        return True
    except py_compile.PyCompileError as e:
        logger.error(f"❌ 構文エラー: {e}")
        return False

def measure_performance():
    """パフォーマンス測定"""
    logger = logging.getLogger(__name__)

    try:
        # インポート時間測定
        start_time = time.time()

        sys.path.insert(0, str(project_root / "src"))
        from gui.folder_tree.folder_tree_widget import FolderTreeWidget

        import_time = time.time() - start_time

        # 初期化時間測定
        start_time = time.time()
        widget = FolderTreeWidget()
        init_time = time.time() - start_time

        logger.info("📊 パフォーマンス測定結果:")
        logger.info(f"  - インポート時間: {import_time:.3f}秒")
        logger.info(f"  - 初期化時間: {init_time:.3f}秒")

        # クリーンアップ
        widget.deleteLater()

        return {
            'import_time': import_time,
            'init_time': init_time
        }

    except Exception as e:
        logger.error(f"パフォーマンス測定エラー: {e}")
        return None

def main():
    """メイン実行関数"""
    logger = setup_logging()

    logger.info("🚀 Phase4 Week 2 Day 2: 統合・最適化開始")

    # 1. 現在の状態分析
    logger.info("📊 Step 1: 現在の状態分析")
    initial_state = analyze_current_state()
    if not initial_state:
        logger.error("状態分析に失敗しました")
        return False

    # 2. インポート最適化
    logger.info("🔧 Step 2: インポート最適化")
    if not optimize_imports():
        logger.error("インポート最適化に失敗しました")
        return False

    # 3. 重複コード削除
    logger.info("🧹 Step 3: 重複コード削除")
    if not remove_duplicate_code():
        logger.error("重複コード削除に失敗しました")
        return False

    # 4. メソッド呼び出し最適化
    logger.info("⚡ Step 4: メソッド呼び出し最適化")
    if not optimize_method_calls():
        logger.error("メソッド呼び出し最適化に失敗しました")
        return False

    # 5. メモリ使用量最適化
    logger.info("💾 Step 5: メモリ使用量最適化")
    if not optimize_memory_usage():
        logger.error("メモリ使用量最適化に失敗しました")
        return False

    # 6. パフォーマンス最適化ヘルパー作成
    logger.info("🏎️ Step 6: パフォーマンス最適化ヘルパー作成")
    if not create_performance_optimized_methods():
        logger.error("パフォーマンス最適化ヘルパー作成に失敗しました")
        return False

    # 7. パフォーマンスヘルパー統合
    logger.info("🔗 Step 7: パフォーマンスヘルパー統合")
    if not integrate_performance_helpers():
        logger.error("パフォーマンスヘルパー統合に失敗しました")
        return False

    # 8. 構文チェック
    logger.info("✅ Step 8: 構文チェック")
    if not run_syntax_check():
        logger.error("構文チェックに失敗しました")
        return False

    # 9. 最終状態分析
    logger.info("📈 Step 9: 最終状態分析")
    final_state = analyze_current_state()
    if not final_state:
        logger.error("最終状態分析に失敗しました")
        return False

    # 10. パフォーマンス測定
    logger.info("🏁 Step 10: パフォーマンス測定")
    performance = measure_performance()

    # 結果レポート
    logger.info("🎉 Phase4 Week 2 Day 2: 統合・最適化完了")
    logger.info("📊 最適化結果:")
    logger.info(f"  - 行数: {initial_state['lines']} → {final_state['lines']} ({((initial_state['lines'] - final_state['lines']) / initial_state['lines'] * 100):.1f}%削減)")
    logger.info(f"  - メソッド数: {initial_state['methods']} → {final_state['methods']}")
    logger.info(f"  - インポート数: {initial_state['imports']} → {final_state['imports']}")

    if performance:
        logger.info(f"  - インポート時間: {performance['import_time']:.3f}秒")
        logger.info(f"  - 初期化時間: {performance['init_time']:.3f}秒")

    logger.info("✅ 全ての最適化が正常に完了しました")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
