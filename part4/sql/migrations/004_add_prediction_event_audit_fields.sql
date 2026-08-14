BEGIN;

ALTER TABLE public.prediction
    ADD COLUMN IF NOT EXISTS baseline_congestion_level character varying(20),
    ADD COLUMN IF NOT EXISTS event_adjustment_levels integer,
    ADD COLUMN IF NOT EXISTS event_adjustment_method character varying(100);

-- Historical no-event predictions can be reconstructed exactly.
UPDATE public.prediction
SET baseline_congestion_level = congestion_level,
    event_adjustment_levels = 0,
    event_adjustment_method = 'none'
WHERE event_id IS NULL
  AND baseline_congestion_level IS NULL;

ALTER TABLE public.prediction DROP CONSTRAINT IF EXISTS prediction_baseline_level_check;
ALTER TABLE public.prediction
    ADD CONSTRAINT prediction_baseline_level_check
    CHECK (
        baseline_congestion_level IS NULL
        OR baseline_congestion_level IN ('Low', 'Medium', 'High')
    );

ALTER TABLE public.prediction DROP CONSTRAINT IF EXISTS prediction_event_adjustment_check;
ALTER TABLE public.prediction
    ADD CONSTRAINT prediction_event_adjustment_check
    CHECK (event_adjustment_levels IS NULL OR event_adjustment_levels BETWEEN 0 AND 2);

COMMIT;
