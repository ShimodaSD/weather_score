BEGIN;
SET LOCAL lock_timeout = '5s';
LOCK TABLE garmin_activities.steps_activities IN ACCESS EXCLUSIVE MODE;

CREATE TEMP TABLE cadence_migration_views (name text, definition text) ON COMMIT DROP;

DO $$
DECLARE
    types text[];
    view_record record;
BEGIN
    SELECT array_agg(format_type(a.atttypid, a.atttypmod) ORDER BY a.attname)
    INTO types
    FROM pg_attribute a
    WHERE a.attrelid = 'garmin_activities.steps_activities'::regclass
      AND a.attname IN ('avg_steps_per_min', 'max_steps_per_min') AND NOT a.attisdropped;
    IF types = ARRAY['double precision', 'double precision'] THEN
        RETURN;
    END IF;
    IF types IS DISTINCT FROM ARRAY['integer', 'integer'] THEN
        RAISE EXCEPTION 'Unexpected cadence column types: %', types;
    END IF;

    FOR view_record IN
        SELECT c.oid, c.relname, c.relowner, c.relacl, c.reloptions,
               obj_description(c.oid) AS description
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'garmin_activities' AND c.relkind = 'v'
          AND c.relname IN ('hiking_activities_view', 'running_activities_view',
                            'steps_activities_view', 'walking_activities_view')
    LOOP
        IF view_record.relowner <> (SELECT usesysid FROM pg_user WHERE usename = current_user)
           OR view_record.relacl IS NOT NULL OR view_record.reloptions IS NOT NULL
           OR view_record.description IS NOT NULL
           OR EXISTS (SELECT 1 FROM pg_trigger t WHERE t.tgrelid = view_record.oid AND NOT t.tgisinternal)
           OR EXISTS (SELECT 1 FROM pg_rewrite r WHERE r.ev_class = view_record.oid AND r.rulename <> '_RETURN')
           OR EXISTS (SELECT 1 FROM pg_seclabel s WHERE s.objoid = view_record.oid AND s.classoid = 'pg_class'::regclass)
           OR EXISTS (SELECT 1 FROM pg_attribute a
                      WHERE a.attrelid = view_record.oid AND a.attnum > 0
                        AND (a.attacl IS NOT NULL OR col_description(a.attrelid, a.attnum) IS NOT NULL)) THEN
            RAISE EXCEPTION 'View % has metadata requiring manual migration', view_record.relname;
        END IF;
        INSERT INTO cadence_migration_views VALUES
            (view_record.relname, pg_get_viewdef(view_record.oid, true));
    END LOOP;
    IF (SELECT count(*) FROM cadence_migration_views) <> 4 THEN
        RAISE EXCEPTION 'Expected four cadence views';
    END IF;

    FOR view_record IN SELECT * FROM cadence_migration_views LOOP
        EXECUTE format('DROP VIEW garmin_activities.%I', view_record.name);
    END LOOP;
    ALTER TABLE garmin_activities.steps_activities
        ALTER COLUMN avg_steps_per_min TYPE double precision,
        ALTER COLUMN max_steps_per_min TYPE double precision;
    FOR view_record IN SELECT * FROM cadence_migration_views LOOP
        EXECUTE format('CREATE VIEW garmin_activities.%I AS %s', view_record.name, view_record.definition);
        IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                   WHERE n.nspname = 'garmin_activities' AND c.relname = view_record.name
                     AND c.relacl IS NOT NULL) THEN
            RAISE EXCEPTION 'Default privileges would change access to view %', view_record.name;
        END IF;
    END LOOP;
END $$;
COMMIT;
