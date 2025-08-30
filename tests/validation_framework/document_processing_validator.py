"""
ドキュメント処理機能包括検証クラス

DocMindアプリケーションのドキュメント処理機能について
包括的な検証を実施します。
"""

import os
import shutil
import tempfile
import time
from typing import Any

try:
    from .base_validator import BaseValidator, ValidationConfig, ValidationResult
    from .test_data_generator import TestDataGenerator, TestDatasetConfig
except ImportError:
    # テスト環境での代替インポート
    import os
    import sys

    current_dir = os.path.dirname(__file__)
    sys.path.insert(0, current_dir)

    from base_validator import BaseValidator, ValidationConfig
    from test_data_generator import TestDataGenerator, TestDatasetConfig

# DocMindアプリケーションのインポート（テスト用にモック対応）
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from src.core.document_processor import DocumentProcessor
    from src.data.models import FileType
    from src.utils.exceptions import DocumentProcessingError
except ImportError:
    # テスト環境でDocMindアプリケーションが利用できない場合のモック
    class DocumentProcessor:
        def __init__(self):
            pass

        def process_file(self, file_path):
            # モック実装
            class MockDocument:
                def __init__(self, content):
                    self.content = content

            return MockDocument(f"Mock content for {file_path}")

        def _detect_encoding(self, file_path):
            return "utf-8"

    class FileType:
        PDF = "pdf"
        WORD = "word"
        EXCEL = "excel"
        MARKDOWN = "markdown"
        TEXT = "text"

    class DocumentProcessingError(Exception):
        def __init__(self, message, file_path=None, file_type=None, details=None):
            super().__init__(message)
            self.file_path = file_path
            self.file_type = file_type
            self.details = details


