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