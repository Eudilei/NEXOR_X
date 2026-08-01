import sqlite3
from pathlib import Path

import pytest

from nexor_x.infrastructure.database import _SCHEMA
from nexor_x.laboratory.importer import import_csv


def prepare_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(_SCHEMA)
    connection.close()


def test_import_csv_is_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "lab.db"
    prepare_database(database)
    csv_file = tmp_path / "observations.csv"
    csv_file.write_text(
        "symbol,decision,raw_edge,regime,realized_r,closed_at\n"
        "BTCUSDT,LONG_BIAS,0.5,TREND_UP,1.2,2025-01-01T00:00:00+00:00\n",
        encoding="utf-8",
    )
    assert import_csv(csv_file, database) == 1
    assert import_csv(csv_file, database) == 0


def test_import_csv_rejects_missing_columns(tmp_path: Path) -> None:
    database = tmp_path / "lab.db"
    prepare_database(database)
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("symbol,raw_edge\nBTCUSDT,0.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="colunas obrigatorias"):
        import_csv(csv_file, database)
