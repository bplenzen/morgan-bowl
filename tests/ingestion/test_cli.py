from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from ingestion.cli import main
from ingestion.config import ConfigurationError, IngestionConfig


def test_cli_invokes_pipeline(monkeypatch, tmp_path):
    # Mock config
    config = IngestionConfig(
        league_id="123456",
        season=2025,
        database_path=tmp_path / "data.duckdb",
    )
    monkeypatch.setattr("ingestion.cli.load_config", lambda: config)

    # Mock components
    client = Mock(name="SleeperClient")
    monkeypatch.setattr("ingestion.cli.SleeperClient", lambda: client)
    store = Mock(name="DataStore")
    monkeypatch.setattr("ingestion.cli.DataStore", lambda database_path: store)

    # Mock ingestion run
    captured_args = {}
    def fake_ingestion(**kwargs):
        captured_args.update(kwargs)
        return {"run_id": "test", "counts": {"users": 12}}
    monkeypatch.setattr("ingestion.cli.run_ingestion", fake_ingestion)

    # Run CLI with specific weeks
    exit_code = main(["--week", "1", "--week", "2"])

    # Verify results
    assert exit_code == 0
    assert captured_args["weeks"] == [1, 2]
    assert captured_args["config"] == config
    assert captured_args["client"] == client
    assert captured_args["store"] == store


def test_cli_defaults_to_full_season(monkeypatch, tmp_path):
    # Mock minimal config
    config = IngestionConfig(
        league_id="123456",
        season=2025,
        database_path=tmp_path / "data.duckdb",
    )
    monkeypatch.setattr("ingestion.cli.load_config", lambda: config)
    monkeypatch.setattr("ingestion.cli.SleeperClient", Mock)
    monkeypatch.setattr("ingestion.cli.DataStore", Mock)

    captured_args = {}
    def fake_ingestion(**kwargs):
        captured_args.update(kwargs)
        return {"run_id": "test", "counts": {}}
    monkeypatch.setattr("ingestion.cli.run_ingestion", fake_ingestion)

    # Run CLI with no arguments
    exit_code = main([])

    # Verify defaults to full season
    assert exit_code == 0
    assert captured_args["weeks"] == list(range(1, 19))


def test_cli_handles_configuration_error(monkeypatch):
    def raise_err():
        raise ConfigurationError("test error")
    monkeypatch.setattr("ingestion.cli.load_config", raise_err)

    exit_code = main([])

    assert exit_code == 1