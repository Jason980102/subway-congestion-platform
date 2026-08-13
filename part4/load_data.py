import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from database import SessionLocal
from models import Ridership, Station


load_dotenv()

REQUIRED_COLUMNS = {
    "transit_timestamp",
    "station_complex_id",
    "ridership",
    "transfers",
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "congestion_level",
}


def load_and_validate_csv(csv_path: Path) -> pd.DataFrame:
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    frame = pd.read_csv(csv_path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {sorted(missing)}")

    frame["transit_timestamp"] = pd.to_datetime(
        frame["transit_timestamp"], errors="raise"
    )
    frame["station_complex_id"] = pd.to_numeric(
        frame["station_complex_id"], errors="raise"
    ).astype(int)
    frame["ridership"] = pd.to_numeric(frame["ridership"], errors="raise")
    frame["transfers"] = pd.to_numeric(
        frame["transfers"], errors="raise"
    ).astype(int)

    duplicate_count = frame.duplicated(
        subset=["station_complex_id", "transit_timestamp"]
    ).sum()
    if duplicate_count:
        raise ValueError(f"CSV contains {duplicate_count} duplicate station-hour rows")

    return frame


def load_ridership() -> dict[str, int]:
    csv_setting = os.getenv("CSV_PATH")
    if not csv_setting:
        raise RuntimeError("Missing required setting: CSV_PATH")

    frame = load_and_validate_csv(Path(csv_setting))

    with SessionLocal.begin() as session:
        station_rows = session.execute(
            select(Station.station_id, Station.mta_complex_id)
        ).all()
        station_map = {
            int(mta_complex_id): station_id
            for station_id, mta_complex_id in station_rows
            if mta_complex_id is not None
        }

        missing_stations = sorted(
            set(frame["station_complex_id"].unique()).difference(station_map)
        )
        if missing_stations:
            raise ValueError(
                "No STATION mapping for MTA complex IDs: "
                f"{missing_stations}"
            )

        records = []
        for row in frame.itertuples(index=False):
            timestamp = row.transit_timestamp.to_pydatetime()
            records.append(
                {
                    "station_id": station_map[int(row.station_complex_id)],
                    "record_date": timestamp.date(),
                    "passenger_count": int(round(row.ridership)),
                    "peak_hour": int(row.hour) in {7, 8, 9, 16, 17, 18, 19},
                    "transit_timestamp": timestamp,
                    "transfers": int(row.transfers),
                    "hour": int(row.hour),
                    "day_of_week": int(row.day_of_week),
                    "month": int(row.month),
                    "is_weekend": bool(int(row.is_weekend)),
                    "congestion_level": str(row.congestion_level),
                }
            )

        statement = insert(Ridership).values(records)
        statement = statement.on_conflict_do_nothing(
            index_elements=["station_id", "transit_timestamp"]
        )
        result = session.execute(statement)

    inserted = result.rowcount if result.rowcount is not None else 0
    print(f"CSV rows validated: {len(frame):,}")
    print(f"New rows inserted: {inserted:,}")
    print("Existing station-hour rows were skipped safely.")
    return {
        "validated_rows": int(len(frame)),
        "inserted_rows": int(inserted),
        "skipped_rows": int(len(frame) - inserted),
    }


if __name__ == "__main__":
    load_ridership()
