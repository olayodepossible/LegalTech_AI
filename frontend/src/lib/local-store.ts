import type { Activity, ActivityType, ChatMessage } from "@/types/app";

const activitiesKey = (userId: string) =>
  `legaltech_activities_v2_${userId}`;
const chatKey = (userId: string) => `legaltech_chat_v2_${userId}`;

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

export function getChatMessages(userId: string): ChatMessage[] {
  if (typeof window === "undefined") return [];
  return safeParse(localStorage.getItem(chatKey(userId)), []);
}

export function appendChatMessage(
  userId: string,
  message: ChatMessage,
): ChatMessage[] {
  const list = getChatMessages(userId);
  const next = [...list, message];
  localStorage.setItem(chatKey(userId), JSON.stringify(next));
  return next;
}

export function clearChat(userId: string): void {
  localStorage.removeItem(chatKey(userId));
}
