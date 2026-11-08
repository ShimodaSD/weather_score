"""Compare decoded FIT records with a read-only GarminDB SQLite reference."""

import argparse
import hashlib
import json
import math
import sqlite3
from datetime import date, datetime, time
from pathlib import Path

from weather_score.fit_activity import UnsupportedMultisportError, decode_activity


def equivalent(reference: object, decoded: object) -> bool:
    """Compare SQLite values with FIT values, allowing tiny floating-point error."""
    if isinstance(reference, str) and isinstance(decoded, datetime):
        try:
            return datetime.fromisoformat(reference) == decoded
        except ValueError:
            return False
    if isinstance(reference, str) and isinstance(decoded, time):
        try:
            return time.fromisoformat(reference) == decoded
        except ValueError:
            return False
    if isinstance(decoded, date | time):
        decoded = (
            decoded.isoformat(sep=" ")
            if isinstance(decoded, datetime)
            else decoded.isoformat()
        )
    if isinstance(reference, int | float) and isinstance(decoded, int | float):
        return math.isclose(reference, decoded, rel_tol=1e-9, abs_tol=1e-9)
    return reference == decoded


def compare(database: Path, inputs: Path) -> dict[str, int]:
    """Count record-level differences without changing the reference database."""
    totals = {
        "activities": 0,
        "missing_fit": 0,
        "unsupported": 0,
        "record_count_mismatch": 0,
        "field_mismatches": 0,
        "lap_count_mismatch": 0,
        "lap_field_mismatches": 0,
    }
    with sqlite3.connect(
        f"{database.resolve().as_uri()}?mode=ro", uri=True
    ) as connection:
        connection.row_factory = sqlite3.Row
        ids = [
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT activity_id FROM activity_records"
            )
        ]
        for activity_id in ids:
            candidates = [
                inputs / f"{activity_id}.fit",
                inputs / f"{activity_id}_ACTIVITY.fit",
            ]
            path = next(
                (candidate for candidate in candidates if candidate.is_file()), None
            )
            if path is None:
                totals["missing_fit"] += 1
                continue
            try:
                decoded = decode_activity(path)
                records = decoded["records"]
            except UnsupportedMultisportError:
                totals["unsupported"] += 1
                continue
            original = connection.execute(
                "SELECT * FROM activity_records WHERE activity_id = ? ORDER BY record",
                (activity_id,),
            ).fetchall()
            totals["activities"] += 1
            totals["record_count_mismatch"] += len(original) != len(records)
            for row, record in zip(original, records, strict=False):
                totals["field_mismatches"] += sum(
                    not equivalent(row[field], value) for field, value in record.items()
                )
            laps = connection.execute(
                "SELECT * FROM activity_laps WHERE activity_id = ? ORDER BY lap",
                (activity_id,),
            ).fetchall()
            totals["lap_count_mismatch"] += len(laps) != len(decoded["laps"])
            for row, lap in zip(laps, decoded["laps"], strict=False):
                totals["lap_field_mismatches"] += sum(
                    not equivalent(row[field], value) for field, value in lap.items()
                )
    return totals


def main() -> None:
    """Print aggregate results without exposing activity details."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("inputs", type=Path)
    args = parser.parse_args()
    root = args.database.resolve().parent
    manifest_file = root / "sha256.json"
    if manifest_file.exists():
        if args.inputs.resolve() != root / "activities":
            raise SystemExit("Reference inputs do not match the manifest")
        manifest = json.loads(manifest_file.read_text())
        for name, expected in manifest.items():
            path = (root / name).resolve()
            if (
                not path.is_relative_to(root)
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected
            ):
                raise SystemExit("Reference integrity check failed")
    for name, count in compare(args.database, args.inputs).items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
