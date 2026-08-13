-- Add auditable model lineage to existing Part IV databases.
ALTER TABLE public.prediction
    ADD COLUMN IF NOT EXISTS model_version character varying(100);

UPDATE public.prediction
SET model_version = 'legacy_unknown'
WHERE model_version IS NULL;

ALTER TABLE public.prediction
    ALTER COLUMN model_version SET NOT NULL;
