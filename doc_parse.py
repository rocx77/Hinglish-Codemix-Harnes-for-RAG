from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("Hinglish_RAG_Report_Final (1).pdf")

print(result.document.export_to_markdown())