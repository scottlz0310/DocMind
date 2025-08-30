"""
インデックス処理ワーカーモジュール

フォルダのインデックス処理を非同期で実行するワーカークラスを提供します。
"""

import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ..data.models import Document
from ..utils.exceptions import DocumentProcessingError
from .document_processor import DocumentProcessor
from .file_watcher import FileWatcher
from .index_manager import IndexManager


@dataclass
class IndexingStatistics:
    """インデックス処理の統計情報"""

    folder_path: str
    total_files_found: int
    files_processed: int
    files_failed: int
    documents_added: int
    processing_time: float
    errors: list[str]

    def to_dict(self) -> dict[str, object]:
        """辞書形式に変換"""
        return asdict(self)


@dataclass
class IndexingProgress:
    """インデックス処理の進捗情報"""

    stage: str  # "scanning", "processing", "indexing", "watching"
    current_file: str  # 現在処理中のファイル
    files_processed: int  # 処理済みファイル数
    total_files: int  # 総ファイル数
    percentage: int  # 進捗率（0-100）

    def get_message(self) -> str:
        """進捗メッセージを生成"""
        if self.stage == "scanning":
            if self.total_files > 0:
                return f"ファイルをスキャン中... ({self.total_files}個発見)"
            else:
                return "ファイルをスキャン中..."
        elif self.stage == "processing":
            if self.current_file:
                file_name = os.path.basename(self.current_file)
                # ファイル名が長い場合は短縮
                if len(file_name) > 35:
                    name, ext = os.path.splitext(file_name)
                    if len(name) > 30:
                        file_name = name[:27] + "..." + ext

                # ファイル拡張子に応じたアイコンを追加
                ext = os.path.splitext(file_name)[1].lower()
                if ext == ".pdf":
                    icon = "📄"
                elif ext in [".docx", ".doc"]:
                    icon = "📝"
                elif ext in [".xlsx", ".xls"]:
                    icon = "📊"
                elif ext == ".md":
                    icon = "📋"
                elif ext == ".txt":
                    icon = "📃"
                else:
                    icon = "📄"

                return f"処理中: {icon} {file_name} ({self.files_processed}/{self.total_files})"
            else:
                return f"ファイル処理中... ({self.files_processed}/{self.total_files})"
        elif self.stage == "indexing":
            if self.files_processed > 0:
                return (
                    f"インデックスを作成中... ({self.files_processed}ファイル処理済み)"
                )
            else:
                return "インデックスを作成中..."
        elif self.stage == "watching":
            return "ファイル監視を開始中..."
        else:
            if self.total_files > 0:
                return f"処理中... ({self.files_processed}/{self.total_files})"
            else:
                return "処理中..."


