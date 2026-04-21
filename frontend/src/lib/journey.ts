import type { Activity, JourneyStep } from "@/types/app";

export const JOURNEY_STEPS: JourneyStep[] = [
  {
    id: "account",
    title: "Create your account",
    description: "Sign up to access the legal workspace.",
    completedWhen: (a) => a.some((x) => x.type === "signup"),
  },
  {
    id: "first_login",
    title: "Sign in",
    description: "Log in securely to sync your history.",
    completedWhen: (a) => a.some((x) => x.type === "login"),
  },
  {
    id: "dashboard",
    title: "Review your workspace",
    description: "Open the dashboard to see journey and activity.",
    completedWhen: (a) => a.some((x) => x.type === "visit_dashboard"),
  },
  {
    id: "chat",
    title: "Start legal assistance",
    description: "Ask questions in the AI chat.",
    completedWhen: (a) => a.some((x) => x.type === "chat_message"),
  },
  {
    id: "document",
    title: "Upload a document",
    description: "Attach contracts or briefs for context-aware answers.",
    completedWhen: (a) => a.some((x) => x.type === "document_upload"),
  },
];

export function journeyProgress(activities: Activity[]): {
  completed: number;
  total: number;
  steps: { step: JourneyStep; done: boolean }[];
} {
  const steps = JOURNEY_STEPS.map((step) => ({
    step,
    done: step.completedWhen(activities),
  }));
  const completed = steps.filter((s) => s.done).length;
  return { completed, total: steps.length, steps };
}
