from cinepi_rag.db import Database


def test_search_round_trip(tmp_path):
    db = Database(tmp_path / "test.sqlite")
    db.init(reset=True)
    source_id = db.add_source("file", "cinemate", "Test", "test.md")
    db.add_chunk(source_id, "mDNS", "cinepi.local may need Bonjour or Avahi", "mDNS")
    results = db.search("cinepi.local Avahi", limit=3)
    assert results
    assert "Avahi" in results[0]["content"]
