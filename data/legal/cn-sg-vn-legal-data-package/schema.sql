-- PostgreSQL schema for legal package index

CREATE TABLE IF NOT EXISTS legal_records_index (
  id TEXT PRIMARY KEY,
  country TEXT NOT NULL,
  domain TEXT NOT NULL,
  law_title_local TEXT,
  law_title_en TEXT,
  citation TEXT,
  issuing_body TEXT,
  effective_date TEXT,
  is_currently_effective BOOLEAN,
  valid_until TEXT,
  official_database TEXT,
  official_url TEXT,
  retrieval_priority TEXT,
  agent_tags_pipe TEXT,
  fetch_status TEXT,
  fetch_method TEXT,
  http_status TEXT,
  content_path TEXT,
  metadata_path TEXT,
  fetch_status_path TEXT,
  content_exists BOOLEAN,
  ingested_at_utc TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_legal_records_country_domain
  ON legal_records_index(country, domain);

CREATE INDEX IF NOT EXISTS idx_legal_records_effective
  ON legal_records_index(is_currently_effective);
