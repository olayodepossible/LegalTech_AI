import type { Activity, ActivityType, ChatMessage } from "@/types/app";

const activitiesKey = (userId: string) =>
  `legaltech_activities_v2_${userId}`;
const chatKey = (userId: string) => `legaltech_chat_v2_${userId}`;
const contractChatKey = (userId: string) =>
  `legaltech_chat_contract_v1_${userId}`;

export type ChatScope = "general" | "contract";

function messagesKey(userId: string, scope: ChatScope): string {
  return scope === "contract" ? contractChatKey(userId) : chatKey(userId);
}

function safeParse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function getActivities(userId: string): Activity[] {
  if (typeof window === "undefined") return [];
  return safeParse(localStorage.getItem(activitiesKey(userId)), []);
}

function writeActivities(userId: string, list: Activity[]): void {
  localStorage.setItem(activitiesKey(userId), JSON.stringify(list));
}

export function logActivity(
  userId: string,
  type: ActivityType,
  label: string,
  detail?: string,
): Activity {
  const list = getActivities(userId);
  const entry: Activity = {
    id: crypto.randomUUID(),
    type,
    label,
    detail,
    at: new Date().toISOString(),
  };
  writeActivities(userId, [entry, ...list].slice(0, 200));
  return entry;
}

export function getChatMessages(
  userId: string,
  scope: ChatScope = "general",
): ChatMessage[] {
  if (typeof window === "undefined") return [];
  return safeParse(localStorage.getItem(messagesKey(userId, scope)), []);
}

export function appendChatMessage(
  userId: string,
  message: ChatMessage,
  scope: ChatScope = "general",
): ChatMessage[] {
  const list = getChatMessages(userId, scope);
  const next = [...list, message];
  localStorage.setItem(messagesKey(userId, scope), JSON.stringify(next));
  return next;
}

export function clearChat(userId: string, scope: ChatScope = "general"): void {
  localStorage.removeItem(messagesKey(userId, scope));
}
