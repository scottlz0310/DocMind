# DocMindテスト用Markdownファイル

これはDocMindアプリケーションのテスト用に作成されたMarkdownファイルです。

## 機能概要

DocMindは以下の機能を提供します：

- **全文検索**: Whooshを使用した高速な全文検索
- **セマンティック検索**: sentence-transformersによる意味的検索
- **ハイブリッド検索**: 全文検索とセマンティック検索の組み合わせ

## サポートファイル形式

1. PDF (.pdf)
2. Word文書 (.doc, .docx)
3. Excel (.xls, .xlsx)
4. Markdown (.md, .markdown)
5. テキストファイル (.txt)

### コード例

```python
# DocumentProcessorの使用例
processor = DocumentProcessor()
document = processor.process_file("sample.txt")
print(document.content)
```

## リンク

詳細については[公式ドキュメント](https://example.com)を参照してください。

---

*このファイルはテスト目的で作成されました。*
#
# 追加セクション

これは包括的テストスイート用に追加されたセクションです。

### 検索テスト用キーワード

- Python プログラミング
- データベース設計
- 機械学習アルゴリズム
- 自然言語処理
- テスト駆動開発

### コードサンプル

```python
def search_documents(query: str) -> List[Document]:
    """ドキュメント検索関数"""
    results = []
    # 検索ロジックの実装
    return results
```

### 表形式データ

| 項目 | 値 | 説明 |
|------|----|----|
| 検索精度 | 95% | 全文検索の精度 |
| 応答時間 | 2秒 | 平均検索時間 |
| インデックスサイズ | 100MB | インデックスファイルサイズ |