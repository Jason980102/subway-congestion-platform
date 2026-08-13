-- Seed data for the four NYU-area subway stations.
-- Run this file after subway_schema.sql.

INSERT INTO
    public.station (
        station_id,
        station_name,
        latitude,
        longitude,
        borough,
        accessibility,
        mta_complex_id,
        daytime_routes
    )
VALUES (
        1,
        '8 St-NYU',
        40.730328,
        -73.992629,
        'Manhattan',
        FALSE,
        16,
        'R,W'
    ),
    (
        2,
        'W 4 St-Wash Sq',
        40.732338,
        -74.000495,
        'Manhattan',
        TRUE,
        167,
        'A,C,E,B,D,F,M'
    ),
    (
        3,
        'Astor Pl',
        40.730054,
        -73.991070,
        'Manhattan',
        FALSE,
        407,
        '6'
    ),
    (
        4,
        'Broadway-Lafayette St/Bleecker St',
        40.725915,
        -73.994659,
        'Manhattan',
        TRUE,
        619,
        'B,D,F,M,6'
    ) ON CONFLICT (station_id) DO
UPDATE
SET
    station_name = EXCLUDED.station_name,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    borough = EXCLUDED.borough,
    accessibility = EXCLUDED.accessibility,
    mta_complex_id = EXCLUDED.mta_complex_id,
    daytime_routes = EXCLUDED.daytime_routes;

SELECT setval (
        pg_get_serial_sequence (
            'public.station', 'station_id'
        ), (
            SELECT MAX(station_id)
            FROM public.station
        ), TRUE
    );