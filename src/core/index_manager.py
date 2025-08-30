"""
Whoosh全文検索インデックス管理モジュール

このモジュールは、Whooshライブラリを使用した全文検索インデックスの
作成、更新、検索機能を提供します。
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from whoosh import fields, index
from whoosh.analysis import NgramAnalyzer, StandardAnalyzer
from whoosh.highlight import ContextFragmenter, HtmlFormatter, highlight
from whoosh.index import Index
from whoosh.qparser import MultifieldParser
from whoosh.query import And, DateRange, Or, Query, Term
from whoosh.searching import Hit

from ..data.models import Document, FileType, SearchResult, SearchType
from ..utils.exceptions import IndexingError, SearchError


class IndexManager:
    """
    Whoosh全文検索インデックス管理クラス

    ドキュメントのインデックス化、検索、更新機能を提供します。
    日本語テキストの処理に最適化されたアナライザーを使用します。
    """

    def __init__(self, index_path: str):
        """
        IndexManagerの初期化

        Args:
            index_path (str): インデックスファイルを保存するディレクトリパス
        """
        self.index_path = Path(index_path)
        self.logger = logging.getLogger(__name__)
        self._index: Index | None = None

        # 日本語対応のアナライザーを設定
        self.analyzer = StandardAnalyzer(minsize=1, maxsize=40, stoplist=None)
        self.ngram_analyzer = NgramAnalyzer(minsize=2, maxsize=4)

        # インデックススキーマの定義
        self._schema = self._create_schema()

        # インデックスの初期化
        self._initialize_index()

    def _create_schema(self) -> fields.Schema:
        """
        Whooshインデックスのスキーマを作成

        Returns:
            fields.Schema: 作成されたスキーマ
        """
        return fields.Schema(
            # ドキュメント識別子（主キー）
            id=fields.ID(stored=True, unique=True),

            # ファイルパス（検索可能、保存）
            file_path=fields.TEXT(stored=True, analyzer=self.analyzer),

            # ドキュメントタイトル（検索可能、保存、重み付け高）
            title=fields.TEXT(stored=True, analyzer=self.analyzer, field_boost=2.0),

            # メインコンテンツ（検索可能、保存）
            content=fields.TEXT(stored=True, analyzer=self.analyzer),

            # N-gram検索用コンテンツ（部分一致検索用）
            content_ngram=fields.TEXT(analyzer=self.ngram_analyzer),

            # ファイルタイプ（フィルタリング用）
            file_type=fields.KEYWORD(stored=True),

            # ファイルサイズ（数値検索用）
            size=fields.NUMERIC(stored=True),

            # 作成日時（日付範囲検索用）
            created_date=fields.DATETIME(stored=True),

            # 更新日時（日付範囲検索用）
            modified_date=fields.DATETIME(stored=True),

            # インデックス化日時（管理用）
            indexed_date=fields.DATETIME(stored=True),

            # コンテンツハッシュ（重複検出用）
            content_hash=fields.ID(stored=True),

            # メタデータ（JSON形式で保存）
            metadata=fields.TEXT(stored=True)
        )

    def _initialize_index(self) -> None:
        """
        インデックスの初期化
        既存のインデックスがある場合は開き、ない場合は新規作成
        """
        try:
            # インデックスディレクトリの作成
            self.index_path.mkdir(parents=True, exist_ok=True)

            # 既存のインデックスを開くか、新規作成
            if index.exists_in(str(self.index_path)):
                self._index = index.open_dir(str(self.index_path))
                self.logger.info(f"既存のインデックスを開きました: {self.index_path}")
            else:
                self._index = index.create_in(str(self.index_path), self._schema)
                self.logger.info(f"新しいインデックスを作成しました: {self.index_path}")

        except Exception as e:
            error_msg = f"インデックスの初期化に失敗しました: {e}"
            self.logger.error(error_msg)
            raise IndexingError(error_msg) from e

    def create_index(self) -> None:
        """
        新しいインデックスを作成（既存のインデックスを削除）
        """
        try:
            # 既存のインデックスファイルを削除
            if self.index_path.exists():
                import shutil
                shutil.rmtree(self.index_path)
                self.logger.info("既存のインデックスを削除しました")

            # 新しいインデックスを作成
            self.index_path.mkdir(parents=True, exist_ok=True)
            self._index = index.create_in(str(self.index_path), self._schema)
            self.logger.info(f"新しいインデックスを作成しました: {self.index_path}")

        except Exception as e:
            error_msg = f"インデックスの作成に失敗しました: {e}"
            self.logger.error(error_msg)
            raise IndexingError(error_msg) from e

    def add_document(self, doc: Document) -> None:
        """
        ドキュメントをインデックスに追加

        Args:
            doc (Document): 追加するドキュメント
        """
        try:
            if not self._index:
                raise IndexingError("インデックスが初期化されていません")

            writer = self._index.writer()
            try:
                # ドキュメントをインデックスに追加
                writer.add_document(
                    id=doc.id,
                    file_path=doc.file_path,
                    title=doc.title,
                    content=doc.content,
                    content_ngram=doc.content,  # N-gram検索用
                    file_type=doc.file_type.value,
                    size=doc.size,
                    created_date=doc.created_date,
                    modified_date=doc.modified_date,
                    indexed_date=doc.indexed_date,
                    content_hash=doc.content_hash,
                    metadata=str(doc.metadata) if doc.metadata else ""
                )
                writer.commit()
                self.logger.debug(f"ドキュメントを追加しました: {doc.title}")

            except Exception as e:
                writer.cancel()
                raise e

        except Exception as e:
            error_msg = f"ドキュメントの追加に失敗しました: {doc.title} - {e}"
            self.logger.error(error_msg)
            raise IndexingError(error_msg) from e

    def update_document(self, doc: Document) -> None:
        """
        ドキュメントを更新（既存のドキュメントを削除して再追加）

        Args:
            doc (Document): 更新するドキュメント
        """
        try:
            if not self._index:
                raise IndexingError("インデックスが初期化されていません")

            writer = self._index.writer()
            try:
                # 既存のドキュメントを削除して新しいドキュメントを追加
                writer.update_document(
                    id=doc.id,
                    file_path=doc.file_path,
                    title=doc.title,
                    content=doc.content,
                    content_ngram=doc.content,
                    file_type=doc.file_type.value,
                    size=doc.size,
                    created_date=doc.created_date,
                    modified_date=doc.modified_date,
                    indexed_date=doc.indexed_date,
                    content_hash=doc.content_hash,
                    metadata=str(doc.metadata) if doc.metadata else ""
                )
                writer.commit()
                self.logger.debug(f"ドキュメントを更新しました: {doc.title}")

            except Exception as e:
                writer.cancel()
                raise e

        except Exception as e:
            error_msg = f"ドキュメントの更新に失敗しました: {doc.title} - {e}"
            self.logger.error(error_msg)
            raise IndexingError(error_msg) from e

    def remove_document(self, doc_id: str) -> None:
        """
        ドキュメントをインデックスから削除

        Args:
            doc_id (str): 削除するドキュメントのID
        """
        try:
            if not self._index:
                raise IndexingError("インデックスが初期化されていません")

            writer = self._index.writer()
            try:
                writer.delete_by_term("id", doc_id)
                writer.commit()
                self.logger.debug(f"ドキュメントを削除しました: {doc_id}")

            except Exception as e:
                writer.cancel()
                raise e

        except Exception as e:
            error_msg = f"ドキュメントの削除に失敗しました: {doc_id} - {e}"
            self.logger.error(error_msg)
            raise IndexingError(error_msg) from e

    def clear_index(self) -> None:
        """
        インデックス全体をクリア

        すべてのドキュメントをインデックスから削除します。
        この操作は取り消しできません。
        """
        try:
            if not self._index:
                raise IndexingError("インデックスが初期化されていません")

            # 方法1: インデックスを再作成（推奨）
            try:
                # 既存のインデックスを閉じる
                if self._index:
                    self._index.close()
                    self._index = None

                # インデックスディレクトリを削除
                import shutil
                if self.index_path.exists():
                    shutil.rmtree(self.index_path)

                # インデックスを再初期化
                self._initialize_index()

                self.logger.info("インデックス全体をクリアしました（再作成方式）")
                return

            except Exception as e:
                self.logger.warning(f"インデックス再作成方式が失敗: {e}")
                # フォールバック: 個別削除方式
                pass

            # 方法2: 個別ドキュメント削除（フォールバック）
            writer = self._index.writer()
            try:
                # すべてのドキュメントIDを取得して削除
                with self._index.searcher() as searcher:
                    doc_ids = [hit['id'] for hit in searcher.documents()]

                # 各ドキュメントを個別に削除
                for doc_id in doc_ids:
                    writer.delete_by_term("id", doc_id)

                writer.commit()
                self.logger.info(
                    f"インデックス全体をクリアしました（個別削除方式）: {len(doc_ids)}件"
                )

            except Exception as e:
                writer.cancel()
                raise e

        except Exception as e:
            error_msg = f"インデックスクリアに失敗: {e}"
            self.logger.error(error_msg)
            raise IndexingError(error_msg) from e

    def search_text(self, query_text: str, limit: int = 100,
                   file_types: list[FileType] | None = None,
                   date_from: datetime | None = None,
                   date_to: datetime | None = None) -> list[SearchResult]:
        """
        全文検索を実行

        Args:
            query_text (str): 検索クエリ
            limit (int): 最大結果数
            file_types (List[FileType], optional): フィルター対象のファイルタイプ
            date_from (datetime, optional): 日付範囲の開始
            date_to (datetime, optional): 日付範囲の終了

        Returns:
            List[SearchResult]: 検索結果のリスト
        """
        try:
            if not self._index:
                raise SearchError("インデックスが初期化されていません")

            if not query_text.strip():
                return []

            # 検索クエリの構築
            query = self._build_search_query(query_text, file_types, date_from, date_to)

            # 検索の実行
            with self._index.searcher() as searcher:
                results = searcher.search(query, limit=limit)

                # 検索結果をSearchResultオブジェクトに変換
                search_results = []
                for i, hit in enumerate(results):
                    search_result = self._create_search_result_from_hit(
                        hit, query_text, i + 1
                    )
                    search_results.append(search_result)

                self.logger.info(f"検索完了: クエリ='{query_text}', 結果数={len(search_results)}")
                return search_results

        except Exception as e:
            error_msg = f"検索に失敗しました: {query_text} - {e}"
            self.logger.error(error_msg)
            raise SearchError(error_msg) from e

    def _build_search_query(self, query_text: str,
                           file_types: list[FileType] | None = None,
                           date_from: datetime | None = None,
                           date_to: datetime | None = None) -> Query:
        """
        検索クエリを構築

        Args:
            query_text (str): 検索テキスト
            file_types (List[FileType], optional): ファイルタイプフィルター
            date_from (datetime, optional): 日付範囲開始
            date_to (datetime, optional): 日付範囲終了

        Returns:
            Query: 構築されたクエリ
        """
        # メインの検索クエリ（タイトルとコンテンツを対象）
        parser = MultifieldParser(["title", "content", "content_ngram"], self._index.schema)
        main_query = parser.parse(query_text)

        # フィルター条件を追加
        filters = []

        # ファイルタイプフィルター
        if file_types:
            type_queries = [Term("file_type", ft.value) for ft in file_types]
            if len(type_queries) == 1:
                filters.append(type_queries[0])
            else:
                filters.append(Or(type_queries))

        # 日付範囲フィルター
        if date_from or date_to:
            date_query = DateRange("modified_date", date_from, date_to)
            filters.append(date_query)

        # フィルターを適用
        if filters:
            if len(filters) == 1:
                return And([main_query, filters[0]])
            else:
                return And([main_query] + filters)

        return main_query

    def _create_search_result_from_hit(self, hit: Hit, query_text: str, rank: int) -> SearchResult:
        """
        Whooshの検索結果からSearchResultオブジェクトを作成

        Args:
            hit (Hit): Whooshの検索結果
            query_text (str): 検索クエリ
            rank (int): 検索結果の順位

        Returns:
            SearchResult: 作成されたSearchResultオブジェクト
        """
        # ドキュメントオブジェクトの再構築
        document = Document(
            id=hit["id"],
            file_path=hit["file_path"],
            title=hit["title"],
            content=hit["content"],
            file_type=FileType(hit["file_type"]),
            size=hit["size"],
            created_date=hit["created_date"],
            modified_date=hit["modified_date"],
            indexed_date=hit["indexed_date"],
            content_hash=hit["content_hash"]
        )

        # スニペットの生成
        snippet = self._generate_snippet(hit, query_text)

        # ハイライト対象の用語を抽出
        highlighted_terms = self._extract_highlighted_terms(query_text)

        # スコアの正規化（Whooshのスコアは0-1の範囲ではないため）
        normalized_score = min(hit.score / 10.0, 1.0)  # 適切な正規化係数を使用

        return SearchResult(
            document=document,
            score=normalized_score,
            search_type=SearchType.FULL_TEXT,
            snippet=snippet,
            highlighted_terms=highlighted_terms,
            relevance_explanation=f"全文検索スコア: {hit.score:.2f}",
            rank=rank
        )

    def _generate_snippet(self, hit: Hit, query_text: str, max_chars: int = 200) -> str:
        """
        検索結果のスニペットを生成

        Args:
            hit (Hit): Whooshの検索結果
            query_text (str): 検索クエリ
            max_chars (int): 最大文字数

        Returns:
            str: 生成されたスニペット
        """
        try:
            # Whooshのハイライト機能を使用
            formatter = HtmlFormatter(tagname="mark")
            fragmenter = ContextFragmenter(maxchars=max_chars, surround=50)

            # コンテンツからスニペットを生成
            content = hit.get("content", "")
            if content:
                # クエリパーサーを使用してハイライト
                from whoosh.qparser import QueryParser
                parser = QueryParser("content", self._index.schema)
                parser.parse(query_text)

                highlighted = highlight(
                    content,
                    [query_text],
                    analyzer=self.analyzer,
                    formatter=formatter,
                    fragmenter=fragmenter
                )

                # HTMLタグを除去してプレーンテキストに変換
                import re
                snippet = re.sub(r'<[^>]+>', '', highlighted)
                return snippet[:max_chars] + "..." if len(snippet) > max_chars else snippet

            # コンテンツがない場合はタイトルを使用
            return hit.get("title", "")[:max_chars]

        except Exception as e:
            self.logger.warning(f"スニペット生成に失敗しました: {e}")
            # フォールバック: コンテンツの先頭部分を返す
            content = hit.get("content", "")
            return content[:max_chars] + "..." if len(content) > max_chars else content

    def _extract_highlighted_terms(self, query_text: str) -> list[str]:
        """
        クエリからハイライト対象の用語を抽出

        Args:
            query_text (str): 検索クエリ

        Returns:
            List[str]: ハイライト対象の用語リスト
        """
        # 簡単な実装: スペースで分割して用語を抽出
        terms = []
        for term in query_text.split():
            # 特殊文字を除去
            clean_term = ''.join(c for c in term if c.isalnum() or c in 'ひらがなカタカナ漢字')
            if clean_term and len(clean_term) > 1:
                terms.append(clean_term)

        return terms

    def rebuild_index(self, documents: list[Document]) -> None:
        """
        インデックスを完全に再構築

        Args:
            documents (List[Document]): インデックス化するドキュメントのリスト
        """
        try:
            self.logger.info(f"インデックスの再構築を開始します: {len(documents)}件のドキュメント")

            # 新しいインデックスを作成
            self.create_index()

            # バッチでドキュメントを追加
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                self._add_documents_batch(batch)
                self.logger.info(f"進捗: {min(i + batch_size, len(documents))}/{len(documents)}")

            # インデックスの最適化
            self.optimize_index()

            self.logger.info("インデックスの再構築が完了しました")

        except Exception as e:
            error_msg = f"インデックスの再構築に失敗しました: {e}"
            self.logger.error(error_msg)
            raise IndexingError(error_msg) from e

    def _add_documents_batch(self, documents: list[Document]) -> None:
        """
        ドキュメントをバッチで追加

        Args:
            documents (List[Document]): 追加するドキュメントのリスト
        """
        if not self._index:
            raise IndexingError("インデックスが初期化されていません")

        writer = self._index.writer()
        try:
            for doc in documents:
                writer.add_document(
                    id=doc.id,
                    file_path=doc.file_path,
                    title=doc.title,
                    content=doc.content,
                    content_ngram=doc.content,
                    file_type=doc.file_type.value,
                    size=doc.size,
                    created_date=doc.created_date,
                    modified_date=doc.modified_date,
                    indexed_date=doc.indexed_date,
                    content_hash=doc.content_hash,
                    metadata=str(doc.metadata) if doc.metadata else ""
                )
            writer.commit()

        except Exception as e:
            writer.cancel()
            raise e

    def optimize_index(self) -> None:
        """
        インデックスを最適化（パフォーマンス向上のため）
        """
        try:
            if not self._index:
                raise IndexingError("インデックスが初期化されていません")

            self.logger.info("インデックスの最適化を開始します")
            self._index.optimize()
            self.logger.info("インデックスの最適化が完了しました")

        except Exception as e:
            error_msg = f"インデックスの最適化に失敗しました: {e}"
            self.logger.error(error_msg)
            raise IndexingError(error_msg) from e

    def get_document_count(self) -> int:
        """
        インデックス内のドキュメント数を取得

        Returns:
            int: ドキュメント数
        """
        try:
            if not self._index:
                return 0

            with self._index.searcher() as searcher:
                return searcher.doc_count()

        except Exception as e:
            self.logger.error(f"ドキュメント数の取得に失敗しました: {e}")
            return 0

    def document_exists(self, doc_id: str) -> bool:
        """
        指定されたIDのドキュメントがインデックスに存在するかチェック

        Args:
            doc_id (str): ドキュメントID

        Returns:
            bool: 存在する場合True
        """
        try:
            if not self._index:
                return False

            with self._index.searcher() as searcher:
                results = searcher.search(Term("id", doc_id), limit=1)
                return len(results) > 0

        except Exception as e:
            self.logger.error(f"ドキュメント存在チェックに失敗しました: {e}")
            return False

    def get_index_stats(self) -> dict[str, Any]:
        """
        インデックスの統計情報を取得

        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            if not self._index:
                return {"document_count": 0, "index_size": 0}

            stats = {
                "document_count": self.get_document_count(),
                "index_size": self._get_index_size(),
                "last_modified": self._get_index_last_modified(),
                "schema_version": str(self._index.schema)
            }

            return stats

        except Exception as e:
            self.logger.error(f"統計情報の取得に失敗しました: {e}")
            return {"document_count": 0, "index_size": 0, "error": str(e)}

    def _get_index_size(self) -> int:
        """
        インデックスファイルの合計サイズを取得

        Returns:
            int: サイズ（バイト）
        """
        total_size = 0
        try:
            for file_path in self.index_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            self.logger.warning(f"インデックスサイズの計算に失敗しました: {e}")

        return total_size

    def _get_index_last_modified(self) -> datetime | None:
        """
        インデックスの最終更新日時を取得

        Returns:
            datetime: 最終更新日時
        """
        try:
            latest_time = None
            for file_path in self.index_path.rglob("*"):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if latest_time is None or mtime > latest_time:
                        latest_time = mtime
            return latest_time
        except Exception as e:
            self.logger.warning(f"最終更新日時の取得に失敗しました: {e}")
            return None

    def close(self) -> None:
        """
        インデックスを閉じる
        """
        if self._index:
            self._index.close()
            self._index = None
            self.logger.info("インデックスを閉じました")
