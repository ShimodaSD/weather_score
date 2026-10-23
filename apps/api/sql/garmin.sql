-- Schema-only snapshot of PostgreSQL 17 / GarminDB 3.9.0.
-- Existing objects and data are preserved; this is not a schema migration.

DO $schema$
BEGIN
CREATE SCHEMA garmin;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE SCHEMA garmin_activities;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TYPE garmin.batterystatus AS ENUM (
    'new',
    'good',
    'ok',
    'low',
    'critical',
    'charging',
    'unknown',
    'invalid'
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TYPE garmin.filetype AS ENUM (
    'fit_unknown0',
    'fit_device',
    'fit_settings',
    'fit_sport_settings',
    'fit_activity',
    'fit_workout',
    'fit_course',
    'fit_schedules',
    'fit_weight',
    'fit_totals',
    'fit_goals',
    'fit_blood_pressure',
    'fit_monitoring_a',
    'fit_activity_summary',
    'fit_monitoring_daily',
    'fit_records',
    'fit_monitoring_b',
    'fit_segment',
    'fit_segment_list',
    'fit_exd_configuration',
    'fit_metrics',
    'fit_sleep',
    'fit_unknown_file_type_64',
    'fit_hrv_status',
    'fit_manufacturer_range_start',
    'fit_invalid',
    'tcx',
    'gpx'
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TYPE garmin.manufacturer AS ENUM (
    'Garmin',
    'garmin_fr405_antfs',
    'zephyr',
    'dayton',
    'idt',
    'srm',
    'quarq',
    'ibike',
    'saris',
    'spark_hk',
    'tanita',
    'echowell',
    'Dynastream_OEM',
    'nautilus',
    'Dynastream',
    'timex',
    'metrigear',
    'xelic',
    'beurer',
    'cardiosport',
    'a_and_d',
    'hmm',
    'Suunto',
    'thita_elektronik',
    'gpulse',
    'clean_mobile',
    'pedal_brain',
    'peaksware',
    'saxonar',
    'lemond_fitness',
    'dexcom',
    'Wahoo_Fitness',
    'Octane_Fitness',
    'archinoetics',
    'the_hurt_box',
    'citizen_systems',
    'magellan',
    'osynce',
    'holux',
    'concept2',
    'shimano',
    'one_giant_leap',
    'ace_sensor',
    'brim_brothers',
    'Xplova',
    'perception_digital',
    'bf1systems',
    'pioneer',
    'spantec',
    'metalogics',
    '_4iiiis',
    'seiko_epson',
    'seiko_epson_oem',
    'ifor_powell',
    'maxwell_guider',
    'Star_Trac',
    'breakaway',
    'alatech_technology_ltd',
    'mio_technology_europe',
    'rotor',
    'geonaute',
    'id_bike',
    'Specialized',
    'wtek',
    'physical_enterprises',
    'north_pole_engineering',
    'bkool',
    'cateye',
    'stages_cycling',
    'sigmasport',
    'TomTom',
    'peripedal',
    'wattbike',
    'moxy',
    'ciclosport',
    'powerbahn',
    'acorn_projects_aps',
    'lifebeam',
    'Bontrager',
    'wellgo',
    'Scosche',
    'magura',
    'woodway',
    'elite',
    'nielsen_kellerman',
    'dk_city',
    'tacx',
    'direction_technology',
    'magtonic',
    'OnePartCarbon',
    'inside_ride_technologies',
    'sound_of_motion',
    'stryd',
    'icg',
    'MiPulse',
    'bsx_athletics',
    'look',
    'campagnolo_srl',
    'body_bike_smart',
    'praxisworks',
    'limits_technology',
    'topaction_technology',
    'cosinuss',
    'fitcare',
    'magene',
    'giant_manufacturing_co',
    'tigrasport',
    'salutron',
    'TechnoGym',
    'Bryton_Sensors',
    'Latitude_Limited',
    'Soaring_Technology',
    'IGPSport',
    'ThinkRider',
    'GopherSport',
    'WaterPower',
    'OrangeTheory',
    'Inpeak',
    'Kinetic',
    'Johnson_Health_Tech',
    'Polar_Electro',
    'Seesense',
    'NCI_Technology',
    'iqsquare',
    'leomo',
    'ifit_com',
    'coros_byte',
    'versa_design',
    'chileaf',
    'cycplus',
    'gravaa_byte',
    'sigeyi',
    'coospo',
    'geoid',
    'bosch',
    'kyto',
    'kinetic_sports',
    'decathlon_byte',
    'tq_systems',
    'tag_heuer',
    'keiser_fitness',
    'zwift_byte',
    'porsche_ep',
    'blackbird',
    'meilan_byte',
    'ezon',
    'laisi',
    'myzone',
    'abawo',
    'bafang',
    'luhong_technology',
    'Garmin_local_154',
    'Garmin_local_218',
    'development',
    'Health_and_Life',
    'lezyne',
    'scribe_labs',
    'zwift',
    'watteam',
    'recon',
    'favero_electronics',
    'dynovelo',
    'Strava',
    'precor',
    'bryton',
    'sram',
    'navman',
    'cobi',
    'spivi',
    'mio_magellan',
    'evesports',
    'sensitivus_gauge',
    'podoon',
    'Life_Time_Fitness',
    'falco_e_motors',
    'Minoura',
    'Cycliq',
    'Luxottica',
    'Trainer_Road',
    'The_Sufferest',
    'FullSpeedAhead',
    'VirtualTraining',
    'FeedbackSports',
    'Omata',
    'VDO',
    'MagneticDays',
    'Hammerhead',
    'Kinetic_By_Kurt',
    'Shapelog',
    'Dabuziduo',
    'JetBlack',
    'Coros',
    'virtugo',
    'velosense',
    'cycligentinc',
    'trailforks',
    'mahle_ebikemotion',
    'nurvv',
    'MicroProgram',
    'Zone5Cloud',
    'GreenTEG',
    'Yamaha_Motors',
    'Whoop',
    'GRAVAA',
    'OneLap',
    'Monark_Exercise',
    'Form',
    'Decathlon',
    'syncros',
    'heatup',
    'cannondale',
    'true_fitness',
    'rgt_cycling',
    'vasa',
    'race_republic',
    'fazua',
    'oreka_training',
    'lsec',
    'lululemon_studio',
    'shanyue',
    'spinning_mda',
    'hilldating',
    'aero_sensor',
    'nike',
    'magicshine',
    'ictrainer',
    'absolute_cycling',
    'eo_swimbetter',
    'mywhoosh',
    'ravemen',
    'tektro_racing_products',
    'darad_innovation_corporation',
    'cycloptim',
    'actigraphcorp',
    'Garmin_local',
    'Garmin_local_start',
    'unknown',
    'invalid',
    'Microsoft',
    'Unknown'
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TYPE garmin_activities.heartratezonesmethod AS ENUM (
    'custom',
    'max_heart_rate',
    'heart_rate_reserve',
    'lactate_threshhold'
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin._attributes (
    "timestamp" timestamp without time zone,
    key character varying NOT NULL,
    value character varying
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.attributes (
    "timestamp" timestamp without time zone,
    key character varying NOT NULL,
    value character varying
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.daily_summary (
    day timestamp without time zone NOT NULL,
    hr_min integer,
    hr_max integer,
    rhr integer,
    stress_avg integer,
    step_goal integer,
    steps integer,
    moderate_activity_time time without time zone NOT NULL,
    vigorous_activity_time time without time zone NOT NULL,
    intensity_time_goal time without time zone NOT NULL,
    floors_up double precision,
    floors_down double precision,
    floors_goal double precision,
    distance double precision,
    calories_goal integer,
    calories_total integer,
    calories_bmr integer,
    calories_active integer,
    calories_consumed integer,
    hydration_goal integer,
    hydration_intake integer,
    sweat_loss integer,
    spo2_avg double precision,
    spo2_min double precision,
    rr_waking_avg double precision,
    rr_max double precision,
    rr_min double precision,
    bb_charged integer,
    bb_max integer,
    bb_min integer,
    description character varying
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.device_info (
    "timestamp" timestamp without time zone NOT NULL,
    file_id character varying,
    serial_number bigint NOT NULL,
    software_version character varying,
    cum_operating_time time without time zone NOT NULL,
    battery_status garmin.batterystatus,
    battery_voltage double precision
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.devices (
    serial_number bigint NOT NULL,
    "timestamp" timestamp without time zone,
    device_type character varying,
    manufacturer garmin.manufacturer,
    product character varying,
    hardware_version character varying
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE VIEW garmin.device_info_view AS
 SELECT device_info."timestamp",
    device_info.file_id,
    device_info.serial_number,
    devices.device_type,
    device_info.software_version,
    devices.manufacturer,
    devices.product,
    devices.hardware_version,
    device_info.battery_status
   FROM (garmin.device_info
     JOIN garmin.devices ON ((devices.serial_number = device_info.serial_number)))
  ORDER BY device_info."timestamp" DESC;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE SEQUENCE garmin.devices_serial_number_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
ALTER SEQUENCE garmin.devices_serial_number_seq OWNED BY garmin.devices.serial_number;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.files (
    id character varying NOT NULL,
    name character varying,
    type garmin.filetype NOT NULL,
    serial_number bigint
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE VIEW garmin.files_view AS
 SELECT device_info."timestamp",
    files.id AS activity_id,
    files.name,
    files.type,
    devices.manufacturer,
    devices.product,
    devices.serial_number
   FROM ((garmin.files
     JOIN garmin.devices ON ((files.serial_number = devices.serial_number)))
     JOIN garmin.device_info ON (((files.id)::text = (device_info.file_id)::text)))
  ORDER BY device_info."timestamp" DESC;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.hrv (
    day timestamp without time zone NOT NULL,
    weekly_avg integer,
    last_night_avg integer,
    last_night_5min_high integer,
    baseline_low integer,
    baseline_upper integer,
    status character varying
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.resting_hr (
    day timestamp without time zone NOT NULL,
    resting_heart_rate double precision
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.sleep (
    day timestamp without time zone NOT NULL,
    start timestamp without time zone,
    "end" timestamp without time zone,
    total_sleep time without time zone NOT NULL,
    deep_sleep time without time zone NOT NULL,
    light_sleep time without time zone NOT NULL,
    rem_sleep time without time zone NOT NULL,
    awake time without time zone NOT NULL,
    avg_spo2 double precision,
    avg_rr double precision,
    avg_stress double precision,
    score integer,
    qualifier character varying
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.sleep_events (
    "timestamp" timestamp without time zone NOT NULL,
    event character varying,
    duration time without time zone NOT NULL
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.stress (
    "timestamp" timestamp without time zone NOT NULL,
    stress integer NOT NULL
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin.weight (
    day timestamp without time zone NOT NULL,
    weight double precision NOT NULL
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin_activities._attributes (
    "timestamp" timestamp without time zone,
    key character varying NOT NULL,
    value character varying
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin_activities.activities (
    activity_id character varying NOT NULL,
    name character varying,
    description character varying,
    type character varying,
    course_id integer,
    laps integer,
    sport character varying,
    sub_sport character varying,
    device_serial_number bigint,
    self_eval_feel character varying,
    self_eval_effort character varying,
    training_load double precision,
    training_effect double precision,
    anaerobic_training_effect double precision,
    start_time timestamp without time zone,
    stop_time timestamp without time zone,
    elapsed_time time without time zone NOT NULL,
    moving_time time without time zone NOT NULL,
    distance double precision,
    cycles double precision,
    avg_hr integer,
    max_hr integer,
    avg_rr double precision,
    max_rr double precision,
    calories integer,
    avg_cadence integer,
    max_cadence integer,
    avg_speed double precision,
    max_speed double precision,
    ascent double precision,
    descent double precision,
    max_temperature double precision,
    min_temperature double precision,
    avg_temperature double precision,
    start_lat double precision,
    start_long double precision,
    stop_lat double precision,
    stop_long double precision,
    hr_zones_method garmin_activities.heartratezonesmethod,
    hrz_1_hr integer,
    hrz_2_hr integer,
    hrz_3_hr integer,
    hrz_4_hr integer,
    hrz_5_hr integer,
    hrz_1_time time without time zone NOT NULL,
    hrz_2_time time without time zone NOT NULL,
    hrz_3_time time without time zone NOT NULL,
    hrz_4_time time without time zone NOT NULL,
    hrz_5_time time without time zone NOT NULL,
    tss double precision
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin_activities.activities_devices (
    activity_id character varying NOT NULL,
    device_serial_number bigint NOT NULL
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin_activities.activity_laps (
    activity_id character varying NOT NULL,
    lap integer NOT NULL,
    start_time timestamp without time zone,
    stop_time timestamp without time zone,
    elapsed_time time without time zone NOT NULL,
    moving_time time without time zone NOT NULL,
    distance double precision,
    cycles double precision,
    avg_hr integer,
    max_hr integer,
    avg_rr double precision,
    max_rr double precision,
    calories integer,
    avg_cadence integer,
    max_cadence integer,
    avg_speed double precision,
    max_speed double precision,
    ascent double precision,
    descent double precision,
    max_temperature double precision,
    min_temperature double precision,
    avg_temperature double precision,
    start_lat double precision,
    start_long double precision,
    stop_lat double precision,
    stop_long double precision,
    hr_zones_method garmin_activities.heartratezonesmethod,
    hrz_1_hr integer,
    hrz_2_hr integer,
    hrz_3_hr integer,
    hrz_4_hr integer,
    hrz_5_hr integer,
    hrz_1_time time without time zone NOT NULL,
    hrz_2_time time without time zone NOT NULL,
    hrz_3_time time without time zone NOT NULL,
    hrz_4_time time without time zone NOT NULL,
    hrz_5_time time without time zone NOT NULL
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin_activities.activity_records (
    activity_id character varying NOT NULL,
    record integer NOT NULL,
    "timestamp" timestamp without time zone,
    position_lat double precision,
    position_long double precision,
    distance double precision,
    cadence integer,
    altitude double precision,
    hr integer,
    rr double precision,
    speed double precision,
    temperature double precision
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin_activities.activity_splits (
    activity_id character varying NOT NULL,
    split integer NOT NULL,
    grade character varying,
    completed boolean,
    falls integer,
    start_time timestamp without time zone,
    stop_time timestamp without time zone,
    elapsed_time time without time zone NOT NULL,
    moving_time time without time zone NOT NULL,
    distance double precision,
    cycles double precision,
    avg_hr integer,
    max_hr integer,
    avg_rr double precision,
    max_rr double precision,
    calories integer,
    avg_cadence integer,
    max_cadence integer,
    avg_speed double precision,
    max_speed double precision,
    ascent double precision,
    descent double precision,
    max_temperature double precision,
    min_temperature double precision,
    avg_temperature double precision,
    start_lat double precision,
    start_long double precision,
    stop_lat double precision,
    stop_long double precision,
    hr_zones_method garmin_activities.heartratezonesmethod,
    hrz_1_hr integer,
    hrz_2_hr integer,
    hrz_3_hr integer,
    hrz_4_hr integer,
    hrz_5_hr integer,
    hrz_1_time time without time zone NOT NULL,
    hrz_2_time time without time zone NOT NULL,
    hrz_3_time time without time zone NOT NULL,
    hrz_4_time time without time zone NOT NULL,
    hrz_5_time time without time zone NOT NULL
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin_activities.climbing_activities (
    total_routes integer,
    activity_id character varying NOT NULL
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE VIEW garmin_activities.climbing_activities_view AS
 SELECT activities.activity_id,
    activities.name,
    activities.description,
    activities.sub_sport,
    activities.start_time,
    activities.stop_time,
    activities.elapsed_time,
    activities.moving_time,
    activities.avg_hr,
    activities.max_hr,
    activities.calories,
    activities.ascent,
    activities.descent,
    climbing_activities.total_routes,
    activities.training_effect,
    activities.anaerobic_training_effect,
    activities.hrz_1_time AS heart_rate_zone_one_time,
    activities.hrz_2_time AS heart_rate_zone_two_time,
    activities.hrz_3_time AS heart_rate_zone_three_time,
    activities.hrz_4_time AS heart_rate_zone_four_time,
    activities.hrz_5_time AS heart_rate_zone_five_time
   FROM (garmin_activities.climbing_activities
     JOIN garmin_activities.activities ON (((activities.activity_id)::text = (climbing_activities.activity_id)::text)))
  ORDER BY activities.start_time DESC;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin_activities.cycle_activities (
    strokes integer,
    vo2_max double precision,
    activity_id character varying NOT NULL
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE VIEW garmin_activities.cycle_activities_view AS
 SELECT activities.activity_id,
    activities.name,
    activities.description,
    activities.sub_sport,
    activities.start_time,
    activities.stop_time,
    activities.elapsed_time,
    round((activities.distance)::numeric, 1) AS distance,
    cycle_activities.strokes,
    activities.avg_hr,
    activities.max_hr,
    activities.avg_rr,
    activities.max_rr,
    activities.calories,
    round((activities.avg_temperature)::numeric, 1) AS avg_temperature,
    activities.avg_cadence AS avg_rpms,
    activities.max_cadence AS max_rpms,
    round((activities.avg_speed)::numeric, 1) AS avg_speed,
    round((activities.max_speed)::numeric, 1) AS max_speed,
    cycle_activities.vo2_max,
    activities.training_effect,
    activities.anaerobic_training_effect,
    activities.hrz_1_time AS heart_rate_zone_one_time,
    activities.hrz_2_time AS heart_rate_zone_two_time,
    activities.hrz_3_time AS heart_rate_zone_three_time,
    activities.hrz_4_time AS heart_rate_zone_four_time,
    activities.hrz_5_time AS heart_rate_zone_five_time,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.start_lat) || ','::text) || activities.start_long) || '&z=13'::text) AS start_loc,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.stop_lat) || ','::text) || activities.stop_long) || '&z=13'::text) AS stop_loc
   FROM (garmin_activities.cycle_activities
     JOIN garmin_activities.activities ON (((activities.activity_id)::text = (cycle_activities.activity_id)::text)))
  ORDER BY activities.start_time DESC;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin_activities.steps_activities (
    steps integer,
    avg_pace time without time zone NOT NULL,
    avg_moving_pace time without time zone NOT NULL,
    max_pace time without time zone NOT NULL,
    avg_steps_per_min integer,
    max_steps_per_min integer,
    avg_step_length double precision,
    avg_vertical_ratio double precision,
    avg_vertical_oscillation double precision,
    avg_gct_balance double precision,
    avg_ground_contact_time time without time zone NOT NULL,
    avg_stance_time_percent double precision,
    vo2_max double precision,
    activity_id character varying NOT NULL
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE VIEW garmin_activities.hiking_activities_view AS
 SELECT activities.activity_id,
    activities.name,
    activities.description,
    activities.start_time,
    activities.stop_time,
    activities.elapsed_time,
    round((activities.distance)::numeric, 1) AS distance,
    steps_activities.steps,
    steps_activities.avg_pace,
    steps_activities.avg_moving_pace,
    steps_activities.max_pace,
    round((steps_activities.avg_steps_per_min)::numeric, 1) AS avg_steps_per_min,
    round((steps_activities.max_steps_per_min)::numeric, 1) AS max_steps_per_min,
    activities.avg_hr,
    activities.max_hr,
    activities.calories,
    round((activities.avg_temperature)::numeric, 1) AS avg_temperature,
    round((activities.avg_speed)::numeric, 1) AS avg_speed,
    round((activities.max_speed)::numeric, 1) AS max_speed,
    round((steps_activities.avg_step_length)::numeric, 1) AS avg_step_length,
    steps_activities.vo2_max,
    activities.training_effect,
    activities.anaerobic_training_effect,
    activities.hrz_1_time AS heart_rate_zone_one_time,
    activities.hrz_2_time AS heart_rate_zone_two_time,
    activities.hrz_3_time AS heart_rate_zone_three_time,
    activities.hrz_4_time AS heart_rate_zone_four_time,
    activities.hrz_5_time AS heart_rate_zone_five_time,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.start_lat) || ','::text) || activities.start_long) || '&z=13'::text) AS start_loc,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.stop_lat) || ','::text) || activities.stop_long) || '&z=13'::text) AS stop_loc
   FROM (garmin_activities.steps_activities
     JOIN garmin_activities.activities ON (((activities.activity_id)::text = (steps_activities.activity_id)::text)))
  WHERE ((activities.sport)::text = 'hiking'::text)
  ORDER BY activities.start_time DESC;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE TABLE garmin_activities.paddle_activities (
    strokes integer,
    avg_stroke_distance double precision,
    activity_id character varying NOT NULL
);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE VIEW garmin_activities.paddle_activities_view AS
 SELECT activities.activity_id,
    activities.name,
    activities.description,
    activities.sport,
    activities.sub_sport,
    activities.start_time,
    activities.stop_time,
    activities.elapsed_time,
    round((activities.distance)::numeric, 1) AS distance,
    paddle_activities.strokes,
    round((paddle_activities.avg_stroke_distance)::numeric, 1) AS avg_stroke_distance,
    activities.avg_cadence,
    activities.max_cadence,
    activities.avg_hr,
    activities.max_hr,
    round((activities.calories)::numeric, 1) AS calories,
    round((activities.avg_temperature)::numeric, 1) AS avg_temperature,
    round((activities.avg_speed)::numeric, 1) AS avg_speed,
    round((activities.max_speed)::numeric, 1) AS max_speed,
    activities.training_effect,
    activities.anaerobic_training_effect,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.start_lat) || ','::text) || activities.start_long) || '&z=13'::text) AS start_loc,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.stop_lat) || ','::text) || activities.stop_long) || '&z=13'::text) AS stop_loc
   FROM (garmin_activities.paddle_activities
     JOIN garmin_activities.activities ON (((activities.activity_id)::text = (paddle_activities.activity_id)::text)))
  ORDER BY activities.start_time DESC;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE VIEW garmin_activities.running_activities_view AS
 SELECT activities.activity_id,
    activities.name,
    activities.description,
    activities.sub_sport,
    activities.course_id,
    activities.start_time,
    activities.stop_time,
    activities.elapsed_time,
    round((activities.distance)::numeric, 1) AS distance,
    steps_activities.steps,
    steps_activities.avg_pace,
    steps_activities.avg_moving_pace,
    steps_activities.max_pace,
    round((steps_activities.avg_steps_per_min)::numeric, 1) AS avg_steps_per_min,
    round((steps_activities.max_steps_per_min)::numeric, 1) AS max_steps_per_min,
    activities.avg_hr,
    activities.max_hr,
    activities.avg_rr,
    activities.max_rr,
    activities.calories,
    round((activities.avg_temperature)::numeric, 1) AS avg_temperature,
    round((activities.avg_speed)::numeric, 1) AS avg_speed,
    round((activities.max_speed)::numeric, 1) AS max_speed,
    round((steps_activities.avg_step_length)::numeric, 1) AS avg_step_length,
    round((steps_activities.avg_vertical_ratio)::numeric, 1) AS avg_vertical_ratio,
    steps_activities.avg_gct_balance,
    round((steps_activities.avg_vertical_oscillation)::numeric, 1) AS avg_vertical_oscillation,
    steps_activities.avg_ground_contact_time,
    steps_activities.avg_stance_time_percent,
    steps_activities.vo2_max,
    activities.training_effect,
    activities.anaerobic_training_effect,
    activities.hrz_1_time AS heart_rate_zone_one_time,
    activities.hrz_2_time AS heart_rate_zone_two_time,
    activities.hrz_3_time AS heart_rate_zone_three_time,
    activities.hrz_4_time AS heart_rate_zone_four_time,
    activities.hrz_5_time AS heart_rate_zone_five_time,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.start_lat) || ','::text) || activities.start_long) || '&z=13'::text) AS start_loc,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.stop_lat) || ','::text) || activities.stop_long) || '&z=13'::text) AS stop_loc
   FROM (garmin_activities.steps_activities
     JOIN garmin_activities.activities ON (((activities.activity_id)::text = (steps_activities.activity_id)::text)))
  WHERE ((activities.sport)::text = 'running'::text)
  ORDER BY activities.start_time DESC;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE VIEW garmin_activities.steps_activities_view AS
 SELECT activities.activity_id,
    activities.name,
    activities.description,
    activities.sport,
    activities.sub_sport,
    activities.type,
    activities.course_id,
    activities.start_time,
    activities.stop_time,
    activities.elapsed_time,
    round((activities.distance)::numeric, 1) AS distance,
    steps_activities.steps,
    steps_activities.avg_pace,
    steps_activities.avg_moving_pace,
    steps_activities.max_pace,
    round((steps_activities.avg_steps_per_min)::numeric, 1) AS avg_steps_per_min,
    round((steps_activities.max_steps_per_min)::numeric, 1) AS max_steps_per_min,
    activities.avg_hr,
    activities.max_hr,
    activities.calories,
    round((activities.avg_temperature)::numeric, 1) AS avg_temperature,
    round((activities.avg_speed)::numeric, 1) AS avg_speed,
    round((activities.max_speed)::numeric, 1) AS max_speed,
    round((steps_activities.avg_step_length)::numeric, 1) AS avg_step_length,
    steps_activities.vo2_max,
    activities.training_effect,
    activities.anaerobic_training_effect,
    activities.hrz_1_time AS heart_rate_zone_one_time,
    activities.hrz_2_time AS heart_rate_zone_two_time,
    activities.hrz_3_time AS heart_rate_zone_three_time,
    activities.hrz_4_time AS heart_rate_zone_four_time,
    activities.hrz_5_time AS heart_rate_zone_five_time,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.start_lat) || ','::text) || activities.start_long) || '&z=13'::text) AS start_loc,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.stop_lat) || ','::text) || activities.stop_long) || '&z=13'::text) AS stop_loc
   FROM (garmin_activities.steps_activities
     JOIN garmin_activities.activities ON (((activities.activity_id)::text = (steps_activities.activity_id)::text)))
  ORDER BY activities.start_time DESC;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
