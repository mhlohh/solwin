import React from "react";

type Tone = "neutral" | "ok" | "warn" | "danger";

interface KpiCardProps {
  label: string;
  value: string | number;
  /** Short factual context, e.g. "2 open" */
  detail?: string;
  tone?: Tone;
}

const TONES: Record<Tone, { value: string; label: string; bar: string }> = {
  neutral: { value: "text-text-1", label: "text-text-2", bar: "bg-line-strong" },
  ok: { value: "text-ok", label: "text-ok", bar: "bg-ok" },
  warn: { value: "text-warn", label: "text-warn", bar: "bg-warn" },
  danger: { value: "text-danger", label: "text-danger", bar: "bg-danger" },
};

export const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  detail,
  tone = "neutral",
}) => {
  const t = TONES[tone];
  return (
    <div className="surface-card px-4 py-3.5">
      <div className={`section-label ${t.label}`}>{label}</div>
      <div className={`mt-1 text-[26px] leading-none font-semibold tabular-nums ${t.value}`}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      {detail && <div className="mt-1.5 text-xs text-text-2">{detail}</div>}
    </div>
  );
};
