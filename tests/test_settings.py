from app.core.settings import Settings


def test_daily_summary_default_time_is_0145():
    settings = Settings(_env_file=None)

    assert settings.daily_summary_hour == 1
    assert settings.daily_summary_minute == 45
