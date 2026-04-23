export type ActivityType =
  | "signup"
  | "login"
  | "logout"
  | "visit_dashboard"
  | "visit_chat"
  | "visit_contract_analysis"
  | "visit_rag"
  | "chat_message"
  | "document_upload";

export type Activity = {
  id: string;
  type: ActivityType;
  label: string;
  detail?: string;
  at: string;
};

export type ChatAttachment = {
  name: string;
  size: number;
  type: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  languageCode: string;
  attachments?: ChatAttachment[];
  at: string;
};

export type JourneyStepId =
  | "account"
  | "first_login"
  | "dashboard"
  | "chat"
  | "document";

export type JourneyStep = {
  id: JourneyStepId;
  title: string;
  description: string;
  completedWhen: (activities: Activity[]) => boolean;
};
