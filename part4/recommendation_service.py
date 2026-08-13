from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select

from database import SessionLocal
from models import Prediction, Recommendation, Station


ALTERNATIVE_STATIONS = {
    16: 407,   # 8 St-NYU -> Astor Pl
    167: 619,  # W 4 St-Wash Sq -> Broadway-Lafayette/Bleecker
    407: 16,   # Astor Pl -> 8 St-NYU
    619: 167,  # Broadway-Lafayette/Bleecker -> W 4 St-Wash Sq
}


@dataclass(frozen=True)
class RecommendationResult:
    recommendation_id: int
    prediction_id: int
    congestion_level: str
    recommended_route: str
    suggested_departure_time: datetime
    incentive: str


def generate_and_save(prediction_id: int) -> RecommendationResult:
    with SessionLocal.begin() as session:
        existing = session.scalar(
            select(Recommendation).where(
                Recommendation.prediction_id == prediction_id
            )
        )
        if existing is not None:
            prediction = session.get(Prediction, prediction_id)
            return RecommendationResult(
                recommendation_id=existing.recommendation_id,
                prediction_id=prediction_id,
                congestion_level=str(prediction.congestion_level),
                recommended_route=str(existing.recommended_route),
                suggested_departure_time=existing.suggested_departure_time,
                incentive=str(existing.incentive),
            )

        prediction = session.get(Prediction, prediction_id)
        if prediction is None:
            raise ValueError(f"Unknown prediction_id: {prediction_id}")

        station = session.get(Station, prediction.station_id)
        if station is None or station.mta_complex_id is None:
            raise ValueError("Prediction is not linked to a valid MTA station")

        congestion_level = str(prediction.congestion_level)

        if congestion_level == "High":
            alternative_complex_id = ALTERNATIVE_STATIONS.get(station.mta_complex_id)
            alternative = session.scalar(
                select(Station).where(
                    Station.mta_complex_id == alternative_complex_id
                )
            )
            if alternative is None:
                raise ValueError("No alternative station mapping is available")

            recommended_route = (
                f"Use {alternative.station_name} "
                f"({alternative.daytime_routes}) or depart 30 minutes later"
            )
            suggested_time = prediction.prediction_time + timedelta(minutes=30)
            incentive = "Off-peak travel credit recommended"

        elif congestion_level == "Medium":
            recommended_route = (
                f"Keep {station.station_name}; consider departing 15 minutes later"
            )
            suggested_time = prediction.prediction_time + timedelta(minutes=15)
            incentive = "No incentive required"

        else:
            recommended_route = f"Keep original plan via {station.station_name}"
            suggested_time = prediction.prediction_time
            incentive = "No incentive required"

        recommendation = Recommendation(
            prediction_id=prediction.prediction_id,
            recommended_route=recommended_route,
            suggested_departure_time=suggested_time,
            incentive=incentive,
        )
        session.add(recommendation)
        session.flush()

        result = RecommendationResult(
            recommendation_id=recommendation.recommendation_id,
            prediction_id=prediction.prediction_id,
            congestion_level=congestion_level,
            recommended_route=recommended_route,
            suggested_departure_time=suggested_time,
            incentive=incentive,
        )

    return result
