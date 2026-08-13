from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Station(Base):
    __tablename__ = "station"

    station_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_name: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric)
    borough: Mapped[str | None] = mapped_column(String)
    accessibility: Mapped[bool | None] = mapped_column(Boolean, default=False)
    mta_complex_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    daytime_routes: Mapped[str | None] = mapped_column(String)

    ridership_records: Mapped[list["Ridership"]] = relationship(back_populates="station")


class Ridership(Base):
    __tablename__ = "ridership"

    ridership_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("station.station_id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    passenger_count: Mapped[int | None] = mapped_column(Integer)
    peak_hour: Mapped[bool | None] = mapped_column(Boolean, default=False)
    transit_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    transfers: Mapped[int | None] = mapped_column(Integer, default=0)
    hour: Mapped[int | None] = mapped_column(Integer)
    day_of_week: Mapped[int | None] = mapped_column(Integer)
    month: Mapped[int | None] = mapped_column(Integer)
    is_weekend: Mapped[bool | None] = mapped_column(Boolean, default=False)
    congestion_level: Mapped[str | None] = mapped_column(String)

    station: Mapped[Station] = relationship(back_populates="ridership_records")


class Prediction(Base):
    __tablename__ = "prediction"

    prediction_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("station.station_id"), nullable=False)
    event_id: Mapped[int | None] = mapped_column(Integer)
    prediction_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    congestion_level: Mapped[str | None] = mapped_column(String)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric)


class Recommendation(Base):
    __tablename__ = "recommendation"

    recommendation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("prediction.prediction_id"), nullable=False
    )
    recommended_route: Mapped[str | None] = mapped_column(String)
    suggested_departure_time: Mapped[datetime | None] = mapped_column(DateTime)
    incentive: Mapped[str | None] = mapped_column(String)


class UserDecision(Base):
    __tablename__ = "user_decision"

    decision_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation.recommendation_id"), nullable=False
    )
    user_action: Mapped[str | None] = mapped_column(String)
    decision_time: Mapped[datetime | None] = mapped_column(DateTime)
