#!/usr/bin/env python3
"""
DocMind - 自動更新システム
アプリケーションの自動更新機能を提供

このモジュールは以下の機能を提供します：
- バージョンチェック
- 更新ファイルのダウンロード
- 自動インストール
- ロールバック機能
"""

import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, urlretrieve

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QProgressDialog

from .config import Config
from .exceptions import UpdateError

logger = logging.getLogger(__name__)


class UpdateInfo:
    """更新情報を格納するクラス"""

    def __init__(self, data: dict[str, Any]):
        self.version = data.get("version", "0.0.0")
        self.download_url = data.get("download_url", "")
        self.changelog = data.get("changelog", "")
        self.file_size = data.get("file_size", 0)
        self.checksum = data.get("checksum", "")
        self.required = data.get("required", False)
        self.release_date = data.get("release_date", "")
        self.minimum_version = data.get("minimum_version", "0.0.0")


class UpdateChecker(QObject):
    """更新チェッククラス"""

    # シグナル定義
    update_available = Signal(object)  # UpdateInfo
    no_update_available = Signal()
    check_failed = Signal(str)  # エラーメッセージ

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.current_version = self._get_current_version()
        self.update_server_url = config.get(
            "update_server_url",
            "https://api.github.com/repos/docmind/docmind/releases/latest",
        )

    def _get_current_version(self) -> str:
        """現在のアプリケーションバージョンを取得"""
        try:
            # バージョン情報ファイルから読み取り
            version_file = Path(__file__).parent.parent.parent / "version.txt"
            if version_file.exists():
                return version_file.read_text().strip()
            else:
                return "1.0.0"  # デフォルトバージョン
        except Exception as e:
            logger.warning(f"バージョン情報の取得に失敗: {e}")
            return "1.0.0"

    def check_for_updates(self) -> None:
        """更新をチェック（非同期）"""
        thread = threading.Thread(target=self._check_updates_thread)
        thread.daemon = True
        thread.start()

    def _check_updates_thread(self) -> None:
        """更新チェックのスレッド処理"""
        try:
            logger.info("更新をチェック中...")

            # 更新サーバーから情報を取得
            with urlopen(self.update_server_url, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            # GitHub APIレスポンスの解析
            if "tag_name" in data:
                latest_version = data["tag_name"].lstrip("v")
                download_url = None

                # Windows用アセットを検索
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".exe") or asset["name"].endswith(".msi"):
                        download_url = asset["browser_download_url"]
                        file_size = asset["size"]
                        break

                if download_url:
                    update_info = UpdateInfo(
                        {
                            "version": latest_version,
                            "download_url": download_url,
                            "changelog": data.get("body", ""),
                            "file_size": file_size,
                            "release_date": data.get("published_at", ""),
                            "required": False,
                        }
                    )

                    # バージョン比較
                    if self._is_newer_version(latest_version, self.current_version):
                        logger.info(f"新しいバージョンが利用可能: {latest_version}")
                        self.update_available.emit(update_info)
                    else:
                        logger.info("最新バージョンを使用中")
                        self.no_update_available.emit()
                else:
                    logger.warning("ダウンロード可能なアセットが見つかりません")
                    self.no_update_available.emit()
            else:
                logger.error("無効な更新情報レスポンス")
                self.check_failed.emit("更新情報の形式が無効です")

        except (URLError, HTTPError) as e:
            logger.error(f"更新チェックでネットワークエラー: {e}")
            self.check_failed.emit(f"ネットワークエラー: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"更新情報の解析エラー: {e}")
            self.check_failed.emit("更新情報の解析に失敗しました")
        except Exception as e:
            logger.error(f"更新チェックで予期しないエラー: {e}")
            self.check_failed.emit(f"予期しないエラー: {e}")

    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """バージョン比較（version1 > version2の場合True）"""
        try:
            v1_parts = [int(x) for x in version1.split(".")]
            v2_parts = [int(x) for x in version2.split(".")]

            # 長さを揃える
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            return v1_parts > v2_parts
        except ValueError:
            logger.warning(f"バージョン比較エラー: {version1} vs {version2}")
            return False


class UpdateDownloader(QObject):
    """更新ファイルダウンローダー"""

    # シグナル定義
    download_progress = Signal(int, int)  # current, total
    download_completed = Signal(str)  # file_path
    download_failed = Signal(str)  # error_message

    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.cancel_requested = False

    def download_update(self, update_info: UpdateInfo) -> None:
        """更新ファイルをダウンロード"""
        if self.download_thread and self.download_thread.is_alive():
            logger.warning("ダウンロードが既に進行中です")
            return

        self.cancel_requested = False
        self.download_thread = threading.Thread(
            target=self._download_thread, args=(update_info,)
        )
        self.download_thread.daemon = True
        self.download_thread.start()

    def cancel_download(self) -> None:
        """ダウンロードをキャンセル"""
        self.cancel_requested = True

    def _download_thread(self, update_info: UpdateInfo) -> None:
        """ダウンロードスレッド処理"""
        temp_file = None
        try:
            # 一時ファイルの作成
            temp_dir = tempfile.gettempdir()
            filename = f"DocMind_Update_{update_info.version}.exe"
            temp_file = os.path.join(temp_dir, filename)

            logger.info(f"更新ファイルをダウンロード中: {update_info.download_url}")

            # プログレス付きダウンロード
            def progress_hook(block_num, block_size, total_size):
                if self.cancel_requested:
                    raise Exception("ダウンロードがキャンセルされました")

                downloaded = block_num * block_size
                if total_size > 0:
                    self.download_progress.emit(downloaded, total_size)

            urlretrieve(update_info.download_url, temp_file, progress_hook)

            # チェックサムの検証（利用可能な場合）
            if update_info.checksum:
                if not self._verify_checksum(temp_file, update_info.checksum):
                    raise UpdateError(
                        "ダウンロードファイルのチェックサムが一致しません"
                    )

            logger.info(f"ダウンロード完了: {temp_file}")
            self.download_completed.emit(temp_file)

        except Exception as e:
            logger.error(f"ダウンロードエラー: {e}")
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            self.download_failed.emit(str(e))

    def _verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        """ファイルのチェックサムを検証"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

            actual_checksum = sha256_hash.hexdigest()
            return actual_checksum.lower() == expected_checksum.lower()
        except Exception as e:
            logger.error(f"チェックサム検証エラー: {e}")
            return False


class UpdateInstaller:
    """更新インストーラー"""

    def __init__(self, config: Config):
        self.config = config

    def install_update(self, installer_path: str) -> bool:
        """更新をインストール"""
        try:
            logger.info(f"更新をインストール中: {installer_path}")

            # インストーラーの実行
            if installer_path.endswith(".exe"):
                # 実行可能インストーラー
                cmd = [installer_path, "/SILENT", "/NORESTART"]
            elif installer_path.endswith(".msi"):
                # MSIインストーラー
                cmd = ["msiexec", "/i", installer_path, "/quiet", "/norestart"]
            else:
                raise UpdateError(
                    f"サポートされていないインストーラー形式: {installer_path}"
                )

            # インストーラーを実行
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("更新のインストールが完了しました")
                return True
            else:
                logger.error(f"インストールエラー: {result.stderr}")
                raise UpdateError(f"インストールに失敗しました: {result.stderr}")

        except Exception as e:
            logger.error(f"更新インストールエラー: {e}")
            raise UpdateError(f"更新のインストールに失敗しました: {e}")

    def schedule_restart(self) -> None:
        """アプリケーションの再起動をスケジュール"""
        try:
            # 現在のアプリケーションパスを取得
            current_exe = sys.executable
            if hasattr(sys, "frozen"):
                current_exe = sys.executable

            # 再起動スクリプトを作成
            restart_script = f"""
@echo off
timeout /t 3 /nobreak >nul
start "" "{current_exe}"
del "%~f0"
"""

            fd, script_path = tempfile.mkstemp(suffix=".bat")
            os.close(fd)  # ファイルディスクリプタを閉じる
            with open(script_path, "w", encoding="shift_jis") as f:
                f.write(restart_script)

            # スクリプトを実行して終了
            subprocess.Popen(["cmd", "/c", script_path], shell=False)

            logger.info("再起動をスケジュールしました")

        except Exception as e:
            logger.error(f"再起動スケジュールエラー: {e}")


class UpdateManager(QObject):
    """更新管理メインクラス"""

    # シグナル定義
    update_check_completed = Signal(bool, object)  # success, update_info
    update_download_progress = Signal(int, int)
    update_installation_completed = Signal(bool, str)  # success, message

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.checker = UpdateChecker(config)
        self.downloader = UpdateDownloader()
        self.installer = UpdateInstaller(config)

        # シグナル接続
        self._connect_signals()

    def _connect_signals(self) -> None:
        """シグナルを接続"""
        self.checker.update_available.connect(self._on_update_available)
        self.checker.no_update_available.connect(self._on_no_update_available)
        self.checker.check_failed.connect(self._on_check_failed)

        self.downloader.download_progress.connect(self.update_download_progress.emit)
        self.downloader.download_completed.connect(self._on_download_completed)
        self.downloader.download_failed.connect(self._on_download_failed)

    def check_for_updates(self, silent: bool = False) -> None:
        """更新をチェック"""
        self.silent_check = silent
        self.checker.check_for_updates()

    def download_and_install_update(self, update_info: UpdateInfo) -> None:
        """更新をダウンロードしてインストール"""
        self.current_update_info = update_info
        self.downloader.download_update(update_info)

    def _on_update_available(self, update_info: UpdateInfo) -> None:
        """更新が利用可能な場合の処理"""
        self.update_check_completed.emit(True, update_info)

    def _on_no_update_available(self) -> None:
        """更新が利用できない場合の処理"""
        self.update_check_completed.emit(False, None)

    def _on_check_failed(self, error_message: str) -> None:
        """更新チェック失敗時の処理"""
        logger.error(f"更新チェック失敗: {error_message}")
        self.update_check_completed.emit(False, None)

    def _on_download_completed(self, file_path: str) -> None:
        """ダウンロード完了時の処理"""
        try:
            # インストールを実行
            success = self.installer.install_update(file_path)

            if success:
                # 一時ファイルを削除
                try:
                    os.remove(file_path)
                except:
                    pass

                self.update_installation_completed.emit(
                    True, "更新が正常にインストールされました"
                )

                # 再起動をスケジュール
                self.installer.schedule_restart()
            else:
                self.update_installation_completed.emit(
                    False, "更新のインストールに失敗しました"
                )

        except Exception as e:
            logger.error(f"インストール処理エラー: {e}")
            self.update_installation_completed.emit(False, f"インストールエラー: {e}")

    def _on_download_failed(self, error_message: str) -> None:
        """ダウンロード失敗時の処理"""
        logger.error(f"ダウンロード失敗: {error_message}")
        self.update_installation_completed.emit(
            False, f"ダウンロードエラー: {error_message}"
        )


def show_update_dialog(parent, update_info: UpdateInfo) -> bool:
    """更新ダイアログを表示"""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("更新が利用可能")
    msg.setText(f"DocMind {update_info.version} が利用可能です。")
    msg.setDetailedText(f"変更内容:\n{update_info.changelog}")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.Yes)

    return msg.exec() == QMessageBox.Yes


def show_update_progress_dialog(parent) -> QProgressDialog:
    """更新進捗ダイアログを表示"""
    progress = QProgressDialog("更新をダウンロード中...", "キャンセル", 0, 100, parent)
    progress.setWindowTitle("更新中")
    progress.setWindowModality(2)  # ApplicationModal
    progress.show()

    return progress