CREATE VIEW garmin_activities.walking_activities_view AS
 SELECT activities.activity_id,
    activities.name,
    activities.description,
    activities.start_time,
    activities.stop_time,
    activities.elapsed_time,
    round((activities.distance)::numeric, 1) AS distance,
    steps_activities.steps,
    steps_activities.avg_pace,
    steps_activities.avg_moving_pace,
    steps_activities.max_pace,
    round((steps_activities.avg_steps_per_min)::numeric, 1) AS avg_steps_per_min,
    round((steps_activities.max_steps_per_min)::numeric, 1) AS max_steps_per_min,
    activities.avg_hr,
    activities.max_hr,
    activities.calories,
    round((activities.avg_temperature)::numeric, 1) AS avg_temperature,
    round((activities.avg_speed)::numeric, 1) AS avg_speed,
    round((activities.max_speed)::numeric, 1) AS max_speed,
    round((steps_activities.avg_step_length)::numeric, 1) AS avg_step_length,
    steps_activities.vo2_max,
    activities.training_effect,
    activities.anaerobic_training_effect,
    activities.hrz_1_time AS heart_rate_zone_one_time,
    activities.hrz_2_time AS heart_rate_zone_two_time,
    activities.hrz_3_time AS heart_rate_zone_three_time,
    activities.hrz_4_time AS heart_rate_zone_four_time,
    activities.hrz_5_time AS heart_rate_zone_five_time,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.start_lat) || ','::text) || activities.start_long) || '&z=13'::text) AS start_loc,
    (((('http://maps.google.com/?ie=UTF8&q='::text || activities.stop_lat) || ','::text) || activities.stop_long) || '&z=13'::text) AS stop_loc
   FROM (garmin_activities.steps_activities
     JOIN garmin_activities.activities ON (((activities.activity_id)::text = (steps_activities.activity_id)::text)))
  WHERE ((activities.sport)::text = 'walking'::text)
  ORDER BY activities.start_time DESC;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
