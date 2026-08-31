"""Tests for the standing-harvest demand snapshot."""

from unittest.mock import MagicMock

import pytest

from app.services import harvest as harvest_module
from app.services.harvest import harvest_demand


@pytest.fixture
def store_mock(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(harvest_module, "store", mock)
    return mock


def test_harvest_demand_uses_candidate_target_title_and_location(store_mock):
    store_mock.candidate.target_title = "Backend Engineer"
    store_mock.candidate.location = "Toronto, ON, Canada"

    demand = harvest_demand()
    assert demand["user_count"] == 1
    assert demand["titles"] == [
        {"raw": "Backend Engineer", "family": "software_engineering", "count": 1}
    ]
    # city_only_location currently preserves the full string if no school hint is found.
    assert demand["locations"] == [{"normalized": "toronto, on, canada", "count": 1}]


def test_harvest_demand_returns_empty_without_candidate(store_mock):
    store_mock.candidate.target_title = None
    store_mock.candidate.location = None

    demand = harvest_demand()
    assert demand["user_count"] == 0
    assert demand["titles"] == []
    assert demand["locations"] == []


def test_harvest_demand_strips_seniority(store_mock):
    store_mock.candidate.target_title = "Senior Software Engineer"
    store_mock.candidate.location = None

    demand = harvest_demand()
    assert demand["titles"][0]["family"] == "software_engineering"
