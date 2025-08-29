#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DocMind フォルダアイテム種別定義

フォルダツリーアイテムの状態を表すEnum定義を提供します。
"""

from enum import Enum


class FolderItemType(Enum):
    """
    フォルダアイテムの種類
    
    フォルダツリー内のアイテムが持つ状態を定義します。
    各状態に応じて異なるアイコンや表示スタイルが適用されます。
    """
    
    ROOT = "root"           # ルートフォルダ
    FOLDER = "folder"       # 通常のフォルダ
    INDEXING = "indexing"   # インデックス処理中フォルダ
    INDEXED = "indexed"     # インデックス済みフォルダ
    EXCLUDED = "excluded"   # 除外されたフォルダ
    ERROR = "error"         # エラー状態のフォルダ
    
    def __str__(self) -> str:
        """文字列表現を返します"""
        return self.value
    
    def is_processing(self) -> bool:
        """処理中状態かどうかを判定します"""
        return self == FolderItemType.INDEXING
    
    def is_available(self) -> bool:
        """利用可能状態かどうかを判定します"""
        return self in (FolderItemType.ROOT, FolderItemType.FOLDER, FolderItemType.INDEXED)
    
    def is_error_state(self) -> bool:
        """エラー状態かどうかを判定します"""
        return self == FolderItemType.ERROR
    
    def is_excluded(self) -> bool:
        """除外状態かどうかを判定します"""
        return self == FolderItemType.EXCLUDED
    
    @classmethod
    def get_display_name(cls, item_type: 'FolderItemType') -> str:
        """表示用の名前を取得します"""
        display_names = {
            cls.ROOT: "ルートフォルダ",
            cls.FOLDER: "フォルダ",
            cls.INDEXING: "処理中",
            cls.INDEXED: "インデックス済み",
            cls.EXCLUDED: "除外",
            cls.ERROR: "エラー"
        }
        return display_names.get(item_type, "不明")