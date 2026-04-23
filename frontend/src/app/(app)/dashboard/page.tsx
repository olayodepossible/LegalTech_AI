"use client";

import {
  getActivityHistory,
  getOrCreateUser,
  type ActivityHistoryRow,
} from "@/lib/api";
import { journeyProgress } from "@/lib/journey";
import { getActivities, logActivity } from "@/lib/local-store";
import type { Activity } from "@/types/app";
import { useAuth, useUser } from "@clerk/nextjs";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

const ACTIVITY_PAGE_SIZE = 5;

type HistoryListItem = {
  id: string;
  label: string;
  detail?: string;
  at: string;
};

function mapApiRow(r: ActivityHistoryRow, i: number): HistoryListItem {
  return {
    id: String(r.id ?? `api-${i}`),
    label: (r.label ?? r.account_name ?? "Activity") as string,
    detail: (r.details ?? r.activity_type ?? undefined) as string | undefined,
    at: (r.created_at ?? r.activity_date ?? new Date().toISOString()) as string,
  };
}

function formatTime(iso: string) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function DashboardPage() {
  const { user, isLoaded } = useUser();
  const { getToken } = useAuth();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [activityPage, setActivityPage] = useState(1);
  const [apiUser, setApiUser] = useState<Record<string, unknown> | null>(null);
  const [apiHistory, setApiHistory] = useState<
    ActivityHistoryRow[] | "pending" | "unavailable"
  >("pending");

  useEffect(() => {
    if (!isLoaded || !user?.id) return;
    const acts = getActivities(user.id);
    if (!acts.some((a) => a.type === "login")) {
      logActivity(user.id, "signup", "Account ready");
      logActivity(user.id, "login", "Signed in with Clerk");
    }
    logActivity(user.id, "visit_dashboard", "Opened dashboard");
    setActivities(getActivities(user.id));
  }, [isLoaded, user?.id]);

  useEffect(() => {
    if (!isLoaded || !user?.id) return;
    let cancelled = false;
    (async () => {
      const token = () => getToken();
      try {
        const [u, hist] = await Promise.all([
          getOrCreateUser(token),
          getActivityHistory(token),
        ]);
        if (cancelled) return;
        setApiUser(u.user);
        setApiHistory(hist);
      } catch {
        if (!cancelled) setApiHistory("unavailable");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isLoaded, user?.id, getToken]);

  const historyRows: HistoryListItem[] = useMemo(() => {
    if (apiHistory === "pending" || apiHistory === "unavailable") {
      return activities.map((a) => ({
        id: a.id,
        label: a.label,
        detail: a.detail,
        at: a.at,
      }));
    }
    return apiHistory.map(mapApiRow);
  }, [apiHistory, activities]);

  const activityTotalPages = Math.max(
    1,
    Math.ceil(historyRows.length / ACTIVITY_PAGE_SIZE),
  );

  useEffect(() => {
    setActivityPage((p) => Math.min(p, activityTotalPages));
  }, [historyRows.length, activityTotalPages]);

  const pagedActivities = useMemo(() => {
    const start = (activityPage - 1) * ACTIVITY_PAGE_SIZE;
    return historyRows.slice(start, start + ACTIVITY_PAGE_SIZE);
  }, [historyRows, activityPage]);

  const rangeStart =
    historyRows.length === 0
      ? 0
      : (activityPage - 1) * ACTIVITY_PAGE_SIZE + 1;
  const rangeEnd = Math.min(
    activityPage * ACTIVITY_PAGE_SIZE,
    historyRows.length,
  );

  const progress = useMemo(
    () => journeyProgress(activities),
    [activities],
  );

  const email =
    (typeof apiUser?.email === "string" && apiUser.email) ||
    user?.primaryEmailAddress?.emailAddress ||
    "—";
  const name =
    (typeof apiUser?.display_name === "string" && apiUser.display_name) ||
    user?.fullName ||
    user?.firstName ||
    user?.primaryEmailAddress?.emailAddress ||
    "—";
  const memberSince = user?.createdAt
    ? formatTime(user.createdAt.toISOString())
    : null;

  if (!isLoaded || !user) return null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Your onboarding journey and recent activity in LegalTech AI.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">
            Your journey
          </h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            {progress.completed} of {progress.total} milestones completed
          </p>
          <ul className="mt-6 space-y-4">
            {progress.steps.map(({ step, done }) => (
              <li key={step.id} className="flex gap-3">
                <span
                  className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                    done
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                      : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500"
                  }`}
                  aria-hidden
                >
                  {done ? "✓" : ""}
                </span>
                <div>
                  <p className="font-medium text-zinc-900 dark:text-zinc-100">
                    {step.title}
                  </p>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">
                    {step.description}
                  </p>
                </div>
              </li>
            ))}
          </ul>
          <Link
            href="/chat"
            className="mt-6 inline-flex rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            Open chat
          </Link>
        </section>

        <section className="rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">
            Account
          </h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div>
              <dt className="text-zinc-500 dark:text-zinc-400">Name</dt>
              <dd className="font-medium text-zinc-900 dark:text-zinc-100">
                {name}
              </dd>
            </div>
            <div>
              <dt className="text-zinc-500 dark:text-zinc-400">Email</dt>
              <dd className="font-medium text-zinc-900 dark:text-zinc-100">
                {email}
              </dd>
            </div>
            {memberSince ? (
              <div>
                <dt className="text-zinc-500 dark:text-zinc-400">Member since</dt>
                <dd className="font-medium text-zinc-900 dark:text-zinc-100">
                  {memberSince}
                </dd>
              </div>
            ) : null}
          </dl>
        </section>
      </div>

      <section className="rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">
          Activity history
        </h2>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          {Array.isArray(apiHistory)
            ? "Synced from your account."
            : "Recent actions in your browser; server history when the API is available."}
        </p>
        {historyRows.length === 0 ? (
          <p className="mt-8 text-sm text-zinc-500 dark:text-zinc-400">
            No activity yet. Explore the chat or upload a document.
          </p>
        ) : (
          <>
            <ul className="mt-6 divide-y divide-zinc-100 dark:divide-zinc-800">
              {pagedActivities.map((a) => (
                <li
                  key={a.id}
                  className="flex flex-col gap-1 py-4 first:pt-0 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="font-medium text-zinc-900 dark:text-zinc-100">
                      {a.label}
                    </p>
                    {a.detail ? (
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">
                        {a.detail}
                      </p>
                    ) : null}
                  </div>
                  <time
                    className="shrink-0 text-xs text-zinc-400 dark:text-zinc-500"
                    dateTime={a.at}
                  >
                    {formatTime(a.at)}
                  </time>
                </li>
              ))}
            </ul>
            <div className="mt-4 flex flex-col gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                Showing {rangeStart}–{rangeEnd} of {historyRows.length}
                {activityTotalPages > 1
                  ? ` · Page ${activityPage} of ${activityTotalPages}`
                  : null}
              </p>
              {activityTotalPages > 1 ? (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={activityPage <= 1}
                    onClick={() => setActivityPage((p) => Math.max(1, p - 1))}
                    className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm font-medium text-zinc-800 enabled:hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:enabled:hover:bg-zinc-800"
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    disabled={activityPage >= activityTotalPages}
                    onClick={() =>
                      setActivityPage((p) =>
                        Math.min(activityTotalPages, p + 1),
                      )
                    }
                    className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm font-medium text-zinc-800 enabled:hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:enabled:hover:bg-zinc-800"
                  >
                    Next
                  </button>
                </div>
              ) : null}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
