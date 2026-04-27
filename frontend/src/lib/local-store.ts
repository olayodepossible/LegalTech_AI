import type { ChatMessage } from "@/types/app";

const contractChatKey = (userId: string) =>
  `legaltech_chat_contract_v1_${userId}`;

const draftKey = (userId: string, sessionId: string) =>
  `legaltech_chat_draft_v1_${userId}_${sessionId}`;

export type ChatDraftV1 = {
  text: string;
  language?: string;
};

function safeParse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

/** Unsent composer text only. Activity history is stored in Aurora via POST /api/activity. */
export function getChatDraft(
  userId: string,
  sessionId: string,
): ChatDraftV1 | null {
  if (typeof window === "undefined") return null;
  return safeParse<ChatDraftV1 | null>(localStorage.getItem(draftKey(userId, sessionId)), null);
}

export function setChatDraft(
  userId: string,
  sessionId: string,
  draft: ChatDraftV1,
): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(draftKey(userId, sessionId), JSON.stringify(draft));
}

export function clearChatDraft(userId: string, sessionId: string): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(draftKey(userId, sessionId));
}

/** Contract analysis thread (local only; not POST /api/chat). */
export function getChatMessages(userId: string, scope: "contract"): ChatMessage[] {
  if (typeof window === "undefined") return [];
  return safeParse(localStorage.getItem(contractChatKey(userId)), []);
}

export function appendChatMessage(
  userId: string,
  message: ChatMessage,
  options: { scope: "contract" },
): ChatMessage[] {
  const list = getChatMessages(userId, "contract");
  const next = [...list, message];
  localStorage.setItem(contractChatKey(userId), JSON.stringify(next));
  return next;
}

export function clearChat(userId: string, scope: "contract" = "contract"): void {
  localStorage.removeItem(contractChatKey(userId));
}
