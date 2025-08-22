"""
DocMindアプリケーション用のカスタム例外クラス

このモジュールは、アプリケーション全体で使用される例外階層を定義します。
各例外クラスは特定のエラー状況に対応し、適切なエラーハンドリングを可能にします。
"""


class DocMindException(Exception):
    """DocMindアプリケーションのベース例外クラス
    
    すべてのDocMind固有の例外はこのクラスを継承します。
    これにより、アプリケーション固有のエラーを一括でキャッチできます。
    """
    
    def __init__(self, message: str, details: str = None):
        """例外を初期化
        
        Args:
            message (str): エラーメッセージ
            details (str, optional): 詳細なエラー情報
        """
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        """例外の文字列表現を返す"""
        if self.details:
            return f"{self.message} - 詳細: {self.details}"
        return self.message


class DocumentProcessingError(DocMindException):
    """ドキュメント処理中に発生するエラー
    
    ファイルの読み込み、テキスト抽出、フォーマット解析などの
    ドキュメント処理で問題が発生した場合に発生します。
    """
    
    def __init__(self, message: str, file_path: str = None, file_type: str = None, details: str = None):
        """ドキュメント処理エラーを初期化
        
        Args:
            message (str): エラーメッセージ
            file_path (str, optional): 問題が発生したファイルのパス
            file_type (str, optional): ファイルの種類
            details (str, optional): 詳細なエラー情報
        """
        super().__init__(message, details)
        self.file_path = file_path
        self.file_type = file_type


class IndexingError(DocMindException):
    """インデックス操作中に発生するエラー
    
    Whooshインデックスの作成、更新、検索などの操作で
    問題が発生した場合に発生します。
    """
    
    def __init__(self, message: str, index_path: str = None, operation: str = None, details: str = None):
        """インデックスエラーを初期化
        
        Args:
            message (str): エラーメッセージ
            index_path (str, optional): インデックスのパス
            operation (str, optional): 失敗した操作の種類
            details (str, optional): 詳細なエラー情報
        """
        super().__init__(message, details)
        self.index_path = index_path
        self.operation = operation


class SearchError(DocMindException):
    """検索操作中に発生するエラー
    
    全文検索、セマンティック検索、ハイブリッド検索などの
    検索操作で問題が発生した場合に発生します。
    """
    
    def __init__(self, message: str, query: str = None, search_type: str = None, details: str = None):
        """検索エラーを初期化
        
        Args:
            message (str): エラーメッセージ
            query (str, optional): 検索クエリ
            search_type (str, optional): 検索の種類
            details (str, optional): 詳細なエラー情報
        """
        super().__init__(message, details)
        self.query = query
        self.search_type = search_type


class EmbeddingError(DocMindException):
    """埋め込み操作中に発生するエラー
    
    sentence-transformersモデルの読み込み、埋め込み生成、
    類似度計算などで問題が発生した場合に発生します。
    """
    
    def __init__(self, message: str, model_name: str = None, operation: str = None, details: str = None):
        """埋め込みエラーを初期化
        
        Args:
            message (str): エラーメッセージ
            model_name (str, optional): 使用していたモデル名
            operation (str, optional): 失敗した操作の種類
            details (str, optional): 詳細なエラー情報
        """
        super().__init__(message, details)
        self.model_name = model_name
        self.operation = operation


class DatabaseError(DocMindException):
    """データベース操作中に発生するエラー
    
    SQLiteデータベースの接続、クエリ実行、データ操作などで
    問題が発生した場合に発生します。
    """
    
    def __init__(self, message: str, database_path: str = None, operation: str = None, details: str = None):
        """データベースエラーを初期化
        
        Args:
            message (str): エラーメッセージ
            database_path (str, optional): データベースファイルのパス
            operation (str, optional): 失敗した操作の種類
            details (str, optional): 詳細なエラー情報
        """
        super().__init__(message, details)
        self.database_path = database_path
        self.operation = operation


class ConfigurationError(DocMindException):
    """設定関連のエラー
    
    アプリケーション設定の読み込み、検証、保存などで
    問題が発生した場合に発生します。
    """
    
    def __init__(self, message: str, config_key: str = None, config_value: str = None, details: str = None):
        """設定エラーを初期化
        
        Args:
            message (str): エラーメッセージ
            config_key (str, optional): 問題が発生した設定キー
            config_value (str, optional): 問題が発生した設定値
            details (str, optional): 詳細なエラー情報
        """
        super().__init__(message, details)
        self.config_key = config_key
        self.config_value = config_value


class FileSystemError(DocMindException):
    """ファイルシステム操作中に発生するエラー
    
    ファイルの監視、ディレクトリの作成、ファイルアクセス権限などで
    問題が発生した場合に発生します。
    """
    
    def __init__(self, message: str, path: str = None, operation: str = None, details: str = None):
        """ファイルシステムエラーを初期化
        
        Args:
            message (str): エラーメッセージ
            path (str, optional): 問題が発生したパス
            operation (str, optional): 失敗した操作の種類
            details (str, optional): 詳細なエラー情報
        """
        super().__init__(message, details)
        self.path = path
        self.operation = operation


class DocumentNotFoundError(DocMindException):
    """ドキュメントが見つからない場合のエラー
    
    指定されたIDやパスのドキュメントがデータベースに存在しない場合に発生します。
    """
    
    def __init__(self, message: str, document_id: str = None, file_path: str = None, details: str = None):
        """ドキュメント未発見エラーを初期化
        
        Args:
            message (str): エラーメッセージ
            document_id (str, optional): 見つからなかったドキュメントID
            file_path (str, optional): 見つからなかったファイルパス
            details (str, optional): 詳細なエラー情報
        """
        super().__init__(message, details)
        self.document_id = document_id
        self.file_path = file_path


class BackgroundProcessingError(DocMindException):
    """バックグラウンド処理エラー"""
    pass


class CacheError(DocMindException):
    """キャッシュ操作エラー"""
    pass


class MemoryError(DocMindException):
    """メモリ管理エラー"""
    pass


class UpdateError(DocMindException):
    """アップデート操作中に発生するエラー
    
    アプリケーションのアップデートチェック、ダウンロード、インストールなどで
    問題が発生した場合に発生します。
    """
    
    def __init__(self, message: str, update_version: str = None, operation: str = None, details: str = None):
        """アップデートエラーを初期化
        
        Args:
            message (str): エラーメッセージ
            update_version (str, optional): アップデート対象のバージョン
            operation (str, optional): 失敗した操作の種類
            details (str, optional): 詳細なエラー情報
        """
        super().__init__(message, details)
        self.update_version = update_version
        self.operation = operation