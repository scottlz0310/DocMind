"""
GUI管理コンポーネント

このパッケージには、メインウィンドウの各種管理機能を担当するクラスが含まれています。
main_window.pyから分離された責務別のマネージャークラスを提供します。
"""

from .layout_manager import LayoutManager
from .progress_manager import ProgressManager
# from .signal_manager import SignalManager  # 未実装
# from .cleanup_manager import CleanupManager  # 未実装

__all__ = [
    'LayoutManager',
    'ProgressManager', 
    # 'SignalManager',  # 未実装
    # 'CleanupManager'  # 未実装
]