import React from "react";
import { PriorityLevel } from "../../types/conversation";

const STYLES: Record<string, string> = {
  CRITICAL: "bg-danger-weak text-danger border-danger-line font-semibold",
  HIGH: "bg-warn-weak text-warn border-warn-line font-medium",
  MEDIUM: "bg-inset text-text-2 border-line",
  LOW: "bg-transparent text-text-3 border-line",
};

export const PriorityBadge: React.FC<{ priority: PriorityLevel | string }> = ({
  priority,
}) => {
  const key = String(priority || "").toUpperCase();
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${
        STYLES[key] || STYLES.MEDIUM
      }`}
    >
      {String(priority || "")}
    </span>
  );
};