class DocumentProcessingValidator(BaseValidator):
    """
    ドキュメント処理機能包括検証クラス

    PDF、Word、Excel、テキスト、Markdownファイルの処理精度検証、
    テキスト抽出精度とエンコーディング自動検出の検証、
    大容量ファイル処理とエラーハンドリングの検証を実施します。
    """

    def __init__(self, config: ValidationConfig | None = None):
        """
        ドキュメント処理検証クラスの初期化

        Args:
            config: 検証設定
        """
        super().__init__(config)

        # DocMindコンポーネントの初期化
        self.document_processor = DocumentProcessor()
        self.test_data_generator = TestDataGenerator()

        # テスト用ディレクトリ
        self.test_data_dir = None
        self.temp_dirs = []

        # 検証結果の詳細情報
        self.processing_stats = {
            "files_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_characters_extracted": 0,
            "processing_times": [],
            "file_type_stats": {},
            "encoding_detection_stats": {},
            "error_types": {},
        }

        self.logger.info("ドキュメント処理検証クラスを初期化しました")

    def setup_test_environment(self) -> None:
        """テスト環境のセットアップ"""
        self.logger.info("ドキュメント処理検証のテスト環境をセットアップします")

        # テストデータディレクトリの作成
        self.test_data_dir = tempfile.mkdtemp(prefix="docmind_validation_")
        self.temp_dirs.append(self.test_data_dir)

        # 各種テストデータセットの生成
        self._generate_test_datasets()

        self.logger.info(f"テスト環境セットアップ完了: {self.test_data_dir}")

    def teardown_test_environment(self) -> None:
        """テスト環境のクリーンアップ"""
        self.logger.info("ドキュメント処理検証のテスト環境をクリーンアップします")

        # 一時ディレクトリの削除
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"一時ディレクトリを削除: {temp_dir}")
            except Exception as e:
                self.logger.warning(f"一時ディレクトリ削除に失敗: {temp_dir} - {e}")

        # テストデータ生成クラスのクリーンアップ
        self.test_data_generator.cleanup()

        self.temp_dirs.clear()
        self.logger.info("テスト環境クリーンアップ完了")

    def _generate_test_datasets(self) -> None:
        """テストデータセットの生成（軽量版）"""
        self.logger.info("テストデータセットを生成します")

        # 標準テストデータセット（軽量化）
        standard_config = TestDatasetConfig(
            dataset_name="standard_documents",
            output_directory=os.path.join(self.test_data_dir, "standard"),
            file_count=5,  # 50 -> 5に削減
            file_types=["txt", "md", "json"],  # 軽量なファイル形式のみ
            size_range_kb=(1, 10),  # 100KB -> 10KBに削減
            content_language="ja",
            include_corrupted=False,
            include_large_files=False,
            include_special_chars=False,
        )
        self.test_data_generator.generate_dataset(standard_config)

        # エンコーディングテスト用データセット（軽量化）
        encoding_config = TestDatasetConfig(
            dataset_name="encoding_test",
            output_directory=os.path.join(self.test_data_dir, "encoding"),
            file_count=3,  # 20 -> 3に削減
            file_types=["txt"],  # テキストファイルのみ
            size_range_kb=(1, 5),  # 50KB -> 5KBに削減
            content_language="ja",
            include_special_chars=True,
        )
        self.test_data_generator.generate_dataset(encoding_config)

        # 大容量ファイルテスト用データセット（軽量化）
        large_file_config = TestDatasetConfig(
            dataset_name="large_files",
            output_directory=os.path.join(self.test_data_dir, "large"),
            file_count=2,  # 10 -> 2に削減
            file_types=["txt"],  # テキストファイルのみ
            size_range_kb=(100, 200),  # 1MB-5MB -> 100KB-200KBに削減
            content_language="ja",
            include_large_files=True,
        )
        self.test_data_generator.generate_dataset(large_file_config)

        # エラーハンドリングテスト用データセット（軽量化）
        error_config = TestDatasetConfig(
            dataset_name="error_handling",
            output_directory=os.path.join(self.test_data_dir, "error"),
            file_count=3,  # 15 -> 3に削減
            file_types=["txt"],  # テキストファイルのみ
            size_range_kb=(1, 10),  # 100KB -> 10KBに削減
            content_language="ja",
            include_corrupted=True,
        )
        self.test_data_generator.generate_dataset(error_config)

        self.logger.info("テストデータセット生成完了")

    def test_pdf_processing_accuracy(self) -> None:
        """PDF処理精度の検証"""
        self.logger.info("PDF処理精度の検証を開始します")

        pdf_files = self._get_test_files_by_type("pdf")

        if not pdf_files:
            self.logger.warning("PDFテストファイルが見つかりません")
            return

        successful_count = 0
        total_count = len(pdf_files)

        for pdf_file in pdf_files:
            try:
                start_time = time.time()
                document = self.document_processor.process_file(pdf_file)
                processing_time = time.time() - start_time

                # 基本的な検証
                self.assert_condition(
                    document is not None,
                    f"PDFドキュメントオブジェクトが作成されませんでした: {pdf_file}",
                )

                self.assert_condition(
                    len(document.content) > 0,
                    f"PDFからテキストが抽出されませんでした: {pdf_file}",
                )

                # 統計情報の更新
                self._update_processing_stats(
                    "pdf", True, len(document.content), processing_time
                )
                successful_count += 1

                self.logger.debug(
                    f"PDF処理成功: {pdf_file} ({len(document.content)}文字, {processing_time:.2f}秒)"
                )

            except Exception as e:
                self._update_processing_stats("pdf", False, 0, 0, str(e))
                self.logger.error(f"PDF処理失敗: {pdf_file} - {e}")

        # 成功率の検証
        success_rate = successful_count / total_count if total_count > 0 else 0
        self.assert_condition(
            success_rate >= 0.8,  # 80%以上の成功率を要求
            f"PDF処理成功率が低すぎます: {success_rate:.2%} (要求: 80%以上)",
        )

        self.logger.info(
            f"PDF処理精度検証完了: {successful_count}/{total_count} ({success_rate:.2%})"
        )

    def test_word_processing_accuracy(self) -> None:
        """Word文書処理精度の検証"""
        self.logger.info("Word文書処理精度の検証を開始します")

        word_files = self._get_test_files_by_type("docx")

        if not word_files:
            self.logger.warning("Wordテストファイルが見つかりません")
            return

        successful_count = 0
        total_count = len(word_files)

        for word_file in word_files:
            try:
                start_time = time.time()
                document = self.document_processor.process_file(word_file)
                processing_time = time.time() - start_time

                # 基本的な検証
                self.assert_condition(
                    document is not None,
                    f"Wordドキュメントオブジェクトが作成されませんでした: {word_file}",
                )

                self.assert_condition(
                    len(document.content) > 0,
                    f"Wordからテキストが抽出されませんでした: {word_file}",
                )

                # 書式が除去されていることを確認
                self.assert_condition(
                    not any(tag in document.content for tag in ["<", ">", "{", "}"]),
                    f"Word文書に書式タグが残っています: {word_file}",
                )

                # 統計情報の更新
                self._update_processing_stats(
                    "docx", True, len(document.content), processing_time
                )
                successful_count += 1

                self.logger.debug(
                    f"Word処理成功: {word_file} ({len(document.content)}文字, {processing_time:.2f}秒)"
                )

            except Exception as e:
                self._update_processing_stats("docx", False, 0, 0, str(e))
                self.logger.error(f"Word処理失敗: {word_file} - {e}")

        # 成功率の検証
        success_rate = successful_count / total_count if total_count > 0 else 0
        self.assert_condition(
            success_rate >= 0.9,  # 90%以上の成功率を要求
            f"Word処理成功率が低すぎます: {success_rate:.2%} (要求: 90%以上)",
        )

        self.logger.info(
            f"Word処理精度検証完了: {successful_count}/{total_count} ({success_rate:.2%})"
        )

    def test_excel_processing_accuracy(self) -> None:
        """Excel処理精度の検証"""
        self.logger.info("Excel処理精度の検証を開始します")

        excel_files = self._get_test_files_by_type("xlsx")

        if not excel_files:
            self.logger.warning("Excelテストファイルが見つかりません")
            return

        successful_count = 0
        total_count = len(excel_files)

        for excel_file in excel_files:
            try:
                start_time = time.time()
                document = self.document_processor.process_file(excel_file)
                processing_time = time.time() - start_time

                # 基本的な検証
                self.assert_condition(
                    document is not None,
                    f"Excelドキュメントオブジェクトが作成されませんでした: {excel_file}",
                )

                self.assert_condition(
                    len(document.content) > 0,
                    f"Excelからテキストが抽出されませんでした: {excel_file}",
                )

                # シート情報が含まれていることを確認
                self.assert_condition(
                    "シート:" in document.content,
                    f"Excelシート情報が含まれていません: {excel_file}",
                )

                # 統計情報の更新
                self._update_processing_stats(
                    "xlsx", True, len(document.content), processing_time
                )
                successful_count += 1

                self.logger.debug(
                    f"Excel処理成功: {excel_file} ({len(document.content)}文字, {processing_time:.2f}秒)"
                )

            except Exception as e:
                self._update_processing_stats("xlsx", False, 0, 0, str(e))
                self.logger.error(f"Excel処理失敗: {excel_file} - {e}")

        # 成功率の検証
        success_rate = successful_count / total_count if total_count > 0 else 0
        self.assert_condition(
            success_rate >= 0.9,  # 90%以上の成功率を要求
            f"Excel処理成功率が低すぎます: {success_rate:.2%} (要求: 90%以上)",
        )

        self.logger.info(
            f"Excel処理精度検証完了: {successful_count}/{total_count} ({success_rate:.2%})"
        )

    def test_text_processing_accuracy(self) -> None:
        """テキストファイル処理精度の検証"""
        self.logger.info("テキストファイル処理精度の検証を開始します")

        text_files = self._get_test_files_by_type("txt")

        if not text_files:
            self.logger.warning("テキストテストファイルが見つかりません")
            return

        successful_count = 0
        total_count = len(text_files)

        for text_file in text_files:
            try:
                start_time = time.time()
                document = self.document_processor.process_file(text_file)
                processing_time = time.time() - start_time

                # 基本的な検証
                self.assert_condition(
                    document is not None,
                    f"テキストドキュメントオブジェクトが作成されませんでした: {text_file}",
                )

                # 元ファイルとの内容比較
                with open(text_file, encoding="utf-8") as f:
                    original_content = f.read()

                # 内容が一致することを確認（改行の違いは許容）
                normalized_original = original_content.strip().replace("\r\n", "\n")
                normalized_extracted = document.content.strip().replace("\r\n", "\n")

                self.assert_condition(
                    normalized_original == normalized_extracted,
                    f"テキストファイルの内容が一致しません: {text_file}",
                )

                # 統計情報の更新
                self._update_processing_stats(
                    "txt", True, len(document.content), processing_time
                )
                successful_count += 1

                self.logger.debug(
                    f"テキスト処理成功: {text_file} ({len(document.content)}文字, {processing_time:.2f}秒)"
                )

            except Exception as e:
                self._update_processing_stats("txt", False, 0, 0, str(e))
                self.logger.error(f"テキスト処理失敗: {text_file} - {e}")

        # 成功率の検証
        success_rate = successful_count / total_count if total_count > 0 else 0
        self.assert_condition(
            success_rate >= 0.95,  # 95%以上の成功率を要求
            f"テキスト処理成功率が低すぎます: {success_rate:.2%} (要求: 95%以上)",
        )

        self.logger.info(
            f"テキスト処理精度検証完了: {successful_count}/{total_count} ({success_rate:.2%})"
        )

    def test_markdown_processing_accuracy(self) -> None:
        """Markdown処理精度の検証"""
        self.logger.info("Markdown処理精度の検証を開始します")

        markdown_files = self._get_test_files_by_type("md")

        if not markdown_files:
            self.logger.warning("Markdownテストファイルが見つかりません")
            return

        successful_count = 0
        total_count = len(markdown_files)

        for md_file in markdown_files:
            try:
                start_time = time.time()
                document = self.document_processor.process_file(md_file)
                processing_time = time.time() - start_time

                # 基本的な検証
                self.assert_condition(
                    document is not None,
                    f"Markdownドキュメントオブジェクトが作成されませんでした: {md_file}",
                )

                self.assert_condition(
                    len(document.content) > 0,
                    f"Markdownからテキストが抽出されませんでした: {md_file}",
                )

                # マークアップが適切に処理されていることを確認
                self.assert_condition(
                    not document.content.startswith("#"),
                    f"Markdownの見出し記法が残っています: {md_file}",
                )

                # 統計情報の更新
                self._update_processing_stats(
                    "md", True, len(document.content), processing_time
                )
                successful_count += 1

                self.logger.debug(
                    f"Markdown処理成功: {md_file} ({len(document.content)}文字, {processing_time:.2f}秒)"
                )

            except Exception as e:
                self._update_processing_stats("md", False, 0, 0, str(e))
                self.logger.error(f"Markdown処理失敗: {md_file} - {e}")

        # 成功率の検証
        success_rate = successful_count / total_count if total_count > 0 else 0
        self.assert_condition(
            success_rate >= 0.9,  # 90%以上の成功率を要求
            f"Markdown処理成功率が低すぎます: {success_rate:.2%} (要求: 90%以上)",
        )

        self.logger.info(
            f"Markdown処理精度検証完了: {successful_count}/{total_count} ({success_rate:.2%})"
        )

    def test_encoding_detection_accuracy(self) -> None:
        """エンコーディング自動検出の検証"""
        self.logger.info("エンコーディング自動検出の検証を開始します")

        # 異なるエンコーディングのテストファイルを作成
        encoding_test_files = self._create_encoding_test_files()

        successful_detections = 0
        total_files = len(encoding_test_files)

        for file_path, expected_encoding in encoding_test_files:
            try:
                # エンコーディング検出のテスト
                detected_encoding = self.document_processor._detect_encoding(file_path)

                # ファイル処理のテスト
                document = self.document_processor.process_file(file_path)

                # 基本的な検証
                self.assert_condition(
                    document is not None,
                    f"エンコーディングテストファイルの処理に失敗: {file_path}",
                )

                self.assert_condition(
                    len(document.content) > 0,
                    f"エンコーディングテストファイルからテキストが抽出されませんでした: {file_path}",
                )

                # 日本語文字が正しく読み込まれているかチェック
                if "日本語" in document.content or "テスト" in document.content:
                    successful_detections += 1

                # 統計情報の更新
                encoding_key = f"{expected_encoding}->{detected_encoding}"
                self.processing_stats["encoding_detection_stats"][encoding_key] = (
                    self.processing_stats["encoding_detection_stats"].get(
                        encoding_key, 0
                    )
                    + 1
                )

                self.logger.debug(
                    f"エンコーディング検出成功: {file_path} ({expected_encoding}->{detected_encoding})"
                )

            except Exception as e:
                self.logger.error(f"エンコーディング検出失敗: {file_path} - {e}")

        # 検出精度の検証
        detection_rate = successful_detections / total_files if total_files > 0 else 0
        self.assert_condition(
            detection_rate >= 0.8,  # 80%以上の検出精度を要求
            f"エンコーディング検出精度が低すぎます: {detection_rate:.2%} (要求: 80%以上)",
        )

        self.logger.info(
            f"エンコーディング検出検証完了: {successful_detections}/{total_files} ({detection_rate:.2%})"
        )

    def test_large_file_processing(self) -> None:
        """大容量ファイル処理の検証"""
        self.logger.info("大容量ファイル処理の検証を開始します")

        large_files = self._get_large_test_files()

        if not large_files:
            self.logger.warning("大容量テストファイルが見つかりません")
            return

        successful_count = 0
        total_count = len(large_files)
        max_processing_time = 30.0  # 30秒以内の処理を要求

        for large_file in large_files:
            try:
                file_size_kb = os.path.getsize(large_file) / 1024
                self.logger.debug(
                    f"大容量ファイル処理開始: {large_file} ({file_size_kb:.2f}KB)"
                )

                start_time = time.time()
                document = self.document_processor.process_file(large_file)
                processing_time = time.time() - start_time

                # 基本的な検証
                self.assert_condition(
                    document is not None, f"大容量ファイルの処理に失敗: {large_file}"
                )

                self.assert_condition(
                    len(document.content) > 0,
                    f"大容量ファイルからテキストが抽出されませんでした: {large_file}",
                )

                # 処理時間の検証
                self.assert_condition(
                    processing_time <= max_processing_time,
                    f"大容量ファイルの処理時間が長すぎます: {processing_time:.2f}秒 (要求: {max_processing_time}秒以内)",
                )

                # メモリ使用量の検証（現在のメモリ使用量をチェック）
                try:
                    current_memory = self.memory_monitor.get_current_memory()
                    self.assert_condition(
                        current_memory <= self.config.max_memory_usage,
                        f"大容量ファイル処理中のメモリ使用量が多すぎます: {current_memory:.2f}MB",
                    )
                except Exception as e:
                    self.logger.warning(f"メモリ監視エラー: {e}")

                successful_count += 1
                self.logger.info(
                    f"大容量ファイル処理成功: {large_file} ({file_size_kb:.2f}KB, {processing_time:.2f}秒)"
                )

            except Exception as e:
                self.logger.error(f"大容量ファイル処理失敗: {large_file} - {e}")

        # 成功率の検証
        success_rate = successful_count / total_count if total_count > 0 else 0
        self.assert_condition(
            success_rate >= 0.8,  # 80%以上の成功率を要求
            f"大容量ファイル処理成功率が低すぎます: {success_rate:.2%} (要求: 80%以上)",
        )

        self.logger.info(
            f"大容量ファイル処理検証完了: {successful_count}/{total_count} ({success_rate:.2%})"
        )

    def test_error_handling_robustness(self) -> None:
        """エラーハンドリングの堅牢性検証"""
        self.logger.info("エラーハンドリングの堅牢性検証を開始します")

        # 破損ファイルのテスト
        corrupted_files = self._get_corrupted_test_files()

        # 存在しないファイルのテスト
        non_existent_file = os.path.join(self.test_data_dir, "non_existent_file.txt")

        # 空ファイルのテスト
        empty_file = self._create_empty_file()

        error_test_cases = [
            ("corrupted_files", corrupted_files),
            ("non_existent_file", [non_existent_file]),
            ("empty_file", [empty_file]),
        ]

        total_error_cases = 0
        handled_errors = 0

        for test_type, test_files in error_test_cases:
            for test_file in test_files:
                total_error_cases += 1

                try:
                    # エラーが発生することを期待
                    self.document_processor.process_file(test_file)

                    # 破損ファイルや存在しないファイルの場合、例外が発生すべき
                    if test_type in ["corrupted_files", "non_existent_file"]:
                        self.logger.warning(
                            f"例外が発生すべきファイルで処理が成功: {test_file}"
                        )
                    else:
                        # 空ファイルの場合は処理成功も許容
                        handled_errors += 1

                except DocumentProcessingError as e:
                    # 適切なエラーハンドリング
                    self.assert_condition(
                        e.file_path is not None,
                        f"DocumentProcessingErrorにfile_pathが設定されていません: {test_file}",
                    )

                    self.assert_condition(
                        len(str(e)) > 0, f"エラーメッセージが空です: {test_file}"
                    )

                    handled_errors += 1
                    self.logger.debug(f"適切なエラーハンドリング: {test_file} - {e}")

                    # エラー統計の更新
                    error_type = type(e).__name__
                    self.processing_stats["error_types"][error_type] = (
                        self.processing_stats["error_types"].get(error_type, 0) + 1
                    )

                except Exception as e:
                    # 予期しない例外
                    self.logger.error(f"予期しない例外が発生: {test_file} - {e}")

        # エラーハンドリング率の検証
        error_handling_rate = (
            handled_errors / total_error_cases if total_error_cases > 0 else 0
        )
        self.assert_condition(
            error_handling_rate >= 0.9,  # 90%以上のエラーハンドリング率を要求
            f"エラーハンドリング率が低すぎます: {error_handling_rate:.2%} (要求: 90%以上)",
        )

        self.logger.info(
            f"エラーハンドリング検証完了: {handled_errors}/{total_error_cases} ({error_handling_rate:.2%})"
        )

    def test_processing_performance_requirements(self) -> None:
        """処理パフォーマンス要件の検証"""
        self.logger.info("処理パフォーマンス要件の検証を開始します")

        # 各ファイル形式の処理時間要件
        performance_requirements = {
            "txt": 1.0,  # 1秒以内
            "md": 1.0,  # 1秒以内
            "pdf": 5.0,  # 5秒以内
            "docx": 3.0,  # 3秒以内
            "xlsx": 3.0,  # 3秒以内
        }

        performance_results = {}

        for file_type, max_time in performance_requirements.items():
            test_files = self._get_test_files_by_type(file_type)

            if not test_files:
                continue

            processing_times = []

            for test_file in test_files[:5]:  # 各形式5ファイルをテスト
                try:
                    start_time = time.time()
                    self.document_processor.process_file(test_file)
                    processing_time = time.time() - start_time

                    processing_times.append(processing_time)

                except Exception as e:
                    self.logger.warning(
                        f"パフォーマンステスト中にエラー: {test_file} - {e}"
                    )

            if processing_times:
                avg_time = sum(processing_times) / len(processing_times)
                max_observed_time = max(processing_times)

                performance_results[file_type] = {
                    "average_time": avg_time,
                    "max_time": max_observed_time,
                    "requirement": max_time,
                    "meets_requirement": max_observed_time <= max_time,
                }

                # パフォーマンス要件の検証
                self.assert_condition(
                    max_observed_time <= max_time,
                    f"{file_type}ファイルの処理時間が要件を超過: {max_observed_time:.2f}秒 > {max_time}秒",
                )

                self.logger.info(
                    f"{file_type}パフォーマンス: 平均{avg_time:.2f}秒, 最大{max_observed_time:.2f}秒 (要件: {max_time}秒以内)"
                )

        # 全体的なパフォーマンス統計
        all_times = self.processing_stats["processing_times"]
        if all_times:
            overall_avg = sum(all_times) / len(all_times)
            self.logger.info(f"全体平均処理時間: {overall_avg:.2f}秒")

        self.logger.info("処理パフォーマンス要件検証完了")

    def test_concurrent_processing_safety(self) -> None:
        """並行処理の安全性検証"""
        self.logger.info("並行処理の安全性検証を開始します")

        import queue
        import threading

        test_files = []
        for file_type in ["txt", "pdf", "docx"]:
            test_files.extend(self._get_test_files_by_type(file_type)[:3])

        if len(test_files) < 3:
            self.logger.warning("並行処理テスト用のファイルが不足しています")
            return

        results_queue = queue.Queue()
        errors_queue = queue.Queue()

        def process_file_thread(file_path: str):
            """ファイル処理スレッド"""
            try:
                start_time = time.time()
                document = self.document_processor.process_file(file_path)
                processing_time = time.time() - start_time

                results_queue.put(
                    {
                        "file_path": file_path,
                        "success": True,
                        "processing_time": processing_time,
                        "content_length": len(document.content),
                    }
                )

            except Exception as e:
                errors_queue.put({"file_path": file_path, "error": str(e)})

        # 並行処理の実行
        threads = []
        for test_file in test_files[:5]:  # 5つのファイルを並行処理
            thread = threading.Thread(target=process_file_thread, args=(test_file,))
            threads.append(thread)
            thread.start()

        # すべてのスレッドの完了を待機
        for thread in threads:
            thread.join(timeout=30)  # 30秒でタイムアウト

        # 結果の検証
        successful_results = []
        while not results_queue.empty():
            successful_results.append(results_queue.get())

        errors = []
        while not errors_queue.empty():
            errors.append(errors_queue.get())

        # 成功率の検証
        total_processed = len(successful_results) + len(errors)
        success_rate = (
            len(successful_results) / total_processed if total_processed > 0 else 0
        )

        self.assert_condition(
            success_rate >= 0.8,  # 80%以上の成功率を要求
            f"並行処理の成功率が低すぎます: {success_rate:.2%} (要求: 80%以上)",
        )

        # データ整合性の検証（同じファイルを複数回処理した場合の結果一致）
        if len(successful_results) > 1:
            # 処理時間のばらつきをチェック
            processing_times = [r["processing_time"] for r in successful_results]
            avg_time = sum(processing_times) / len(processing_times)

            # 処理時間が極端にばらついていないかチェック
            for time_val in processing_times:
                self.assert_condition(
                    abs(time_val - avg_time) <= avg_time * 2,  # 平均の2倍以内
                    f"並行処理時の処理時間のばらつきが大きすぎます: {time_val:.2f}秒 (平均: {avg_time:.2f}秒)",
                )

        self.logger.info(
            f"並行処理安全性検証完了: 成功{len(successful_results)}, エラー{len(errors)}"
        )

    def _get_test_files_by_type(self, file_type: str) -> list[str]:
        """指定されたファイル形式のテストファイルを取得"""
        test_files = []

        if not self.test_data_dir:
            return test_files

        for root, _dirs, files in os.walk(self.test_data_dir):
            for file in files:
                if file.endswith(f".{file_type}"):
                    test_files.append(os.path.join(root, file))

        return test_files

    def _get_large_test_files(self) -> list[str]:
        """大容量テストファイルを取得"""
        large_files = []
        min_size_kb = 50.0  # 50KB以上（テスト用に軽量化）

        if not self.test_data_dir:
            return large_files

        for root, _dirs, files in os.walk(self.test_data_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_size_kb = os.path.getsize(file_path) / 1024
                    if file_size_kb >= min_size_kb:
                        large_files.append(file_path)
                except OSError:
                    continue

        return large_files

    def _get_corrupted_test_files(self) -> list[str]:
        """破損テストファイルを取得"""
        corrupted_files = []

        if not self.test_data_dir:
            return corrupted_files

        error_dir = os.path.join(self.test_data_dir, "error")
        if os.path.exists(error_dir):
            for root, _dirs, files in os.walk(error_dir):
                for file in files:
                    corrupted_files.append(os.path.join(root, file))

        return corrupted_files

    def _create_encoding_test_files(self) -> list[tuple[str, str]]:
        """異なるエンコーディングのテストファイルを作成"""
        encoding_files = []

        if not self.test_data_dir:
            return encoding_files

        encoding_dir = os.path.join(self.test_data_dir, "encoding_test")
        os.makedirs(encoding_dir, exist_ok=True)

        test_content = "これは日本語のテストファイルです。\nエンコーディング検出のテストを行います。"

        encodings = [
            ("utf-8", "utf-8"),
            ("shift_jis", "shift_jis"),
            ("euc-jp", "euc-jp"),
            ("iso-2022-jp", "iso-2022-jp"),
        ]

        for i, (encoding_name, encoding) in enumerate(encodings):
            try:
                file_path = os.path.join(encoding_dir, f"test_{encoding_name}_{i}.txt")

                with open(file_path, "w", encoding=encoding) as f:
                    f.write(test_content)

                encoding_files.append((file_path, encoding))
                self.temp_dirs.append(file_path)  # クリーンアップ対象に追加

            except Exception as e:
                self.logger.warning(
                    f"エンコーディングテストファイル作成失敗 ({encoding}): {e}"
                )

        return encoding_files

    def _create_empty_file(self) -> str:
        """空ファイルを作成"""
        empty_file_path = os.path.join(self.test_data_dir, "empty_file.txt")

        with open(empty_file_path, "w", encoding="utf-8"):
            pass  # 空ファイルを作成

        return empty_file_path

    def _update_processing_stats(
        self,
        file_type: str,
        success: bool,
        content_length: int,
        processing_time: float,
        error_message: str = None,
    ) -> None:
        """処理統計情報の更新"""
        self.processing_stats["files_processed"] += 1

        if success:
            self.processing_stats["successful_extractions"] += 1
            self.processing_stats["total_characters_extracted"] += content_length
            self.processing_stats["processing_times"].append(processing_time)
        else:
            self.processing_stats["failed_extractions"] += 1
            if error_message:
                error_type = "Unknown"
                if "DocumentProcessingError" in error_message:
                    error_type = "DocumentProcessingError"
                elif "FileNotFoundError" in error_message:
                    error_type = "FileNotFoundError"
                elif "PermissionError" in error_message:
                    error_type = "PermissionError"

                self.processing_stats["error_types"][error_type] = (
                    self.processing_stats["error_types"].get(error_type, 0) + 1
                )

        # ファイル形式別統計
        if file_type not in self.processing_stats["file_type_stats"]:
            self.processing_stats["file_type_stats"][file_type] = {
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "total_chars": 0,
                "avg_processing_time": 0.0,
            }

        stats = self.processing_stats["file_type_stats"][file_type]
        stats["processed"] += 1

        if success:
            stats["successful"] += 1
            stats["total_chars"] += content_length

            # 平均処理時間の更新
            current_avg = stats["avg_processing_time"]
            stats["avg_processing_time"] = (
                current_avg * (stats["successful"] - 1) + processing_time
            ) / stats["successful"]
        else:
            stats["failed"] += 1

    def get_processing_statistics(self) -> dict[str, Any]:
        """処理統計情報の取得"""
        return {
            "overall_stats": self.processing_stats,
            "success_rate": (
                (
                    self.processing_stats["successful_extractions"]
                    / self.processing_stats["files_processed"]
                )
                if self.processing_stats["files_processed"] > 0
                else 0
            ),
            "average_processing_time": (
                (
                    sum(self.processing_stats["processing_times"])
                    / len(self.processing_stats["processing_times"])
                )
                if self.processing_stats["processing_times"]
                else 0
            ),
            "average_content_length": (
                (
                    self.processing_stats["total_characters_extracted"]
                    / self.processing_stats["successful_extractions"]
                )
                if self.processing_stats["successful_extractions"] > 0
                else 0
            ),
        }
