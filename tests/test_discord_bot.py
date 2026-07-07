from cinepi_rag.discord_bot import allowed_channel, split_discord_message


def test_split_discord_message_keeps_parts_under_limit():
    parts = split_discord_message("word " * 1000, limit=100)
    assert len(parts) > 1
    assert all(len(part) <= 100 for part in parts)


def test_allowed_channel_empty_list_allows_all():
    assert allowed_channel(123, [])


def test_allowed_channel_restricts_when_configured():
    assert allowed_channel(123, [123, 456])
    assert not allowed_channel(789, [123, 456])
