"""Configure GarminDB schemas when a pooler ignores startup options."""


def configure_schema_connections() -> None:
    """Set each GarminDB connection's schema after connecting to PostgreSQL."""
    import idbutils.db
    from sqlalchemy import event

    original = idbutils.db.create_engine
    if getattr(original, "_weather_score_schema_fix", False) is True:
        return
    engines = {}

    def create_engine(*args, **kwargs):
        connect_args = kwargs.get("connect_args", {})
        options = connect_args.get("options")
        if not options:
            return original(*args, **kwargs)
        prefix = "-csearch_path="
        schema = options.removeprefix(prefix)
        if options != prefix + schema or schema not in {
            "garmin", "garmin_activities", "garmin_monitoring", "garmin_summary", "summary"
        }:
            raise ValueError("Unexpected GarminDB PostgreSQL schema")
        kwargs["connect_args"] = {key: value for key, value in connect_args.items() if key != "options"}
        key = (args[0], schema, kwargs.get("echo"), tuple(sorted(kwargs["connect_args"].items())))
        if key in engines:
            return engines[key]
        engine = original(*args, **kwargs)

        @event.listens_for(engine, "connect")
        def set_search_path(connection, _record):
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path TO "{schema}"')
            connection.commit()

        engines[key] = engine
        return engine

    create_engine._weather_score_schema_fix = True
    idbutils.db.create_engine = create_engine