class IndexingWorker(QObject):
    """フォルダインデックス処理を非同期で実行するワーカー"""

    # シグナル定義
    progress_updated = Signal(str, int, int)  # message, current, total
    file_processed = Signal(str, bool, str)  # file_path, success, error_msg
    indexing_completed = Signal(str, dict)  # folder_path, statistics
    error_occurred = Signal(str, str)  # context, error_message

    def __init__(
        self,
        folder_path: str,
        document_processor: DocumentProcessor,
        index_manager: IndexManager,
        file_watcher: FileWatcher | None = None,
    ):
        super().__init__()
        self.folder_path = folder_path
        self.document_processor = document_processor
        self.index_manager = index_manager
        self.file_watcher = file_watcher
        self.should_stop = False

        # ログ設定
        self.logger = logging.getLogger(__name__)

        # サポートされているファイル形式
        self.supported_extensions = {
            ".pdf",
            ".docx",
            ".doc",
            ".xlsx",
            ".xls",
            ".md",
            ".txt",
            ".rtf",
            ".odt",
            ".ods",
        }

        # 統計情報
        self.stats = IndexingStatistics(
            folder_path=folder_path,
            total_files_found=0,
            files_processed=0,
            files_failed=0,
            documents_added=0,
            processing_time=0.0,
            errors=[],
        )

    def process_folder(self) -> None:
        """フォルダ処理のメインロジック"""
        start_time = time.time()

        try:
            self.logger.info(f"フォルダのインデックス処理を開始: {self.folder_path}")

            # 1. ファイルスキャン段階
            self._update_progress("scanning", "", 0, 0)
            files = self._scan_files()
            self.stats.total_files_found = len(files)

            if not files:
                self.logger.info(
                    f"処理対象のファイルが見つかりませんでした: {self.folder_path}"
                )
                self._emit_completion()
                return

            # スキャン完了の進捗更新
            self._update_progress("scanning", "", len(files), len(files))

            # 2. ファイル処理段階
            self._process_files(files)

            # 3. インデックス作成段階
            self._update_progress(
                "indexing", "", self.stats.files_processed, self.stats.total_files_found
            )

            # 4. 統計情報の更新
            self.stats.processing_time = time.time() - start_time

            # 5. FileWatcher開始段階
            if self.file_watcher:
                self._update_progress("watching", "", 0, 0)
                self._start_file_watching()

            # 6. 完了通知
            self._emit_completion()

        except Exception as e:
            error_msg = f"フォルダ処理中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.error_occurred.emit("folder_processing", error_msg)

    def _scan_files(self) -> list[str]:
        """サポートされているファイルをスキャン"""
        self.logger.debug(f"ファイルスキャンを開始: {self.folder_path}")

        files: list[str] = []
        scanned_dirs = 0
        total_dirs = 0

        try:
            # まず総ディレクトリ数を概算
            try:
                for _root, dirs, _ in os.walk(self.folder_path):
                    total_dirs += 1 + len(dirs)
                    if total_dirs > 1000:  # 大量のディレクトリがある場合は概算で止める
                        break
            except Exception:
                total_dirs = 0

            # 実際のスキャン
            for root, _, filenames in os.walk(self.folder_path):
                if self.should_stop:
                    break

                scanned_dirs += 1

                # 定期的に進捗を更新
                if scanned_dirs % 5 == 0 or total_dirs == 0:
                    current_dir = (
                        os.path.basename(root)
                        if root != self.folder_path
                        else "ルートフォルダ"
                    )
                    # 現在発見されているファイル数も含めて進捗を更新
                    scan_message = f"スキャン中: {current_dir} ({len(files)}個発見)"
                    self._update_progress(
                        "scanning",
                        scan_message,
                        scanned_dirs,
                        max(total_dirs, scanned_dirs),
                    )

                for filename in filenames:
                    if self.should_stop:
                        break
                    file_path = os.path.join(root, filename)
                    if self._is_supported_file(file_path):
                        files.append(file_path)

            self.logger.info(f"スキャン完了: {len(files)}個のファイルを発見")
            return files

        except Exception as e:
            error_msg = f"ファイルスキャン中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.error_occurred.emit("file_scanning", error_msg)
            return []

    def _is_supported_file(self, file_path: str) -> bool:
        """ファイルがサポートされているかチェック"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    def _process_files(self, files: list[str]) -> None:
        """ファイルの処理"""
        self.logger.debug(f"ファイル処理を開始: {len(files)}個のファイル")

        batch_size = 50  # バッチサイズ
        current_batch: list[Document] = []

        for i, file_path in enumerate(files):
            if self.should_stop:
                break

            try:
                # 進捗更新（処理開始時）
                self._update_progress("processing", file_path, i, len(files))

                # ファイル処理
                document = self._process_single_file(file_path)
                if document:
                    current_batch.append(document)
                    self.stats.documents_added += 1

                self.stats.files_processed += 1

                # 進捗更新（処理完了時）
                self._update_progress("processing", file_path, i + 1, len(files))

                # バッチ処理
                if len(current_batch) >= batch_size:
                    # バッチ処理中の進捗更新
                    self._update_progress("indexing", "", i + 1, len(files))
                    self._process_batch(current_batch)
                    current_batch = []

                # ファイル処理完了シグナル
                self.file_processed.emit(file_path, True, "")

                # 定期的な進捗更新（10ファイルごと）
                if (i + 1) % 10 == 0:
                    self.logger.info(
                        f"進捗: {i + 1}/{len(files)}ファイル処理完了 ({((i + 1) / len(files)) * 100:.1f}%)"
                    )

            except Exception as e:
                error_msg = f"ファイル処理中にエラーが発生しました: {e}"
                self.logger.error(f"{file_path}: {error_msg}")
                self.stats.errors.append(f"{file_path}: {error_msg}")
                self.stats.files_failed += 1
                self.file_processed.emit(file_path, False, str(e))

                # エラー時も進捗を更新
                self._update_progress("processing", file_path, i + 1, len(files))

        # 残りのバッチを処理
        if current_batch and not self.should_stop:
            self._process_batch(current_batch)

    def _process_single_file(self, file_path: str) -> Document | None:
        """単一ファイルの処理"""
        try:
            self.logger.debug(f"ファイルを処理中: {file_path}")

            # DocumentProcessorを使用してファイルを処理
            document = self.document_processor.process_file(file_path)

            if document:
                self.logger.debug(f"ファイル処理完了: {file_path}")
                return document
            else:
                self.logger.warning(
                    f"ファイル処理でドキュメントが生成されませんでした: " f"{file_path}"
                )
                return None

        except DocumentProcessingError as e:
            self.logger.warning(f"ドキュメント処理エラー: {file_path} - {e}")
            raise
        except Exception as e:
            self.logger.error(f"予期しないエラー: {file_path} - {e}")
            raise

    def _process_batch(self, documents: list[Document]) -> None:
        """ドキュメントのバッチ処理"""
        if not documents:
            return

        try:
            self.logger.debug(f"バッチ処理を開始: {len(documents)}個のドキュメント")

            # IndexManagerに一括追加
            for document in documents:
                if self.should_stop:
                    break
                self.index_manager.add_document(document)

            self.logger.debug(f"バッチ処理完了: {len(documents)}個のドキュメント")

        except Exception as e:
            error_msg = f"バッチ処理中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.error_occurred.emit("batch_processing", error_msg)

    def _start_file_watching(self) -> None:
        """ファイル監視の開始"""
        try:
            if self.file_watcher:
                self.logger.info(f"ファイル監視を開始: {self.folder_path}")
                self.file_watcher.add_watch_path(self.folder_path)

        except Exception as e:
            error_msg = f"ファイル監視の開始に失敗しました: {e}"
            self.logger.error(error_msg)
            self.error_occurred.emit("file_watching", error_msg)

    def _update_progress(
        self, stage: str, current_file: str, processed: int, total: int
    ) -> None:
        """進捗情報の更新"""
        percentage = int((processed / total) * 100) if total > 0 else 0

        progress = IndexingProgress(
            stage=stage,
            current_file=current_file,
            files_processed=processed,
            total_files=total,
            percentage=percentage,
        )

        message = progress.get_message()
        self.progress_updated.emit(message, processed, total)

        # より詳細なログ出力
        if stage == "processing" and current_file:
            file_name = os.path.basename(current_file)
            file_size = ""
            try:
                # ファイルサイズを取得して表示
                size_bytes = os.path.getsize(current_file)
                if size_bytes < 1024:
                    file_size = f" ({size_bytes}B)"
                elif size_bytes < 1024 * 1024:
                    file_size = f" ({size_bytes/1024:.1f}KB)"
                else:
                    file_size = f" ({size_bytes/(1024*1024):.1f}MB)"
            except Exception as e:
                self.logger.debug(f"ファイルサイズ取得エラー: {e}")

            self.logger.debug(
                f"処理中: {file_name}{file_size} ({processed}/{total} - {percentage}%)"
            )
        elif stage == "scanning":
            self.logger.debug(f"スキャン進捗: {message}")
        elif stage == "indexing":
            self.logger.debug(f"インデックス進捗: {message}")
        else:
            self.logger.debug(f"進捗更新: {stage} - {message} ({processed}/{total})")

    def _emit_completion(self) -> None:
        """完了通知の送信"""
        self.logger.info(f"インデックス処理完了: {self.folder_path}")
        self.logger.info(f"統計: {self.stats}")

        stats_dict = self.stats.to_dict()
        self.indexing_completed.emit(self.folder_path, stats_dict)

    def stop(self) -> None:
        """処理の停止"""
        self.logger.info("インデックス処理の停止を要求されました")
        self.should_stop = True
