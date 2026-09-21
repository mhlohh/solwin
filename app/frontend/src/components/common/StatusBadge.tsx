import React from "react";
import { ConversationStatusType } from "../../types/conversation";

const STYLES: Record<string, string> = {
  OPEN: "bg-accent-weak text-accent border-accent-line",
  IN_PROGRESS: "bg-warn-weak text-warn border-warn-line",
  RESOLVED: "bg-ok-weak text-ok border-ok-line",
  CLOSED: "bg-inset text-text-2 border-line",
};

const LABELS: Record<string, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In progress",
  RESOLVED: "Resolved",
  CLOSED: "Closed",
};

export const StatusBadge: React.FC<{ status: ConversationStatusType | string }> = ({
  status,
}) => {
  const key = String(status || "").toUpperCase();
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
        STYLES[key] || STYLES.CLOSED
      }`}
    >
      {LABELS[key] || status}
    </span>
  );
};
