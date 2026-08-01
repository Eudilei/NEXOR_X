from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

REQUIRED_COLUMNS = {"symbol", "decision", "raw_edge", "regime", "realized_r", "closed_at"}


def import_csv(csv_path: Path, database_path: Path) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    inserted = 0
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_COLUMNS.difference(reader.fieldnames or ())
            if missing:
                raise ValueError(f"colunas obrigatorias ausentes: {', '.join(sorted(missing))}")
            for line_number, row in enumerate(reader, start=2):
                try:
                    raw_edge = float(row["raw_edge"])
                    realized_r = float(row["realized_r"])
                    if not -1.0 <= raw_edge <= 1.0:
                        raise ValueError("raw_edge fora do intervalo [-1, 1]")
                    closed_at = datetime.fromisoformat(row["closed_at"]).isoformat()
                except Exception as exc:
                    raise ValueError(f"linha {line_number} invalida: {exc}") from exc
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO quant_observations
                    (symbol, decision, raw_edge, regime, realized_r, closed_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        row["symbol"].strip().upper(),
                        row["decision"].strip().upper(),
                        raw_edge,
                        row["regime"].strip().upper(),
                        realized_r,
                        closed_at,
                    ),
                )
                inserted += cursor.rowcount
        connection.commit()
        return inserted
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa observacoes encerradas no laboratorio")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--database", type=Path, default=Path("data/nexor_x.db"))
    args = parser.parse_args()
    count = import_csv(args.csv_path, args.database)
    print(f"{count} observacoes importadas")


if __name__ == "__main__":
    main()
