/**
 * Client for `backend/api/main.py` — Clerk JWT on each request.
 */
import { getApiBaseUrl } from "@/lib/api-base";

export function parseApiError(
  status: number,
  body: unknown,
  raw: string,
): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
  }
  return raw || `Request failed (${status})`;
}

async function readJson(
  res: Response,
): Promise<{ ok: boolean; data: unknown; raw: string }> {
  const raw = await res.text();
  let data: unknown = raw;
  try {
    data = raw ? (JSON.parse(raw) as unknown) : null;
  } catch {
    data = raw;
  }
  return { ok: res.ok, data, raw };
}

export type UserResponse = { user: Record<string, unknown>; created: boolean };

export type ActivityHistoryRow = {
  id?: string;
  clerk_user_id?: string;
  account_name?: string;
  label?: string | null;
  details?: string | null;
  activity_type?: string | null;
  activity_date?: string | null;
  created_at?: string;
  email?: string | null;
};

export type LegalChatResponse = { reply: string };

export type ContractAnalysisResult = {
  executive_summary: string;
  pain_points: { title: string; detail: string }[];
  red_flags: { title: string; detail: string }[];
  potential_risks: { title: string; detail: string }[];
};

export type RagUploadResult = {
  document_id: string;
  s3_key: string;
  bucket: string;
  size_bytes: number;
  content_type: string | null;
  ingestion_queued?: boolean;
  sqs_message_id?: string | null;
};

export async function getOrCreateUser(
  getToken: () => Promise<string | null>,
): Promise<UserResponse> {
  const t = await getToken();
  if (!t) throw new Error("Not signed in");
  const res = await fetch(`${getApiBaseUrl()}/api/user`, {
    headers: { Authorization: `Bearer ${t}` },
  });
  const { ok, data, raw } = await readJson(res);
  if (!ok) throw new Error(parseApiError(res.status, data, raw));
  return data as UserResponse;
}

export async function getActivityHistory(
  getToken: () => Promise<string | null>,
): Promise<ActivityHistoryRow[]> {
  const t = await getToken();
  if (!t) throw new Error("Not signed in");
  const res = await fetch(`${getApiBaseUrl()}/api/activity-history`, {
    headers: { Authorization: `Bearer ${t}` },
  });
  const { ok, data, raw } = await readJson(res);
  if (!ok) throw new Error(parseApiError(res.status, data, raw));
  return data as ActivityHistoryRow[];
}

export async function postLegalChat(
  message: string,
  language: string,
  getToken: () => Promise<string | null>,
): Promise<LegalChatResponse> {
  const t = await getToken();
  if (!t) throw new Error("Not signed in");
  const res = await fetch(`${getApiBaseUrl()}/api/chat`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${t}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, language }),
  });
  const { ok, data, raw } = await readJson(res);
  if (!ok) throw new Error(parseApiError(res.status, data, raw));
  return data as LegalChatResponse;
}

export async function postContractAnalyze(
  file: File,
  message: string,
  language: string,
  getToken: () => Promise<string | null>,
): Promise<ContractAnalysisResult> {
  const t = await getToken();
  if (!t) throw new Error("Not signed in");
  const form = new FormData();
  form.append("file", file);
  form.append("message", message);
  form.append("language", language);
  const res = await fetch(`${getApiBaseUrl()}/api/contracts/analyze`, {
    method: "POST",
    headers: { Authorization: `Bearer ${t}` },
    body: form,
  });
  const { ok, data, raw } = await readJson(res);
  if (!ok) throw new Error(parseApiError(res.status, data, raw));
  return data as ContractAnalysisResult;
}

export async function postRagDocumentUpload(
  file: File,
  getToken: () => Promise<string | null>,
): Promise<RagUploadResult> {
  const t = await getToken();
  if (!t) throw new Error("Not signed in");
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${getApiBaseUrl()}/api/rag/documents/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${t}` },
    body: form,
  });
  const { ok, data, raw } = await readJson(res);
  if (!ok) throw new Error(parseApiError(res.status, data, raw));
  return data as RagUploadResult;
}
