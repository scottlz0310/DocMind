# -*- coding: utf-8 -*-
"""
設定管理モジュール

アプリケーションの設定を管理し、デフォルト値の提供、
設定ファイルの読み書き、環境変数の処理を行います。
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """
    アプリケーション設定管理クラス
    
    設定値の取得、保存、デフォルト値の管理を行います。
    設定は以下の優先順位で決定されます：
    1. 環境変数
    2. 設定ファイル
    3. デフォルト値
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        設定管理クラスの初期化
        
        Args:
            config_file: 設定ファイルのパス（省略時はデフォルトパスを使用）
        """
        self.logger = logging.getLogger(__name__)
        
        # デフォルト設定値
        self._defaults = {
            "data_directory": "./docmind_data",
            "log_level": "INFO",
            "max_documents": 50000,
            "search_timeout": 5.0,
            "embedding_model": "all-MiniLM-L6-v2",
            "whoosh_index_dir": "whoosh_index",
            "database_file": "documents.db",
            "embeddings_file": "embeddings.pkl",
            "ui_theme": "default",
            "window_width": 1200,
            "window_height": 800,
            "enable_file_watching": True,
            "batch_size": 100,
            "cache_size": 1000
        }
        
        # 設定の初期化（デフォルト値で開始）
        self._config = self._defaults.copy()
        
        # 設定ファイルのパス
        if config_file is None:
            config_file = os.path.join(self.get_data_directory(), "config.json")
        self.config_file = Path(config_file)
        
        # 設定の読み込み（ファイルが存在する場合）
        self._load_config_from_file()
    
    def _load_config_from_file(self) -> None:
        """
        設定ファイルから設定を読み込んで現在の設定を更新する
        """
        # 設定ファイルが存在する場合は読み込み
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
                self.logger.info(f"設定ファイルを読み込みました: {self.config_file}")
            except Exception as e:
                self.logger.warning(f"設定ファイルの読み込みに失敗しました: {e}")
    
    def save_config(self) -> bool:
        """
        現在の設定を設定ファイルに保存
        
        Returns:
            保存が成功した場合True
        """
        try:
            # 設定ディレクトリの作成
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 設定ファイルの保存
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"設定ファイルを保存しました: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"設定ファイルの保存に失敗しました: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値を取得
        
        Args:
            key: 設定キー
            default: デフォルト値
            
        Returns:
            設定値
        """
        # 環境変数をチェック（DOCMIND_プレフィックス付き）
        env_key = f"DOCMIND_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        # 設定ファイルの値を返す
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        設定値を設定
        
        Args:
            key: 設定キー
            value: 設定値
        """
        self._config[key] = value
    
    def get_data_directory(self) -> str:
        """データディレクトリのパスを取得"""
        return self.get("data_directory")
    
    @property
    def data_dir(self) -> str:
        """データディレクトリのパス（プロパティ）"""
        return self.get_data_directory()
    
    def get_log_level(self) -> str:
        """ログレベルを取得"""
        return self.get("log_level")
    
    def get_max_documents(self) -> int:
        """最大ドキュメント数を取得"""
        return int(self.get("max_documents"))
    
    def get_search_timeout(self) -> float:
        """検索タイムアウト時間を取得"""
        return float(self.get("search_timeout"))
    
    def get_embedding_model(self) -> str:
        """埋め込みモデル名を取得"""
        return self.get("embedding_model")
    
    def get_database_path(self) -> str:
        """データベースファイルのフルパスを取得"""
        return os.path.join(
            self.get_data_directory(),
            self.get("database_file")
        )
    
    def get_embeddings_path(self) -> str:
        """埋め込みファイルのフルパスを取得"""
        return os.path.join(
            self.get_data_directory(),
            self.get("embeddings_file")
        )
    
    def get_index_path(self) -> str:
        """Whooshインデックスディレクトリのフルパスを取得"""
        return os.path.join(
            self.get_data_directory(),
            self.get("whoosh_index_dir")
        )
    
    def get_window_size(self) -> tuple:
        """ウィンドウサイズを取得"""
        return (
            int(self.get("window_width")),
            int(self.get("window_height"))
        )
    
    def is_file_watching_enabled(self) -> bool:
        """ファイル監視が有効かどうかを取得"""
        return bool(self.get("enable_file_watching"))
    
    def get_batch_size(self) -> int:
        """バッチサイズを取得"""
        return int(self.get("batch_size"))
    
    def get_cache_size(self) -> int:
        """キャッシュサイズを取得"""
        return int(self.get("cache_size"))