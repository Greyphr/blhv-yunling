"""Tests for the date parsing in customs.py and a smoke test of the bot wiring.

No network and no Discord connection.

Run with:  python -m pytest
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

import customs

LAGOS = ZoneInfo("Africa/Lagos")


@pytest.fixture
def fixed_now(monkeypatch):
    """Freeze 'now' at 2027-11-01 09:00 Lagos time (the next year is a leap year)."""

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2027, 11, 1, 9, 0, tzinfo=tz)

    monkeypatch.setattr(customs, "datetime", FakeDatetime)


def parse(text):
    return customs._parse_event_datetime(text, "Africa/Lagos")


def test_later_today_stays_this_year(fixed_now):
    assert parse("11/01 9:30 AM") == datetime(2027, 11, 1, 9, 30, tzinfo=LAGOS)


def test_date_already_passed_rolls_to_next_year(fixed_now):
    assert parse("01/05 8:00 PM") == datetime(2028, 1, 5, 20, 0, tzinfo=LAGOS)


def test_leap_day_is_accepted_when_only_next_year_has_it(fixed_now):
    # 2027 has no Feb 29, 2028 does. Used to fail: strptime parsed into 1900.
    assert parse("02/29 8:00 PM") == datetime(2028, 2, 29, 20, 0, tzinfo=LAGOS)


def test_just_passed_is_rejected_not_pushed_a_year(fixed_now):
    assert parse("11/01 8:55 AM") is None


@pytest.mark.parametrize("text", ["", "tomorrow", "13/40 8:00 PM", "12/25"])
def test_garbage_is_rejected(fixed_now, text):
    assert parse(text) is None


@pytest.mark.parametrize("text", ["12/25 8:00 PM", "12/25 8:00PM", "12/25 8:00 pm", "12/25 20:00"])
def test_accepted_formats(fixed_now, text):
    assert parse(text) == datetime(2027, 12, 25, 20, 0, tzinfo=LAGOS)


def test_bad_timezone_returns_none(fixed_now):
    assert customs._parse_event_datetime("12/25 8:00 PM", "Not/AZone") is None


def test_bot_wiring_imports_and_registers_commands(monkeypatch, tmp_path):
    """Importing bot.py builds the whole command tree; this catches wiring
    mistakes (bad imports, duplicate command names) without logging in."""
    monkeypatch.setenv("DISCORD_TOKEN", "x")
    monkeypatch.setenv("TWITCH_CLIENT_ID", "x")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "x")
    import bot

    names = {c.name for c in bot.bot.tree.get_commands()}
    assert {
        "setchannel", "addstreamer", "removestreamer", "liststreamers",
        "setcustomschannel", "settimezone", "create", "end",
        "play", "playlist", "skip", "previous", "pause", "resume",
        "stop", "queue", "shuffle", "nowplaying", "volume", "leave",
    } <= names
    assert bot.normalize_twitch_username("https://www.twitch.tv/Some_Name?x=1") == "some_name"
    assert bot.normalize_twitch_username("not a name!") is None
    assert os.path.isabs(bot.storage.DATA_FILE)
