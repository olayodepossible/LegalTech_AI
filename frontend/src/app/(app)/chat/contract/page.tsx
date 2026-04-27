"use client";

import {
  logActivityRemote,
  postContractAnalyze,
  type ContractAnalysisResult,
} from "@/lib/api";
import { RESPONSE_LANGUAGES, languageLabel } from "@/lib/languages";
import { appendChatMessage, getChatMessages } from "@/lib/local-store";
import { ChatMarkdown } from "@/components/chat-markdown";
import type { ChatMessage } from "@/types/app";
import { useAuth, useUser } from "@clerk/react";
import { useEffect, useRef, useState } from "react";

type ConcernItem = { title: string; detail: string };

function formatAnalysisMarkdown(data: ContractAnalysisResult): string {
  const lines: string[] = [];
  lines.push("## Summary\n", data.executive_summary, "\n");
  const section = (title: string, items: ConcernItem[]) => {
    lines.push(`## ${title}\n`);
    if (!items.length) {
      lines.push("*No items identified in this category.*\n\n");
      return;
    }
    for (const it of items) {
      const t = (it.title ?? "").trim();
      const d = (it.detail ?? "").trim();
      if (t && d) {
        lines.push(`- **${t}** — ${d}\n`);
      } else if (t) {
        lines.push(`- **${t}**\n`);
      } else if (d) {
        lines.push(`- ${d}\n`);
      }
    }
    lines.push("\n");
  };
  section("Pain points", data.pain_points);
  section("Red flags", data.red_flags);
  section("Potential risks", data.potential_risks);
  return lines.join("\n");
}

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

export default function ContractAnalysisPage() {
  const { user, isLoaded } = useUser();
  const { getToken } = useAuth();
  const userId = user?.id;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("en");
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!userId) return;
    logActivityRemote(getToken, "visit_contract_analysis", "Opened contract analysis");
    setMessages(getChatMessages(userId, "contract"));
  }, [userId, getToken]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function onPickFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files ? Array.from(e.target.files) : [];
    setPendingFiles((prev) => [...prev, ...files]);
    e.target.value = "";
  }

  function removePending(i: number) {
    setPendingFiles((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function handleSend() {
    if (!userId || (!input.trim() && pendingFiles.length === 0) || sending)
      return;

    if (pendingFiles.length === 0) {
      setError("Please upload a contract file (PDF or text).");
      return;
    }

    setSending(true);
    setError(null);

    const file = pendingFiles[0];
    const attachments = [
      {
        name: file.name,
        size: file.size,
        type: file.type || "application/octet-stream",
      },
    ];

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim() || "(Contract upload)",
      languageCode: language,
      attachments,
      at: new Date().toISOString(),
    };

    let stored = appendChatMessage(userId, userMsg, { scope: "contract" });
    setMessages(stored);
    logActivityRemote(
      getToken,
      "document_upload",
      "Contract analysis upload",
      file.name,
    );

    const text = userMsg.content;
    setInput("");
    setPendingFiles([]);

    try {
      const data = await postContractAnalyze(
        file,
        text,
        language,
        () => getToken(),
      );
      const replyText = formatAnalysisMarkdown(data);
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: replyText,
        languageCode: language,
        at: new Date().toISOString(),
      };
      stored = appendChatMessage(userId, assistantMsg, { scope: "contract" });
      setMessages(stored);
      logActivityRemote(
        getToken,
        "chat_message",
        "Contract analysis completed",
        languageLabel(language),
      );
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "Contract analysis failed.";
      setError(msg);
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `**Error:** ${msg}`,
        languageCode: language,
        at: new Date().toISOString(),
      };
      stored = appendChatMessage(userId, assistantMsg, { scope: "contract" });
      setMessages(stored);
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
          Contract analysis
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Upload a contract (PDF or text). The assistant returns structured pain
          points, red flags, and risks via Agentic models.
        </p>
      </div>

      {error ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100">
          {error}
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
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.text,text/plain,application/pdf"
            className="hidden"
            onChange={onPickFiles}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-sm font-medium text-zinc-800 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
          >
            Upload contract
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {messages.length === 0 ? (
            <p className="py-12 text-center text-sm text-zinc-500 dark:text-zinc-400">
              Upload a contract and optionally add instructions for what to
              focus on.
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
            </ul>
          )}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={onFormSubmit}
          className="border-t border-zinc-100 p-4 dark:border-zinc-800"
        >
          <div className="mx-auto flex max-w-3xl flex-col gap-2 sm:flex-row sm:items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Optional: what should we focus on? (e.g. termination, liability, IP)"
              rows={2}
              className="min-h-[44px] flex-1 resize-y rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
            <button
              type="submit"
              disabled={sending}
              className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {sending ? "Analyzing…" : "Analyze"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
