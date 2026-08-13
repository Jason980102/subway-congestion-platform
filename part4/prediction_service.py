import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import func, select

from database import SessionLocal
from models import Prediction, Ridership, Station


load_dotenv()


@dataclass(frozen=True)
class PredictionResult:
    prediction_id: int
    station_id: int
    station_name: str
    prediction_time: datetime
    congestion_level: str
    confidence_score: float
    estimated_transfers: float
    model_version: str


def load_model_bundle() -> dict:
    model_setting = os.getenv("MODEL_PATH")
    if not model_setting:
        raise RuntimeError("Missing required setting: MODEL_PATH")

    model_path = Path(model_setting)
    if not model_path.is_file():
        raise FileNotFoundError(f"Model not found: {model_path}")

    bundle = joblib.load(model_path)
    required_keys = {"model", "features", "model_version"}
    if not isinstance(bundle, dict) or not required_keys.issubset(bundle):
        raise ValueError("The model artifact is not the expected model bundle")
    return bundle


def historical_average_transfers(session, station_id: int, when: datetime) -> float:
    exact_average = session.scalar(
        select(func.avg(Ridership.transfers)).where(
            Ridership.station_id == station_id,
            Ridership.hour == when.hour,
            Ridership.day_of_week == when.weekday(),
        )
    )
    if exact_average is not None:
        return float(exact_average)

    station_average = session.scalar(
        select(func.avg(Ridership.transfers)).where(
            Ridership.station_id == station_id
        )
    )
    return float(station_average or 0.0)


def predict_and_save(station_id: int, when: datetime) -> PredictionResult:
    bundle = load_model_bundle()
    model = bundle["model"]
    expected_features = list(bundle["features"])

    with SessionLocal.begin() as session:
        station = session.get(Station, station_id)
        if station is None:
            raise ValueError(f"Unknown station_id: {station_id}")
        if station.mta_complex_id is None:
            raise ValueError(f"Station {station_id} has no MTA complex ID")

        estimated_transfers = historical_average_transfers(session, station_id, when)
        feature_values = {
            "hour": when.hour,
            "day_of_week": when.weekday(),
            "month": when.month,
            "is_weekend": int(when.weekday() >= 5),
            "station_complex_id": station.mta_complex_id,
            "transfers": estimated_transfers,
        }
        feature_frame = pd.DataFrame([feature_values], columns=expected_features)

        predicted_level = str(model.predict(feature_frame)[0])
        probabilities = model.predict_proba(feature_frame)[0]
        confidence = float(max(probabilities))

        prediction = Prediction(
            station_id=station_id,
            event_id=None,
            prediction_time=when,
            congestion_level=predicted_level,
            confidence_score=round(confidence, 4),
        )
        session.add(prediction)
        session.flush()

        result = PredictionResult(
            prediction_id=prediction.prediction_id,
            station_id=station.station_id,
            station_name=station.station_name,
            prediction_time=when,
            congestion_level=predicted_level,
            confidence_score=confidence,
            estimated_transfers=estimated_transfers,
            model_version=str(bundle["model_version"]),
        )

    return result
