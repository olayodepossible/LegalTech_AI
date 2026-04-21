"use client";

import { journeyProgress } from "@/lib/journey";
import { getActivities, logActivity } from "@/lib/local-store";
import type { Activity } from "@/types/app";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

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
  const [activities, setActivities] = useState<Activity[]>([]);

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

  const progress = useMemo(
    () => journeyProgress(activities),
    [activities],
  );

  const email = user?.primaryEmailAddress?.emailAddress ?? "—";
  const name =
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
          Recent actions stored in your browser for this demo.
        </p>
        {activities.length === 0 ? (
          <p className="mt-8 text-sm text-zinc-500 dark:text-zinc-400">
            No activity yet. Explore the chat or upload a document.
          </p>
        ) : (
          <ul className="mt-6 divide-y divide-zinc-100 dark:divide-zinc-800">
            {activities.map((a) => (
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
        )}
      </section>
    </div>
  );
}
