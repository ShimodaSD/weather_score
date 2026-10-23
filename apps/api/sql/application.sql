-- Schema-only snapshot of PostgreSQL 17 / GarminDB 3.9.0.
-- Existing objects and data are preserved; this is not a schema migration.

DO $schema$
BEGIN
CREATE TABLE public.activity_grades (
    activity_id text NOT NULL,
    status text NOT NULL,
    score double precision,
    segments jsonb DEFAULT '[]'::jsonb NOT NULL,
    error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    calculation_version integer DEFAULT 4 NOT NULL,
    CONSTRAINT activity_grades_score_check CHECK (((score >= (0)::double precision) AND (score <= (100)::double precision))),
    CONSTRAINT activity_grades_status_check CHECK ((status = ANY (ARRAY['processing'::text, 'complete'::text, 'failed'::text])))
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE public.athlete_profile (
    id smallint DEFAULT 1 NOT NULL,
    name text,
    threshold_heart_rate_bpm smallint DEFAULT 157 NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT athlete_profile_id_check CHECK ((id = 1)),
    CONSTRAINT athlete_profile_name_check CHECK (((name IS NULL) OR ((length(TRIM(BOTH FROM name)) >= 1) AND (length(TRIM(BOTH FROM name)) <= 100)))),
    CONSTRAINT athlete_profile_threshold_heart_rate_bpm_check CHECK (((threshold_heart_rate_bpm >= 30) AND (threshold_heart_rate_bpm <= 250)))
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'public.activity_grades'::regclass AND conname = 'activity_grades_pkey') THEN
ALTER TABLE ONLY public.activity_grades
    ADD CONSTRAINT activity_grades_pkey PRIMARY KEY (activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'public.athlete_profile'::regclass AND conname = 'athlete_profile_pkey') THEN
ALTER TABLE ONLY public.athlete_profile
    ADD CONSTRAINT athlete_profile_pkey PRIMARY KEY (id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;
