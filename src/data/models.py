"""
DocMindアプリケーション用のデータモデル

このモジュールは、アプリケーション全体で使用されるデータ構造を定義します。
すべてのモデルは型ヒントと検証機能を含み、データの整合性を保証します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import os
from pathlib import Path


class SearchType(Enum):
    """検索タイプを定義する列挙型
    
    アプリケーションでサポートされる検索方法を定義します。
    """
    FULL_TEXT = "full_text"      # 全文検索（Whooshベース）
    SEMANTIC = "semantic"        # セマンティック検索（埋め込みベース）
    HYBRID = "hybrid"           # ハイブリッド検索（全文+セマンティック）


class FileType(Enum):
    """サポートされるファイルタイプを定義する列挙型"""
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    MARKDOWN = "markdown"
    TEXT = "text"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_extension(cls, file_path: str) -> 'FileType':
        """ファイル拡張子からFileTypeを判定
        
        Args:
            file_path (str): ファイルパス
            
        Returns:
            FileType: 判定されたファイルタイプ
        """
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            return cls.PDF
        elif ext in ['.doc', '.docx']:
            return cls.WORD
        elif ext in ['.xls', '.xlsx']:
            return cls.EXCEL
        elif ext in ['.md', '.markdown']:
            return cls.MARKDOWN
        elif ext in ['.txt', '.text']:
            return cls.TEXT
        else:
            return cls.UNKNOWN


@dataclass
class Document:
    """ドキュメントを表すデータクラス
    
    インデックス化されたドキュメントのメタデータとコンテンツを保持します。
    すべてのフィールドは検証され、データの整合性が保証されます。
    """
    
    # 必須フィールド
    id: str                                    # ドキュメントの一意識別子
    file_path: str                            # ファイルの絶対パス
    title: str                                # ドキュメントのタイトル
    content: str                              # 抽出されたテキストコンテンツ
    file_type: FileType                       # ファイルタイプ
    size: int                                 # ファイルサイズ（バイト）
    created_date: datetime                    # ファイル作成日時
    modified_date: datetime                   # ファイル最終更新日時
    indexed_date: datetime                    # インデックス化日時
    
    # オプションフィールド
    content_hash: str = field(default="")     # コンテンツのハッシュ値
    metadata: Dict[str, Any] = field(default_factory=dict)  # 追加メタデータ
    
    def __post_init__(self):
        """初期化後の検証とデータ処理"""
        self._validate_fields()
        self._generate_content_hash()
        self._set_default_title()
    
    def _validate_fields(self):
        """フィールドの検証を実行"""
        if not self.id:
            raise ValueError("ドキュメントIDは必須です")
        
        if not self.file_path:
            raise ValueError("ファイルパスは必須です")
        
        if not os.path.exists(self.file_path):
            raise ValueError(f"ファイルが存在しません: {self.file_path}")
        
        if self.size < 0:
            raise ValueError("ファイルサイズは0以上である必要があります")
        
        if not isinstance(self.file_type, FileType):
            raise ValueError("file_typeはFileType列挙型である必要があります")
    
    def _generate_content_hash(self):
        """コンテンツのハッシュ値を生成"""
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(
                self.content.encode('utf-8')
            ).hexdigest()
    
    def _set_default_title(self):
        """デフォルトタイトルを設定"""
        if not self.title:
            self.title = Path(self.file_path).stem
    
    @classmethod
    def create_from_file(cls, file_path: str, content: str = "") -> 'Document':
        """ファイルパスからDocumentインスタンスを作成
        
        Args:
            file_path (str): ファイルパス
            content (str): 抽出されたコンテンツ
            
        Returns:
            Document: 作成されたDocumentインスタンス
        """
        if not os.path.exists(file_path):
            raise ValueError(f"ファイルが存在しません: {file_path}")
        
        file_stat = os.stat(file_path)
        file_path_obj = Path(file_path)
        
        return cls(
            id=cls._generate_id(file_path),
            file_path=str(file_path_obj.absolute()),
            title=file_path_obj.stem,
            content=content,
            file_type=FileType.from_extension(file_path),
            size=file_stat.st_size,
            created_date=datetime.fromtimestamp(file_stat.st_ctime),
            modified_date=datetime.fromtimestamp(file_stat.st_mtime),
            indexed_date=datetime.now()
        )
    
    @staticmethod
    def _generate_id(file_path: str) -> str:
        """ファイルパスから一意のIDを生成
        
        Args:
            file_path (str): ファイルパス
            
        Returns:
            str: 生成されたID
        """
        return hashlib.md5(str(Path(file_path).absolute()).encode('utf-8')).hexdigest()
    
    def is_modified_since_indexing(self) -> bool:
        """インデックス化以降にファイルが変更されたかチェック
        
        Returns:
            bool: 変更されている場合True
        """
        if not os.path.exists(self.file_path):
            return True
        
        current_mtime = datetime.fromtimestamp(os.path.getmtime(self.file_path))
        return current_mtime > self.indexed_date
    
    def get_summary(self, max_length: int = 200) -> str:
        """ドキュメントの要約を取得
        
        Args:
            max_length (int): 最大文字数
            
        Returns:
            str: 要約テキスト
        """
        if len(self.content) <= max_length:
            return self.content
        
        # 文の境界で切り取る
        summary = self.content[:max_length]
        last_sentence_end = max(
            summary.rfind('。'),
            summary.rfind('.'),
            summary.rfind('!'),
            summary.rfind('?')
        )
        
        if last_sentence_end > max_length // 2:
            return summary[:last_sentence_end + 1]
        else:
            return summary + "..."


@dataclass
class SearchResult:
    """検索結果を表すデータクラス
    
    検索操作の結果として返されるドキュメント情報とスコアリング情報を保持します。
    """
    
    # 必須フィールド
    document: Document                        # 検索にヒットしたドキュメント
    score: float                             # 関連度スコア（0.0-1.0）
    search_type: SearchType                  # 使用された検索タイプ
    
    # オプションフィールド
    snippet: str = ""                        # ハイライトされたスニペット
    highlighted_terms: List[str] = field(default_factory=list)  # ハイライト対象の用語
    relevance_explanation: str = ""          # 関連度の説明
    rank: int = 0                           # 検索結果内での順位
    
    def __post_init__(self):
        """初期化後の検証"""
        self._validate_fields()
        self._generate_default_snippet()
    
    def _validate_fields(self):
        """フィールドの検証を実行"""
        if not isinstance(self.document, Document):
            raise ValueError("documentはDocumentインスタンスである必要があります")
        
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
        """フォーマットされたスコアを取得
        
        Returns:
            str: パーセンテージ形式のスコア
        """
        return f"{self.score * 100:.1f}%"
    
    def get_search_type_display(self) -> str:
        """表示用の検索タイプ名を取得
        
        Returns:
            str: 日本語の検索タイプ名
        """
        type_names = {
            SearchType.FULL_TEXT: "全文検索",
            SearchType.SEMANTIC: "セマンティック検索",
            SearchType.HYBRID: "ハイブリッド検索"
        }
        return type_names.get(self.search_type, "不明")


@dataclass
class SearchQuery:
    """検索クエリを表すデータクラス
    
    検索リクエストの詳細情報を保持します。
    """
    
    # 必須フィールド
    query_text: str                          # 検索クエリテキスト
    search_type: SearchType                  # 検索タイプ
    
    # オプションフィールド
    limit: int = 100                         # 最大結果数
    file_types: List[FileType] = field(default_factory=list)  # フィルター対象のファイルタイプ
    date_from: Optional[datetime] = None     # 日付範囲の開始
    date_to: Optional[datetime] = None       # 日付範囲の終了
    folder_paths: List[str] = field(default_factory=list)  # 検索対象フォルダ
    weights: Dict[str, float] = field(default_factory=dict)  # ハイブリッド検索の重み
    
    def __post_init__(self):
        """初期化後の検証"""
        self._validate_fields()
        self._set_default_weights()
    
    def _validate_fields(self):
        """フィールドの検証を実行"""
        if not self.query_text.strip():
            raise ValueError("検索クエリは空にできません")
        
        if not isinstance(self.search_type, SearchType):
            raise ValueError("search_typeはSearchType列挙型である必要があります")
        
        if self.limit <= 0:
            raise ValueError("制限数は1以上である必要があります")
        
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("開始日は終了日より前である必要があります")
    
    def _set_default_weights(self):
        """ハイブリッド検索のデフォルト重みを設定"""
        if self.search_type == SearchType.HYBRID and not self.weights:
            self.weights = {
                "full_text": 0.6,
                "semantic": 0.4
            }


@dataclass
class IndexStats:
    """インデックス統計情報を表すデータクラス"""
    
    total_documents: int = 0                 # 総ドキュメント数
    total_size: int = 0                     # 総ファイルサイズ
    last_updated: Optional[datetime] = None  # 最終更新日時
    file_type_counts: Dict[FileType, int] = field(default_factory=dict)  # ファイルタイプ別カウント
    
    def get_formatted_size(self) -> str:
        """フォーマットされたサイズを取得
        
        Returns:
            str: 人間が読みやすい形式のサイズ
        """
        if self.total_size < 1024:
            return f"{self.total_size} B"
        elif self.total_size < 1024 * 1024:
            return f"{self.total_size / 1024:.1f} KB"
        elif self.total_size < 1024 * 1024 * 1024:
            return f"{self.total_size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.total_size / (1024 * 1024 * 1024):.1f} GB"