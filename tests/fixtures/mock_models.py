"""
テスト用のモックモデル

実際のファイル存在チェックを回避したテスト専用のモデルクラスを提供します。
"""

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.data.models import FileType, SearchType


@dataclass
class MockDocument:
    """テスト用のDocumentクラス
    
    ファイル存在チェックを行わないテスト専用バージョン
    """
    
    # 必須フィールド
    id: str
    file_path: str
    title: str
    content: str
    file_type: FileType
    size: int
    created_date: datetime
    modified_date: datetime
    indexed_date: datetime
    
    # オプションフィールド
    content_hash: str = field(default="")
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の処理（ファイル存在チェックなし）"""
        self._validate_fields_without_file_check()
        self._generate_content_hash()
        self._set_default_title()
    
    def _validate_fields_without_file_check(self):
        """ファイル存在チェックを除いた検証"""
        if not self.id:
            raise ValueError("ドキュメントIDは必須です")
        
        if not self.file_path:
            raise ValueError("ファイルパスは必須です")
        
        if self.size < 0:
            raise ValueError("ファイルサイズは0以上である必要があります")
        
        if not isinstance(self.file_type, FileType):
            raise ValueError("file_typeはFileType列挙型である必要があります")
    
    def _generate_content_hash(self):
        """コンテンツのハッシュ値を生成"""
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
    
    def _set_default_title(self):
        """デフォルトタイトルを設定"""
        if not self.title:
            self.title = Path(self.file_path).stem
    
    def get_summary(self, max_length: int = 200) -> str:
        """ドキュメントの要約を取得"""
        if len(self.content) <= max_length:
            return self.content
        
        # 文の境界で切り取る
        summary = self.content[:max_length]
        last_sentence_end = max(
            summary.rfind("。"),
            summary.rfind("."),
            summary.rfind("!"),
            summary.rfind("?"),
        )
        
        if last_sentence_end > max_length // 2:
            return summary[:last_sentence_end + 1]
        else:
            return summary + "..."
    
    def is_modified_since_indexing(self) -> bool:
        """テスト用：常にFalseを返す"""
        return False


@dataclass
class MockSearchResult:
    """テスト用のSearchResultクラス"""
    
    document: MockDocument
    score: float
    search_type: SearchType
    snippet: str = ""
    highlighted_terms: list[str] = field(default_factory=list)
    relevance_explanation: str = ""
    rank: int = 0
    
    def __post_init__(self):
        """初期化後の検証"""
        self._validate_fields()
        self._generate_default_snippet()
    
    def _validate_fields(self):
        """フィールドの検証を実行"""
        if not isinstance(self.document, MockDocument):
            raise ValueError("documentはMockDocumentインスタンスである必要があります")
        
        if not (0.0 <= self.score <= 1.0):
            raise ValueError("スコアは0.0から1.0の範囲である必要があります")
        
        if not isinstance(self.search_type, SearchType):
            raise ValueError("search_typeはSearchType列挙型である必要があります")
        
        if self.rank < 0:
            raise ValueError("順位は0以上である必要があります")
    
    def _generate_default_snippet(self):
        """デフォルトスニペットを生成"""
        if not self.snippet and self.document.content:
            self.snippet = self.document.get_summary(150)
    
    def get_formatted_score(self) -> str:
        """フォーマットされたスコアを取得"""
        return f"{self.score * 100:.1f}%"


def create_mock_document(
    doc_id: str = "test_doc",
    file_path: str = "/test/sample.txt",
    title: str = "テストドキュメント",
    content: str = "これはテスト用のドキュメントです。",
    file_type: FileType = FileType.TEXT,
    size: int = 1024
) -> MockDocument:
    """テスト用のMockDocumentを簡単に作成するヘルパー関数"""
    now = datetime.now()
    
    return MockDocument(
        id=doc_id,
        file_path=file_path,
        title=title,
        content=content,
        file_type=file_type,
        size=size,
        created_date=now,
        modified_date=now,
        indexed_date=now,
        content_hash=""
    )


def create_mock_documents(count: int = 5) -> list[MockDocument]:
    """複数のテスト用MockDocumentを作成するヘルパー関数"""
    documents = []
    for i in range(count):
        doc = create_mock_document(
            doc_id=f"test_doc_{i}",
            file_path=f"/test/sample_{i}.txt",
            title=f"テストドキュメント{i}",
            content=f"これは{i}番目のテストドキュメントです。検索テスト用データ。",
            size=1024 + i * 100
        )
        documents.append(doc)
    
    return documents