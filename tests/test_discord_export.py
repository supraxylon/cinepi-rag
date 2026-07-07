from cinepi_rag.db import Database
from cinepi_rag.discord_export import chunk_discord_export, message_text
from cinepi_rag.ingestion import ingest_discord_export


def sample_export():
    return {
        "guild": {"id": "g1", "name": "CinePI"},
        "channel": {"id": "c1", "name": "raspberry-pi", "category": "hardware", "topic": "Pi troubleshooting"},
        "exportedAt": "2026-07-07T00:00:00+00:00",
        "messageCount": 2,
        "messages": [
            {
                "id": "m1",
                "timestamp": "2026-07-07T00:01:00+00:00",
                "type": "Default",
                "isPinned": False,
                "content": "cinepi.local does not resolve",
                "author": {"id": "u1", "name": "person", "nickname": "Person", "isBot": False, "roles": []},
                "attachments": [],
                "embeds": [],
            },
            {
                "id": "m2",
                "timestamp": "2026-07-07T00:02:00+00:00",
                "type": "Reply",
                "isPinned": True,
                "content": "Try the Pi IP and check Avahi.",
                "author": {"id": "u2", "name": "schoolpost", "nickname": "Schoolpost", "isBot": False, "roles": [{"name": "Admin"}]},
                "reference": {"messageId": "m1", "channelId": "c1", "guildId": "g1", "type": "Default"},
                "attachments": [{"fileName": "log.txt", "url": "https://cdn.discordapp.com/attachments/c1/a/log.txt?hm=secret", "fileSizeBytes": 12}],
                "embeds": [{"title": "Avahi docs", "url": "https://example.com/avahi", "description": "mDNS service discovery"}],
            },
        ],
    }


def test_message_text_preserves_admin_and_pseudonymizes_normal_user():
    data = sample_export()
    by_id = {msg["id"]: msg for msg in data["messages"]}
    text = message_text(data["messages"][1], by_id)
    assert "Schoolpost" in text
    assert "replies to user_" in text
    assert "?hm=secret" not in text
    assert "Avahi docs" in text


def test_chunk_discord_export_groups_messages():
    chunks = chunk_discord_export(sample_export(), max_messages=20)
    assert len(chunks) == 1
    assert "cinepi.local" in chunks[0].text
    assert chunks[0].metadata["message_id_start"] == "m1"
    assert chunks[0].metadata["message_id_end"] == "m2"


def test_ingest_discord_export(tmp_path):
    export_path = tmp_path / "channel.json"
    import json
    export_path.write_text(json.dumps(sample_export()), encoding="utf-8")
    db = Database(tmp_path / "rag.sqlite")
    db.init(reset=True)
    assert ingest_discord_export(db, export_path) == 1
    results = db.search("Avahi cinepi.local", limit=3)
    assert results
    assert results[0]["source_type"] == "discord_export_raw"


def test_trusted_author_metadata_and_name_preservation():
    discord_config = {
        "trusted_authors": [{"aliases": ["schoolpost", "Schoolpost"], "score": 2.0, "reason": "creator of CinePI"}],
        "trusted_roles": {"Admin": 1.5},
    }
    chunks = chunk_discord_export(sample_export(), max_messages=20, discord_config=discord_config)
    assert chunks[0].metadata["authority_score"] == 2.0
    assert chunks[0].metadata["authority_reason"] == "creator of CinePI"
    assert chunks[0].metadata["trusted_authors"] == ["Schoolpost"]
    assert chunks[0].metadata["is_pinned"] is True
    assert "Schoolpost" in chunks[0].text


def test_authority_boost_can_rerank_results(tmp_path):
    db = Database(tmp_path / "rag.sqlite")
    db.init(reset=True)
    source_id = db.add_source("test", "cinepi", "test", "memory")
    db.add_chunk(source_id, "normal", "Avahi cinepi.local troubleshooting general note", "normal", {"authority_score": 1.0})
    db.add_chunk(source_id, "trusted", "Avahi cinepi.local troubleshooting maintainer note", "trusted", {"authority_score": 2.0})
    results = db.search("Avahi cinepi.local troubleshooting", limit=2, retrieval_config={"authority_boost_weight": 1.0, "pinned_boost_weight": 0.0, "reaction_boost_weight": 0.0})
    assert results[0]["title"] == "trusted"
    assert results[0]["authority_boost"] > 0
