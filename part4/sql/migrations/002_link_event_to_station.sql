BEGIN;

ALTER TABLE public.event
    ADD COLUMN IF NOT EXISTS station_id integer;

UPDATE public.event e
SET station_id = p.station_id
FROM public.prediction p
WHERE p.event_id = e.event_id
  AND e.station_id IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_event_station'
    ) THEN
        ALTER TABLE public.event
            ADD CONSTRAINT fk_event_station
            FOREIGN KEY (station_id) REFERENCES public.station(station_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_event_station_time
    ON public.event (station_id, start_time, end_time);

COMMIT;
