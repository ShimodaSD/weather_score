"""Run GarminDB's PostgreSQL import with text activity identifiers."""

import runpy
import shutil
from typing import Any


def import_activity_json(processor: Any, data: dict[str, object]) -> int:
    """Normalize the JSON identifier before GarminDB queries text primary keys."""
    with processor.garmin_act_db.managed_session() as processor.garmin_act_db_session:
        return processor._activities_process_json(
            data | {"activityId": str(data["activityId"])}
        )


def main() -> None:
    """Apply the GarminDB 3.9 JSON compatibility fix in this subprocess only."""
    from garmindb.garmin_json_data import GarminJsonActivityData

    GarminJsonActivityData._process_json = import_activity_json
    executable = shutil.which("garmindb_cli.py")
    if executable is None:
        raise SystemExit("GarminDB CLI is not installed")
    runpy.run_path(executable, run_name="__main__")


if __name__ == "__main__":
    main()
