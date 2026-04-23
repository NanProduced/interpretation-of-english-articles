-- Fix double-serialized JSONB columns in daily_readers table.
-- The asyncpg JSONB codec was registered but code also called orjson.dumps() manually,
-- causing values to be stored as JSON strings inside JSONB instead of proper JSONB objects.
-- This migration unwraps the inner JSON string and stores it as the correct JSONB type.

DO $$
DECLARE
    rec RECORD;
    new_body jsonb;
    new_hl jsonb;
    new_footer jsonb;
    new_tags jsonb;
    new_sec jsonb;
    new_meta jsonb;
BEGIN
    FOR rec IN SELECT id, body_json, highlights_json, footer_analysis_json, tags, content_sec_check, pipeline_meta FROM daily_readers LOOP
        -- Only fix if the value is a JSONB string (double-serialized)
        IF jsonb_typeof(rec.body_json) = 'string' THEN
            new_body := (rec.body_json #>> '{}')::jsonb;
        ELSE
            new_body := rec.body_json;
        END IF;

        IF jsonb_typeof(rec.highlights_json) = 'string' THEN
            new_hl := (rec.highlights_json #>> '{}')::jsonb;
        ELSE
            new_hl := rec.highlights_json;
        END IF;

        IF jsonb_typeof(rec.footer_analysis_json) = 'string' THEN
            new_footer := (rec.footer_analysis_json #>> '{}')::jsonb;
        ELSE
            new_footer := rec.footer_analysis_json;
        END IF;

        IF jsonb_typeof(rec.tags) = 'string' THEN
            new_tags := (rec.tags #>> '{}')::jsonb;
        ELSE
            new_tags := rec.tags;
        END IF;

        IF jsonb_typeof(rec.content_sec_check) = 'string' THEN
            new_sec := (rec.content_sec_check #>> '{}')::jsonb;
        ELSE
            new_sec := rec.content_sec_check;
        END IF;

        IF jsonb_typeof(rec.pipeline_meta) = 'string' THEN
            new_meta := (rec.pipeline_meta #>> '{}')::jsonb;
        ELSE
            new_meta := rec.pipeline_meta;
        END IF;

        UPDATE daily_readers
        SET body_json = new_body,
            highlights_json = new_hl,
            footer_analysis_json = new_footer,
            tags = new_tags,
            content_sec_check = new_sec,
            pipeline_meta = new_meta
        WHERE id = rec.id;
    END LOOP;
END $$;