ALTER TABLE ONLY garmin.devices ALTER COLUMN serial_number SET DEFAULT nextval('garmin.devices_serial_number_seq'::regclass);
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin._attributes'::regclass AND conname = '_attributes_pkey') THEN
ALTER TABLE ONLY garmin._attributes
    ADD CONSTRAINT _attributes_pkey PRIMARY KEY (key);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.attributes'::regclass AND conname = 'attributes_pkey') THEN
ALTER TABLE ONLY garmin.attributes
    ADD CONSTRAINT attributes_pkey PRIMARY KEY (key);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.daily_summary'::regclass AND conname = 'daily_summary_pkey') THEN
ALTER TABLE ONLY garmin.daily_summary
    ADD CONSTRAINT daily_summary_pkey PRIMARY KEY (day);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.device_info'::regclass AND conname = 'device_info_pkey') THEN
ALTER TABLE ONLY garmin.device_info
    ADD CONSTRAINT device_info_pkey PRIMARY KEY ("timestamp", serial_number);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.devices'::regclass AND conname = 'devices_pkey') THEN
ALTER TABLE ONLY garmin.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (serial_number);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.files'::regclass AND conname = 'files_name_key') THEN
ALTER TABLE ONLY garmin.files
    ADD CONSTRAINT files_name_key UNIQUE (name);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.files'::regclass AND conname = 'files_pkey') THEN
