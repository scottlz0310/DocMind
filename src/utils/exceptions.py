# -*- coding: utf-8 -*-
"""
カスタム例外定義モジュール

DocMindアプリケーション固有の例外クラスを定義し、
エラーハンドリングの統一化と詳細なエラー情報の提供を行います。
"""


class DocMindException(Exception):
    """
    DocMindアプリケーションのベース例外クラス
    
    すべてのDocMind固有の例外はこのクラスを継承します。
    """
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        """
        例外の初期化
        
        Args:
            message: エラーメッセージ
            error_code: エラーコード（オプション）
            details: 追加の詳細情報（オプション）
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        """文字列表現を返す"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class DocumentProcessingError(DocMindException):
    """
    ドキュメント処理中に発生するエラー
    
    ファイルの読み込み、テキスト抽出、フォーマット変換などで
    問題が発生した場合に使用されます。
    """
    pass


class IndexingError(DocMindException):
    """
    インデックス操作中に発生するエラー
    
    Whooshインデックスの作成、更新、検索などで
    問題が発生した場合に使用されます。
    """
    pass


class SearchError(DocMindException):
    """
    検索操作中に発生するエラー
    
    全文検索、セマンティック検索、ハイブリッド検索などで
    問題が発生した場合に使用されます。
    """
    pass


class EmbeddingError(DocMindException):
    """
    埋め込み処理中に発生するエラー
    
    sentence-transformersモデルの読み込み、埋め込み生成、
    類似度計算などで問題が発生した場合に使用されます。
    """
    pass


class DatabaseError(DocMindException):
    """
    データベース操作中に発生するエラー
    
    SQLiteデータベースの接続、クエリ実行、データ操作などで
    問題が発生した場合に使用されます。
    """
    pass


class ConfigurationError(DocMindException):
    """
    設定関連のエラー
    
    設定ファイルの読み込み、設定値の検証、
    環境設定などで問題が発生した場合に使用されます。
    """
    pass


class FileSystemError(DocMindException):
    """
    ファイルシステム操作中に発生するエラー
    
    ファイルの監視、ディレクトリの作成、
    ファイルアクセスなどで問題が発生した場合に使用されます。
    """
    pass


class UIError(DocMindException):
    """
    ユーザーインターフェース関連のエラー
    
    GUI操作、ウィジェットの初期化、
    イベント処理などで問題が発生した場合に使用されます。
    """
    pass


# エラーコード定数
class ErrorCodes:
    """エラーコード定数クラス"""
    
    # ドキュメント処理エラー
    DOC_FILE_NOT_FOUND = "DOC_001"
    DOC_UNSUPPORTED_FORMAT = "DOC_002"
    DOC_EXTRACTION_FAILED = "DOC_003"
    DOC_ENCODING_ERROR = "DOC_004"
    
    # インデックスエラー
    IDX_CREATION_FAILED = "IDX_001"
    IDX_UPDATE_FAILED = "IDX_002"
    IDX_SEARCH_FAILED = "IDX_003"
    IDX_CORRUPTION = "IDX_004"
    
    # 検索エラー
    SEARCH_TIMEOUT = "SEARCH_001"
    SEARCH_INVALID_QUERY = "SEARCH_002"
    SEARCH_NO_RESULTS = "SEARCH_003"
    
    # 埋め込みエラー
    EMB_MODEL_LOAD_FAILED = "EMB_001"
    EMB_GENERATION_FAILED = "EMB_002"
    EMB_SIMILARITY_FAILED = "EMB_003"
    EMB_CACHE_ERROR = "EMB_004"
    
    # データベースエラー
    DB_CONNECTION_FAILED = "DB_001"
    DB_QUERY_FAILED = "DB_002"
    DB_MIGRATION_FAILED = "DB_003"
    DB_CORRUPTION = "DB_004"
    
    # 設定エラー
    CFG_FILE_NOT_FOUND = "CFG_001"
    CFG_INVALID_FORMAT = "CFG_002"
    CFG_VALIDATION_FAILED = "CFG_003"
    
    # ファイルシステムエラー
    FS_PERMISSION_DENIED = "FS_001"
    FS_DISK_FULL = "FS_002"
    FS_WATCH_FAILED = "FS_003"
    
    # UIエラー
    UI_INITIALIZATION_FAILED = "UI_001"
    UI_WIDGET_ERROR = "UI_002"
    UI_EVENT_ERROR = "UI_003"