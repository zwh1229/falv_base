-- Usage example (psql):
-- Run from this package directory:
--   psql -d <db_name> -f schema.sql
--   psql -d <db_name> -f import-example.sql

\copy legal_records_index (
  id,country,domain,law_title_local,law_title_en,citation,issuing_body,
  effective_date,is_currently_effective,valid_until,official_database,official_url,
  retrieval_priority,agent_tags_pipe,fetch_status,fetch_method,http_status,
  content_path,metadata_path,fetch_status_path,content_exists,ingested_at_utc
)
FROM 'index.csv'
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
