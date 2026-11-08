BEGIN;
SET LOCAL lock_timeout = '5s';
ALTER TABLE garmin_activities.activities ADD COLUMN IF NOT EXISTS import_fingerprint text;
ALTER TABLE public.athlete_profile ADD COLUMN IF NOT EXISTS tss_sync_key text;
COMMIT;
