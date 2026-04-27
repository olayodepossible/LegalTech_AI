"use client";

import { ChatMarkdown } from "@/components/chat-markdown";
import {
  createLegalChat,
  getLegalChatMessages,
  logActivityRemote,
  postLegalChat,
  type LegalChatMessageRow,
} from "@/lib/api";
import { RESPONSE_LANGUAGES, languageLabel } from "@/lib/languages";
import {
  clearChatDraft,
  getChatDraft,
  setChatDraft,
} from "@/lib/local-store";
import type { ChatMessage } from "@/types/app";
import { useAuth, useUser } from "@clerk/react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

function formatTime(iso: string) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return "";
  }
}

function mapServerMessage(m: LegalChatMessageRow): ChatMessage {
  return {
    id: m.id,
    role: m.role === "assistant" ? "assistant" : "user",
    content: m.content,
    languageCode: m.language_code,
    at: m.created_at || new Date().toISOString(),
  };
}

/**
 * With ``output: 'export'`` there is no ``/chat/[id]`` dynamic route; the session
 * id lives in the ``session`` query so the app builds as a single static page.
 */
function ChatSessionInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const session = searchParams.get("session");
  const { user, isLoaded } = useUser();
  const { getToken } = useAuth();
  const userId = user?.id;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("en");
  const [sending, setSending] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const draftSync = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!isLoaded || !userId) return;
    if (session) return;
    router.replace(`/chat?session=${crypto.randomUUID()}`);
  }, [isLoaded, userId, session, router]);

  useEffect(() => {
    if (!userId || !session) return;
    const d = getChatDraft(userId, session);
    if (d?.text) setInput(d.text);
    if (d?.language) setLanguage(d.language);
  }, [userId, session]);

  useEffect(() => {
    if (!userId || !session) return;
    if (draftSync.current) clearTimeout(draftSync.current);
    draftSync.current = setTimeout(() => {
      if (input.trim() || (language && language !== "en")) {
        setChatDraft(userId, session, { text: input, language });
      } else {
        clearChatDraft(userId, session);
      }
    }, 400);
    return () => {
      if (draftSync.current) clearTimeout(draftSync.current);
    };
  }, [userId, session, input, language]);

  useEffect(() => {
    if (!userId || !session) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setLoadError(null);
      try {
        await createLegalChat(getToken, session);
        const rows = await getLegalChatMessages(session, getToken);
        if (!cancelled) setMessages(rows.map(mapServerMessage));
        logActivityRemote(getToken, "visit_chat", "Opened chat");
      } catch (e) {
        if (!cancelled) {
          setLoadError(
            e instanceof Error ? e.message : "Could not load conversation.",
          );
          setMessages([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId, session, getToken]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!userId || !session || !input.trim() || sending) return;

    setSending(true);
    setLoadError(null);

    const userMsgText = input.trim();
    setInput("");

    try {
      await postLegalChat(userMsgText, language, session, getToken);
      const rows = await getLegalChatMessages(session, getToken);
      setMessages(rows.map(mapServerMessage));
      clearChatDraft(userId, session);
      logActivityRemote(
        getToken,
        "chat_message",
        "Sent chat message",
        languageLabel(language),
      );
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("legaltech-chats-updated"));
      }
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "Could not get a response from the API.";
      setInput(userMsgText);
      setLoadError(msg);
    } finally {
      setSending(false);
    }
  }

  function onFormSubmit(e: React.FormEvent) {
    e.preventDefault();
    void handleSend();
  }

  if (!isLoaded || !userId) return null;

  return (
    <div className="flex h-[calc(100vh-8rem)] min-h-[420px] flex-col gap-4 sm:h-[calc(100vh-6rem)]">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          Legal Companion
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Conversations are stored in your account on the server. This device
          only keeps an optional unsent message draft in the browser.
        </p>
      </div>

      {loadError ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900 dark:border-rose-900/40 dark:bg-rose-950/40 dark:text-rose-100">
          {loadError}
        </p>
      ) : null}

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex flex-wrap items-center gap-3 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800">
          <label className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-300">
            <span className="font-medium text-zinc-700 dark:text-zinc-200">
              Response language
            </span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            >
              {RESPONSE_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {loading ? (
            <p className="py-12 text-center text-sm text-zinc-500 dark:text-zinc-400">
              Loading conversation…
            </p>
          ) : messages.length === 0 ? (
            <p className="py-12 text-center text-sm text-zinc-500 dark:text-zinc-400">
              Start by typing a legal question. For contract analysis, open
              Contract analysis in the sidebar and upload the document.
            </p>
          ) : (
            <ul className="mx-auto flex max-w-3xl flex-col gap-4">
              {messages.map((m) => (
                <li
                  key={m.id}
                  className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      m.role === "user"
                        ? "bg-indigo-600 text-white"
                        : "border border-zinc-200 bg-zinc-50 text-zinc-900 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
                    }`}
                  >
                    <div className="mb-1 flex flex-wrap items-center gap-2 text-xs opacity-80">
                      <span className="font-semibold uppercase tracking-wide">
                        {m.role === "user" ? "You" : "Assistant"}
                      </span>
                      <span>·</span>
                      <span>{languageLabel(m.languageCode)}</span>
                      <span>·</span>
                      <time dateTime={m.at}>{formatTime(m.at)}</time>
                    </div>
                    {m.attachments?.length ? (
                      <ul className="mb-2 flex flex-wrap gap-1">
                        {m.attachments.map((a) => (
                          <li
                            key={`${m.id}-${a.name}`}
                            className="rounded-md bg-white/15 px-2 py-0.5 text-xs dark:bg-zinc-800"
                          >
                            {a.name}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    {m.role === "assistant" ? (
                      <ChatMarkdown content={m.content} />
                    ) : (
                      <p className="whitespace-pre-wrap">{m.content}</p>
                    )}
                  </div>
                </li>
              ))}
              <div ref={bottomRef} />
            </ul>
          )}
        </div>

        <form
          onSubmit={onFormSubmit}
          className="border-t border-zinc-100 p-4 dark:border-zinc-800"
        >
          <div className="mx-auto flex max-w-3xl gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSend();
                }
              }}
              placeholder="Ask about clauses, risk, or jurisdiction…"
              rows={2}
              className="min-h-[48px] flex-1 resize-none rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
            <button
              type="submit"
              disabled={sending || !input.trim() || !session}
              className="shrink-0 self-end rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {sending ? "…" : "Send"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] items-center justify-center text-sm text-zinc-500 dark:text-zinc-400">
          Loading chat…
        </div>
      }
    >
      <ChatSessionInner />
    </Suspense>
  );
}
