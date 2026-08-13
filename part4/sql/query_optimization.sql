-- Part IV query optimization evidence

-- Indexes supporting station-hour lookups and transactional joins.
CREATE UNIQUE INDEX IF NOT EXISTS ux_ridership_station_timestamp
    ON ridership (station_id, transit_timestamp);

CREATE INDEX IF NOT EXISTS ix_user_decision_recommendation
    ON user_decision (recommendation_id);

-- Part III already created equivalent idx_* indexes. Remove the duplicate
-- ix_* copies added during integration so writes maintain fewer indexes.
DROP INDEX IF EXISTS ix_prediction_station_time;
DROP INDEX IF EXISTS ix_recommendation_prediction;
DROP INDEX IF EXISTS ix_ridership_station;

-- Query 1: station-hour range used by historical feature lookup.
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    transit_timestamp,
    passenger_count,
    transfers,
    congestion_level
FROM ridership
WHERE station_id = (
    SELECT station_id
    FROM station
    WHERE mta_complex_id = 16
)
AND transit_timestamp >= TIMESTAMP '2024-12-01 00:00:00'
AND transit_timestamp <  TIMESTAMP '2024-12-02 00:00:00'
ORDER BY transit_timestamp;

-- Query 2: reconstruct one complete application workflow.
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    p.prediction_id,
    s.station_name,
    p.prediction_time,
    p.congestion_level,
    p.confidence_score,
    r.recommendation_id,
    r.recommended_route,
    r.suggested_departure_time,
    u.decision_id,
    u.user_action,
    u.decision_time
FROM prediction p
JOIN station s
    ON s.station_id = p.station_id
JOIN recommendation r
    ON r.prediction_id = p.prediction_id
LEFT JOIN user_decision u
    ON u.recommendation_id = r.recommendation_id
WHERE p.prediction_id = 3;