ALTER TABLE ONLY garmin.files
    ADD CONSTRAINT files_pkey PRIMARY KEY (id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.hrv'::regclass AND conname = 'hrv_pkey') THEN
ALTER TABLE ONLY garmin.hrv
    ADD CONSTRAINT hrv_pkey PRIMARY KEY (day);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.resting_hr'::regclass AND conname = 'resting_hr_pkey') THEN
ALTER TABLE ONLY garmin.resting_hr
    ADD CONSTRAINT resting_hr_pkey PRIMARY KEY (day);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.sleep_events'::regclass AND conname = 'sleep_events_pkey') THEN
ALTER TABLE ONLY garmin.sleep_events
    ADD CONSTRAINT sleep_events_pkey PRIMARY KEY ("timestamp");
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.sleep'::regclass AND conname = 'sleep_pkey') THEN
ALTER TABLE ONLY garmin.sleep
    ADD CONSTRAINT sleep_pkey PRIMARY KEY (day);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.stress'::regclass AND conname = 'stress_pkey') THEN
ALTER TABLE ONLY garmin.stress
    ADD CONSTRAINT stress_pkey PRIMARY KEY ("timestamp");
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.weight'::regclass AND conname = 'weight_pkey') THEN
ALTER TABLE ONLY garmin.weight
    ADD CONSTRAINT weight_pkey PRIMARY KEY (day);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities._attributes'::regclass AND conname = '_attributes_pkey') THEN
ALTER TABLE ONLY garmin_activities._attributes
    ADD CONSTRAINT _attributes_pkey PRIMARY KEY (key);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.activities_devices'::regclass AND conname = 'activities_devices_pkey') THEN
ALTER TABLE ONLY garmin_activities.activities_devices
    ADD CONSTRAINT activities_devices_pkey PRIMARY KEY (activity_id, device_serial_number);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.activities'::regclass AND conname = 'activities_pkey') THEN
ALTER TABLE ONLY garmin_activities.activities
    ADD CONSTRAINT activities_pkey PRIMARY KEY (activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.activity_laps'::regclass AND conname = 'activity_laps_pkey') THEN
ALTER TABLE ONLY garmin_activities.activity_laps
    ADD CONSTRAINT activity_laps_pkey PRIMARY KEY (activity_id, lap);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.activity_records'::regclass AND conname = 'activity_records_pkey') THEN
ALTER TABLE ONLY garmin_activities.activity_records
    ADD CONSTRAINT activity_records_pkey PRIMARY KEY (activity_id, record);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.activity_splits'::regclass AND conname = 'activity_splits_pkey') THEN
ALTER TABLE ONLY garmin_activities.activity_splits
    ADD CONSTRAINT activity_splits_pkey PRIMARY KEY (activity_id, split);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.climbing_activities'::regclass AND conname = 'climbing_activities_pkey') THEN
ALTER TABLE ONLY garmin_activities.climbing_activities
    ADD CONSTRAINT climbing_activities_pkey PRIMARY KEY (activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.cycle_activities'::regclass AND conname = 'cycle_activities_pkey') THEN
ALTER TABLE ONLY garmin_activities.cycle_activities
    ADD CONSTRAINT cycle_activities_pkey PRIMARY KEY (activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.paddle_activities'::regclass AND conname = 'paddle_activities_pkey') THEN
ALTER TABLE ONLY garmin_activities.paddle_activities
    ADD CONSTRAINT paddle_activities_pkey PRIMARY KEY (activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.steps_activities'::regclass AND conname = 'steps_activities_pkey') THEN
ALTER TABLE ONLY garmin_activities.steps_activities
    ADD CONSTRAINT steps_activities_pkey PRIMARY KEY (activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.device_info'::regclass AND conname = 'device_info_file_id_fkey') THEN
ALTER TABLE ONLY garmin.device_info
    ADD CONSTRAINT device_info_file_id_fkey FOREIGN KEY (file_id) REFERENCES garmin.files(id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.device_info'::regclass AND conname = 'device_info_serial_number_fkey') THEN
ALTER TABLE ONLY garmin.device_info
    ADD CONSTRAINT device_info_serial_number_fkey FOREIGN KEY (serial_number) REFERENCES garmin.devices(serial_number);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin.files'::regclass AND conname = 'files_serial_number_fkey') THEN
ALTER TABLE ONLY garmin.files
    ADD CONSTRAINT files_serial_number_fkey FOREIGN KEY (serial_number) REFERENCES garmin.devices(serial_number);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.activity_laps'::regclass AND conname = 'activity_laps_activity_id_fkey') THEN
ALTER TABLE ONLY garmin_activities.activity_laps
    ADD CONSTRAINT activity_laps_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES garmin_activities.activities(activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.activity_records'::regclass AND conname = 'activity_records_activity_id_fkey') THEN
ALTER TABLE ONLY garmin_activities.activity_records
    ADD CONSTRAINT activity_records_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES garmin_activities.activities(activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.activity_splits'::regclass AND conname = 'activity_splits_activity_id_fkey') THEN
ALTER TABLE ONLY garmin_activities.activity_splits
    ADD CONSTRAINT activity_splits_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES garmin_activities.activities(activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.climbing_activities'::regclass AND conname = 'climbing_activities_activity_id_fkey') THEN
ALTER TABLE ONLY garmin_activities.climbing_activities
    ADD CONSTRAINT climbing_activities_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES garmin_activities.activities(activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.cycle_activities'::regclass AND conname = 'cycle_activities_activity_id_fkey') THEN
ALTER TABLE ONLY garmin_activities.cycle_activities
    ADD CONSTRAINT cycle_activities_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES garmin_activities.activities(activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.paddle_activities'::regclass AND conname = 'paddle_activities_activity_id_fkey') THEN
ALTER TABLE ONLY garmin_activities.paddle_activities
    ADD CONSTRAINT paddle_activities_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES garmin_activities.activities(activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;

DO $schema$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'garmin_activities.steps_activities'::regclass AND conname = 'steps_activities_activity_id_fkey') THEN
ALTER TABLE ONLY garmin_activities.steps_activities
    ADD CONSTRAINT steps_activities_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES garmin_activities.activities(activity_id);
END IF;
EXCEPTION WHEN duplicate_schema OR duplicate_table OR duplicate_object THEN
    NULL;
END
$schema$;
