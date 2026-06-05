import type {
  AuditRiskAnalysis,
  AuditTask,
  CreateAuditTaskRequest,
  LegalImportResponse,
  LegalRecord,
  LegalSearchResponse,
  SubmitAuditAnswerRequest,
} from "./types";

const API_PREFIX = "/api/v1";

async function readErrorMessage(response: Response): Promise<string> {
  const rawMessage = await response.text();

  if (!rawMessage) {
    return `请求失败：${response.status}`;
  }

  try {
    const parsed = JSON.parse(rawMessage) as { detail?: unknown };

    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
  } catch {
    return rawMessage;
  }

  return rawMessage;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json() as Promise<T>;
}

export function healthCheck() {
  return request<{ status: string; service: string }>("/health");
}

export function createAuditTask(payload: CreateAuditTaskRequest) {
  return request<AuditTask>("/audit-tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAuditTask(taskId: string) {
  return request<AuditTask>(`/audit-tasks/${taskId}`);
}

export function submitAuditAnswer(taskId: string, payload: SubmitAuditAnswerRequest) {
  return request<AuditTask>(`/audit-tasks/${taskId}/answers`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createAuditAnalysis(taskId: string) {
  return request<AuditRiskAnalysis>(`/audit-tasks/${taskId}/analysis`, {
    method: "POST",
  });
}

export function getLatestAuditAnalysis(taskId: string) {
  return request<AuditRiskAnalysis>(`/audit-tasks/${taskId}/analysis/latest`);
}

export function importLegalData() {
  return request<LegalImportResponse>("/legal-data/import", {
    method: "POST",
  });
}

export function listLegalRecords(filters: { country?: string; domain?: string }) {
  const params = new URLSearchParams();
  if (filters.country) params.set("country", filters.country);
  if (filters.domain) params.set("domain", filters.domain);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request<LegalRecord[]>(`/legal-data/records${suffix}`);
}

export function searchLegalHybrid(payload: {
  query: string;
  top_k: number;
  countries?: string[];
  domains?: string[];
  rebuild_index?: boolean;
}) {
  return request<LegalSearchResponse>("/legal-search/hybrid", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function searchLegalVector(payload: {
  query: string;
  top_k: number;
  countries?: string[];
  domains?: string[];
  rebuild_index?: boolean;
}) {
  return request<LegalSearchResponse>("/legal-search/vector", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
