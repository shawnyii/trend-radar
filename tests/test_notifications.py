from app.services.notifications import DISCORD_CONTENT_LIMIT, truncate_discord_content


def test_truncate_discord_content_keeps_short_message():
    assert truncate_discord_content("hello") == "hello"


def test_truncate_discord_content_limits_long_message():
    message = "x" * (DISCORD_CONTENT_LIMIT + 100)

    result = truncate_discord_content(message)

    assert len(result) <= DISCORD_CONTENT_LIMIT
    assert result.endswith("...[truncated]")
