"""
設定ダイアログモジュール

アプリケーションの設定を変更するためのダイアログウィンドウを提供します。
検索パラメーター、UIオプション、フォルダ管理、ログ設定などを含みます。
"""

import logging
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..utils.config import Config


class SettingsDialog(QDialog):
    """
    設定ダイアログクラス

    アプリケーションの各種設定を変更するためのダイアログを提供します。
    タブ形式で設定項目を整理し、ユーザーフレンドリーなインターフェースを提供します。
    """

    # 設定変更時に発行されるシグナル
    settings_changed = Signal(dict)

    def __init__(self, config: Config, parent=None):
        """
        設定ダイアログの初期化

        Args:
            config: 設定管理オブジェクト
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 設定値の一時保存用
        self.temp_settings = {}

        self.setWindowTitle("DocMind 設定")
        self.setModal(True)
        self.resize(600, 500)

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """UIの初期化"""
        layout = QVBoxLayout(self)

        # タブウィジェットの作成
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 各タブの作成
        self._create_general_tab()
        self._create_search_tab()
        self._create_folders_tab()
        self._create_storage_tab()
        self._create_logging_tab()
        self._create_ui_tab()

        # ボタンボックス
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self._save_and_close)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self._apply_settings)
        layout.addWidget(button_box)

    def _create_general_tab(self):
        """一般設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 基本設定グループ
        basic_group = QGroupBox("基本設定")
        basic_layout = QFormLayout(basic_group)

        # 最大ドキュメント数
        self.max_documents_spin = QSpinBox()
        self.max_documents_spin.setRange(1000, 1000000)
        self.max_documents_spin.setSuffix(" ドキュメント")
        basic_layout.addRow("最大ドキュメント数:", self.max_documents_spin)

        # 検索タイムアウト
        self.search_timeout_spin = QDoubleSpinBox()
        self.search_timeout_spin.setRange(1.0, 60.0)
        self.search_timeout_spin.setSuffix(" 秒")
        self.search_timeout_spin.setDecimals(1)
        basic_layout.addRow("検索タイムアウト:", self.search_timeout_spin)

        # バッチサイズ
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(10, 1000)
        basic_layout.addRow("バッチサイズ:", self.batch_size_spin)

        # キャッシュサイズ
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(100, 10000)
        basic_layout.addRow("キャッシュサイズ:", self.cache_size_spin)

        layout.addWidget(basic_group)

        # ファイル監視設定グループ
        watch_group = QGroupBox("ファイル監視")
        watch_layout = QFormLayout(watch_group)

        self.enable_file_watching_check = QCheckBox("ファイル変更の自動監視を有効にする")
        watch_layout.addRow(self.enable_file_watching_check)

        layout.addWidget(watch_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "一般")

    def _create_search_tab(self):
        """検索設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 埋め込みモデル設定グループ
        model_group = QGroupBox("埋め込みモデル")
        model_layout = QFormLayout(model_group)

        self.embedding_model_combo = QComboBox()
        self.embedding_model_combo.addItems([
            "all-MiniLM-L6-v2",
            "all-MiniLM-L12-v2",
            "paraphrase-MiniLM-L6-v2",
            "distilbert-base-nli-mean-tokens"
        ])
        model_layout.addRow("セマンティック検索モデル:", self.embedding_model_combo)

        layout.addWidget(model_group)

        # 検索パラメーター設定グループ
        params_group = QGroupBox("検索パラメーター")
        params_layout = QFormLayout(params_group)

        # 検索結果の最大数
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(10, 1000)
        self.max_results_spin.setValue(100)
        params_layout.addRow("最大検索結果数:", self.max_results_spin)

        # セマンティック検索の重み
        self.semantic_weight_slider = QSlider(Qt.Horizontal)
        self.semantic_weight_slider.setRange(0, 100)
        self.semantic_weight_slider.setValue(50)
        self.semantic_weight_label = QLabel("50%")
        self.semantic_weight_slider.valueChanged.connect(
            lambda v: self.semantic_weight_label.setText(f"{v}%")
        )

        weight_layout = QHBoxLayout()
        weight_layout.addWidget(self.semantic_weight_slider)
        weight_layout.addWidget(self.semantic_weight_label)
        params_layout.addRow("セマンティック検索の重み:", weight_layout)

        layout.addWidget(params_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "検索")

    def _create_folders_tab(self):
        """フォルダ管理タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # インデックス対象フォルダ
        folders_group = QGroupBox("インデックス対象フォルダ")
        folders_layout = QVBoxLayout(folders_group)

        # フォルダリスト
        self.folders_list = QListWidget()
        folders_layout.addWidget(self.folders_list)

        # フォルダ操作ボタン
        buttons_layout = QHBoxLayout()

        self.add_folder_btn = QPushButton("フォルダを追加")
        self.add_folder_btn.clicked.connect(self._add_folder)
        buttons_layout.addWidget(self.add_folder_btn)

        self.remove_folder_btn = QPushButton("選択したフォルダを削除")
        self.remove_folder_btn.clicked.connect(self._remove_folder)
        buttons_layout.addWidget(self.remove_folder_btn)

        buttons_layout.addStretch()
        folders_layout.addLayout(buttons_layout)

        layout.addWidget(folders_group)

        # 除外パターン設定
        exclude_group = QGroupBox("除外パターン")
        exclude_layout = QFormLayout(exclude_group)

        self.exclude_patterns_text = QTextEdit()
        self.exclude_patterns_text.setMaximumHeight(100)
        self.exclude_patterns_text.setPlaceholderText(
            "除外するファイルパターンを1行ずつ入力\n例: *.tmp\n例: __pycache__/*"
        )
        exclude_layout.addRow("除外パターン:", self.exclude_patterns_text)

        layout.addWidget(exclude_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "フォルダ")

    def _create_storage_tab(self):
        """ストレージ設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # データストレージ設定グループ
        storage_group = QGroupBox("データストレージ")
        storage_layout = QFormLayout(storage_group)

        # データディレクトリ
        data_dir_layout = QHBoxLayout()
        self.data_directory_edit = QLineEdit()
        self.data_directory_edit.setReadOnly(True)
        data_dir_layout.addWidget(self.data_directory_edit)

        self.browse_data_dir_btn = QPushButton("参照")
        self.browse_data_dir_btn.clicked.connect(self._browse_data_directory)
        data_dir_layout.addWidget(self.browse_data_dir_btn)

        storage_layout.addRow("データディレクトリ:", data_dir_layout)

        # データベースファイル名
        self.database_file_edit = QLineEdit()
        storage_layout.addRow("データベースファイル名:", self.database_file_edit)

        # 埋め込みファイル名
        self.embeddings_file_edit = QLineEdit()
        storage_layout.addRow("埋め込みファイル名:", self.embeddings_file_edit)

        # インデックスディレクトリ名
        self.index_dir_edit = QLineEdit()
        storage_layout.addRow("インデックスディレクトリ名:", self.index_dir_edit)

        layout.addWidget(storage_group)

        # ストレージ情報表示
        info_group = QGroupBox("ストレージ情報")
        info_layout = QFormLayout(info_group)

        self.storage_info_label = QLabel("読み込み中...")
        info_layout.addRow("使用容量:", self.storage_info_label)

        layout.addWidget(info_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "ストレージ")

    def _create_logging_tab(self):
        """ログ設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ログレベル設定グループ
        log_group = QGroupBox("ログ設定")
        log_layout = QFormLayout(log_group)

        # ログレベル
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        log_layout.addRow("ログレベル:", self.log_level_combo)

        # ログファイルの場所
        log_file_layout = QHBoxLayout()
        self.log_file_edit = QLineEdit()
        self.log_file_edit.setReadOnly(True)
        log_file_layout.addWidget(self.log_file_edit)

        self.browse_log_btn = QPushButton("参照")
        self.browse_log_btn.clicked.connect(self._browse_log_file)
        log_file_layout.addWidget(self.browse_log_btn)

        log_layout.addRow("ログファイル:", log_file_layout)

        layout.addWidget(log_group)

        # ログ表示設定
        display_group = QGroupBox("ログ表示設定")
        display_layout = QFormLayout(display_group)

        self.console_logging_check = QCheckBox("コンソールにログを出力")
        display_layout.addRow(self.console_logging_check)

        self.file_logging_check = QCheckBox("ファイルにログを出力")
        display_layout.addRow(self.file_logging_check)

        layout.addWidget(display_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "ログ")

    def _create_ui_tab(self):
        """UI設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ウィンドウ設定グループ
        window_group = QGroupBox("ウィンドウ設定")
        window_layout = QFormLayout(window_group)

        # ウィンドウサイズ
        self.window_width_spin = QSpinBox()
        self.window_width_spin.setRange(800, 2560)
        self.window_width_spin.setSuffix(" px")
        window_layout.addRow("ウィンドウ幅:", self.window_width_spin)

        self.window_height_spin = QSpinBox()
        self.window_height_spin.setRange(600, 1440)
        self.window_height_spin.setSuffix(" px")
        window_layout.addRow("ウィンドウ高さ:", self.window_height_spin)

        # テーマ設定
        self.ui_theme_combo = QComboBox()
        self.ui_theme_combo.addItems(["default", "dark", "light"])
        window_layout.addRow("UIテーマ:", self.ui_theme_combo)

        layout.addWidget(window_group)

        # フォント設定グループ
        font_group = QGroupBox("フォント設定")
        font_layout = QFormLayout(font_group)

        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems([
            "システムデフォルト", "Yu Gothic UI", "Meiryo UI",
            "MS Gothic", "Arial", "Helvetica"
        ])
        font_layout.addRow("フォントファミリー:", self.font_family_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setSuffix(" pt")
        font_layout.addRow("フォントサイズ:", self.font_size_spin)

        layout.addWidget(font_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "UI")

    def _load_current_settings(self):
        """現在の設定値をUIに読み込み"""
        try:
            # 一般設定
            self.max_documents_spin.setValue(self.config.get_max_documents())
            self.search_timeout_spin.setValue(self.config.get_search_timeout())
            self.batch_size_spin.setValue(self.config.get_batch_size())
            self.cache_size_spin.setValue(self.config.get_cache_size())
            self.enable_file_watching_check.setChecked(self.config.is_file_watching_enabled())

            # 検索設定
            self.embedding_model_combo.setCurrentText(self.config.get_embedding_model())
            self.max_results_spin.setValue(self.config.get("max_results", 100))
            self.semantic_weight_slider.setValue(int(self.config.get("semantic_weight", 50)))

            # フォルダ設定
            indexed_folders = self.config.get("indexed_folders", [])
            for folder in indexed_folders:
                self.folders_list.addItem(folder)

            exclude_patterns = self.config.get("exclude_patterns", [])
            self.exclude_patterns_text.setPlainText("\n".join(exclude_patterns))

            # ストレージ設定
            self.data_directory_edit.setText(self.config.get_data_directory())
            self.database_file_edit.setText(self.config.get("database_file"))
            self.embeddings_file_edit.setText(self.config.get("embeddings_file"))
            self.index_dir_edit.setText(self.config.get("whoosh_index_dir"))

            # ログ設定
            self.log_level_combo.setCurrentText(self.config.get_log_level())
            log_file = os.path.join(self.config.get_data_directory(), "logs", "docmind.log")
            self.log_file_edit.setText(log_file)
            self.console_logging_check.setChecked(self.config.get("console_logging", True))
            self.file_logging_check.setChecked(self.config.get("file_logging", True))

            # UI設定
            width, height = self.config.get_window_size()
            self.window_width_spin.setValue(width)
            self.window_height_spin.setValue(height)
            self.ui_theme_combo.setCurrentText(self.config.get("ui_theme"))
            self.font_family_combo.setCurrentText(self.config.get("font_family", "システムデフォルト"))
            self.font_size_spin.setValue(self.config.get("font_size", 10))

            # ストレージ情報の更新
            self._update_storage_info()

        except Exception as e:
            self.logger.error(f"設定の読み込みに失敗しました: {e}")
            QMessageBox.warning(self, "エラー", f"設定の読み込みに失敗しました: {e}")

    def _update_storage_info(self):
        """ストレージ使用量情報を更新"""
        try:
            data_dir = Path(self.config.get_data_directory())
            if data_dir.exists():
                total_size = sum(f.stat().st_size for f in data_dir.rglob('*') if f.is_file())
                size_mb = total_size / (1024 * 1024)
                self.storage_info_label.setText(f"{size_mb:.2f} MB")
            else:
                self.storage_info_label.setText("データディレクトリが存在しません")
        except Exception as e:
            self.storage_info_label.setText(f"計算エラー: {e}")

    def _add_folder(self):
        """インデックス対象フォルダを追加"""
        folder = QFileDialog.getExistingDirectory(
            self, "インデックス対象フォルダを選択", ""
        )
        if folder:
            # 重複チェック
            for i in range(self.folders_list.count()):
                if self.folders_list.item(i).text() == folder:
                    QMessageBox.information(self, "情報", "このフォルダは既に追加されています。")
                    return

            self.folders_list.addItem(folder)

    def _remove_folder(self):
        """選択されたフォルダを削除"""
        current_item = self.folders_list.currentItem()
        if current_item:
            reply = QMessageBox.question(
                self, "確認",
                f"フォルダ '{current_item.text()}' を削除しますか？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.folders_list.takeItem(self.folders_list.row(current_item))

    def _browse_data_directory(self):
        """データディレクトリを参照"""
        directory = QFileDialog.getExistingDirectory(
            self, "データディレクトリを選択", self.data_directory_edit.text()
        )
        if directory:
            self.data_directory_edit.setText(directory)

    def _browse_log_file(self):
        """ログファイルを参照"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ログファイルを選択", self.log_file_edit.text(),
            "ログファイル (*.log);;すべてのファイル (*)"
        )
        if file_path:
            self.log_file_edit.setText(file_path)

    def _collect_settings(self) -> dict[str, Any]:
        """UIから設定値を収集"""
        settings = {}

        # 一般設定
        settings["max_documents"] = self.max_documents_spin.value()
        settings["search_timeout"] = self.search_timeout_spin.value()
        settings["batch_size"] = self.batch_size_spin.value()
        settings["cache_size"] = self.cache_size_spin.value()
        settings["enable_file_watching"] = self.enable_file_watching_check.isChecked()

        # 検索設定
        settings["embedding_model"] = self.embedding_model_combo.currentText()
        settings["max_results"] = self.max_results_spin.value()
        settings["semantic_weight"] = self.semantic_weight_slider.value()

        # フォルダ設定
        indexed_folders = []
        for i in range(self.folders_list.count()):
            indexed_folders.append(self.folders_list.item(i).text())
        settings["indexed_folders"] = indexed_folders

        exclude_patterns = [
            line.strip() for line in self.exclude_patterns_text.toPlainText().split('\n')
            if line.strip()
        ]
        settings["exclude_patterns"] = exclude_patterns

        # ストレージ設定
        settings["data_directory"] = self.data_directory_edit.text()
        settings["database_file"] = self.database_file_edit.text()
        settings["embeddings_file"] = self.embeddings_file_edit.text()
        settings["whoosh_index_dir"] = self.index_dir_edit.text()

        # ログ設定
        settings["log_level"] = self.log_level_combo.currentText()
        settings["console_logging"] = self.console_logging_check.isChecked()
        settings["file_logging"] = self.file_logging_check.isChecked()

        # UI設定
        settings["window_width"] = self.window_width_spin.value()
        settings["window_height"] = self.window_height_spin.value()
        settings["ui_theme"] = self.ui_theme_combo.currentText()
        settings["font_family"] = self.font_family_combo.currentText()
        settings["font_size"] = self.font_size_spin.value()

        return settings

    def _apply_settings(self):
        """設定を適用（保存はしない）"""
        try:
            settings = self._collect_settings()

            # 設定の検証
            if not self._validate_settings(settings):
                return

            # 設定を一時保存
            self.temp_settings = settings

            # 設定変更シグナルを発行
            self.settings_changed.emit(settings)

            QMessageBox.information(self, "情報", "設定が適用されました。")

        except Exception as e:
            self.logger.error(f"設定の適用に失敗しました: {e}")
            QMessageBox.critical(self, "エラー", f"設定の適用に失敗しました: {e}")

    def _save_and_close(self):
        """設定を保存してダイアログを閉じる"""
        try:
            settings = self._collect_settings()

            # 設定の検証
            if not self._validate_settings(settings):
                return

            # 設定をConfigオブジェクトに適用
            for key, value in settings.items():
                self.config.set(key, value)

            # 設定ファイルに保存
            if self.config.save_config():
                # 設定変更シグナルを発行
                self.settings_changed.emit(settings)
                self.accept()
            else:
                QMessageBox.critical(self, "エラー", "設定の保存に失敗しました。")

        except Exception as e:
            self.logger.error(f"設定の保存に失敗しました: {e}")
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {e}")

    def _validate_settings(self, settings: dict[str, Any]) -> bool:
        """設定値の検証"""
        try:
            # データディレクトリの検証
            data_dir = Path(settings["data_directory"])
            if not data_dir.parent.exists():
                QMessageBox.warning(
                    self, "警告",
                    f"データディレクトリの親ディレクトリが存在しません: {data_dir.parent}"
                )
                return False

            # インデックス対象フォルダの検証
            for folder in settings["indexed_folders"]:
                if not Path(folder).exists():
                    reply = QMessageBox.question(
                        self, "確認",
                        f"フォルダが存在しません: {folder}\n続行しますか？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return False

            # 数値範囲の検証
            if settings["max_documents"] < 1000:
                QMessageBox.warning(self, "警告", "最大ドキュメント数は1000以上である必要があります。")
                return False

            if settings["search_timeout"] < 1.0:
                QMessageBox.warning(self, "警告", "検索タイムアウトは1秒以上である必要があります。")
                return False

            return True

        except Exception as e:
            self.logger.error(f"設定の検証に失敗しました: {e}")
            QMessageBox.critical(self, "エラー", f"設定の検証に失敗しました: {e}")
            return False
