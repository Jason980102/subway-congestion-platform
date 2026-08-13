from sqlalchemy import text

from database import engine


with engine.connect() as connection:
    database_name = connection.execute(text("SELECT current_database()" )).scalar_one()
    print(f"Connected successfully to: {database_name}")

