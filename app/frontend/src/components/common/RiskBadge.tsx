import React from "react";
import { RiskLevel } from "../../types/conversation";

const STYLES: Record<string, string> = {
  LOW: "bg-ok-weak text-ok border-ok-line",
  MEDIUM: "bg-warn-weak text-warn border-warn-line",
  HIGH: "bg-warn-weak text-warn border-warn-line font-semibold",
  CRITICAL: "bg-danger-weak text-danger border-danger-line font-semibold",
};

export const RiskBadge: React.FC<{
  level: RiskLevel | string;
  showIcon?: boolean;
  size?: "sm" | "md";
}> = ({ level, size = "md" }) => {
  const key = String(level || "").toUpperCase();
  const pad = size === "sm" ? "px-1.5 py-px text-[11px]" : "px-2 py-0.5 text-xs";
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full border font-medium ${
        STYLES[key] || STYLES.LOW
      } ${pad}`}
    >
      {key === "CRITICAL" && <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-danger" />}
      {key === "HIGH" && <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-warn" />}
      {key || "LOW"} risk
    </span>
  );
};
