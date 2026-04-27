"use client";

import { getLegalChats, type LegalChatListItem } from "@/lib/api";
import { useAuth, useUser } from "@clerk/react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

type Props = {
  onNavigate?: () => void;
};

export function ChatSidebarHistory({ onNavigate }: Props) {
  const { user } = useUser();
  const { getToken } = useAuth();
  const pathname = usePathname() || "";
  const searchParams = useSearchParams();
  const currentSession = searchParams.get("session");
  const userId = user?.id;
  const [sessions, setSessions] = useState<LegalChatListItem[]>([]);

  const refresh = useCallback(async () => {
    if (!userId) {
      setSessions([]);
      return;
    }
    try {
      const rows = await getLegalChats(getToken);
      setSessions(rows);
    } catch {
      setSessions([]);
    }
  }, [userId, getToken]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onUpd = () => void refresh();
    window.addEventListener("legaltech-chats-updated", onUpd);
    return () => window.removeEventListener("legaltech-chats-updated", onUpd);
  }, [refresh]);

  if (!userId || sessions.length === 0) return null;

  return (
    <div className="mt-1 min-h-0 border-t border-zinc-100 pt-2 dark:border-zinc-800">
      <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-500">
        Recent chats
      </p>
      <ul
        className="flex max-h-52 flex-col gap-0.5 overflow-y-auto overscroll-contain"
        role="list"
      >
        {sessions.map((s) => {
          const href = `/chat?session=${encodeURIComponent(s.id)}`;
          const active =
            pathname === "/chat" && currentSession === s.id;
          return (
            <li key={s.id}>
              <Link
                href={href}
                onClick={onNavigate}
                className={[
                  "block min-w-0 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                  active
                    ? "bg-zinc-200/90 font-medium text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                    : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800/80",
                ].join(" ")}
                title={s.title}
              >
                <span className="line-clamp-2 break-words">{s.title}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
