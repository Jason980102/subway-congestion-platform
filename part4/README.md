# Part IV - End-to-End Database Application

## What is implemented

- PostgreSQL schema and SQLAlchemy ORM mappings for `STATION`, `RIDERSHIP`, `PREDICTION`, `RECOMMENDATION`, and `USER_DECISION`
- Repeat-safe ETL and validation for 11,667 hourly observations
- Persisted Random Forest production model using Joblib
- Database-driven candidate-model retraining with a chronological train/test split
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

## Run the application

From the `part4` directory:

```powershell
python test_connection.py
python load_data.py
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
- `prediction_service.py` - feature creation, inference, and prediction write
- `recommendation_service.py` - recommendation generation and write
- `user_decision_service.py` - commuter decision write
- `train_model.py` - database-driven retraining

## Demonstrated result

The documented future request for 8 St-NYU at 6:00 PM on September 1, 2026 produced Medium congestion at 65.0% confidence, generated a 15-minute-delay recommendation, and saved an Accepted user decision.
