from cinepi_rag.utils import redacted, stable_id


def test_redacted_removes_email_and_ip():
    text = redacted("email me@example.com and hit 192.168.1.2")
    assert "me@example.com" not in text
    assert "192.168.1.2" not in text


def test_stable_id_is_stable():
    assert stable_id("a", "b") == stable_id("a", "b")
