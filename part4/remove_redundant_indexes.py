from sqlalchemy import text

from database import engine


REDUNDANT_INDEXES = (
    "ix_prediction_station_time",
    "ix_recommendation_prediction",
    "ix_ridership_station",
)


with engine.begin() as connection:
    for index_name in REDUNDANT_INDEXES:
        connection.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
        print(f"Removed redundant index if present: {index_name}")
