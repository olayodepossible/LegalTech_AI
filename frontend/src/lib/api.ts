/**
 * Client for `backend/api/main.py` — Clerk JWT on each request.
 */
import { getApiBaseUrl } from "@/lib/api-base";

/** CloudFront, API Gateway, and load balancers often return HTML error pages — never show that raw text in the UI. */
function bodyLooksLikeHtml(s: string): boolean {
  const t = s.trim();
  if (t.length < 12) return false;
  const low = t.toLowerCase();
  if (low.startsWith("<!doctype") || low.startsWith("<html")) return true;
  if (low.includes("cloudfront") && low.includes("<")) return true;
  if (low.includes("the request could not be satisfied")) return true;
  if (low.includes("504 gateway") || low.includes("502 bad gateway")) return true;
  return false;
}

function friendlyHttpMessage(status: number): string {
  switch (status) {
    case 401:
      return "You need to sign in again, then try once more.";
    case 403:
      return "You do not have permission to do this.";
    case 404:
      return "The requested resource was not found.";
    case 408:
    case 504:
      return "The request timed out. The service may be busy or the operation took too long. Please try again in a moment.";
    case 502:
      return "The app could not reach the server (bad gateway). Please try again shortly.";
    case 503:
      return "The service is temporarily unavailable. Please try again in a few moments.";
    case 500:
    case 0:
    default:
      if (status >= 500) {
        return "Something went wrong on the server. Please try again later.";
      }
      return "Something went wrong. Please try again.";
  }
}

/**
 * Map failed HTTP responses to a short, human-readable string.
 * Strips HTML error pages (e.g. CloudFront 502/503/504) that would otherwise fill the screen.
 */
export function parseApiError(
  status: number,
  body: unknown,
  raw: string,
): string {
  if (raw && bodyLooksLikeHtml(raw)) {
    return friendlyHttpMessage(status);
  }
  if (typeof body === "string" && bodyLooksLikeHtml(body)) {
    return friendlyHttpMessage(status);
  }
  if (body && typeof body === "object" && body !== null && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string" && d.length > 0) {
      if (bodyLooksLikeHtml(d)) return friendlyHttpMessage(status);
      return d;
    }
    if (Array.isArray(d) && d.length > 0) {
      const parts: string[] = [];
      for (const item of d) {
        if (item && typeof item === "object" && "msg" in (item as object)) {
          const m = (item as { msg?: unknown }).msg;
          if (typeof m === "string" && m) parts.push(m);
        }
      }
      if (parts.length) return parts.join(" ");
    }
  }
  if (raw && !bodyLooksLikeHtml(raw) && raw.length <= 500) {
    return raw;
  }
  if (raw && !bodyLooksLikeHtml(raw) && raw.length > 500) {
    return `${raw.slice(0, 200)}…`;
  }
  if (status && status >= 400) {
    return friendlyHttpMessage(status);
  }
  return `Request failed (${status || "unknown"})`;
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

/**
 * Persist a product/analytics event (Aurora ``activity_history``), tied to the JWT user.
 */
export async function postActivity(
  payload: { activity_type: string; label: string; details?: string },
  getToken: () => Promise<string | null>,
): Promise<{ ok: boolean; id: string } | null> {
  const t = await getToken();
  if (!t) return null;
  const res = await fetch(`${getApiBaseUrl()}/api/activity`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${t}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  const { ok, data, raw } = await readJson(res);
  if (!ok) throw new Error(parseApiError(res.status, data, raw));
  return data as { ok: boolean; id: string };
}

/** Fire-and-forget; failures are ignored so UI never blocks. */
export function logActivityRemote(
  getToken: () => Promise<string | null>,
  activity_type: string,
  label: string,
  details?: string,
): void {
  void postActivity({ activity_type, label, details }, getToken).catch(
    () => undefined,
  );
}

export type LegalChatResponse = { reply: string };

export type LegalChatListItem = {
  id: string;
  title: string;
  language: string;
  updated_at?: string | null;
  created_at?: string | null;
};

export type LegalChatMessageRow = {
  id: string;
  role: string;
  content: string;
  language_code: string;
  created_at?: string | null;
};

export async function getLegalChats(
  getToken: () => Promise<string | null>,
): Promise<LegalChatListItem[]> {
  const t = await getToken();
  if (!t) throw new Error("Not signed in");
  const res = await fetch(`${getApiBaseUrl()}/api/chats`, {
    headers: { Authorization: `Bearer ${t}` },
  });
  const { ok, data, raw } = await readJson(res);
  if (!ok) throw new Error(parseApiError(res.status, data, raw));
  return Array.isArray(data) ? (data as LegalChatListItem[]) : [];
}

export async function createLegalChat(
  getToken: () => Promise<string | null>,
  id?: string,
): Promise<LegalChatListItem> {
  const t = await getToken();
  if (!t) throw new Error("Not signed in");
  const res = await fetch(`${getApiBaseUrl()}/api/chats`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${t}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(id ? { id } : {}),
  });
  const { ok, data, raw } = await readJson(res);
  if (!ok) throw new Error(parseApiError(res.status, data, raw));
  return data as LegalChatListItem;
}

export async function getLegalChatMessages(
  chatId: string,
  getToken: () => Promise<string | null>,
): Promise<LegalChatMessageRow[]> {
  const t = await getToken();
  if (!t) throw new Error("Not signed in");
  const res = await fetch(
    `${getApiBaseUrl()}/api/chats/${encodeURIComponent(chatId)}/messages`,
    { headers: { Authorization: `Bearer ${t}` } },
  );
  const { ok, data, raw } = await readJson(res);
  if (!ok) throw new Error(parseApiError(res.status, data, raw));
  return Array.isArray(data) ? (data as LegalChatMessageRow[]) : [];
}

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
  /** Presigned S3 GET URL; expires (default 7d on server). */
  download_url?: string | null;
};

export type RagDocumentRow = {
  document_id: string;
  name: string;
  s3_key: string;
  size_bytes: number;
  last_modified?: string | null;
  download_url?: string | null;
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
  chatId: string,
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
    body: JSON.stringify({ message, language, chat_id: chatId }),
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

export async function getRagDocuments(
  getToken: () => Promise<string | null>,
): Promise<RagDocumentRow[]> {
  const t = await getToken();
  if (!t) throw new Error("Not signed in");
  const res = await fetch(`${getApiBaseUrl()}/api/rag/documents`, {
    headers: { Authorization: `Bearer ${t}` },
  });
  const { ok, data, raw } = await readJson(res);
  if (!ok) throw new Error(parseApiError(res.status, data, raw));
  const rows = (data as { documents?: RagDocumentRow[] })?.documents;
  return Array.isArray(rows) ? rows : [];
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
