# Database Import Guide

## Files
- `index.csv`: relational import file (one row per law record)
- `index.ndjson`: document-db / streaming import file
- `schema.sql`: PostgreSQL table and indexes
- `import-example.sql`: PostgreSQL `\copy` import example

## Recommended relational flow (PostgreSQL)
1. Create table: run `schema.sql`
2. Import rows: run `import-example.sql`
3. Query examples:
   - Current effective only:
     `SELECT id, country, domain, law_title_local FROM legal_records_index WHERE is_currently_effective = true;`
   - By jurisdiction and topic:
     `SELECT * FROM legal_records_index WHERE country='China' AND domain='cross_border_data';`

## Notes
- `content_path` points to raw legal text file already archived in `raw-sources/`.
- `agent_tags_pipe` uses `|` as delimiter for easy split in SQL/ETL.
