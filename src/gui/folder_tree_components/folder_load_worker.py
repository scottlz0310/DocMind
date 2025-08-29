#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
フォルダ読み込みワーカー

フォルダ構造を非同期で読み込むワーカークラスです。
元のfolder_tree.pyから分離されました。
"""

import logging
import os
from typing import List
from PySide6.QtCore import QObject, Signal


class FolderLoadWorker(QObject):
    """
    フォルダ構造を非同期で読み込むワーカー
    
    大量のフォルダ構造を効率的に読み込むため、
    非同期処理とメモリ保護機能を提供します。
    """
    
    # シグナル定義
    folder_loaded = Signal(str, list)  # path, subdirectories
    load_error = Signal(str, str)      # path, error_message
    finished = Signal()
    
    def __init__(self, root_path: str, max_depth: int = 3):
        """
        フォルダ読み込みワーカーの初期化
        
        Args:
            root_path: 読み込み対象のルートパス
            max_depth: 最大読み込み深度
        """
        super().__init__()
        self.root_path = root_path
        self.max_depth = max_depth
        self.should_stop = False
        self.logger = logging.getLogger(__name__)
        
    def do_work(self):
        """フォルダ構造を読み込みます"""
        try:
            self.logger.info(f"フォルダ読み込み開始: {self.root_path}")
            self._load_folder_recursive(self.root_path, 0)
        except Exception as e:
            if not self.should_stop:
                self.logger.error(f"フォルダ読み込みエラー: {e}")
                self.load_error.emit(self.root_path, str(e))
        finally:
            self.logger.info("フォルダ読み込み完了")
            self.finished.emit()
    
    def stop(self):
        """読み込みを停止します"""
        self.should_stop = True
        self.logger.info("フォルダ読み込み停止要求")
    
    def _load_folder_recursive(self, path: str, depth: int):
        """
        再帰的にフォルダ構造を読み込みます
        
        Args:
            path: 読み込み対象パス
            depth: 現在の深度
        """
        if self.should_stop or depth > self.max_depth:
            return
            
        try:
            # パスの妥当性チェック
            if not os.path.exists(path) or not os.path.isdir(path):
                return
                
            # アクセス権限チェック
            if not os.access(path, os.R_OK):
                self.load_error.emit(path, "アクセス権限がありません")
                return
                
            # メモリ保護チェック
            if not self._check_memory_limits(path, depth):
                return
                
            subdirs = self._get_subdirectories(path)
            
            if not self.should_stop:
                self.folder_loaded.emit(path, subdirs)
            
            # 再帰的に子フォルダを処理
            if depth < self.max_depth:
                for subdir in subdirs:
                    if not self.should_stop:
                        self._load_folder_recursive(subdir, depth + 1)
                        
        except PermissionError:
            if not self.should_stop:
                self.load_error.emit(path, "アクセス権限がありません")
        except OSError as e:
            if not self.should_stop:
                self.load_error.emit(path, f"OSエラー: {e}")
        except Exception as e:
            if not self.should_stop:
                self.load_error.emit(path, f"予期しないエラー: {type(e).__name__}: {str(e)}")
    
    def _check_memory_limits(self, path: str, depth: int) -> bool:
        """
        メモリ保護のための制限チェック
        
        Args:
            path: チェック対象パス
            depth: 現在の深度
            
        Returns:
            処理を続行可能かどうか
        """
        try:
            items = os.listdir(path)
            
            # ファイル数制限（メモリ保護）
            if len(items) > 10000:
                self.load_error.emit(path, "ファイル数が多すぎます（10,000件以上）")
                return False
                
            # 深さ制限によるメモリ保護
            if depth > 5:
                self.load_error.emit(path, "フォルダの深さが深すぎます（5レベル以上）")
                return False
                
            return True
            
        except OSError as e:
            self.load_error.emit(path, f"ディレクトリ読み込みエラー: {e}")
            return False
    
    def _get_subdirectories(self, path: str) -> List[str]:
        """
        指定パスのサブディレクトリを取得します
        
        Args:
            path: 対象パス
            
        Returns:
            サブディレクトリのパスリスト
        """
        subdirs = []
        
        try:
            items = os.listdir(path)
            
            for item in items:
                if self.should_stop:
                    break
                    
                try:
                    item_path = os.path.join(path, item)
                    
                    # シンボリックリンクの安全な処理
                    if os.path.islink(item_path):
                        if self._is_safe_symlink(item_path, item):
                            subdirs.append(item_path)
                    elif os.path.isdir(item_path) and not item.startswith('.'):
                        subdirs.append(item_path)
                        
                except (OSError, PermissionError):
                    # 個別アイテムのエラーはログに記録してスキップ
                    continue
                    
        except (OSError, PermissionError):
            # ディレクトリ全体のアクセスエラー
            pass
            
        return subdirs
    
    def _is_safe_symlink(self, item_path: str, item: str) -> bool:
        """
        シンボリックリンクが安全かどうかチェックします
        
        Args:
            item_path: アイテムのフルパス
            item: アイテム名
            
        Returns:
            安全なシンボリックリンクかどうか
        """
        try:
            real_path = os.path.realpath(item_path)
            return os.path.isdir(real_path) and not item.startswith('.')
        except (OSError, RuntimeError):
            # シンボリックリンクの解決に失敗した場合は安全でないと判断
            return False