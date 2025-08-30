"""
テスト用IndexManager v2

完全にモック化されたテスト専用のIndexManagerクラス
"""

from whoosh.searching import Hit

from tests.fixtures.mock_models import MockDocument, MockSearchResult

from ..data.models import FileType, SearchType
from .index_manager import IndexManager


class TestIndexManagerV2(IndexManager):
    """テスト用IndexManager v2

    検索結果作成時にMockSearchResultを使用してすべての検証を回避
    """

    def _create_search_result_from_hit(
        self, hit: Hit, query_text: str, rank: int
    ) -> MockSearchResult:
        """
        Whooshの検索結果からMockSearchResultオブジェクトを作成（テスト用）

        Args:
            hit (Hit): Whooshの検索結果
            query_text (str): 検索クエリ
            rank (int): 検索結果の順位

        Returns:
            MockSearchResult: 作成されたMockSearchResultオブジェクト
        """
        # MockDocumentオブジェクトの作成（ファイル存在チェックなし）
        document = MockDocument(
            id=hit["id"],
            file_path=hit["file_path"],
            title=hit["title"],
            content=hit["content"],
            file_type=FileType(hit["file_type"]),
            size=hit["size"],
            created_date=hit["created_date"],
            modified_date=hit["modified_date"],
            indexed_date=hit["indexed_date"],
            content_hash=hit["content_hash"],
        )

        # スニペットの生成
        snippet = self._generate_snippet(hit, query_text)

        # ハイライト対象の用語を抽出
        highlighted_terms = self._extract_highlighted_terms(query_text)

        # スコアの正規化（Whooshのスコアは0-1の範囲ではないため）
        normalized_score = min(hit.score / 10.0, 1.0)  # 適切な正規化係数を使用

        return MockSearchResult(
            document=document,
            score=normalized_score,
            search_type=SearchType.FULL_TEXT,
            snippet=snippet,
            highlighted_terms=highlighted_terms,
            relevance_explanation=f"全文検索スコア: {hit.score:.2f}",
            rank=rank,
        )
