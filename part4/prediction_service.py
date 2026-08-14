import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import func, select

from database import SessionLocal
from models import Event, Prediction, Ridership, Station
from event_service import find_nearby_event


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
    event_id: int | None
    event_name: str | None
    baseline_congestion_level: str
    event_adjustment: str


CONGESTION_LEVELS = ["Low", "Medium", "High"]


def apply_event_adjustment(
    baseline: str, risk_level: str | None
) -> tuple[str, int, str]:
    """Apply a transparent official-event risk adjustment to the RF baseline."""
    steps = {"High": 2, "Medium": 1, "Low": 0}.get(risk_level, 0)

    baseline_index = CONGESTION_LEVELS.index(baseline)
    adjusted = CONGESTION_LEVELS[min(baseline_index + steps, 2)]
    if steps == 0:
        explanation = f"Official event risk: {risk_level or 'Low'}; no level uplift"
    else:
        explanation = f"Official event risk: {risk_level}; +{steps} congestion level(s)"
    applied_steps = CONGESTION_LEVELS.index(adjusted) - baseline_index
    if steps and applied_steps < steps:
        explanation += "; final level capped at High"
    return adjusted, applied_steps, explanation


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


def predict_and_save(
    station_id: int,
    when: datetime,
) -> PredictionResult:
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

        baseline_level = str(model.predict(feature_frame)[0])
        probabilities = model.predict_proba(feature_frame)[0]
        confidence = float(max(probabilities))

        event = find_nearby_event(session, station_id, when)

        if event is None:
            predicted_level = baseline_level
            event_adjustment_levels = 0
            event_adjustment = "No event scenario applied"
        else:
            predicted_level, event_adjustment_levels, event_adjustment = apply_event_adjustment(
                baseline_level, event.risk_level
            )

        prediction = Prediction(
            station_id=station_id,
            event_id=event.event_id if event else None,
            prediction_time=when,
            congestion_level=predicted_level,
            confidence_score=round(confidence, 4),
            model_version=str(bundle["model_version"]),
            baseline_congestion_level=baseline_level,
            event_adjustment_levels=event_adjustment_levels,
            event_adjustment_method=(
                "official_event_type_and_street_closure_rule_v1"
                if event else "none"
            ),
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
            event_id=event.event_id if event else None,
            event_name=event.event_name if event else None,
            baseline_congestion_level=baseline_level,
            event_adjustment=event_adjustment,
        )

    return result
