"""
設定管理モジュール

アプリケーションの設定を管理し、デフォルト値の提供、
設定ファイルの読み書き、環境変数の処理を行います。
"""

import json
import logging
import os
from pathlib import Path
from typing import Any


class Config:
    """
    アプリケーション設定管理クラス

    設定値の取得、保存、デフォルト値の管理を行います。
    設定は以下の優先順位で決定されます：
    1. 環境変数
    2. 設定ファイル
    3. デフォルト値
    """

    def __init__(self, config_file: str | None = None):
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
            "cache_size": 1000,
            # 検索設定
            "max_results": 100,
            "semantic_weight": 50,
            # フォルダ管理
            "indexed_folders": [],
            "exclude_patterns": [
                "*.tmp",
                "*.log",
                "__pycache__/*",
                ".git/*",
                "node_modules/*",
            ],
            # ログ設定
            "console_logging": True,
            "file_logging": True,
            "log_file": "logs/docmind.log",
            # UI設定
            "font_family": "システムデフォルト",
            "font_size": 10,
            # パフォーマンス設定
            "enable_preview_cache": True,
            "preview_cache_size": 50,
            "enable_search_history": True,
            "search_history_limit": 1000,
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
                with open(self.config_file, encoding="utf-8") as f:
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
            with open(self.config_file, "w", encoding="utf-8") as f:
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
        """
        データディレクトリのパスを文字列で取得

        既存のAPIとの互換性を維持

        Returns:
            データディレクトリのパス（文字列）
        """
        return self.get("data_directory")

    @property
    def data_dir(self) -> Path:
        """
        データディレクトリのパスを取得

        Returns:
            Pathオブジェクト（文字列ではなく）
        """
        return Path(self.get_data_directory())

    @property
    def database_file(self) -> str:
        """データベースファイル名を取得"""
        return self.get("database_file")

    @property
    def embeddings_file(self) -> str:
        """埋め込みファイル名を取得"""
        return self.get("embeddings_file")

    @property
    def index_dir(self) -> Path:
        """インデックスディレクトリのパスを取得

        Returns:
            Pathオブジェクト（文字列ではなく）
        """
        return Path(self.get_index_path())

    @property
    def log_dir(self) -> Path:
        """ログディレクトリのパスを取得

        Returns:
            Pathオブジェクト（文字列ではなく）
        """
        return self.data_dir / "logs"

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
        return os.path.join(self.get_data_directory(), self.get("database_file"))

    def get_embeddings_path(self) -> str:
        """埋め込みファイルのフルパスを取得"""
        return os.path.join(self.get_data_directory(), self.get("embeddings_file"))

    def get_index_path(self) -> str:
        """Whooshインデックスディレクトリのフルパスを取得"""
        return os.path.join(self.get_data_directory(), self.get("whoosh_index_dir"))

    def get_window_size(self) -> tuple:
        """ウィンドウサイズを取得"""
        return (int(self.get("window_width")), int(self.get("window_height")))

    def is_file_watching_enabled(self) -> bool:
        """ファイル監視が有効かどうかを取得"""
        return bool(self.get("enable_file_watching"))

    def get_batch_size(self) -> int:
        """バッチサイズを取得"""
        return int(self.get("batch_size"))

    def get_cache_size(self) -> int:
        """キャッシュサイズを取得"""
        return int(self.get("cache_size"))

    def get_indexed_folders(self) -> list[str]:
        """インデックス対象フォルダのリストを取得"""
        folders = self.get("indexed_folders", [])
        return folders if isinstance(folders, list) else []

    def add_indexed_folder(self, folder_path: str) -> bool:
        """インデックス対象フォルダを追加"""
        try:
            folders = self.get_indexed_folders()
            if folder_path not in folders:
                folders.append(folder_path)
                self.set("indexed_folders", folders)
                return True
            return False
        except Exception as e:
            self.logger.error(f"フォルダの追加に失敗しました: {e}")
            return False

    def remove_indexed_folder(self, folder_path: str) -> bool:
        """インデックス対象フォルダを削除"""
        try:
            folders = self.get_indexed_folders()
            if folder_path in folders:
                folders.remove(folder_path)
                self.set("indexed_folders", folders)
                return True
            return False
        except Exception as e:
            self.logger.error(f"フォルダの削除に失敗しました: {e}")
            return False

    def get_exclude_patterns(self) -> list[str]:
        """除外パターンのリストを取得"""
        patterns = self.get("exclude_patterns", [])
        return patterns if isinstance(patterns, list) else []

    def set_exclude_patterns(self, patterns: list[str]) -> None:
        """除外パターンを設定"""
        self.set("exclude_patterns", patterns)

    def get_log_file_path(self) -> str:
        """ログファイルのフルパスを取得"""
        log_file = self.get("log_file", "logs/docmind.log")
        if os.path.isabs(log_file):
            return log_file
        return os.path.join(self.get_data_directory(), log_file)

    def is_console_logging_enabled(self) -> bool:
        """コンソールログが有効かどうかを取得"""
        return bool(self.get("console_logging", True))

    def is_file_logging_enabled(self) -> bool:
        """ファイルログが有効かどうかを取得"""
        return bool(self.get("file_logging", True))

    def get_font_settings(self) -> dict[str, Any]:
        """フォント設定を取得"""
        return {
            "family": self.get("font_family", "システムデフォルト"),
            "size": int(self.get("font_size", 10)),
        }

    def get_ui_theme(self) -> str:
        """UIテーマを取得"""
        return self.get("ui_theme", "default")

    def get_search_settings(self) -> dict[str, Any]:
        """検索関連設定を取得"""
        return {
            "max_results": int(self.get("max_results", 100)),
            "semantic_weight": float(self.get("semantic_weight", 50)),
            "enable_search_history": bool(self.get("enable_search_history", True)),
            "search_history_limit": int(self.get("search_history_limit", 1000)),
        }

    def get_performance_settings(self) -> dict[str, Any]:
        """パフォーマンス関連設定を取得"""
        return {
            "enable_preview_cache": bool(self.get("enable_preview_cache", True)),
            "preview_cache_size": int(self.get("preview_cache_size", 50)),
            "batch_size": self.get_batch_size(),
            "cache_size": self.get_cache_size(),
        }

    def validate_settings(self) -> list[str]:
        """設定の妥当性を検証し、問題があれば警告メッセージのリストを返す"""
        warnings = []

        try:
            # データディレクトリの検証
            data_dir = Path(self.get_data_directory())
            if not data_dir.parent.exists():
                warnings.append(
                    f"データディレクトリの親ディレクトリが存在しません: {data_dir.parent}"
                )

            # インデックス対象フォルダの検証
            for folder in self.get_indexed_folders():
                if not Path(folder).exists():
                    warnings.append(f"インデックス対象フォルダが存在しません: {folder}")

            # 数値設定の検証
            if self.get_max_documents() < 1000:
                warnings.append("最大ドキュメント数は1000以上である必要があります")

            if self.get_search_timeout() < 1.0:
                warnings.append("検索タイムアウトは1秒以上である必要があります")

            if self.get_batch_size() < 10:
                warnings.append("バッチサイズは10以上である必要があります")

            if self.get_cache_size() < 100:
                warnings.append("キャッシュサイズは100以上である必要があります")

            # ログファイルの検証
            log_file = Path(self.get_log_file_path())
            if not log_file.parent.exists():
                warnings.append(
                    f"ログファイルのディレクトリが存在しません: {log_file.parent}"
                )

        except Exception as e:
            warnings.append(f"設定の検証中にエラーが発生しました: {e}")

        return warnings

    def reset_to_defaults(self) -> None:
        """設定をデフォルト値にリセット"""
        self._config = self._defaults.copy()
        self.logger.info("設定をデフォルト値にリセットしました")

    def export_settings(self, file_path: str) -> bool:
        """設定をファイルにエクスポート"""
        try:
            export_data = {
                "version": "1.0",
                "timestamp": (
                    Path(file_path).stat().st_mtime
                    if Path(file_path).exists()
                    else None
                ),
                "settings": self._config.copy(),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"設定をエクスポートしました: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"設定のエクスポートに失敗しました: {e}")
            return False

    def import_settings(self, file_path: str) -> bool:
        """ファイルから設定をインポート"""
        try:
            with open(file_path, encoding="utf-8") as f:
                import_data = json.load(f)

            if "settings" in import_data:
                # バージョンチェック（将来の拡張用）
                version = import_data.get("version", "1.0")
                if version == "1.0":
                    self._config.update(import_data["settings"])
                    self.logger.info(f"設定をインポートしました: {file_path}")
                    return True
                else:
                    self.logger.warning(
                        f"サポートされていない設定ファイルのバージョンです: {version}"
                    )
                    return False
            else:
                self.logger.error("無効な設定ファイル形式です")
                return False

        except Exception as e:
            self.logger.error(f"設定のインポートに失敗しました: {e}")
            return False


# グローバル設定インスタンス
_global_config = None


def get_config() -> Config:
    """グローバル設定インスタンスを取得

    Returns:
        Config: グローバル設定インスタンス
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def set_config(config: Config) -> None:
    """グローバル設定インスタンスを設定

    Args:
        config: 設定するConfigインスタンス
    """
    global _global_config
    _global_config = config
