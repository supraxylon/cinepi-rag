from cinepi_rag.chunking import chunk_markdown, chunk_plain_text


def test_chunk_markdown_splits_by_heading():
    chunks = chunk_markdown("Doc", "# A\nText A\n\n## B\nText B")
    assert len(chunks) == 2
    assert chunks[0].title == "A"
    assert chunks[1].title == "B"


def test_chunk_plain_text_keeps_content():
    chunks = chunk_plain_text("Note", "hello\n\nworld", max_chars=100)
    assert len(chunks) == 1
    assert "hello" in chunks[0].text
    assert "world" in chunks[0].text
