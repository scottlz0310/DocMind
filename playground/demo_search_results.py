#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索結果表示ウィジェットのデモンストレーション

SearchResultsWidgetの機能をデモンストレーションするスクリプトです。
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt

from src.gui.search_results import SearchResultsWidget
from src.data.models import SearchResult, SearchType, FileType, Document


class SearchResultsDemo(QMainWindow):
    """検索結果ウィジェットのデモウィンドウ"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DocMind 検索結果ウィジェット デモ")
        self.setGeometry(100, 100, 1200, 800)
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # レイアウト
        layout = QVBoxLayout(central_widget)
        
        # ボタン行
        button_layout = QHBoxLayout()
        
        self.load_sample_button = QPushButton("サンプルデータを読み込み")
        self.load_sample_button.clicked.connect(self.load_sample_data)
        button_layout.addWidget(self.load_sample_button)
        
        self.clear_button = QPushButton("クリア")
        self.clear_button.clicked.connect(self.clear_results)
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 検索結果ウィジェット
        self.search_results_widget = SearchResultsWidget()
        layout.addWidget(self.search_results_widget)
        
        # シグナル接続
        self.search_results_widget.result_selected.connect(self.on_result_selected)
        self.search_results_widget.preview_requested.connect(self.on_preview_requested)
        
        # 初期データを読み込み
        self.load_sample_data()
    
    def load_sample_data(self):
        """サンプルデータを作成して表示"""
        sample_results = []
        
        # 既存のテストファイルを使用
        test_files = [
            ("tests/fixtures/sample_text.txt", FileType.TEXT),
            ("tests/fixtures/sample_markdown.md", FileType.MARKDOWN)
        ]
        
        search_types = [SearchType.FULL_TEXT, SearchType.SEMANTIC, SearchType.HYBRID]
        
        for i in range(30):  # 30件のサンプルデータ
            file_path, file_type = test_files[i % len(test_files)]
            
            # ファイルが存在するかチェック
            if not os.path.exists(file_path):
                # 存在しない場合はダミーファイルを作成
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"サンプルファイル {i} の内容です。")
            
            doc = Document(
                id=f"demo_doc_{i}",
                file_path=file_path,
                title=f"サンプルドキュメント {i + 1}",
                content=f"これはサンプルドキュメント{i + 1}のコンテンツです。検索デモのために作成されました。",
                file_type=file_type,
                size=1024 * (i + 1),
                created_date=datetime(2024, 1, (i % 28) + 1, 10, 0, 0),
                modified_date=datetime(2024, 1, (i % 28) + 1, 14, 30, 0),
                indexed_date=datetime(2024, 1, (i % 28) + 1, 9, 0, 0)
            )
            
            result = SearchResult(
                document=doc,
                score=0.95 - (i * 0.02),  # スコアを徐々に下げる
                search_type=search_types[i % len(search_types)],
                snippet=f"サンプルスニペット {i + 1}: これは検索結果のプレビューテキストです。",
                highlighted_terms=["サンプル", "検索", "ドキュメント"],
                relevance_explanation=f"キーワードマッチによる関連度: {0.95 - (i * 0.02):.2f}",
                rank=i + 1
            )
            
            sample_results.append(result)
        
        # 検索結果を表示
        self.search_results_widget.display_results(sample_results)
        print(f"サンプルデータを読み込みました: {len(sample_results)}件")
    
    def clear_results(self):
        """検索結果をクリア"""
        self.search_results_widget.clear_results()
        print("検索結果をクリアしました")
    
    def on_result_selected(self, result):
        """検索結果が選択された時の処理"""
        print(f"結果選択: {result.document.title} (スコア: {result.get_formatted_score()})")
    
    def on_preview_requested(self, result):
        """プレビューが要求された時の処理"""
        print(f"プレビュー要求: {result.document.title}")


def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    
    # デモウィンドウを作成
    demo = SearchResultsDemo()
    demo.show()
    
    # アプリケーションを実行
    sys.exit(app.exec())


if __name__ == "__main__":
    main()