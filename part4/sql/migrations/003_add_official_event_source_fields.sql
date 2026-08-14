BEGIN;

ALTER TABLE public.event
    ADD COLUMN IF NOT EXISTS source_event_id character varying(50),
    ADD COLUMN IF NOT EXISTS event_agency character varying(150),
    ADD COLUMN IF NOT EXISTS street_closure_type character varying(100),
    ADD COLUMN IF NOT EXISTS risk_level character varying(20);

CREATE UNIQUE INDEX IF NOT EXISTS ux_event_source_event_id
    ON public.event (source_event_id)
    WHERE source_event_id IS NOT NULL;

ALTER TABLE public.event DROP CONSTRAINT IF EXISTS event_risk_level_check;
ALTER TABLE public.event
    ADD CONSTRAINT event_risk_level_check
    CHECK (risk_level IS NULL OR risk_level IN ('Low', 'Medium', 'High'));

COMMIT;
