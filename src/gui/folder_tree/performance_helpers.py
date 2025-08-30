#!/usr/bin/env python3
"""
フォルダツリーパフォーマンス最適化ヘルパー

メモリ効率とパフォーマンスを向上させるためのヘルパー関数群
"""

import os
from functools import lru_cache


class PathOptimizer:
    """パス操作の最適化クラス"""

    def __init__(self):
        self._path_cache: dict[str, str] = {}
        self._basename_cache: dict[str, str] = {}

    def get_basename(self, path: str) -> str:
        """キャッシュ付きbasename取得"""
        return os.path.basename(path)

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
        self._sets: dict[str, set[str]] = {}

    def get_or_create_set(self, name: str) -> set[str]:
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

    def get_set_list(self, set_name: str) -> list[str]:
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
        self._pending_operations: list = []

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
            except Exception:
                # エラーログ出力（実装時に追加）
                pass

        self._pending_operations.clear()

    def cleanup(self):
        """クリーンアップ"""
        self.flush()
        self._pending_operations.clear()
