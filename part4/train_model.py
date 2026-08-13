import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sqlalchemy import select

from database import SessionLocal
from models import Ridership, Station


FEATURES = [
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "station_complex_id",
    "transfers",
]
TARGET = "congestion_level"


def read_training_data() -> pd.DataFrame:
    statement = (
        select(
            Ridership.transit_timestamp,
            Ridership.hour,
            Ridership.day_of_week,
            Ridership.month,
            Ridership.is_weekend,
            Station.mta_complex_id.label("station_complex_id"),
            Ridership.transfers,
            Ridership.congestion_level,
        )
        .join(Station, Station.station_id == Ridership.station_id)
        .order_by(Ridership.transit_timestamp, Station.mta_complex_id)
    )

    with SessionLocal() as session:
        rows = session.execute(statement).mappings().all()

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError("RIDERSHIP contains no training data")

    required = ["transit_timestamp", *FEATURES, TARGET]
    if frame[required].isnull().any().any():
        null_counts = frame[required].isnull().sum()
        raise ValueError(f"Training data contains nulls:\n{null_counts}")

    frame["transit_timestamp"] = pd.to_datetime(frame["transit_timestamp"])
    frame["is_weekend"] = frame["is_weekend"].astype(int)
    frame["station_complex_id"] = frame["station_complex_id"].astype(int)
    frame["transfers"] = frame["transfers"].astype(float)
    return frame


def chronological_split(
    frame: pd.DataFrame,
    train_fraction: float = 0.8,
) -> tuple[pd.DataFrame, pd.DataFrame, datetime]:
    timestamps = frame["transit_timestamp"].drop_duplicates().sort_values()
    split_position = int(len(timestamps) * train_fraction)
    if split_position <= 0 or split_position >= len(timestamps):
        raise ValueError("Not enough timestamps for chronological train/test split")

    cutoff = timestamps.iloc[split_position]
    train_frame = frame[frame["transit_timestamp"] < cutoff].copy()
    test_frame = frame[frame["transit_timestamp"] >= cutoff].copy()

    if train_frame.empty or test_frame.empty:
        raise ValueError("Chronological split produced an empty dataset")
    return train_frame, test_frame, cutoff.to_pydatetime()


def train_and_save() -> None:
    frame = read_training_data()
    train_frame, test_frame, cutoff = chronological_split(frame)

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train_frame[FEATURES], train_frame[TARGET])

    predictions = model.predict(test_frame[FEATURES])
    accuracy = float(accuracy_score(test_frame[TARGET], predictions))
    labels = ["Low", "Medium", "High"]
    report = classification_report(
        test_frame[TARGET],
        predictions,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(
        test_frame[TARGET],
        predictions,
        labels=labels,
    ).tolist()

    trained_at = datetime.now(timezone.utc)
    version = trained_at.strftime("random_forest_%Y%m%d_%H%M%S_utc")
    artifact_directory = Path(__file__).resolve().parent / "artifacts"
    artifact_directory.mkdir(exist_ok=True)

    model_path = artifact_directory / "congestion_model_retrained.joblib"
    report_path = artifact_directory / "training_report.json"

    model_bundle = {
        "model": model,
        "features": FEATURES,
        "classes": model.classes_.tolist(),
        "accuracy": accuracy,
        "trained_at": trained_at.isoformat(),
        "model_version": version,
        "training_rows": len(train_frame),
        "test_rows": len(test_frame),
        "training_start": frame["transit_timestamp"].min().isoformat(),
        "training_end": frame["transit_timestamp"].max().isoformat(),
        "split_cutoff": cutoff.isoformat(),
    }
    joblib.dump(model_bundle, model_path)

    evaluation = {
        key: value for key, value in model_bundle.items() if key != "model"
    }
    evaluation["classification_report"] = report
    evaluation["confusion_matrix_labels"] = labels
    evaluation["confusion_matrix"] = matrix
    report_path.write_text(
        json.dumps(evaluation, indent=2),
        encoding="utf-8",
    )

    print(f"Database rows read: {len(frame):,}")
    print(f"Training rows: {len(train_frame):,}")
    print(f"Test rows: {len(test_frame):,}")
    print(f"Chronological split cutoff: {cutoff:%Y-%m-%d %H:%M}")
    print(f"Test accuracy: {accuracy:.4f}")
    print(f"Model saved: {model_path}")
    print(f"Evaluation saved: {report_path}")
    print("The current production model was not overwritten.")


if __name__ == "__main__":
    train_and_save()
