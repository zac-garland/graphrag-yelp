"""Tests for pipeline.ingest (use small synthetic data, not full Yelp dataset)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from pipeline.ingest import _parse_categories, _parse_friends, load_city_businesses, stream_reviews_for_businesses


def test_parse_friends() -> None:
    assert _parse_friends("u1, u2, u3") == ["u1", "u2", "u3"]
    assert _parse_friends(["a", "b"]) == ["a", "b"]
    assert _parse_friends("") == []
    assert _parse_friends("None") == []
    assert _parse_friends(None) == []


def test_parse_categories() -> None:
    assert _parse_categories("Restaurant, Bar, Food") == ["Restaurant", "Bar", "Food"]
    assert _parse_categories("") == []
    assert _parse_categories(None) == []


def test_stream_reviews_for_businesses(tmp_path: Path) -> None:
    (tmp_path / "review.json").write_text(
        '{"review_id":"r1","business_id":"b1","user_id":"u1","stars":5,"date":"2020-01-01"}\n'
        '{"review_id":"r2","business_id":"b2","user_id":"u2","stars":4,"date":"2020-01-02"}\n'
        '{"review_id":"r3","business_id":"b1","user_id":"u3","stars":3,"date":"2020-01-03"}\n'
    )
    df = stream_reviews_for_businesses({"b1"}, review_path=tmp_path / "review.json")
    assert len(df) == 2
    assert set(df["business_id"]) == {"b1"}
    assert set(df["review_id"]) == {"r1", "r3"}
