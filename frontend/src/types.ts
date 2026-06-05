export type AuditScope = "china" | "china_singapore" | "china_vietnam";

export type AuditTask = {
  task_id: string;
  company_name?: string | null;
  scope: AuditScope;
  countries: string[];
  status: string;
  current_round: number;
  next_question?: string | null;
};

export type CreateAuditTaskRequest = {
  company_name?: string | null;
  scope: AuditScope;
};

export type SubmitAuditAnswerRequest = {
  answer: string;
};

export type LegalRecord = {
  record_id: string;
  country: string;
  domain: string;
  law_title_local?: string | null;
  law_title_en?: string | null;
  citation?: string | null;
  issuing_body?: string | null;
  is_currently_effective?: boolean | null;
  effective_date?: string | null;
  valid_until?: string | null;
  official_database?: string | null;
  official_url?: string | null;
  agent_tags: string[];
  retrieval_priority?: string | null;
  fetch_status?: string | null;
  fetch_method?: string | null;
  http_status?: number | null;
  content_path?: string | null;
  metadata_path?: string | null;
  fetch_status_path?: string | null;
  content_exists: boolean;
  ingested_at_utc?: string | null;
};

export type LegalImportResponse = {
  package_name: string;
  validity_as_of?: string | null;
  total_records: number;
  inserted_records: number;
  updated_records: number;
};

export type AuditAnalysisEvidence = {
  record_id: string;
  country: string;
  domain: string;
  law_title: string;
  chunk_index: number;
  hybrid_score: number;
  vector_score: number;
  bm25_score: number;
};

export type AuditRiskAnalysis = {
  task_id: string;
  analysis_id: string;
  model_name?: string | null;
  retrieval_method: string;
  created_at_utc: string;
  company_name?: string | null;
  scope: AuditScope;
  countries: string[];
  audit_context: string;
  evidences: AuditAnalysisEvidence[];
  analysis: string;
};

export type LegalSearchHit = {
  score?: number;
  hybrid_score?: number;
  vector_score?: number;
  bm25_score?: number;
  record_id: string;
  country: string;
  domain: string;
  law_title: string;
  chunk_index: number;
  text: string;
};

export type LegalSearchResponse = {
  query: string;
  index_chunk_count?: number;
  index_dimension: number;
  vector_index_chunk_count?: number;
  bm25_index_chunk_count?: number;
  hits: LegalSearchHit[];
};

export type SavedAnswer = {
  round: number;
  question: string;
  answer: string;
};
