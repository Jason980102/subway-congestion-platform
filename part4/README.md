# Part IV - End-to-End Database Application

## What is implemented

- PostgreSQL schema and SQLAlchemy ORM mappings for `STATION`, `RIDERSHIP`, `EVENT`, `PREDICTION`, `RECOMMENDATION`, and `USER_DECISION`
- Repeat-safe ETL and validation for 11,667 hourly observations
- Persisted Random Forest production model using Joblib
- Database-driven candidate-model retraining with a chronological train/test split
- One-command data maintenance pipeline with JSON audit logs
- Streamlit future congestion interface
- Rule-based recommendation generation
- User decision write-back
- PostgreSQL index and query-plan analysis

## Requirements

- Python 3.11 or compatible
- PostgreSQL running locally
- Database named `subway_congestion_db`

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env`, then replace only the local database password if the other defaults match your system.

```powershell
Copy-Item .env.example .env
```

The committed CSV and production model use repository-relative paths. The real `.env` is excluded from Git.

## Create or restore the PostgreSQL database

Create a PostgreSQL database named `subway_congestion_db`. From pgAdmin Query Tool, connect to that database and run these files in order:

1. `sql/subway_schema.sql` - creates the tables, keys, constraints, indexes, and materialized view.
2. `sql/station_seed.sql` - inserts the four NYU-area stations required by the application.

Then load the cleaned hourly ridership data:

```powershell
python load_data.py
```

The loader is repeat-safe, so running it again does not duplicate the same station/timestamp observations.

## Run the application

From the `part4` directory:

```powershell
python test_connection.py
python -m streamlit run app.py
```

Open `http://localhost:8501`, select a future date, station, and time, then save either `Accepted` or `Kept Original Plan`.

## Retrain a candidate model

```powershell
python train_model.py
```

Retraining reads PostgreSQL `RIDERSHIP` data, applies a chronological 80/20 split, and writes:

- `artifacts/congestion_model_retrained.joblib`
- `artifacts/training_report.json`

The candidate is evaluated separately and does not automatically replace the production model.

## Run the data maintenance pipeline

```powershell
python run_pipeline.py
```

The pipeline checks database connectivity and computes a SHA-256 fingerprint of the configured CSV. When the source changes, it validates and repeat-safely loads the data, retrains a candidate model with the chronological split, and verifies the final database row count. When the source is unchanged, ETL and retraining are skipped. Each run writes a timestamped JSON audit log under `artifacts/pipeline_runs/`. Use `python run_pipeline.py --force` for a deliberate full rerun. The production model is never promoted automatically.

### Schedule automatic source monitoring on Windows

Run PowerShell as the current user from the `part4` directory:

```powershell
powershell -ExecutionPolicy Bypass -File automation/install_pipeline_task.ps1
```

This creates a daily Windows Task Scheduler job named `SubwayCongestionPart4Pipeline`. It runs at 2:00 AM and invokes the change-aware pipeline. To remove it:

```powershell
powershell -ExecutionPolicy Bypass -File automation/remove_pipeline_task.ps1
```

The scheduler only launches the pipeline; source fingerprinting prevents unnecessary retraining. Task registration is an operational deployment step and is not required to inspect or run the repository manually.

## Database migration for model traceability

Existing databases must run `sql/migrations/001_add_prediction_model_version.sql`. New databases created from `sql/subway_schema.sql` already include the required `PREDICTION.model_version` column. Each new prediction now persists the Joblib bundle's model version.

To enable automatic official-event detection on an existing database, run
`sql/migrations/002_link_event_to_station.sql` and then
`sql/migrations/003_add_official_event_source_fields.sql`. Each scheduled
pipeline run queries NYC Open Data dataset `tvpp-9vvx`, keeps current Manhattan
events, maps recognizable NYU-area locations to one of the four supported
stations, and repeat-safely upserts them using the official Event ID.

The commuter enters only a station, future date, and time. The prediction
service automatically checks for a mapped event overlapping a two-hour window
around that request. The Random Forest produces the recurring-pattern baseline;
a transparent rule based on official event type and street-closure information
then applies zero, one, or two congestion-level uplifts, capped at High. The
interface labels the probability as baseline model confidence. This is an
auditable scenario adjustment and not a claim that the Random Forest learned a
causal event effect.

Every new prediction persists `baseline_congestion_level`,
`event_adjustment_levels`, and `event_adjustment_method` alongside the final
`congestion_level`. Existing databases must run
`sql/migrations/004_add_prediction_event_audit_fields.sql`. These fields make
the transformation (for example, Medium baseline + one-level event uplift =
High final result) reconstructable directly from PostgreSQL.

The official feed does not provide attendance or coordinates. The prototype
therefore uses a conservative, documented location-keyword mapping for the four
NYU-area stations. Unmapped Manhattan events are skipped and reported in the
pipeline audit log.

## Query optimization

```powershell
python analyze_queries.py
```

SQL and execution-plan evidence are stored in `sql/`, `artifacts/`, and `screenshots/`.

## Main files

- `app.py` - Streamlit interface
- `database.py` - engine and session management
- `models.py` - SQLAlchemy ORM models
- `load_data.py` - validation and ETL
- `event_service.py` - official NYC event synchronization, station mapping, and risk classification
- `prediction_service.py` - baseline inference, official-event adjustment, and prediction write
- `recommendation_service.py` - recommendation generation and write
- `user_decision_service.py` - commuter decision write
- `train_model.py` - database-driven retraining
- `run_pipeline.py` - orchestrated ETL, retraining, verification, and audit logging

## Project documentation

The final reports for all four project phases are available in `docs/`:

- `Jason_Chen_p1_su26.docx`
- `Jason_Chen_p2_su26.docx`
- `Jason_Chen_p3_su26.docx`
- `Jason_Chen_final-project_su26.docx`

The Part IV report contains the integrated workflow, implementation evidence, query-plan results, limitations, and updated reference architecture.

## Demonstrated result

The final documented request used W 4 St-Wash Sq at 3:00 PM on September 20, 2026. The application automatically matched the official Washington Square Park Folk Festival, recorded a Medium Random Forest baseline with 99.0% baseline confidence, applied a transparent one-level event uplift, produced final High congestion, generated Recommendation ID 27, and saved the commuter's Accepted response as Decision ID 9 under Prediction ID 28.
