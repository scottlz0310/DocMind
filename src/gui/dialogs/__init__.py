"""
ダイアログ管理コンポーネント

このパッケージには、各種ダイアログの管理を担当するクラスが含まれています。
main_window.pyから分離されたダイアログ表示・管理機能を提供します。
"""

from .dialog_manager import DialogManager

__all__ = [
    'DialogManager'
]