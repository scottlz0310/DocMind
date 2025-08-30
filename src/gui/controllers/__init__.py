"""
GUI制御コンポーネント

このパッケージには、ビジネスロジックの制御を担当するコントローラークラスが含まれています。
main_window.pyから分離されたビジネスロジック制御機能を提供します。
"""

from .index_controller import IndexController

__all__ = ["IndexController"]
