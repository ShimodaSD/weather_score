# Graph Report - murre  (2026-10-28)

## Corpus Check
- 238 files · ~220,035 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 51 file(s) not represented in the graph (top: .csv 37, (none) 9, .example 2)

## Summary
- 2056 nodes · 3376 edges · 177 communities (107 shown, 70 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 65 edges (avg confidence: 0.88)
- Token cost: unavailable (worker usage not exposed; stored zero values are placeholders)

## Community Hubs (Navigation)
- UI Dataset Quality
- Garmin Download Progress
- UI Accessibility Guidelines
- Database Initialization
- Behavioral Design Principles
- Docker Service Configuration
- Garmin Prediction Routes
- Design System Persistence
- Customer Activation Strategy
- Design Search Internals
- Run Grade Routes
- Activity TSS Client
- Accessible Color Palettes
- Platform Guidance Tests
- Garmin Data Import
- Activities Dashboard
- Garmin Database Schema
- Pricing Strategy
- Design Search Contracts
- Activity Detail Routes
- Customer Retention Strategy
- Product Feature Discipline
- API Application Lifecycle
- Activity Route Grading
- Product Positioning Strategy
- API Integration Tests
- Chart Design Guidelines
- BM25 Search Ranking
- Frontend Package Tooling
- Activity Index Routes
- Run Grade Equations
- Review Notification Workflow
- Activity API Tests
- Profile Route Composition
- Design Output Formatting
- Activity Chart Conversion
- Design Domain Detection
- Authentication Sessions
- Run Suitability Grading
- Design Recommendation Generator
- Authentication API Client
- Weather Provider Tests
- Weather Factor Penalties
- Conversion Landing Pages
- Training Stress Documentation
- Growth Experiment Metrics
- Design Recommendation Assembly
- Design Catalog Validation
- Running Prediction Evidence
- Training Stress Tests
- AI Product Differentiation
- Market Positioning Principles
- TypeScript Compiler Configuration
- Weekly Training Aggregation
- Repository Agent Guide
- Weekly Training Chart
- WeatherAPI Provider Adapter
- Checkout Conversion Strategy
- Profile Persistence Tests
- Running Performance Predictions
- Run Grade Schemas
- Design Decision Grammar
- Run Grade Tests
- Activity API Documentation
- Activity Grade Persistence
- Design Reasoning Matching
- Garmin Sync Documentation
- SaaS Hero Structure
- Actionable Dashboard Design
- Revenue Design Skill
- Theme Advice Filtering
- Search Quality Gates
- Dashboard Browser Tests
- Webhook Notification Security
- Humidity Penalty Tests
- Customer Awareness Stages
- Workshop Setup Checklist
- Workshop AI Assistant
- Data Storytelling Process
- Waterproofing Landing Page
- Attention Research Screenshot
- Hotel Scarcity Design
- Style Identity Contracts
- Landing Dataset Contracts
- Text Layout Contracts
- PostgreSQL Schema Snapshots
- Product Checkout Example
- Workshop Revenue Dashboard
- Confidence Knowledge Curve
- Destructive Action Design
- Game Design Illustration
- Pricing Choice Overload
- Welcome Video Modal
- Workshop Onboarding Cards
- Smart Alert Tooltip
- Dashboard Error Illustration
- Sales Analytics Dashboard
- Search Metric Tests
- Temperature Penalty Tests
- Wind Penalty Tests
- Minimal Development Rules
- CRM Landing Comparison
- Musician Bat Illustration
- Demographic Persona Comparison
- Space Dog Illustration
- Checkout Analysis Paralysis
- Decoy Pricing Plans
- Country Indicator Framing
- Country Comparison Framing
- Neighborhood Celebration Illustration
- Revenue Goal Onboarding
- Workshop Specialty Selection
- Guided Product Tour
- Dashboard Preparation Feedback
- Travel Health Landing
- Dashboard Visual Hierarchy
- Real Estate Billboard
- Product Bundle Offer
- Search Fixture Validation
- Dollar Price Tag
- Historical Dashboard Illustration
- Application Database Schema
- Implementation Documentation
- Product Originality Critique
- Automotive Design Comparison
- Reservation Goal Gradient
- Pricing Serial Position
- Financial Overview Dashboard
- Profitability Chart Examples
- Geographic Distribution Chart
- Financial Health Charts
- Feature Complexity Tradeoff
- Landing Page Comparison
- Marketing Prioritization Framework
- Creator Progress Feedback
- Keyboard Shortcut Onboarding
- Time To Value
- Typography Visual Hierarchy
- First Order Celebration
- Plain Language Contracts
- Simplified Login Choices
- Customer Identity Onboarding
- Sequential Setup Checklist
- Customer Testimonial Wall
- Feature Complexity Diagram
- Consent Default Effects
- Impact Effort Prioritization
- Subscription Choice Framing
- Sports Concept Design
- Delivery Vehicle Concept
- Compact Vehicle Concept
- Inventory Landing Section
- Accumulated Journey Friction
- Account Creation Video
- Market Size Segments
- Retention Growth Chart
- Monthly Subscription Tiers
- Launch Scale Pricing
- One Time Pricing
- Pull Request Template
- API Docker Setup
- Wind Score Favicon
- Garmin Database Bootstrap
- Function Naming Convention
- Web Application Guide
- Root Package Metadata
- Wind Score Overview

## God Nodes (most connected - your core abstractions)
1. `ui-ux-pro-max` - 52 edges
2. `Conversion & Landing Pages` - 50 edges
3. `search()` - 43 edges
4. `Onboarding & Activation` - 40 edges
5. `search_stack()` - 35 edges
6. `DesignSystemGenerator` - 35 edges
7. `Pricing & Monetization Psychology` - 29 edges
8. `Activities()` - 26 edges
9. `Churn & Retention` - 26 edges
10. `Product Strategy & Feature Discipline` - 26 edges

## Surprising Connections (you probably didn't know these)
- `test_sync_status_reports_only_counters()` --calls--> `GarminSyncProgress`  [EXTRACTED]
  tests/api/test_activities.py → apps/api/schemas/activity.py
- `grade_run_at_address()` --uses--> `RunGrade`  [INFERRED]
  apps/api/services/scoring.py → src/weather_score/application/run_grade.py
- `test_processor_grades_each_200_metres_and_persists_average()` --uses--> `HistoricalConditions`  [INFERRED]
  tests/api/test_activity_grades.py → src/weather_score/weather/providers/weather_api.py
- `get_weekly_tss()` --calls--> `calculate_tss_total()`  [EXTRACTED]
  apps/api/routes/garmin.py → src/weather_score/application/training_stress.py
- `get_weekly_training()` --calls--> `calculate_weekly_training()`  [EXTRACTED]
  apps/api/routes/garmin.py → src/weather_score/application/weekly_training.py

## Import Cycles
- None detected.

## Communities (177 total, 70 thin omitted)

### Community 0 - "UI Dataset Quality"
Cohesion: 0.07
Nodes (44): read_rows(), TestAccessibilityGuidance, TestChartsTypographyAndIcons, TestCurrentReactGuidance, TestSemanticColors, TestGeneratedCatalogContract, _catalog_date(), _check_app_interface_contract() (+36 more)

### Community 1 - "Garmin Download Progress"
Cohesion: 0.06
Nodes (38): install_download_progress(), fetch_activities(), fetch_summaries(), print_progress(), record_download(), save_binary_file(), save_json_file(), main() (+30 more)

### Community 2 - "UI Accessibility Guidelines"
Cohesion: 0.04
Nodes (53): 10. Charts & Data (LOW), 1. Accessibility (CRITICAL), 2. Touch & Interaction (CRITICAL), 3. Performance (HIGH), 4. Style Selection (HIGH), 5. Layout & Responsive (HIGH), 6. Typography & Color (MEDIUM), 7. Animation (MEDIUM) (+45 more)

### Community 3 - "Database Initialization"
Cohesion: 0.09
Nodes (35): initialize_databases(), _bootstrap_database(), _fail_sync(), _fetch_tss_threshold(), _get_garmin_config(), _get_postgres_parameters(), _import_postgres(), _initialize_postgres_tables() (+27 more)

### Community 4 - "Behavioral Design Principles"
Cohesion: 0.04
Nodes (27): @richardrx · 2025-11-04, @richardrx · 2025-11-07, @richardrx · 2025-11-10, @richardrx · 2025-12-19, @richardrx · 2026-01-02, @richardrx · 2026-01-14, @richardrx · 2026-02-05, @richardrx · 2026-02-09 (+19 more)

### Community 5 - "Docker Service Configuration"
Cohesion: 0.04
Nodes (48): build, command, depends_on, env_file, environment, image, ports, volumes (+40 more)

### Community 6 - "Garmin Prediction Routes"
Cohesion: 0.07
Nodes (16): fetch_running_prediction_inputs(), get_garmin_sync_status(), get_running_predictions(), require_activity_database(), ActivityDetailResponse, ActivityIndexResponse, ActivityResponse, ActivityTssResponse (+8 more)

### Community 7 - "Design System Persistence"
Cohesion: 0.09
Nodes (9): _detect_page_type(), format_master_md(), format_page_override_md(), _generate_intelligent_overrides(), persist_design_system(), safe_slug(), _write_persisted_file(), read_rows() (+1 more)

### Community 8 - "Customer Activation Strategy"
Cohesion: 0.05
Nodes (21): @richardrx · 2026-02-04, @richardrx · 2026-03-13, @richardrx · 2026-03-24, @richardrx · 2026-03-26, @richardrx · 2026-03-27, @richardrx · 2026-04-04, @richardrx · 2026-04-10, @richardrx · 2026-04-16 (+13 more)

### Community 9 - "Design Search Internals"
Cohesion: 0.07
Nodes (21): _contains_phrase(), _exact_match_diagnostic(), _exact_row_identity(), _exact_stack_identifier(), _file_signature(), _legacy_successor_guidance(), _load_csv_snapshot(), _normalize() (+13 more)

### Community 10 - "Run Grade Routes"
Cohesion: 0.11
Nodes (11): grade_run(), score_run(), CoordinatesResponse, ErrorResponse, LocationOption, LocationOptionsResponse, geocode_address(), grade_run_at_address() (+3 more)

### Community 11 - "Activity TSS Client"
Cohesion: 0.12
Nodes (32): ActivityTssPanel(), ActivityDetail, ActivityGradeSegment, activityNumbers, ActivityTss, AthleteProfile, fetchActivityDetail(), fetchActivityIndex() (+24 more)

### Community 12 - "Accessible Color Palettes"
Cohesion: 0.09
Nodes (11): _contrast_ratio(), _derive_dark_palette(), _palette_is_dark(), _query_wants_dark(), _relative_luminance(), _resolve_color_mode(), _select_palette_for_mode(), _style_is_dark_primary() (+3 more)

### Community 13 - "Platform Guidance Tests"
Cohesion: 0.10
Nodes (5): search_stack(), _rows(), TestNativeDesktopStackFreshness, _rows(), TestWebStackFreshness

### Community 14 - "Garmin Data Import"
Cohesion: 0.10
Nodes (13): _activity_id(), get_sync_progress(), _open_activities(), _postgres_row(), run_garmindb_sync(), sync_activities(), test_reads_garmindb_activities_in_batches(), test_rejects_activity_without_identifier() (+5 more)

### Community 15 - "Activities Dashboard"
Cohesion: 0.13
Nodes (27): Activities(), generateGrade(), gradeLabel(), loadGrades(), syncGarmin(), formatNumber(), Metric(), ActivityGradesPage() (+19 more)

### Community 16 - "Garmin Database Schema"
Cohesion: 0.12
Nodes (30): garmin_activities.activities, garmin_activities.activities_devices, garmin_activities.activity_laps, garmin_activities.activity_records, garmin_activities.activity_splits, garmin_activities._attributes, garmin_activities.climbing_activities, garmin_activities.climbing_activities_view (+22 more)

### Community 17 - "Pricing Strategy"
Cohesion: 0.07
Nodes (15): @richardrx · 2026-02-02, @richardrx · 2026-02-03, @richardrx · 2026-03-05, @richardrx · 2026-03-16, @richardrx · 2026-04-14, @richardrx · 2026-04-21, @richardrx · 2026-05-15, @richardrx · 2026-05-28 (+7 more)

### Community 18 - "Design Search Contracts"
Cohesion: 0.10
Nodes (5): search(), TestDiagnosticsContracts, TestSearchDomains, TestStyleTaxonomy, TestTextLayoutRetrieval

### Community 19 - "Activity Detail Routes"
Cohesion: 0.09
Nodes (10): fetch_activity(), fetch_activity_summary(), fetch_weekly_tss_inputs(), get_activity(), get_activity_summary(), get_activity_tss(), get_weekly_training(), get_weekly_tss() (+2 more)

### Community 20 - "Customer Retention Strategy"
Cohesion: 0.07
Nodes (14): @richardrx · 2025-12-17, @richardrx · 2026-01-30, @richardrx · 2026-03-19, @richardrx · 2026-03-27, @richardrx · 2026-04-08, @richardrx · 2026-04-23, @richardrx · 2026-04-24, @richardrx · 2026-04-29 (+6 more)

### Community 21 - "Product Feature Discipline"
Cohesion: 0.07
Nodes (14): @richardrx · 2025-11-03, @richardrx · 2026-03-11, @richardrx · 2026-03-17, @richardrx · 2026-03-18, @richardrx · 2026-04-01, @richardrx · 2026-05-20, @richardrx · 2026-05-26, @richardrx · 2026-07-02 (+6 more)

### Community 22 - "API Application Lifecycle"
Cohesion: 0.10
Nodes (6): create_app(), lifespan(), _database_url(), get_database_pool(), initialize_activity_grades(), initialize_profile()

### Community 23 - "Activity Route Grading"
Cohesion: 0.13
Nodes (16): ActivitySegment, build_activity_segments(), calculate_headwind_component(), calculate_outdoor_wbgt(), calculate_route_bearing(), _point(), record(), test_builds_one_segment_for_each_complete_200_metres() (+8 more)

### Community 24 - "Product Positioning Strategy"
Cohesion: 0.08
Nodes (13): @richardrx · 2026-02-13, @richardrx · 2026-02-25, @richardrx · 2026-03-04, @richardrx · 2026-03-24, @richardrx · 2026-03-30, @richardrx · 2026-04-06, @richardrx · 2026-05-05, @richardrx · 2026-05-12 (+5 more)

### Community 25 - "API Integration Tests"
Cohesion: 0.09
Nodes (7): response_with(), test_ambiguous_address_returns_options_without_fetching_weather(), test_grade_run_rejects_invalid_coordinates(), test_grade_run_rejects_invalid_pace_format(), test_startup_initializes_storage_and_closes_pools_on_failure(), test_unknown_address_returns_error(), test_unused_routes_are_removed()

### Community 26 - "Chart Design Guidelines"
Cohesion: 0.08
Nodes (25): Accessibility and responsive design, Accessibility Checklist, Accessibility Considerations, Avoid misleading visualization choices, Chart.js code patterns, Chart selection guide, Code review checklist, Color Blindness (+17 more)

### Community 27 - "BM25 Search Ranking"
Cohesion: 0.14
Nodes (5): BM25, _get_bm25(), _suggest_identities(), TestBm25CoreBehavior, TestTokenizer

### Community 28 - "Frontend Package Tooling"
Cohesion: 0.10
Nodes (23): devDependencies, @types/node@^24.0.0, @types/react@^19.2.0, @types/react-dom@^19.2.0, typescript@^5.9.0, vite@^7.3.0, engines, node (+15 more)

### Community 29 - "Activity Index Routes"
Cohesion: 0.10
Nodes (11): fetch_activity_index(), list_activity_grades(), list_activity_index(), start_activity_grade(), sync_garmin_activities(), _complete_activity_grade(), _fail_activity_grade(), fetch_activity_grades() (+3 more)

### Community 30 - "Run Grade Equations"
Cohesion: 0.08
Nodes (24): 1. Convert pace to running speed, 2. Calculate relative air speed, 3. Derive the wind coefficients, 4. Calculate wind-related metabolic change, 5. Calculate thermal performance loss, 6. Combine and bound the score, 7. Round response values, *Air speed and direction affect metabolic and
  thermoregulatory responses during walking and running in a temperate
  environment* (+16 more)

### Community 31 - "Review Notification Workflow"
Cohesion: 0.08
Nodes (23): GITHUB_EVENT_PATH, OPENBOT_WEBHOOK_SECRET, OPENBOT_WEBHOOK_URL, jobs, notify-openbot, name, if, runs-on (+15 more)

### Community 32 - "Activity API Tests"
Cohesion: 0.09
Nodes (6): test_activity_tss_missing_activity_or_data(), test_activity_tss_rejects_invalid_thresholds(), test_missing_garmin_tables_explain_first_import(), test_sync_status_reports_only_counters(), test_weekly_tss_calendar_boundaries_and_saved_threshold(), test_weekly_tss_query_includes_monday_and_excludes_next_monday()

### Community 33 - "Profile Route Composition"
Cohesion: 0.11
Nodes (5): update_profile(), service_status(), ProfileResponse, ProfileUpdate, save_profile()

### Community 34 - "Design Output Formatting"
Cohesion: 0.09
Nodes (8): ansi_ljust(), format_ascii_box(), format_markdown(), generate_design_system(), hex_to_ansi(), section_header(), format_output(), TestPersistence

### Community 35 - "Activity Chart Conversion"
Cohesion: 0.19
Nodes (19): formatDate(), formatDuration(), formatPace(), buildActivitySeries(), buildLapMarkers(), ChartPoint, MAX_PACE_MIN_PER_KM, MIN_PACE_MIN_PER_KM (+11 more)

### Community 36 - "Design Domain Detection"
Cohesion: 0.14
Nodes (6): detect_domain(), _domain_keywords(), _load_csv(), _load_product_keywords(), _load_rows_or_empty(), TestDomainDetection

### Community 37 - "Authentication Sessions"
Cohesion: 0.15
Nodes (6): authenticate_user(), get_session(), login(), logout(), require_access_token(), valid_session()

### Community 38 - "Run Suitability Grading"
Cohesion: 0.16
Nodes (13): grade_segment(), calculate_run_grade(), RunGrade, grade(), test_extreme_conditions_are_clamped_to_zero(), test_headwind_uses_pace_to_increase_relative_air_speed(), test_hot_and_cold_boundaries_use_published_slopes(), test_ideal_conditions_score_one_hundred() (+5 more)

### Community 40 - "Authentication API Client"
Cohesion: 0.20
Nodes (16): signIn(), base(), endSession(), fetchAccessToken(), fetchRunGrade(), fetchRunScore(), hasSession(), ActivityDetailPage (+8 more)

### Community 41 - "Weather Provider Tests"
Cohesion: 0.16
Nodes (12): test_propagates_http_errors(), test_propagates_invalid_json(), test_propagates_timeouts(), test_rejects_malformed_elevation(), test_returns_elevation(), test_propagates_provider_errors(), test_rejects_malformed_history(), test_rejects_malformed_weather() (+4 more)

### Community 42 - "Weather Factor Penalties"
Cohesion: 0.22
Nodes (12): calculate_activity_score(), calculate_altitude_penalty(), calculate_humidity_interaction_penalty(), calculate_rain_penalty(), calculate_temperature_penalty(), calculate_wind_penalty(), _number(), _weather_values() (+4 more)

### Community 43 - "Conversion Landing Pages"
Cohesion: 0.12
Nodes (9): @richardrx · 2026-02-28, @richardrx · 2026-03-23, @richardrx · 2026-04-20, @richardrx · 2026-04-26, @richardrx · 2026-05-04, @richardrx · 2026-05-19, @richardrx · 2026-06-02, @richardrx · 2026-06-25 (+1 more)

### Community 44 - "Training Stress Documentation"
Cohesion: 0.12
Nodes (16): Activity Training Stress Score, API and validation, Athlete profile, Author manuscript, average-HR estimation table, Five research sources, Formula and provenance, Functional threshold power (+8 more)

### Community 45 - "Growth Experiment Metrics"
Cohesion: 0.13
Nodes (8): @richardrx · 2026-01-20, @richardrx · 2026-01-22, @richardrx · 2026-02-18, @richardrx · 2026-03-02, @richardrx · 2026-04-29, @richardrx · 2026-05-22, @richardrx · 2026-06-04, Behavioral Science & Persuasion

### Community 46 - "Design Recommendation Assembly"
Cohesion: 0.20
Nodes (3): _resolve_dial(), read_rows(), TestReasoningContract

### Community 48 - "Running Prediction Evidence"
Cohesion: 0.13
Nodes (15): An empirical study of race times in recreational endurance runners (2016), PMID 27570626, Benchmark efforts, Data to provide for better running predictions, Emig–Peltonen performance model, Fill-in template, Held-out race validation, How to establish whether predictions improve, Human running performance from real-world big data (2020), PMID 33024098 (+7 more)

### Community 49 - "Training Stress Tests"
Cohesion: 0.33
Nodes (11): calculate_activity_tss(), test_cycling_rejects_missing_and_invalid_inputs(), test_cycling_rejects_zero_divisors_and_extreme_values(), test_cycling_threshold_duration_and_intensity(), test_heart_rate_estimate_duration_and_cycling_zones(), test_heart_rate_estimate_uses_threshold_zones(), test_heart_rate_rejects_invalid_missing_and_mixed_inputs(), test_running_rejects_missing_and_invalid_inputs() (+3 more)

### Community 50 - "AI Product Differentiation"
Cohesion: 0.14
Nodes (7): @richardrx · 2026-01-19, @richardrx · 2026-02-18, @richardrx · 2026-02-21, @richardrx · 2026-02-26, @richardrx · 2026-03-03, @richardrx · 2026-04-02, AI-Era Differentiation & Moats

### Community 51 - "Market Positioning Principles"
Cohesion: 0.15
Nodes (7): @richardrx · 2026-01-12, @richardrx · 2026-04-06, @richardrx · 2026-04-17, @richardrx · 2026-06-01, @richardrx · 2026-06-11, @richardrx · 2026-07-27, Metrics, Experimentation & Business Math

### Community 52 - "TypeScript Compiler Configuration"
Cohesion: 0.15
Nodes (12): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleResolution, noEmit, skipLibCheck (+4 more)

### Community 53 - "Weekly Training Aggregation"
Cohesion: 0.22
Nodes (4): calculate_tss_total(), _validate_number(), calculate_weekly_training(), test_weekly_training_combines_tss_but_separates_distance()

### Community 54 - "Repository Agent Guide"
Cohesion: 0.17
Nodes (12): Backend: FastAPI, Configuration and security, Definition of done, Frontend: React, Project overview, Python documentation convention, Repository structure, Review guidelines (+4 more)

### Community 55 - "Weekly Training Chart"
Cohesion: 0.20
Nodes (11): dependencies, chart.js@^4.5.1, react@^19.2.0, react-dom@^19.2.0, WeeklyTrainingChart, WeeklyTraining, weekLabel(), WeeklyTrainingChart() (+3 more)

### Community 56 - "WeatherAPI Provider Adapter"
Cohesion: 0.30
Nodes (7): _client(), fetch_current_weather(), fetch_historical_conditions(), HistoricalConditions, _number(), _optional_number(), _time()

### Community 57 - "Checkout Conversion Strategy"
Cohesion: 0.18
Nodes (6): @richardrx · 2025-12-09, @richardrx · 2025-12-12, @richardrx · 2025-12-23, @richardrx · 2026-06-29, @richardrx · 2026-08-12, Checkout & Forms (Conversion-Completion Layer)

### Community 59 - "Running Performance Predictions"
Cohesion: 0.31
Nodes (6): calculate_running_predictions(), _fit_model(), _predict_time(), test_inconsistent_or_invalid_efforts_do_not_claim_a_personal_fit(), test_predictions_fit_two_consistent_race_distance_efforts(), test_single_recent_benchmark_returns_bounded_ranges_not_fitted_times()

### Community 61 - "Design Decision Grammar"
Cohesion: 0.27
Nodes (4): apply_decision_rules(), _object_without_duplicates(), parse_decision_rules(), _validate_action()

### Community 62 - "Run Grade Tests"
Cohesion: 0.38
Nodes (6): conditions(), test_combines_all_penalties(), test_extreme_conditions_are_clamped_to_zero(), test_ideal_conditions_score_100(), test_inputs_are_not_modified(), test_rejects_missing_weather_or_altitude_values()

### Community 63 - "Activity API Documentation"
Cohesion: 0.22
Nodes (9): Activity API, Activity route grades, Emig–Peltonen performance model, GarminDB, Training Stress Score, WBGT, WeatherAPI History API, WeatherAPI's WBGT method (+1 more)

### Community 66 - "Garmin Sync Documentation"
Cohesion: 0.25
Nodes (8): Athlete profile, Docker Compose, Download progress, GarminDB, GarminDB sync, PostgreSQL, Running without Docker, Training Stress Score

### Community 67 - "SaaS Hero Structure"
Cohesion: 0.29
Nodes (7): Five second comprehension test, Headline, Primary CTA, SaaS hero section formula, Secondary CTA, Subheadline, Trust bar

### Community 68 - "Actionable Dashboard Design"
Cohesion: 0.29
Nodes (4): @richardrx · 2025-11-04, @richardrx · 2025-12-16, @richardrx · 2026-07-10, Dashboards & Data Visualization (Retention Surface)

### Community 69 - "Revenue Design Skill"
Cohesion: 0.29
Nodes (7): @richardrx, How to use it, Provenance, Reference library, Revenue-Centric Design, The spine: Revenue-Centric Design in 9 principles, Usage boundary (required)

### Community 73 - "Webhook Notification Security"
Cohesion: 0.29
Nodes (7): GitHub Actions, GitHub review event documentation, HMAC-SHA256, OpenBot webhook, OpenBot webhook contract, Pull-request notifications, Trusted default branch

### Community 74 - "Humidity Penalty Tests"
Cohesion: 0.43
Nodes (3): test_humidity_interaction_penalty(), test_humidity_penalty_rejects_invalid_humidity(), test_humidity_penalty_rejects_invalid_temperature()

### Community 75 - "Customer Awareness Stages"
Cohesion: 0.33
Nodes (6): Five stages of customer awareness, Most aware, Problem aware, Product aware, Solution aware, Unaware

### Community 76 - "Workshop Setup Checklist"
Cohesion: 0.33
Nodes (6): Employee registration, First work order, Legal information, RepareCar five step setup checklist, Service registration, Workshop address

### Community 77 - "Workshop AI Assistant"
Cohesion: 0.33
Nodes (6): AI assistant, Prompt input, RepareCar AI assistant start screen, Suggested finance prompts, Suggested management prompts, Suggested marketing prompts

### Community 78 - "Data Storytelling Process"
Cohesion: 0.33
Nodes (6): Data analysis, Data collection, Data preparation, Data storytelling, Data visualization, Raw data to actionable data diagram

### Community 79 - "Waterproofing Landing Page"
Cohesion: 0.33
Nodes (6): Basement waterproofing, DryShield Pro waterproofing landing page, Free inspection lead form, Trust statistics, Urgency countdown, Warranty claims

### Community 80 - "Attention Research Screenshot"
Cohesion: 0.33
Nodes (6): Attention network test, Executive control, Frontiers in Human Neuroscience, Mobile phone short video use negatively impacts attention functions: an EEG study, Self control, Short video attention EEG research screenshot

### Community 81 - "Hotel Scarcity Design"
Cohesion: 0.33
Nodes (6): Guest reviews, HF Fenix Urban Hotel, Hotel detail action, Lisbon hotel listing design, Nightly price, Two rooms remaining scarcity message

### Community 82 - "Style Identity Contracts"
Cohesion: 0.47
Nodes (3): split_values(), style_identities(), TestStyleIdentityContract

### Community 85 - "PostgreSQL Schema Snapshots"
Cohesion: 0.33
Nodes (6): Advisory lock, GarminDB, PostgreSQL, PostgreSQL schema initialization, Schema snapshots, Table inventory

### Community 86 - "Product Checkout Example"
Cohesion: 0.40
Nodes (5): Baralho de Vieses checkout, Customer information form, Customer testimonial, Order summary, Trust guarantees

### Community 87 - "Workshop Revenue Dashboard"
Cohesion: 0.40
Nodes (5): Revenue composition donut chart, Revenue history line chart, Revenue KPI, Service order navigation, Workshop revenue dashboard

### Community 88 - "Confidence Knowledge Curve"
Cohesion: 0.40
Nodes (5): Confidence, Confidence gap, Dunning Kruger confidence curve, Dunning Kruger effect, Knowledge

### Community 89 - "Destructive Action Design"
Cohesion: 0.40
Nodes (5): Destructive action button contrast, Low emphasis cancel action, Permanent file deletion dialog, Red primary delete button, Von Restorff effect

### Community 90 - "Game Design Illustration"
Cohesion: 0.40
Nodes (5): Compass, Game controller, Game design illustration, Game terrain, Pencil

### Community 91 - "Pricing Choice Overload"
Cohesion: 0.40
Nodes (5): Four pricing tiers, Hick law, High price anchor, Highlighted popular plan, Pricing choices and Hick law

### Community 92 - "Welcome Video Modal"
Cohesion: 0.40
Nodes (5): Account created confirmation, Next step action, RepareCar, RepareCar welcome video modal, Tutorial video

### Community 93 - "Workshop Onboarding Cards"
Cohesion: 0.40
Nodes (5): First work order, Mechanic registration, Service registration, Workshop information, Workshop setup onboarding cards

### Community 94 - "Smart Alert Tooltip"
Cohesion: 0.40
Nodes (5): Oil change reminder, RepareCar smart alerts tooltip, Smart alerts, Tutorial action, Workshop revenue

### Community 95 - "Dashboard Error Illustration"
Cohesion: 0.40
Nodes (5): 404 error, Business dashboard failure illustration, Business metrics, Payments, Red error symbol

### Community 96 - "Sales Analytics Dashboard"
Cohesion: 0.40
Nodes (5): Referral sources, Revenue KPI, Sales analytics dashboard, Sales trend chart, Salesperson comparison

### Community 100 - "Minimal Development Rules"
Cohesion: 0.50
Nodes (4): Before you write, Levels, Ponytail, The smallest complete change

### Community 101 - "CRM Landing Comparison"
Cohesion: 0.50
Nodes (4): Claimed 102.5 percent increase, Highrise CRM, Highrise landing page comparison, Person focused testimonial design

### Community 102 - "Musician Bat Illustration"
Cohesion: 0.50
Nodes (4): Black bat, Purple round glasses, Stylized musician and bat illustration, Yellow background

### Community 103 - "Demographic Persona Comparison"
Cohesion: 0.50
Nodes (4): King Charles, King Charles and Ozzy Osbourne comparison, Ozzy Osbourne, Shared demographic attributes

### Community 104 - "Space Dog Illustration"
Cohesion: 0.50
Nodes (4): Black hole, Dog in Soviet marked spacesuit, Space dog illustration, Yellow background

### Community 105 - "Checkout Analysis Paralysis"
Cohesion: 0.50
Nodes (4): Analysis paralysis, Analysis paralysis checkout guidance, Payment method choices, Smaller checkout stages

### Community 106 - "Decoy Pricing Plans"
Cohesion: 0.50
Nodes (4): Decoy effect, Decoy pricing comparison, Professional plan, Three pricing tiers

### Community 107 - "Country Indicator Framing"
Cohesion: 0.50
Nodes (4): Brazil, Paraguay, Paraguay and Brazil comparison table, Selectively highlighted indicators

### Community 108 - "Country Comparison Framing"
Cohesion: 0.50
Nodes (4): Brazil, Brazil and Paraguay comparison table, Paraguay, Selectively highlighted indicators

### Community 109 - "Neighborhood Celebration Illustration"
Cohesion: 0.50
Nodes (4): Houses, Neighborhood celebration illustration, Party decorations, Picnic table

### Community 110 - "Revenue Goal Onboarding"
Cohesion: 0.50
Nodes (4): Mobile onboarding, Primary goal selection, Revenue target slider, Workshop goal selection onboarding

### Community 111 - "Workshop Specialty Selection"
Cohesion: 0.50
Nodes (4): Progress indicator, RepareCar, Workshop specialty options, Workshop specialty selection

### Community 112 - "Guided Product Tour"
Cohesion: 0.50
Nodes (4): Home navigation tooltip, Next tutorial step, RepareCar guided product tour, Skip tutorial action

### Community 113 - "Dashboard Preparation Feedback"
Cohesion: 0.50
Nodes (4): Acknowledgement action, Dashboard preparation message, Dashboard preparation state, Future real workshop data

### Community 114 - "Travel Health Landing"
Cohesion: 0.50
Nodes (4): Consultation booking action, Social proof, Travel health landing page wireframe, Travel health services

### Community 115 - "Dashboard Visual Hierarchy"
Cohesion: 0.50
Nodes (4): Dashboard visual hierarchy comparison, F pattern layout, Larger primary metric, Top left priority

### Community 116 - "Real Estate Billboard"
Cohesion: 0.50
Nodes (4): Jill Biggs Group, Jill Biggs Group real estate billboard, List responsibly slogan, Sales volume comparison

### Community 117 - "Product Bundle Offer"
Cohesion: 0.50
Nodes (4): Baralho de Vieses offer redesign, Before and after product offer, Bundle emphasis, Claimed 68 percent AOV increase

### Community 120 - "Dollar Price Tag"
Cohesion: 0.67
Nodes (3): Dollar price tag illustration, Dollar symbol, Price tag

### Community 121 - "Historical Dashboard Illustration"
Cohesion: 0.67
Nodes (3): Historical dashboard illustration, Horse carriage, Protective dashboard panel

### Community 123 - "Implementation Documentation"
Cohesion: 0.67
Nodes (3): Implementation notes, Pace-aware run grade, Python documentation convention

## Knowledge Gaps
- **532 isolated node(s):** `weather_score`, `Core workflow`, `Chart selection guide`, `Avoid misleading visualization choices`, `Setup and reusable defaults` (+527 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1103 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **70 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BM25` connect `BM25 Search Ranking` to `Design Search Internals`, `Design System Persistence`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **What connects `weather_score`, `Core workflow`, `Chart selection guide` to the rest of the system?**
  _532 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `UI Dataset Quality` be split into smaller, more focused modules?**
  _Cohesion score 0.06583850931677018 - nodes in this community are weakly interconnected._
- **Why does `_filter_anti_patterns_for_mode()` connect `Theme Advice Filtering` to `Accessible Color Palettes`, `Design Recommendation Assembly`, `Design System Persistence`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Should `Garmin Download Progress` be split into smaller, more focused modules?**
  _Cohesion score 0.06060606060606061 - nodes in this community are weakly interconnected._
- **Why does `search_stack()` connect `Platform Guidance Tests` to `Design Output Formatting`, `Design Domain Detection`, `Design System Persistence`, `Design Search Internals`, `Design Search Contracts`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Should `UI Accessibility Guidelines` be split into smaller, more focused modules?**
  _Cohesion score 0.03773584905660377 - nodes in this community are weakly interconnected._
## Build limitations

- Token usage: unavailable. Zero token counts above are placeholders, not measured usage or cost.
- Video omitted: `.agents/skills/revenue-centric-design/assets/2024076972565963186__q__1.mp4` could not be transcribed because faster-whisper is unavailable.
- Sensitive file skipped: `apps/web/.env.development`.
- Integrity warning: 389 dangling-endpoint edges, 1 self-loop, and 104 same-endpoint edge collapses in the default undirected graph. The graph may be incomplete.
- Seven code files yielded no symbols; structural coverage is limited by the extractor.
- `graphify-out/` was written into the working tree and is currently untracked. Ignore it or commit only outputs the team should share.
- Benchmark estimates: 102,800 corpus words, approximately 137,066 naive tokens versus 1,630 average query tokens (84.1x reduction). These are heuristic retrieval estimates, not measured model token savings; detection counted 220,035 words.
