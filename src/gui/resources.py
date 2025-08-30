"""DocMind リソース管理"""

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


def get_app_icon():
    """アプリケーションアイコンを取得"""
    app = QApplication.instance()
    if app:
        style = app.style()
        return style.standardIcon(style.StandardPixmap.SP_ComputerIcon)
    else:
        return QIcon()


def get_search_icon():
    """検索アイコンを取得"""
    app = QApplication.instance()
    if app:
        style = app.style()
        return style.standardIcon(style.StandardPixmap.SP_FileDialogDetailedView)
    else:
        return QIcon()


def get_settings_icon():
    """設定アイコンを取得"""
    app = QApplication.instance()
    if app:
        style = app.style()
        return style.standardIcon(style.StandardPixmap.SP_ComputerIcon)
    else:
        return QIcon()
