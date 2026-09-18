import React from "react";
import { SentimentType } from "../../types/conversation";

const STYLES: Record<string, string> = {
  POSITIVE: "bg-ok-weak text-ok border-ok-line",
  NEUTRAL: "bg-inset text-text-2 border-line",
  NEGATIVE: "bg-danger-weak text-danger border-danger-line",
};

const LABELS: Record<string, string> = {
  POSITIVE: "Positive",
  NEUTRAL: "Neutral",
  NEGATIVE: "Negative",
};

export const SentimentBadge: React.FC<{
  sentiment: SentimentType | string;
  showIcon?: boolean;
}> = ({ sentiment }) => {
  const key = String(sentiment || "").toUpperCase();
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
        STYLES[key] || STYLES.NEUTRAL
      }`}
    >
      {LABELS[key] || sentiment}
    </span>
  );
};
