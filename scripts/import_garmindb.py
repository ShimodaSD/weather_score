"""Run GarminDB's PostgreSQL import with text activity identifiers."""

import os
import runpy
import shutil
from typing import Any


def import_activity_json(processor: Any, data: dict[str, object]) -> int:
    """Normalize the JSON identifier before GarminDB queries text primary keys."""
    with processor.garmin_act_db.managed_session() as processor.garmin_act_db_session:
        return processor._activities_process_json(
            data | {"activityId": str(data["activityId"])}
        )


def get_measurement_system(
    attributes: Any, database: Any, default: str = "metric"
) -> Any:
    """Keep stored units and use metric when a fresh database has no settings FIT."""
    from fitfile.field_enums import DisplayMeasure

    return DisplayMeasure.from_string(
        attributes.get_string(database, "measurement_system", default)
    )


def main() -> None:
    """Apply the GarminDB 3.9 JSON compatibility fix in this subprocess only."""
    if os.environ.get("DB_SHARED_GARMIN") == "1":
        try:
            from .garmindb_postgres import configure_schema_connections
        except ImportError:
            from garmindb_postgres import configure_schema_connections
        configure_schema_connections()

    from garmindb.garmin_json_data import GarminJsonActivityData
    from garmindb.garmindb import Attributes

    GarminJsonActivityData._process_json = import_activity_json
    Attributes.measurements_type = classmethod(get_measurement_system)
    executable = shutil.which("garmindb_cli.py")
    if executable is None:
        raise SystemExit("GarminDB CLI is not installed")
    runpy.run_path(executable, run_name="__main__")


if __name__ == "__main__":
    main()
