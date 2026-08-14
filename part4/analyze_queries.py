from pathlib import Path

from sqlalchemy import text

from database import engine


INDEX_QUERY = text(
    """
    SELECT tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename IN (
          'station', 'ridership', 'prediction',
          'recommendation', 'user_decision'
      )
    ORDER BY tablename, indexname
    """
)

RIDERSHIP_EXPLAIN = text(
    """
    EXPLAIN (ANALYZE, BUFFERS)
    SELECT transit_timestamp, passenger_count, transfers, congestion_level
    FROM ridership
    WHERE station_id = (
        SELECT station_id FROM station WHERE mta_complex_id = 16
    )
      AND transit_timestamp >= TIMESTAMP '2024-12-01 00:00:00'
      AND transit_timestamp <  TIMESTAMP '2024-12-02 00:00:00'
    ORDER BY transit_timestamp
    """
)

WORKFLOW_EXPLAIN = text(
    """
    EXPLAIN (ANALYZE, BUFFERS)
    SELECT
        p.prediction_id, s.station_name, p.prediction_time,
        p.congestion_level, p.confidence_score, p.model_version,
        p.baseline_congestion_level, p.event_adjustment_levels,
        p.event_adjustment_method,
        e.source_event_id, e.event_name, e.risk_level,
        r.recommendation_id, r.recommended_route,
        r.suggested_departure_time,
        u.decision_id, u.user_action, u.decision_time
    FROM prediction p
    JOIN station s ON s.station_id = p.station_id
    LEFT JOIN event e ON e.event_id = p.event_id
    JOIN recommendation r ON r.prediction_id = p.prediction_id
    LEFT JOIN user_decision u ON u.recommendation_id = r.recommendation_id
    WHERE p.prediction_id = 3
    """
)


def explain_lines(connection, statement) -> list[str]:
    return [row[0] for row in connection.execute(statement)]


def main() -> None:
    sections: list[str] = []
    with engine.connect() as connection:
        sections.append("CURRENT INDEXES")
        for table_name, index_name, definition in connection.execute(INDEX_QUERY):
            sections.append(f"{table_name}.{index_name}: {definition}")

        sections.append("\nRIDERSHIP STATION/TIME QUERY")
        sections.extend(explain_lines(connection, RIDERSHIP_EXPLAIN))

        sections.append("\nEND-TO-END WORKFLOW QUERY")
        sections.extend(explain_lines(connection, WORKFLOW_EXPLAIN))

    report = "\n".join(sections) + "\n"
    report_path = Path(__file__).resolve().parent / "artifacts" / "query_optimization_report.txt"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
