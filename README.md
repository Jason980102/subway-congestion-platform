# Subway Congestion Decision Support Platform

Database Systems Project Part IV for CSCI-GA.2433-001.

This repository contains an end-to-end NYU-area subway congestion application that connects historical MTA ridership data, PostgreSQL, a persisted Random Forest classifier, recommendations, and commuter decisions.

## End-to-end workflow

1. Validate and load 11,667 hourly ridership observations into PostgreSQL.
2. Accept a future station, date, and time through Streamlit.
3. Load the persisted Random Forest model and predict congestion.
4. Write the result to `PREDICTION`.
5. Generate and write a linked `RECOMMENDATION`.
6. Record the commuter's accepted or original-plan choice in `USER_DECISION`.

The implementation and documentation are in [`part4`](part4/README.md).

## Security

The real `.env` file and database password are intentionally excluded from version control. Use `part4/.env.example` to configure a local installation.
